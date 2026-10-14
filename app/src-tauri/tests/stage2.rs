//! Aşama 2 (SPEC_APP §7) Rust tarafı: U7, U9, U10, U11 (kod), U36 (yükleme), U40 (şerit), U27'nin
//! yol koruması, U32 git beyaz listesi. Ayrıca vitest'in render fixture'larını Rust komutlarının
//! GERÇEK çıktısından üretir ve güncelliğini sınar (ön uç testleri elle yazılmış sayı kullanmaz):
//!
//!   BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage2   # app/tests/fixtures/ui/*.json yeniden yazılır
mod fixture_cmp;

use borsai_app_lib::commands::ceiling::{ceiling_display_value, streak_view_in, SVector};
use borsai_app_lib::commands::git::{git_command, git_readonly, GIT_NOT_ALLOWED};
use borsai_app_lib::commands::models::app_info_value;
use borsai_app_lib::commands::path::{path_display_value, PathOutputArg};
use borsai_app_lib::commands::predict::{predict_all_value, F6Arg};
use borsai_app_lib::commands::config::is_within;
use borsai_app_lib::commands::scenario::{
    export_all_scenarios_in, export_scenario_in, list_scenarios_in, load_scenario_in, pretty, save_scenario_in, scenarios_dir,
    F6Doc, ObservedStreakUser, SaveScenarioReq, SCENARIO_PATH_INSIDE_REPO,
};
use borsai_app_lib::commands::scores::score_hints_from;
use borsai_app_lib::embedded;
use borsai_app_lib::state::AppState;
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

fn app_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").canonicalize().unwrap()
}

fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

fn tmp_dir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("borsai_stage2_{name}_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d.canonicalize().unwrap()
}

/// Fixture ya yazılır (BORSAI_UPDATE_UI_FIXTURES=1) ya da diskteki ile birebir karşılaştırılır.
fn fixture(name: &str, v: &Value) {
    fixture_opt(name, v, true)
}

/// `compare = false`: repo ile değişen girdiden (scores.json) üretilen anlık görüntü; yalnız varlığı sınanır.
fn fixture_opt(name: &str, v: &Value, compare: bool) {
    let path = app_dir().join("tests").join("fixtures").join("ui").join(name);
    let text = pretty(v);
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&path, &text).unwrap();
        return;
    }
    let disk = std::fs::read_to_string(&path).unwrap_or_default();
    if !compare {
        assert!(!disk.is_empty(), "{} yok", path.display());
        return;
    }
    // FAZ9_WINDOWS K-WIN-5: macOS'ta bayt bayt (bit-eşitlik); öbür sistemlerde yapı/metin birebir, sayılar 1e-9 (fixture_cmp)
    if cfg!(target_os = "macos") {
        assert!(
            disk == text,
            "{} güncel değil; BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage2 ile yeniden üretin",
            path.display()
        );
    } else {
        fixture_cmp::assert_close(name, &disk, &text, "BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage2 ile yeniden üretin");
    }
}

/// K-WIN-5: macOS dışı fikstür karşılaştırıcısının kuralları (her sistemde koşar): tolerans içi sayı farkı kabul ve kayıt;
/// tolerans dışı sayı, metin, anahtar, uzunluk, tamsayı ve tür farkı KIRMIZI.
#[test]
fn fixture_cmp_rules() {
    let base = r#"{"a": 0.216, "b": [1, "x", null, true], "c": {"d": 1.5}}"#;
    let ok = fixture_cmp::compare(base, r#"{"a": 0.21599999999999997, "b": [1, "x", null, true], "c": {"d": 1.5}}"#);
    assert!(ok.errors.is_empty() && ok.numeric.len() == 1 && ok.numeric[0].starts_with("/a: 0.216 → 0.21599999999999997"), "{:?}", ok.numeric);
    for (bad, why) in [
        (r#"{"a": 0.2161, "b": [1, "x", null, true], "c": {"d": 1.5}}"#, "tolerans dışı"),
        (r#"{"a": 0.216, "b": [1, "y", null, true], "c": {"d": 1.5}}"#, "metin"),
        (r#"{"a": 0.216, "b": [2, "x", null, true], "c": {"d": 1.5}}"#, "tamsayı"),
        (r#"{"a": 0.216, "b": [1, "x", 0, true], "c": {"d": 1.5}}"#, "null ↔ sayı"),
        (r#"{"a": 0.216, "b": [1, "x", null], "c": {"d": 1.5}}"#, "uzunluk"),
        (r#"{"a": 0.216, "b": [1, "x", null, true], "c": {"e": 1.5}}"#, "anahtar"),
        (r#"{"b": [1, "x", null, true], "a": 0.216, "c": {"d": 1.5}}"#, "anahtar sırası"),
        (r#"{"a": 0.216, "b": [1, "x", null, true], "c": {"d": 1}}"#, "tür (kayan ↔ tamsayı)"),
        ("{", "JSON değil"),
    ] {
        assert!(!fixture_cmp::compare(base, bad).errors.is_empty(), "{why}");
    }
}

fn obj(v: Value) -> Map<String, Value> {
    v.as_object().unwrap().clone()
}

/// Sicil girdi belgesinden (salt okuma) 17 model girdisi — `borsai.registry.model_inputs` gibi.
fn registry_inputs(ticker: &str) -> Map<String, Value> {
    let doc: Value =
        serde_json::from_slice(&std::fs::read(repo_dir().join(format!("registry/inputs/{ticker}.json"))).unwrap()).unwrap();
    borsai_app_lib::commands::form::model_input_fields()
        .map(|f| (f.to_string(), doc["fields"][f]["value"].clone()))
        .collect()
}

fn record_f6(ticker: &str) -> F6Arg {
    let dir = repo_dir().join(format!("registry/records/{ticker}"));
    let mut files: Vec<_> = std::fs::read_dir(dir).unwrap().flatten().map(|e| e.path()).collect();
    files.sort();
    let rec: Value = serde_json::from_slice(&std::fs::read(&files[0]).unwrap()).unwrap();
    F6Arg { value: Some(rec["market20"]["f6"].clone()), refusal: None }
}

/// `t`: ilk işlem günü (TÜFE ayı T'den türetilir; EK 3 §3.3). Bağımsız durum: gömülü TÜFE tablosu.
fn runs(inputs: &Map<String, Value>, f6: &F6Arg, t: Option<&str>) -> Vec<Value> {
    predict_all_value(&AppState::from_embedded(), inputs, f6, t).unwrap()
}

/// Sicil girdi belgesinin ilk işlem günü (salt okuma).
fn registry_t(ticker: &str) -> String {
    let doc: Value =
        serde_json::from_slice(&std::fs::read(repo_dir().join(format!("registry/inputs/{ticker}.json"))).unwrap()).unwrap();
    doc["fields"]["first_trading_date"]["value"].as_str().unwrap().to_string()
}

fn by_id<'a>(runs: &'a [Value], id: &str) -> &'a Value {
    runs.iter().find(|r| r["model_id"] == json!(id)).unwrap()
}

fn s_vectors(runs: &[Value]) -> Vec<SVector> {
    runs.iter()
        .filter(|r| r["status"] == json!("PREDICTED") && (r["kind"] == json!("hazard") || r["kind"] == json!("km")))
        .map(|r| SVector { model_id: r["model_id"].as_str().unwrap().into(), s: serde_json::from_value(r["output"]["S"].clone()).unwrap() })
        .collect()
}

fn netgl() -> Map<String, Value> {
    registry_inputs("NETGL")
}

/// Tavan yolu çıktıları (`predict_all` sonucundan) → `path_display` girdisi.
fn path_args(runs: &[Value]) -> Vec<PathOutputArg> {
    runs.iter()
        .filter(|r| r["kind"] == json!("ceiling_path") && r["status"] == json!("PREDICTED"))
        .map(|r| PathOutputArg { model_id: r["model_id"].as_str().unwrap().into(), output: r["output"].clone() })
        .collect()
}

/// U7 → U63 (EK 3 §10.1) → P4: VEYAS girdileri (f3 boş) → 10 model F3_MISSING (v1 üçü ve (C) h99/pooled TÜFE'den önce),
/// 17 model tahmin (`pooled@INF`, (C) addsale ve @ZERO dahil).
#[test]
fn u7_veyas_four_refusals() {
    let inputs = registry_inputs("VEYAS");
    assert!(inputs["total_demand_multiple"].is_null());
    let r = runs(&inputs, &record_f6("VEYAS"), Some(&registry_t("VEYAS")));
    let refused: Vec<&str> =
        r.iter().filter(|x| x["status"] == json!("REFUSED")).map(|x| x["model_id"].as_str().unwrap()).collect();
    assert_eq!(
        refused,
        [
            "v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0", "ceiling_path_v0", "ceiling_hazard_v1_clip",
            "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "fall_d10_v0_h99", "fall_d10_v0_pooled"
        ]
    );
    for x in r.iter().filter(|x| x["status"] == json!("REFUSED")) {
        assert_eq!((x["refusal"]["code"].as_str(), x["refusal"]["field"].as_str()), (Some("F3_MISSING"), Some("total_demand_multiple")));
    }
    assert_eq!(r.iter().filter(|x| x["status"] == json!("PREDICTED")).count(), 17);
    assert_eq!(by_id(&r, "ceiling_hazard_v1_pooled@INF")["status"], json!("PREDICTED"));
    assert_eq!(by_id(&r, "fall_d10_v0_addsale")["status"], json!("PREDICTED"));
    assert_eq!(by_id(&r, "fall_d10_v0_pooled@ZERO")["status"], json!("PREDICTED"));
    fixture("runs_veyas.json", &Value::Array(r.clone()));
    let price = inputs["ipo_price_tl"].as_str();
    fixture("ceiling_veyas_j0.json", &serde_json::to_value(ceiling_display_value(&s_vectors(&r), 0, price).unwrap()).unwrap());
    // EK 2 §4.1 fiyat kuralı: medyan limit atomuysa C_h metni, değilse ≈ P × (1 + medyan)
    let disp = path_display_value(&path_args(&r));
    assert_eq!(disp.len(), 2, "VEYAS: ceiling_path_v0 RET, iki sütun dolu");
    let inf = disp.iter().find(|d| d.model_id == "ceiling_path_v0@INF").unwrap();
    assert_eq!(inf.ipo_price.as_deref(), Some("136"));
    assert_eq!(inf.c[0], "149.60");
    assert!(inf.cells[0].on_limit_path && inf.cells[0].c_text.as_deref() == Some("149.60"));
    assert!(!inf.cells[4].on_limit_path && inf.cells[4].approx_price.is_some(), "h = 5'te medyan limit atomu değil");
    fixture("path_display_veyas.json", &serde_json::to_value(&disp).unwrap());
}

/// EK 2 §4.1/§4.2: `POST_BREAK_INSUFFICIENT` hücresi "—" gösterilir. Yamalı parametre: hücreler boş.
#[test]
fn path_post_break_insufficient_fixture() {
    let state = AppState::from_embedded();
    let models = &state.models.as_ref().unwrap().models;
    let m = models.iter().find(|x| x.model_id == "ceiling_path_v0@INF").expect("gömülü model");
    let mut params = m.params.clone();
    for g in ["Z", "B"] {
        let n = if g == "Z" { 10 } else { 9 };
        for i in 1..=n {
            params["post_break"]["cells"][g][i.to_string()] = json!([]);
        }
    }
    let run = borsai_predict::run_model(&params, &netgl());
    let out = run.output.as_ref().map(borsai_predict::Output::to_json).expect("çıktı");
    for h in 1..=10 {
        assert_eq!(out[format!("D{h}")]["post_break"]["status"], json!("POST_BREAK_INSUFFICIENT"));
        assert!(out[format!("D{h}")]["return"].is_null(), "getiri/kuantil üretilmez");
    }
    assert!(out["S"].is_array(), "S ve P_L yine vardır");
    let cell = json!({"model_id": "ceiling_path_v0@INF", "params_sha256": m.params_sha256, "kind": "ceiling_path",
                      "status": run.status, "refusal": Value::Null, "output": out.clone()});
    fixture("runs_path_insufficient.json", &Value::Array(vec![cell]));
    let disp = path_display_value(&[PathOutputArg { model_id: "ceiling_path_v0@INF".into(), output: out }]);
    assert!(disp[0].cells.iter().all(|c| !c.on_limit_path && c.approx_price.is_none()));
    fixture("path_display_insufficient.json", &serde_json::to_value(&disp).unwrap());
}

/// U9: f6 yok / bayat → yalnız v1_5_market20_v0 RET (MARKET20_NOT_PROVIDED / MARKET20_STALE_S0); diğer 18 model aynı.
#[test]
fn u9_f6_missing_and_stale() {
    let t = registry_t("NETGL");
    let base = runs(&netgl(), &record_f6("NETGL"), Some(&t));
    let missing = runs(&netgl(), &F6Arg::default(), Some(&t));
    let stale = runs(&netgl(), &F6Arg { value: None, refusal: Some("STALE_S0".into()) }, Some(&t));
    for (r, code) in [(&missing, "MARKET20_NOT_PROVIDED"), (&stale, "MARKET20_STALE_S0")] {
        let m = by_id(r, "v1_5_market20_v0");
        assert_eq!((m["status"].as_str(), m["refusal"]["code"].as_str()), (Some("REFUSED"), Some(code)));
        assert_eq!(m["refusal"]["field"], json!("f6_market20"));
        for (a, b) in base.iter().zip(r.iter()).filter(|(a, _)| a["model_id"] != json!("v1_5_market20_v0")) {
            assert_eq!(a, b, "{} f6'dan etkilenmemeli", a["model_id"]);
        }
    }
    fixture("runs_f6_missing.json", &Value::Array(missing));
    fixture("runs_f6_stale.json", &Value::Array(stale));
}

/// U10: kırpma — `return` fiziksel sınırda, `return_unclipped` ham, `return_clipped` yön.
#[test]
fn u10_clipping() {
    let line = std::fs::read_to_string(app_dir().join("parity/golden/v1_5_h99.jsonl")).unwrap();
    let case: Value = serde_json::from_str(line.lines().nth(1).unwrap()).unwrap();
    assert_eq!(case["case_id"], json!("v1_5_h99/0001"));
    let f6 = F6Arg { value: Some(case["extra"]["f6_market20"].clone()), refusal: None };
    let r = runs(case["inputs"].as_object().unwrap(), &f6, None);
    let d1 = &by_id(&r, "v1_5_h99")["output"]["D1"];
    assert_eq!(d1["return_clipped"], json!("UPPER"));
    assert_eq!(d1["return"], json!(0.1), "D1 üst sınır +%10");
    assert!(d1["return_unclipped"].as_f64().unwrap() > 0.1);
    let w = by_id(&r, "v1_5_h99")["output"]["warnings"].as_array().unwrap().clone();
    assert!(w.iter().any(|x| x["code"] == json!("RETURN_CLIPPED_TO_PHYSICAL_BOUND") && x["horizon"] == json!("D1")));
    fixture("runs_clipped.json", &Value::Array(r));
}

/// U11: OUT_OF_TRAINING_RANGE + F4_ZERO + PB4 aynı girdide; 16 modelin hepsi tahmin verir.
#[test]
fn u11_warnings_do_not_hide() {
    let mut i = netgl();
    i.insert("capital_increase_shares".into(), json!("0"));
    i.insert("existing_share_sale_shares".into(), json!("87500000"));
    i.insert("total_demand_multiple".into(), json!("500"));
    i.insert("planned_additional_sale_ceiling".into(), json!("12500000"));
    i.insert("planned_max_offer_shares".into(), json!("100000000"));
    let r = runs(&i, &record_f6("NETGL"), Some(&registry_t("NETGL")));
    assert!(r.iter().all(|x| x["status"] == json!("PREDICTED")), "{r:?}");
    let codes: Vec<String> = r
        .iter()
        .flat_map(|x| x["output"]["warnings"].as_array().unwrap().iter().map(|w| w["code"].as_str().unwrap().to_string()))
        .collect();
    for c in ["OUT_OF_TRAINING_RANGE", "F4_ZERO_NO_TRAINING_EXAMPLE", "PB4_ADDITIONAL_SALE_CEILING"] {
        assert!(codes.iter().any(|x| x == c), "{c} yok");
    }
    fixture("runs_warnings.json", &Value::Array(r));
}

fn outcomes(case: &str) -> PathBuf {
    app_dir().join("tests/fixtures/outcomes").join(case)
}

/// U40: şerit ve tanımsızlık (sentetik SNTA1). Resmi j yalnız dosyadan gelir; `streak_view_in`
/// imzasında beyan parametresi yoktur (U52-5), beyan bir etikettir ve ön uçta durur.
#[test]
fn u40_streak_and_undefined() {
    let v = streak_view_in(Some(&outcomes("pending")), Some("SNTA1")).unwrap();
    assert_eq!((v.j_observed, v.broken, v.unlabeled, v.file_status), (Some(3), false, false, "FOUND"));
    assert_eq!(v.as_of.as_deref(), Some("2030-01-09"));
    let states: Vec<_> = v.days.iter().map(|d| d.file.clone().unwrap()).collect();
    assert_eq!(&states[..4], ["CEILING", "CEILING", "CEILING", "PENDING"]);
    fixture("streak_pending.json", &serde_json::to_value(&v).unwrap());

    let b = streak_view_in(Some(&outcomes("broken")), Some("SNTA1")).unwrap();
    assert_eq!((b.j_observed, b.broken), (Some(2), true), "D3'te bozuldu: L = 2 (D4'teki tavan sayılmaz)");
    fixture("streak_broken.json", &serde_json::to_value(&b).unwrap());

    let n = streak_view_in(Some(&outcomes("na_limit")), Some("SNTA1")).unwrap();
    assert_eq!((n.j_observed, n.unlabeled, n.days[1].file.as_deref()), (Some(1), true, Some("NO_LABEL")));
    fixture("streak_na_limit.json", &serde_json::to_value(&n).unwrap());

    let a = streak_view_in(Some(&outcomes("all10")), Some("SNTA1")).unwrap();
    assert_eq!(a.j_observed, Some(10));
    fixture("streak_all10.json", &serde_json::to_value(&a).unwrap());

    // U52 fixture'ları: SNTB1 (D1–D2 tavan, D3 PENDING → resmi j = 2) ve pozitif kontrol (D3 tavan → j = 3)
    let b1 = streak_view_in(Some(&outcomes("sntb1")), Some("SNTB1")).unwrap();
    assert_eq!((b1.j_observed, b1.broken, b1.days[2].file.as_deref()), (Some(2), false, Some("PENDING")));
    fixture("streak_sntb1.json", &serde_json::to_value(&b1).unwrap());
    let b1ok = streak_view_in(Some(&outcomes("sntb1_ok")), Some("SNTB1")).unwrap();
    assert_eq!((b1ok.j_observed, b1ok.days[2].file.as_deref()), (Some(3), Some("CEILING")));
    fixture("streak_sntb1_ok.json", &serde_json::to_value(&b1ok).unwrap());

    // dosya yok / repo yok: beyan artık j üretmez (U52), dosya yoksa j_observed null
    let m = streak_view_in(Some(&outcomes("pending")), Some("SNTB2")).unwrap();
    assert_eq!((m.file_status, m.j_observed), ("MISSING", None));
    fixture("streak_missing.json", &serde_json::to_value(&m).unwrap());
    let no_repo = streak_view_in(None, None).unwrap();
    assert_eq!((no_repo.file_status, no_repo.j_observed), ("NO_REPO", None));
    assert!(streak_view_in(None, Some("../x")).is_err(), "yol parçası olarak güvensiz arz kodu");

    // koşullu: NETGL S vektörleri, j = 2 (resmi) ve j = 3 (U52'de yasak küme); j = 10 ve S_j = 0 → tanımsız
    let r = runs(&netgl(), &record_f6("NETGL"), Some(&registry_t("NETGL")));
    // U63: NETGL T = 2026-09-17 → TÜFE 2026-07 = 132.31; real ve pooled dolu
    for id in ["ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"] {
        assert_eq!(by_id(&r, id)["status"], json!("PREDICTED"), "{id}");
        assert_eq!(by_id(&r, id)["output"]["tufe_index_used"], json!("132.31"), "{id}");
    }
    let sv = s_vectors(&r);
    fixture("runs_netgl.json", &Value::Array(r.clone()));
    fixture("path_display_netgl.json", &serde_json::to_value(path_display_value(&path_args(&r))).unwrap());
    fixture("ceiling_netgl_j0.json", &serde_json::to_value(ceiling_display_value(&sv, 0, Some("25.52")).unwrap()).unwrap());
    fixture("ceiling_netgl_j2.json", &serde_json::to_value(ceiling_display_value(&sv, 2, Some("25.52")).unwrap()).unwrap());
    fixture("ceiling_netgl_j3.json", &serde_json::to_value(ceiling_display_value(&sv, 3, Some("25.52")).unwrap()).unwrap());
    let j10 = ceiling_display_value(&sv, 10, None).unwrap();
    assert!(j10.rows.iter().all(|x| x.cond.is_none()));
    fixture("ceiling_netgl_j10.json", &serde_json::to_value(&j10).unwrap());
    let zero = vec![SVector { model_id: "base_km_expanding".into(), s: vec![0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }];
    let z = ceiling_display_value(&zero, 2, None).unwrap();
    assert!(z.rows[0].cond.is_none() && z.rows[1].cond.is_some(), "S_j = 0 → tanımsız; her zaman tavan tanımlı");
    fixture("ceiling_zero_sj.json", &serde_json::to_value(&z).unwrap());
}

/// U52-5: koşullu hesap yapan Rust komutlarının imzasında beyan parametresi YOKTUR. Tarama,
/// adında `conditional` / `streak` / `ceiling` (`path_conditional` dahil, P2'de gelince) geçen her
/// `pub fn`'in parametre listesini denetler; ayrıca `user_days` hiçbir Rust kaynağında geçmez.
#[test]
fn conditional_commands_take_no_declaration() {
    fn walk(p: &Path, out: &mut Vec<PathBuf>) {
        for e in std::fs::read_dir(p).expect("src").flatten() {
            let path = e.path();
            if path.is_dir() {
                walk(&path, out);
            } else if path.extension().is_some_and(|x| x == "rs") {
                out.push(path);
            }
        }
    }
    let roots = [
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("crates/borsai_predict/src"),
    ];
    let mut files = Vec::new();
    for r in &roots {
        walk(r, &mut files);
    }
    let banned = ["user_days", "declar", "observed_streak_user", "user_day"];
    let mut checked = 0usize;
    for f in &files {
        let text = std::fs::read_to_string(f).unwrap();
        for b in banned {
            assert!(!text.contains(b) || f.ends_with("scenario.rs"), "{}: {b} geçmemeli", f.display());
        }
        for (at, _) in text.match_indices("pub fn ") {
            let rest = &text[at + "pub fn ".len()..];
            let open = rest.find('(').expect("imza");
            let name = &rest[..open];
            let lname = name.to_lowercase();
            if !(lname.contains("conditional") || lname.contains("streak") || lname.contains("ceiling")) {
                continue;
            }
            let sig = &rest[open..open + rest[open..].find(')').expect("imza sonu")];
            for b in banned {
                assert!(!sig.contains(b), "{name} imzasında {b}: {sig}");
            }
            checked += 1;
        }
    }
    assert!(checked >= 4, "beklenen imzalar taranmadı: {checked}");
}

fn save_req(title: &str) -> SaveScenarioReq {
    SaveScenarioReq {
        title: title.into(),
        stage: "POST_BOOKBUILD_PRE_LISTING".into(),
        ticker_label: Some("NETGL".into()),
        inputs: netgl(),
        input_dates: obj(json!({"first_trading_date": "2026-09-17"})),
        f6: F6Doc { value: record_f6("NETGL").value.and_then(|v| v.as_str().map(str::to_string)), origin: "MANUAL".into(), ..Default::default() },
        observed_streak_user: Some(ObservedStreakUser { ticker: Some("NETGL".into()), days: vec![Some("CEILING".into()), None] }),
    }
}

/// U36: farklı `models_index_sha256` ile kaydedilmiş senaryo `same_index = false` ile açılır; çıktı
/// dosyadaki gibidir (üzerine yazılmaz, yeniden hesaplanmaz). Ayrıca belge biçimi (§2.4).
#[test]
fn u36_scenario_other_index() {
    let data = tmp_dir("u36");
    let state = AppState::from_embedded();
    let saved = save_scenario_in(&state, &data, &[repo_dir()], &save_req("NETGL senaryo")).unwrap();
    let path = data.join("scenarios").join(format!("{}.json", saved.scenario_id));
    let mut doc: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(doc["schema_version"], json!("borsai.app_scenario/1"));
    assert_eq!(doc["official"], json!(false));
    assert!(doc.get("record_type").is_none(), "record_type anahtarı olmamalı (§2.4)");
    assert_eq!(doc["models_index_sha256"], json!(embedded::BUILD_INFO.index_sha256));
    assert_eq!(doc["outputs"].as_object().unwrap().len(), 27);
    // senaryo tahmini de TÜFE'yi T'den alır (EK 3 §3.3): NETGL T = 2026-09-17 → 2026-07
    assert_eq!(doc["outputs"]["ceiling_hazard_v1_real"]["output"]["tufe_index_used"], json!("132.31"));
    assert_eq!(doc["observed_streak_user"]["days"][0], json!("CEILING"));
    let fresh = load_scenario_in(&data, &saved.scenario_id, embedded::BUILD_INFO.index_sha256).unwrap();
    assert!(fresh.same_index);

    // başka model kümesi: sha farklı ve çıktı kasten ayırt edici bir değerle
    doc["models_index_sha256"] = json!("0".repeat(64));
    doc["outputs"]["v1_5_h99"]["output"]["D1"]["return"] = json!(0.0123456789);
    std::fs::write(&path, pretty(&doc)).unwrap();
    let loaded = load_scenario_in(&data, &saved.scenario_id, embedded::BUILD_INFO.index_sha256).unwrap();
    assert!(!loaded.same_index);
    assert_eq!(loaded.doc, doc, "yüklenen çıktı dosyadakiyle birebir");
    assert_eq!(std::fs::read(&path).unwrap(), pretty(&doc).into_bytes(), "yükleme dosyaya yazmaz");
    let list = list_scenarios_in(&data, embedded::BUILD_INFO.index_sha256).unwrap();
    assert_eq!((list.len(), list[0].same_index, list[0].status), (1, false, "OK"));

    // sabit alanlarla fixture (kimlik/zaman/HEAD sabitlenir)
    let mut fx = loaded.doc.clone();
    fx["scenario_id"] = json!("01J0000000000000000000FXTR");
    fx["created_at_local"] = json!("2026-09-22T10:00:00+03:00");
    fx["build_git_head"] = json!("FIXTURE");
    fixture("scenario_other_index.json", &json!({"doc": fx, "same_index": false, "embedded_index_sha256": "FIXTURE"}));

    // eski sürüm: listede OLD_VERSION, açılmaz
    doc["schema_version"] = json!("borsai.app_scenario/0");
    std::fs::write(&path, pretty(&doc)).unwrap();
    assert_eq!(list_scenarios_in(&data, "x").unwrap()[0].status, "OLD_VERSION");
    assert_eq!(load_scenario_in(&data, &saved.scenario_id, "x").unwrap_err().code, "SCENARIO_SCHEMA_UNSUPPORTED");
    let _ = std::fs::remove_dir_all(&data);
}

/// U27 (yol kısmı; tam betik aşama 3): repo altındaki uygulama verisine senaryo yazılmaz, dizin bile açılmaz.
#[test]
fn scenario_path_guard() {
    let repo = tmp_dir("guard_repo");
    let inside = repo.join("registry").join("records");
    let err = save_scenario_in(&AppState::from_embedded(), &inside, &[repo.clone()], &save_req("x")).unwrap_err();
    assert_eq!(err.code, SCENARIO_PATH_INSIDE_REPO);
    assert!(!inside.exists(), "repo altında dizin oluşturulmamalı");
    // sembolik bağla repo'ya yönlenen uygulama verisi de reddedilir (bağ testleri yalnız unix; FAZ9_WINDOWS K-WIN-3:
    // Windows'ta bağ oluşturmak ayrıcalık ister)
    let outside = tmp_dir("guard_link");
    #[cfg(unix)]
    {
        let link = outside.join("appdata");
        std::os::unix::fs::symlink(&repo, &link).unwrap();
        assert_eq!(scenarios_dir(&link, &[repo.clone()]).unwrap_err().code, SCENARIO_PATH_INSIDE_REPO);
    }
    assert!(scenarios_dir(&outside.join("real"), &[repo.clone()]).is_ok());
    // dışa aktarma da repo altına yapılamaz
    let data = tmp_dir("guard_data");
    let saved = save_scenario_in(&AppState::from_embedded(), &data, &[repo.clone()], &save_req("x")).unwrap();
    let target = repo.join("registry").join("kacak.json");
    assert_eq!(
        export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, &target).unwrap_err().code,
        SCENARIO_PATH_INSIDE_REPO
    );
    assert!(!target.exists(), "repo altına dosya yazılmamalı");
    assert!(export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, &outside.join("disari.json")).is_ok());

    #[cfg(unix)]
    {
        // B1: sembolik bağ ve `..` hedefleri. Bağların hedefi repo altında ve henüz YOK (askıda bağ):
        // bağ izlenirse kişisel kayıt sicile düşer. Tekli, toplu dışa aktarma ve kaydetme aynı bekçiden geçer.
        let records = repo.join("registry").join("records");
        std::fs::create_dir_all(&records).unwrap();
        let repo_before = file_listing(&repo);
        let dangling_file = outside.join("askida_bag.json");
        std::os::unix::fs::symlink(records.join("kacak_bag.json"), &dangling_file).unwrap();
        let dangling_dir = outside.join("askida_dizin");
        std::os::unix::fs::symlink(repo.join("registry").join("yeni_dizin"), &dangling_dir).unwrap();
        let dir_link = outside.join("repo_bagi");
        std::os::unix::fs::symlink(&repo, &dir_link).unwrap();
        let hostile: Vec<(&str, PathBuf)> = vec![
            ("askıda dosya bağı", dangling_file.clone()),
            ("askıda dizin bağı", dangling_dir.join("kacak.json")),
            ("dizin bağı", dir_link.join("registry").join("records").join("kacak_dizin.json")),
            ("var olmayan ara dizinli ..", dir_link.join("registry").join("yok").join("..").join("records").join("kacak_nokta.json")),
            ("repo içinde var olmayan ara dizinli ..", records.join("yok").join("..").join("kacak_nokta2.json")),
        ];
        // Bütün vakalar koşar, sapmalar birlikte raporlanır.
        let mut bad: Vec<String> = Vec::new();
        let code = |r: Result<String, String>| r.map(|_| "Ok".to_string()).unwrap_or_else(|c| c);
        for (name, t) in &hostile {
            if !is_within(t, &repo) {
                bad.push(format!("is_within[{name}] = false"));
            }
            let one = code(export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, t).map_err(|e| e.code));
            let all = code(export_all_scenarios_in(&data, &[repo.clone()], t).map(|r| r.path).map_err(|e| e.code));
            for (what, got) in [("tekli dışa aktarma", one), ("toplu dışa aktarma", all)] {
                if got != SCENARIO_PATH_INSIDE_REPO {
                    bad.push(format!("{what}[{name}] -> {got}"));
                }
            }
        }
        // kaydetme: uygulama verisi (ya da scenarios/) askıda bir bağla repo altına yönleniyor
        let data_link = outside.join("appdata_askida");
        std::os::unix::fs::symlink(repo.join("appdata"), &data_link).unwrap();
        let data_scen = outside.join("appdata_scen");
        std::fs::create_dir_all(&data_scen).unwrap();
        std::os::unix::fs::symlink(records.join("SNTX"), data_scen.join("scenarios")).unwrap();
        for (name, d) in [
            ("askıda uygulama verisi bağı", data_link.clone()),
            ("askıda scenarios bağı", data_scen.clone()),
            ("var olmayan ara dizinli ..", dir_link.join("yok").join("..").join("appdata")),
        ] {
            let dir = code(scenarios_dir(&d, &[repo.clone()]).map(|p| p.display().to_string()).map_err(|e| e.code));
            let save = code(save_scenario_in(&AppState::from_embedded(), &d, &[repo.clone()], &save_req("x")).map(|s| s.scenario_id).map_err(|e| e.code));
            for (what, got) in [("scenarios_dir", dir), ("kaydetme", save)] {
                if got != SCENARIO_PATH_INSIDE_REPO {
                    bad.push(format!("{what}[{name}] -> {got}"));
                }
            }
        }
        let repo_after = file_listing(&repo);
        let appeared: Vec<&String> =
            repo_after.iter().filter(|x| !repo_before.contains(x)).map(|(p, _, _)| p).collect();
        if !appeared.is_empty() {
            bad.push(format!("repo ağacında yeni/değişen girdi: {appeared:?}"));
        }
        assert!(bad.is_empty(), "B1 yol bekçisi {} vakada açık:\n  {}", bad.len(), bad.join("\n  "));
        // repo dışını gösteren bağ da izlenmez: hedef sembolik bağsa yazılmaz (bağın hedefi oluşmaz)
        let elsewhere = outside.join("baska_yer.json");
        let link_out = outside.join("disari_bag.json");
        std::os::unix::fs::symlink(&elsewhere, &link_out).unwrap();
        let one = code(export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, &link_out).map_err(|e| e.code));
        let all = code(export_all_scenarios_in(&data, &[repo.clone()], &link_out).map(|r| r.path).map_err(|e| e.code));
        assert_eq!((one.as_str(), all.as_str(), elsewhere.exists()), ("INVALID_ARGUMENT", "INVALID_ARGUMENT", false), "bağ izlenmemeli");
    }
    // var olan normal dosyanın üzerine yazma bugünkü gibi sürer (dosya seçici onayı sonrası)
    let existing = outside.join("disari.json");
    std::fs::write(&existing, b"eski").unwrap();
    export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, &existing).expect("üzerine yazma");
    let src = std::fs::read(data.join("scenarios").join(format!("{}.json", saved.scenario_id))).unwrap();
    assert_eq!(std::fs::read(&existing).unwrap(), src);
    export_all_scenarios_in(&data, &[repo.clone()], &existing).expect("toplu üzerine yazma");
    assert!(std::fs::read_to_string(&existing).unwrap().starts_with('['));
    let _ = std::fs::remove_dir_all(&data);
    let _ = std::fs::remove_dir_all(&repo);
    let _ = std::fs::remove_dir_all(&outside);
}

/// Dizin ağacındaki her girdi (bağlar izlenmeden): göreli yol, tür ve içerik.
#[cfg(unix)]
fn file_listing(root: &Path) -> Vec<(String, String, Vec<u8>)> {
    fn walk(root: &Path, p: &Path, out: &mut Vec<(String, String, Vec<u8>)>) {
        let mut entries: Vec<_> = std::fs::read_dir(p).unwrap().flatten().map(|e| e.path()).collect();
        entries.sort();
        for path in entries {
            let rel = path.strip_prefix(root).unwrap().display().to_string();
            let meta = std::fs::symlink_metadata(&path).unwrap();
            if meta.file_type().is_symlink() {
                out.push((rel, "link".into(), std::fs::read_link(&path).unwrap().display().to_string().into_bytes()));
            } else if meta.is_dir() {
                out.push((rel, "dir".into(), Vec::new()));
                walk(root, &path, out);
            } else {
                out.push((rel, "file".into(), std::fs::read(&path).unwrap()));
            }
        }
    }
    let mut out = Vec::new();
    walk(root, root, &mut out);
    out
}

/// U32: git yalnız salt okuma alt komutlarıyla; `Command::new("git")` yalnız git.rs'de (ve build_embed.rs'de).
#[test]
fn git_readonly_whitelist() {
    let repo = repo_dir();
    for bad in ["commit", "push", "add", "tag", "-c", "reset", "checkout", ""] {
        assert_eq!(git_command(&repo, &[bad]).unwrap_err().code, GIT_NOT_ALLOWED, "{bad}");
    }
    assert_eq!(git_readonly(&repo, &["rev-parse", "--is-inside-work-tree"]).unwrap().trim(), "true");
    let src = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut offenders = Vec::new();
    fn walk(p: &Path, out: &mut Vec<PathBuf>) {
        for e in std::fs::read_dir(p).unwrap().flatten() {
            let path = e.path();
            if path.is_dir() {
                walk(&path, out);
            } else if path.extension().is_some_and(|x| x == "rs") {
                out.push(path);
            }
        }
    }
    let mut files = Vec::new();
    walk(&src, &mut files);
    for f in files {
        let text = std::fs::read_to_string(&f).unwrap();
        if text.contains("Command::new(\"git\")") && !f.ends_with("commands/git.rs") {
            offenders.push(f);
        }
    }
    assert!(offenders.is_empty(), "git çağrısı git.rs dışında: {offenders:?}");
}

/// Model kartı ve "backtest tipik hata" ipuçları için fixture'lar (gerçek gömülü dosyalardan).
#[test]
fn card_fixtures() {
    let info = app_info_value(&AppState::from_embedded());
    assert_eq!(info.models.len(), 27);
    assert!(info.models.iter().all(|m| m.description.is_some()));
    fixture("app_models.json", &serde_json::to_value(&info.models).unwrap());
    if let Some(text) = embedded::SCORES_JSON {
        let h = score_hints_from(text, "EMBEDDED", embedded::BUILD_INFO.index_sha256).unwrap();
        let mae = &h.models["v1_5_h99"]["mae"]["D1"];
        assert_eq!(mae["n"], json!(89));
        let mut v = serde_json::to_value(&h).unwrap();
        v["sha12"] = json!("FIXTURE");
        fixture_opt("score_hints.json", &v, false);
    }
}

/// §2.5: sürümü farklı ayar dosyası config.json.bak olarak saklanır; uygulama verisi repo altına
/// düşecek repo kökü reddedilir (U27'nin ayar kısmı).
#[test]
fn config_reset_and_data_dir_guard() {
    use borsai_app_lib::commands::config::{load_config, set_config_value, AppConfig, CONFIG_RESET, DATA_DIR_INSIDE_REPO};
    let data = tmp_dir("cfg");
    std::fs::write(data.join("config.json"), r#"{"schema_version":"borsai.app_config/0","repo_root":"/x"}"#).unwrap();
    let (cfg, note) = load_config(&data);
    assert_eq!((cfg, note.as_deref()), (AppConfig::default(), Some(CONFIG_RESET)));
    assert!(data.join("config.json.bak").is_file() && !data.join("config.json").exists());

    let repo = tmp_dir("cfg_repo");
    let inside = repo.join("appdata");
    std::fs::create_dir_all(&inside).unwrap();
    let state = AppState::from_embedded();
    state.attach_data_dir(&inside);
    let cfg = AppConfig { repo_root: Some(repo.display().to_string()), ..AppConfig::default() };
    assert_eq!(set_config_value(&state, cfg).unwrap_err().code, DATA_DIR_INSIDE_REPO);
    assert!(!inside.join("config.json").exists(), "reddedilen ayar yazılmaz");
    // repo'suz ayar kaydedilir ve geri okunur
    let saved = set_config_value(&state, AppConfig { scores_source: "EMBEDDED".into(), ..AppConfig::default() }).unwrap();
    assert!(!saved.repo_mode);
    assert_eq!(load_config(&inside).0.scores_source, "EMBEDDED");
    let _ = std::fs::remove_dir_all(&data);
    let _ = std::fs::remove_dir_all(&repo);
}

/// Sicil girdi belgesi salt okunur kopyalanır: VEYAS f3 boş ve missing_reason taşır.
#[test]
fn input_document_read_only() {
    use borsai_app_lib::commands::inputs_doc::{list_input_documents_in, read_input_document_in};
    let repo = repo_dir();
    let before = std::fs::read(repo.join("registry/inputs/VEYAS.json")).unwrap();
    let list = list_input_documents_in(&repo).unwrap();
    assert!(list.contains(&"VEYAS".to_string()) && list.contains(&"NETGL".to_string()));
    let d = read_input_document_in(&repo, "VEYAS").unwrap();
    assert!(d.values["total_demand_multiple"].is_null());
    assert!(d.missing_reasons["total_demand_multiple"].as_str().unwrap().contains("talep"));
    assert_eq!(d.values["ipo_price_tl"], json!("136"));
    assert_eq!(d.values.len(), 20);
    assert!(read_input_document_in(&repo, "../registry").is_err());
    assert_eq!(std::fs::read(repo.join("registry/inputs/VEYAS.json")).unwrap(), before);

    // B6 (U35, §2.5): desteklenmeyen sürüm → INPUTS_SCHEMA_UNSUPPORTED, hiçbir değer dönmez.
    // Asıl belgenin kopyası geçici repoda; yalnız schema_version değişir.
    let tmp = tmp_dir("inputs_v0");
    std::fs::create_dir_all(tmp.join("registry/inputs")).unwrap();
    let mut doc: Value = serde_json::from_slice(&before).unwrap();
    assert_eq!(doc["schema_version"], json!("borsai.inputs/1"));
    doc["schema_version"] = json!("borsai.inputs/0");
    std::fs::write(tmp.join("registry/inputs/VEYAS.json"), pretty(&doc)).unwrap();
    assert_eq!(list_input_documents_in(&tmp).unwrap(), vec!["VEYAS".to_string()], "listede durur");
    let err = read_input_document_in(&tmp, "VEYAS").map(|d| d.values.len()).unwrap_err();
    assert_eq!(err.code, "INPUTS_SCHEMA_UNSUPPORTED");
    assert!(err.message.contains("borsai.inputs/0"), "{}", err.message);
    let _ = std::fs::remove_dir_all(&tmp);
}

/// §3a.2: repo modunda f6 Python `borsai.market20`'den. T boş → t_unknown.
#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn market20_via_python_repo() {
    use borsai_app_lib::commands::market20::market20_value;
    let repo = PathBuf::from(std::env::var("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let data = tmp_dir("m20");
    let state = AppState::from_embedded().with_repo_for_tests(&data, &repo);
    let v = market20_value(&state, Some("2026-09-22".into()), None).unwrap();
    assert!(v.t_unknown);
    assert_eq!(v.record["ref_date"], json!("2026-09-22"));
    assert!(v.record["f6"].is_string() || v.record["refusal"].is_string(), "{}", v.record);
    let live = market20_value(&state, Some("2026-09-22".into()), Some("2026-10-30".into())).unwrap();
    assert_eq!(live.record["refusal"], json!("PREDICTION_TOO_EARLY"), "kural 5: T − tahmin tarihi > 12");
    assert_eq!(market20_value(&state, Some("22.09.2026".into()), None).unwrap_err().code, "INVALID_ARGUMENT");
    let no_repo = AppState::from_embedded();
    assert_eq!(market20_value(&no_repo, None, None).unwrap_err().code, "REPO_MODE_REQUIRED");
    let _ = std::fs::remove_dir_all(&data);
}

// ================================================================ EK 3 P1-D: zaman-dışı okuyucu, öne çıkarma, kart

mod d {
    pub use borsai_app_lib::commands::ceiling::{ceiling_summary_value, CeilingSummary, SummaryModel};
    pub use borsai_app_lib::commands::scores::{featured_ceiling, scores_doc};
    pub use borsai_app_lib::commands::scores_oot::{
        repo_parse_count, scores_oot_embedded, scores_oot_path_in, scores_oot_repo, scores_oot_value, strip_rows, ScoresOotDoc,
    };
}

fn real_oot() -> std::sync::Arc<d::ScoresOotDoc> {
    d::scores_oot_repo(&d::scores_oot_path_in(&repo_dir())).expect("scores/scores_oot.json var").expect("okunur")
}

fn real_scores() -> Value {
    serde_json::from_slice(&std::fs::read(repo_dir().join("scores/scores.json")).unwrap()).unwrap()
}

fn embedded_pairs() -> Vec<(String, String)> {
    let state = AppState::from_embedded();
    state.models.as_ref().unwrap().models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect()
}

/// K-P1-3: gerçek `scores_oot.json` bütünlükten geçer (kasa bloklarındaki SEALED kapalı satırlar meşru); repo modunda
/// dosya bir kez okunup önbelleğe alınır; gömülü süzülmüş kopyanın hücreleri ve sayaçları repo dosyasıyla BİREBİR
/// (orkestratör eki: satırlar ve retro listeleri gömülmez; kaynak sha256 ve not eklenir).
#[test]
fn scores_oot_reader_real_file() {
    let before = d::repo_parse_count();
    let a = real_oot();
    let b = real_oot();
    assert!(std::sync::Arc::ptr_eq(&a, &b), "ikinci okuma önbellekten");
    assert_eq!(d::repo_parse_count() - before <= 1, true, "dosya tahmin başına yeniden ayrıştırılmaz");
    assert!(a.unsupported_version.is_none());
    assert_eq!(a.integrity, None, "gerçek dosya bütünlükten geçer");
    assert!(a.vault_open && a.rows_present);
    // gömülü kopya: yalnız süzme
    let emb = d::scores_oot_embedded().expect("gömülü süzülmüş kopya");
    assert!(!emb.rows_present && emb.integrity.is_none());
    let raw = std::fs::read(d::scores_oot_path_in(&repo_dir())).unwrap();
    assert_eq!(emb.source_sha256.as_deref(), Some(borsai_app_lib::commands::models::sha256_hex(&raw).as_str()), "kaynak sha256");
    let full: Value = serde_json::from_slice(&raw).unwrap();
    let text = borsai_app_lib::embedded::SCORES_OOT_JSON.unwrap();
    let e: Value = serde_json::from_str(text).unwrap();
    assert_eq!(e["embedded_copy"]["rows_embedded"], json!(false));
    assert!(e.get("retro_info").is_none() && !text.contains("\"rows\""), "satır ve retro listesi gömülmez");
    let stripped = d::strip_rows(full.clone());
    let mut n_models = 0usize;
    for blk in ["oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"] {
        assert_eq!(e[blk], stripped[blk], "{blk}: gömülü blok repo dosyasındakiyle birebir (satırsız)");
        n_models += e[blk]["models"].as_array().map_or(0, Vec::len);
        for (m, fm) in e[blk]["models"].as_array().unwrap().iter().zip(full[blk]["models"].as_array().unwrap()) {
            assert_eq!(m["cells"], fm["cells"], "{blk}/{}: hücreler", m["model_id"]);
        }
    }
    assert_eq!(n_models, 27 + 27 + 19 + 3, "27 + 27 + 19 model bloğu + üç D1 sonrası bloğu");
    for k in ["schema_version", "generated_at_utc", "code", "cohort_sha256", "definitions"] {
        assert_eq!(e[k], full[k], "{k}");
    }
    println!("gömülü scores_oot kopyası: {} bayt (kaynak {} bayt)", text.len(), raw.len());
}

fn synthetic_oot(sealed: bool) -> Value {
    let cell = |label: &str, rule: &str, v: &str, ci: [f64; 2], mv: f64| {
        json!({"label": label, "output": "S", "horizon_or_k": null, "metric": "RPS", "rule_id": rule, "n": 62,
               "model_value": mv, "rule_value": 0.2, "diff": ci[0], "ci95": ci, "verdict": v, "n_live": 0, "n_late": 0, "n_blocks": 28})
    };
    let block = |id: &str, cells: Vec<Value>, rows: Vec<Value>| {
        json!({"model_id": id, "kind": "hazard", "n_scored": 62, "cells": cells, "by_year": [], "by_regime": [], "rows": rows})
    };
    let open_rows = vec![json!({"ticker": "SNTO1", "open": true, "vault": "OPEN"})];
    let mut d = json!({
        "schema_version": "borsai.scores_oot/1", "generated_at_utc": "2030-01-01T00:00:00Z",
        "oot_pre_h99": {"title": "t", "models": [block("ceiling_hazard_v0", vec![], open_rows.clone())]},
    });
    if sealed {
        let sealed_rows = vec![json!({"ticker": "SNTS1", "open": false, "vault": "SEALED"})];
        d["oot_pre_h99_sealed"] = json!({"title": "k", "models": [
            block("ceiling_hazard_v0", vec![cell("birincil", "base_km_expanding", "ayırt edilemiyor", [-0.01, 0.1], 0.27)], sealed_rows.clone()),
            block("ceiling_hazard_v1_clip", vec![cell("birincil", "base_km_expanding", "geçiyor", [-0.06, -0.01], 0.1801),
                                                 cell("ikincil", "ceiling_hazard_v0", "geçiyor", [-0.06, -0.02], 0.1801)], sealed_rows.clone()),
            block("ceiling_hazard_v1_real", vec![cell("birincil", "base_km_expanding", "geçiyor", [-0.06, -0.01], 0.1809),
                                                 cell("ikincil", "ceiling_hazard_v0", "geçiyor", [-0.07, -0.03], 0.1809)], sealed_rows.clone()),
            block("ceiling_hazard_v1_pooled", vec![cell("birincil", "base_km_expanding", "geçiyor", [-0.06, -0.01], 0.15),
                                                   cell("ikincil", "ceiling_hazard_v0", "geçiyor", [-0.1, -0.03], 0.15)], sealed_rows),
        ]});
    }
    d
}

fn synthetic_scores(labels: &[(&str, &str)]) -> Value {
    let models: Vec<Value> = labels
        .iter()
        .map(|(id, l)| {
            json!({"model_id": id, "backtest": {"cells": [], "near_era": {"schema_version": "borsai.near_era/1", "label": l,
                   "comparator": "ceiling_hazard_v0", "metric": "RPS", "subset": "first_trading_date >= 2024-01-01",
                   "diff": -0.001, "ci95": [-0.006, 0.004], "n": 78, "n_blocks": 22}},
                   "live": {"n_scored": 0, "cells": []}})
        })
        .collect();
    json!({"schema_version": "borsai.scores/1", "models": models})
}

/// K-P1-3 bütünlük değişikliği: açık küme bloğunda `open: false` → OOT_ROW_NOT_OPEN (kod basılmaz, yalnız sayı);
/// kasa bloğunda SEALED kapalı satır meşru, SEALED olmayan kapalı satır ihlal; küçük n'de hücre, canlı sayaç, hükümsüz
/// aralık ve sürüm.
#[test]
fn scores_oot_integrity_rules() {
    let ok = d::scores_oot_value(&synthetic_oot(true));
    assert_eq!(ok.integrity, None, "kasa bloğundaki SEALED kapalı satır hata değil");
    let mut bad = synthetic_oot(true);
    bad["oot_pre_h99"]["models"][0]["rows"][0]["open"] = json!(false);
    let p = d::scores_oot_value(&bad).integrity.expect("açık küme bloğunda kapalı satır");
    assert_eq!(p.rule, "OOT_ROW_NOT_OPEN");
    assert!(!p.detail.contains("SNTO1") && p.detail.contains("1 satır"), "kod basılmaz: {}", p.detail);
    let mut bad = synthetic_oot(true);
    bad["oot_pre_h99_sealed"]["models"][1]["rows"][0]["vault"] = json!("OPEN");
    assert_eq!(d::scores_oot_value(&bad).integrity.map(|p| p.rule), Some("OOT_ROW_NOT_OPEN".into()));
    let mut bad = synthetic_oot(true);
    bad["oot_pre_h99_sealed"]["models"][1]["n_scored"] = json!(8);
    assert_eq!(d::scores_oot_value(&bad).integrity.map(|p| p.rule), Some("OOT_CELLS_BELOW_MIN_N".into()));
    let mut bad = synthetic_oot(true);
    bad["oot_pre_h99_sealed"]["models"][1]["cells"][0]["n_live"] = json!(1);
    assert_eq!(d::scores_oot_value(&bad).integrity.map(|p| p.rule), Some("OOT_LIVE_COUNTS_NONZERO".into()));
    let mut bad = synthetic_oot(true);
    bad["oot_pre_h99_sealed"]["models"][1]["cells"][0]["n"] = json!(20);
    assert_eq!(d::scores_oot_value(&bad).integrity.map(|p| p.rule), Some("VERDICT_WITHOUT_INTERVAL".into()));
    let mut v2 = synthetic_oot(true);
    v2["schema_version"] = json!("borsai.scores_oot/2");
    assert_eq!(d::scores_oot_value(&v2).unsupported_version.as_deref(), Some("borsai.scores_oot/2"));
}

fn ids() -> Vec<String> {
    embedded_pairs().into_iter().map(|(id, _)| id).collect()
}

/// U61: öne çıkarma kuralı yalnız dosyadaki verdict / ci95 / model_value / etiketi karşılaştırır.
#[test]
fn featured_ceiling_rules() {
    let ids = ids();
    let all_ok = synthetic_scores(&[
        ("ceiling_hazard_v1_clip", "tolerans içinde"),
        ("ceiling_hazard_v1_real", "tolerans içinde"),
        ("ceiling_hazard_v1_pooled", "bozuyor"),
    ]);
    // kasa bloğu yok → v0, VAULT_CLOSED_V0_DEFAULT
    let f = d::featured_ceiling(Some(&all_ok), Some(&synthetic_oot(false)), &ids);
    assert_eq!((f.model_id.as_str(), f.reason), ("ceiling_hazard_v0", "VAULT_CLOSED_V0_DEFAULT"));
    let f = d::featured_ceiling(Some(&all_ok), None, &ids);
    assert_eq!(f.reason, "VAULT_CLOSED_V0_DEFAULT");
    // (a)+(c): clip ve real uygun; model_value 0.1801 < 0.1809 → clip; pooled "bozuyor" (b) uygun değil
    let f = d::featured_ceiling(Some(&all_ok), Some(&synthetic_oot(true)), &ids);
    assert_eq!((f.model_id.as_str(), f.reason), ("ceiling_hazard_v1_clip", "RULE_5_5"));
    let pooled = f.candidates.iter().find(|c| c.model_id.ends_with("pooled")).unwrap();
    assert!(pooled.k1 && pooled.k2 && !pooled.k3 && !pooled.eligible, "(b) geçiyor ama bozuyor");
    // (c) yuvarlanınca eşit (0.18041 / 0.18049 → 0.180): basit olan (clip < real)
    let mut o = synthetic_oot(true);
    o["oot_pre_h99_sealed"]["models"][1]["cells"][0]["model_value"] = json!(0.18049);
    o["oot_pre_h99_sealed"]["models"][2]["cells"][0]["model_value"] = json!(0.18041);
    assert_eq!(d::featured_ceiling(Some(&all_ok), Some(&o), &ids).model_id, "ceiling_hazard_v1_clip");
    // yuvarlanınca farklı: düşük olan kazanır (real 0.179 < clip 0.180)
    o["oot_pre_h99_sealed"]["models"][2]["cells"][0]["model_value"] = json!(0.1790);
    assert_eq!(d::featured_ceiling(Some(&all_ok), Some(&o), &ids).model_id, "ceiling_hazard_v1_real");
    // (d) yakın dönem bloğu yok → k3 = false
    let none = synthetic_scores(&[]);
    let f = d::featured_ceiling(Some(&none), Some(&synthetic_oot(true)), &ids);
    assert_eq!((f.model_id.as_str(), f.reason), ("ceiling_hazard_v0", "RULE_5_5_NONE_ELIGIBLE_V0"));
    assert!(f.candidates.iter().all(|c| !c.k3));
    // (e) k2: ci95[1] = 0.0 → uygun değil
    let mut o = synthetic_oot(true);
    for i in [1, 2] {
        o["oot_pre_h99_sealed"]["models"][i]["cells"][1]["ci95"] = json!([-0.05, 0.0]);
    }
    let f = d::featured_ceiling(Some(&all_ok), Some(&o), &ids);
    assert_eq!(f.reason, "RULE_5_5_NONE_ELIGIBLE_V0");
    // GERÇEK dosyalar (kasa açıldı): uygun v1 adayı yok → v0 (K-P1-2; SKOR_RAPOR T6)
    let real = real_oot();
    let f = d::featured_ceiling(Some(&real_scores()), real.usable(), &ids);
    assert_eq!((f.model_id.as_str(), f.reason), ("ceiling_hazard_v0", "RULE_5_5_NONE_ELIGIBLE_V0"));
    let k: Vec<(&str, bool, bool, bool)> = f.candidates.iter().map(|c| (c.model_id.as_str(), c.k1, c.k2, c.k3)).collect();
    assert_eq!(
        k,
        [
            ("ceiling_hazard_v1_clip", false, true, true),
            ("ceiling_hazard_v1_real", false, true, false),
            ("ceiling_hazard_v1_pooled", true, true, false),
        ],
        "k1: kasa birincil · k2: v0'a karşı üst uç < 0 · k3: yakın dönem"
    );
    // fonksiyon skor hesaplamaz: gövdesinde istatistik ya da toplama çağrısı yok
    let src = std::fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/commands/scores.rs")).unwrap();
    let body = &src[src.find("pub fn featured_ceiling").unwrap()..];
    let body = &body[..body.find("\n}\n").unwrap()];
    for banned in ["mean", "sum(", "fold(", "sqrt", "resampl"] {
        assert!(!body.contains(banned), "featured_ceiling: {banned}");
    }
}

fn summary_models(runs: &[Value]) -> Vec<d::SummaryModel> {
    runs.iter().map(|r| serde_json::from_value(r.clone()).unwrap()).collect()
}

/// U60: kart fixture'ları Rust'ın gerçek çıktısından (NETGL/VEYAS `predict_all`; gerçek ve sentetik skor dosyaları).
#[test]
fn ceiling_summary_fixtures() {
    let emb = embedded_pairs();
    let t = registry_t("NETGL");
    let netgl = runs(&netgl(), &record_f6("NETGL"), Some(&t));
    let veyas = runs(&registry_inputs("VEYAS"), &record_f6("VEYAS"), Some(&registry_t("VEYAS")));
    let state = AppState::from_embedded();
    let tufe = borsai_app_lib::commands::predict::tufe_info_value(&state, Some(&t));
    // gerçek dosyalar (kasa açık): öne çıkan v0, neden RULE_5_5_NONE_ELIGIBLE_V0
    let sc = real_scores();
    let oot = real_oot();
    let sha = "FIXTURE";
    let real = |j: usize, runs: &[Value], tufe: Option<_>| {
        d::ceiling_summary_value(&summary_models(runs), j, Some(2), false, None, &emb, Some((&sc, "REPO", sha)), Some(&oot), tufe)
    };
    let s0 = real(0, &netgl, tufe.clone());
    assert_eq!((s0.featured.model_id.as_str(), s0.featured.reason), ("ceiling_hazard_v0", "RULE_5_5_NONE_ELIGIBLE_V0"));
    assert!(s0.integrity.is_none());
    let row = |s: &d::CeilingSummary, id: &str| s.rows.iter().find(|r| r.model_id == id).cloned().unwrap();
    for (id, v) in [
        ("ceiling_hazard_v0", "ayırt edilemiyor"),
        ("ceiling_hazard_v1_clip", "ayırt edilemiyor"),
        ("ceiling_hazard_v1_real", "ayırt edilemiyor"),
        ("ceiling_hazard_v1_pooled", "geçiyor"),
    ] {
        assert_eq!((row(&s0, id).vault.status, row(&s0, id).vault.verdict.as_deref()), ("OPEN", Some(v)), "{id} kasa");
    }
    for (id, l) in [("ceiling_hazard_v1_clip", Some("tolerans içinde")), ("ceiling_hazard_v1_real", Some("bozuyor")),
                    ("ceiling_hazard_v1_pooled", Some("bozuyor")), ("ceiling_hazard_v0", None), ("base_km_expanding", None)] {
        assert_eq!(row(&s0, id).near_era.and_then(|n| n.label).as_deref(), l, "{id} yakın dönem");
    }
    assert_eq!(row(&s0, "base_km_expanding").vault.verdict, None, "birincil hücresi olmayan kural: —");
    assert_eq!(s0.rows[0].model_id, "ceiling_hazard_v0");
    assert_eq!(s0.rows.last().unwrap().role, "CONSTANT");
    // satır değerleri ceiling_display'den aynen: S[2], S[4], S[9], beklenen, medyan
    let disp = ceiling_display_value(&s_vectors(&netgl), 0, None).unwrap();
    for r in s0.rows.iter().filter(|r| r.p_ge3.is_some() && r.role != "CONSTANT") {
        let c = disp.rows.iter().find(|x| x.model_id == r.model_id).unwrap();
        assert_eq!((r.p_ge3, r.p_ge5, r.p_10), (Some(c.s[2]), Some(c.s[4]), Some(c.s[9])), "{}", r.model_id);
        assert_eq!((r.expected_l, r.median_l, r.mode_l), (Some(c.expected_l), Some(c.median_l), Some(c.mode_l)));
    }
    fixture_opt("summary_real_netgl_j0.json", &serde_json::to_value(&s0).unwrap(), false);
    let s2 = real(2, &netgl, tufe.clone());
    assert_eq!(s2.j_source, "OFFICIAL");
    assert!(s2.rows[0].cond.is_some());
    fixture_opt("summary_real_netgl_j2.json", &serde_json::to_value(&s2).unwrap(), false);
    let sv = real(0, &veyas, None);
    assert!(sv.f3_missing, "VEYAS: f3 boş, PB aynası açık");
    assert_eq!(row(&sv, "ceiling_hazard_v0").refused.unwrap()["code"], json!("F3_MISSING"));
    assert_eq!(row(&sv, "ceiling_hazard_v1_pooled@INF").status.as_deref(), Some("PREDICTED"));
    fixture_opt("summary_real_veyas_j0.json", &serde_json::to_value(&sv).unwrap(), false);

    // sentetik skorlar, kasa kapalı (EK 3 U60 fixture'ı): VAULT_CLOSED_V0_DEFAULT, "kasa: bekliyor"
    let syn = synthetic_scores(&[
        ("ceiling_hazard_v1_clip", "tolerans içinde"),
        ("ceiling_hazard_v1_real", "bozuyor"),
        ("ceiling_hazard_v1_pooled", "bozuyor"),
    ]);
    let closed = d::scores_oot_value(&synthetic_oot(false));
    let c0 = d::ceiling_summary_value(&summary_models(&netgl), 0, None, false, None, &emb, Some((&syn, "REPO", sha)), Some(&closed), tufe.clone());
    assert_eq!(c0.featured.reason, "VAULT_CLOSED_V0_DEFAULT");
    assert!(c0.rows.iter().filter(|r| r.role != "CONSTANT").all(|r| r.vault.status == "CLOSED"));
    fixture("summary_closed_netgl_j0.json", &serde_json::to_value(&c0).unwrap());
    let c2 = d::ceiling_summary_value(&summary_models(&netgl), 2, None, false, None, &emb, Some((&syn, "REPO", sha)), Some(&closed), tufe);
    assert_eq!(c2.j_source, "HYPOTHETICAL");
    fixture("summary_closed_netgl_j2.json", &serde_json::to_value(&c2).unwrap());

    // en olası bozulma günü üç dal: l = 0, orta, 10 (sentetik S vektörleri)
    let mk = |id: &str, s: [f64; 10]| json!({"model_id": id, "status": "PREDICTED", "refusal": null, "output": {"S": s}});
    let branch = vec![
        mk("ceiling_hazard_v0", [0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0001]),
        mk("ceiling_hazard_v0@INF", [0.9, 0.8, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.001]),
        mk("base_km_expanding", [0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92, 0.91, 0.9]),
    ];
    let b = d::ceiling_summary_value(&summary_models(&branch), 0, None, false, None, &emb, None, None, None);
    let modes: Vec<(String, Option<usize>)> =
        b.rows.iter().filter(|r| r.status.is_some()).map(|r| (r.model_id.clone(), r.mode_l)).collect();
    assert_eq!(
        modes,
        [("ceiling_hazard_v0".to_string(), Some(0)), ("ceiling_hazard_v0@INF".into(), Some(2)), ("base_km_expanding".into(), Some(10))]
    );
    fixture("summary_mode_branches.json", &serde_json::to_value(&b).unwrap());
}

// ================================================================ EK 3 P4: "Düşüş (D10)" kartı (§8.4; K-P4-1, K-P4-2, U79)

mod fl {
    pub use borsai_app_lib::commands::fall::{fall_summary_value, FallSummary};
    pub use borsai_app_lib::commands::scores::featured_fall;
}

const FALL_ROWS: [&str; 6] =
    ["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO", "base_rate", "v1_5_h99"];

fn model_refs() -> Vec<borsai_predict::ModelRef> {
    AppState::from_embedded().models.as_ref().unwrap().models.clone()
}

/// Sentetik kasa bloğu ((C) adayları; `p_up` · D10 · Brier hücreleri): addsale ve h99 k1/k2 sağlar, pooled k2'de kalır.
fn fall_oot(sealed: bool) -> Value {
    let cell = |label: &str, rule: &str, v: &str, ci: [f64; 2], mv: f64| {
        json!({"label": label, "output": "p_up", "horizon_or_k": "D10", "metric": "Brier", "rule_id": rule, "n": 60,
               "model_value": mv, "rule_value": 0.17, "diff": ci[0], "ci95": ci, "verdict": v, "n_live": 0, "n_late": 0, "n_blocks": 27})
    };
    let block = |id: &str, cells: Vec<Value>| json!({"model_id": id, "kind": "fall", "n_scored": 60, "cells": cells, "by_year": [], "by_regime": []});
    let mut d = json!({"schema_version": "borsai.scores_oot/1", "generated_at_utc": "2030-01-01T00:00:00Z",
                       "oot_pre_h99": {"title": "t", "models": [block("fall_d10_v0_h99", vec![])]}});
    if sealed {
        d["oot_pre_h99_sealed"] = json!({"title": "k", "models": [
            block("fall_d10_v0_addsale", vec![cell("birincil", "base_rate", "geçiyor", [-0.05, -0.01], 0.140),
                                              cell("ikincil", "v1_5_h99", "geçiyor", [-0.04, -0.005], 0.140)]),
            block("fall_d10_v0_h99", vec![cell("birincil", "base_rate", "geçiyor", [-0.06, -0.01], 0.1201),
                                          cell("ikincil", "v1_5_h99", "geçiyor", [-0.05, -0.002], 0.1201)]),
            block("fall_d10_v0_pooled", vec![cell("birincil", "base_rate", "geçiyor", [-0.07, -0.01], 0.1150),
                                             cell("ikincil", "v1_5_h99", "ayırt edilemiyor", [-0.03, 0.02], 0.1150)]),
        ]});
    }
    d
}

/// Sentetik yakın dönem blokları: (model, etiket, karşılaştırıcı, ci95).
fn fall_scores(near: &[(&str, &str, &str, [f64; 2])]) -> Value {
    let models: Vec<Value> = near
        .iter()
        .map(|(id, l, cmp, ci)| {
            json!({"model_id": id, "backtest": {"cells": [], "near_era": {"schema_version": "borsai.near_era/1", "label": l,
                   "comparator": cmp, "metric": "D10 Brier", "subset": "first_trading_date >= 2024-01-01",
                   "diff": ci[0], "ci95": ci, "n": 75, "n_blocks": 22, "tolerance": 0.008}},
                   "card": {"training_n": 94, "training_cutoff": "2026-08-19", "params_sha256_8": "abcdef12", "n_variants_same_data": 2059},
                   "primary_cell": {"output": "p_up", "horizon_or_k": "D10", "metric": "Brier", "rule_ids": ["base_rate"]},
                   "live": {"n_scored": 0, "cells": []}})
        })
        .collect();
    json!({"schema_version": "borsai.scores/1", "models": models})
}

fn fall_near_ok() -> Value {
    fall_scores(&[
        ("fall_d10_v0_addsale", "belirsiz", "base_rate", [-0.03, 0.016]),
        ("fall_d10_v0_h99", "tolerans içinde", "base_rate", [-0.077, -0.005]),
        ("fall_d10_v0_pooled", "belirsiz", "fall_d10_v0_h99", [-0.034, 0.022]),
        ("fall_d10_v0_pooled@ZERO", "tolerans içinde", "base_rate", [-0.016, 0.008]),
    ])
}

/// U79 (EK 3 §8.4-5; SPEC_C_V0 §5.5): `featured_fall` yalnız dosyadaki verdict / ci95 / model_value / yakın dönem bloğunu
/// karşılaştırır: kasa yok → öne çıkan yok ("kasa: bekliyor"); k1–k3; eşitlikte basit olan; uygun yok; gerçek dosyalar.
#[test]
fn featured_fall_rules() {
    let ids = ids();
    let near = fall_near_ok();
    // kasa bloğu yok → öne çıkan yok, neden VAULT_CLOSED; sağlanmayan koşul yazılmaz
    let f = fl::featured_fall(Some(&near), Some(&fall_oot(false)), &ids);
    assert_eq!((f.model_id.as_deref(), f.reason), (None, "VAULT_CLOSED"));
    assert!(f.candidates.iter().all(|c| c.first_failed.is_none()));
    // addsale (0.140) ve h99 (0.1201) uygun; pooled k2'de kalır → h99 (round 0.120 < 0.140)
    let f = fl::featured_fall(Some(&near), Some(&fall_oot(true)), &ids);
    assert_eq!((f.model_id.as_deref(), f.reason), (Some("fall_d10_v0_h99"), "RULE_5_5"));
    let ff: Vec<(&str, Option<&str>)> = f.candidates.iter().map(|c| (c.model_id.as_str(), c.first_failed)).collect();
    assert_eq!(ff, [("fall_d10_v0_addsale", None), ("fall_d10_v0_h99", None), ("fall_d10_v0_pooled", Some("k2"))]);
    // yuvarlanınca eşit (0.12049 / 0.12041 → 0.120): basit olan (addsale < h99 < pooled)
    let mut o = fall_oot(true);
    o["oot_pre_h99_sealed"]["models"][0]["cells"][0]["model_value"] = json!(0.12049);
    o["oot_pre_h99_sealed"]["models"][1]["cells"][0]["model_value"] = json!(0.12041);
    assert_eq!(fl::featured_fall(Some(&near), Some(&o), &ids).model_id.as_deref(), Some("fall_d10_v0_addsale"));
    // k3 (h99/addsale): yakın dönem − taban oran aralığı tamamen 0'ın üstünde → uygun değil
    let worse = fall_scores(&[
        ("fall_d10_v0_addsale", "belirsiz", "base_rate", [-0.03, 0.016]),
        ("fall_d10_v0_h99", "bozuyor", "base_rate", [0.001, 0.02]),
        ("fall_d10_v0_pooled", "bozuyor", "fall_d10_v0_h99", [0.002, 0.03]),
    ]);
    let mut o = fall_oot(true);
    o["oot_pre_h99_sealed"]["models"][2]["cells"][1]["ci95"] = json!([-0.03, -0.001]); // pooled k2 sağlar
    let f = fl::featured_fall(Some(&worse), Some(&o), &ids);
    let ff: Vec<(&str, Option<&str>)> = f.candidates.iter().map(|c| (c.model_id.as_str(), c.first_failed)).collect();
    assert_eq!(ff, [("fall_d10_v0_addsale", None), ("fall_d10_v0_h99", Some("k3")), ("fall_d10_v0_pooled", Some("k3"))]);
    assert_eq!(f.model_id.as_deref(), Some("fall_d10_v0_addsale"));
    // yakın dönem bloğu yok → k3 = false → uygun aday yok
    let f = fl::featured_fall(Some(&fall_scores(&[])), Some(&fall_oot(true)), &ids);
    assert_eq!((f.model_id.as_deref(), f.reason), (None, "RULE_5_5_NONE_ELIGIBLE"));
    // k2: ci95[1] = 0.0 → uygun değil
    let mut o = fall_oot(true);
    for i in [0, 1] {
        o["oot_pre_h99_sealed"]["models"][i]["cells"][1]["ci95"] = json!([-0.05, 0.0]);
    }
    assert_eq!(fl::featured_fall(Some(&near), Some(&o), &ids).reason, "RULE_5_5_NONE_ELIGIBLE");
    // GERÇEK dosyalar (K-P4-1): öne çıkan yok; pooled k2'de, h99 ve addsale k1'de kalır
    let real = real_oot();
    let f = fl::featured_fall(Some(&real_scores()), real.usable(), &ids);
    assert_eq!((f.model_id.as_deref(), f.reason), (None, "RULE_5_5_NONE_ELIGIBLE"));
    let k: Vec<(&str, bool, bool, bool, Option<&str>)> =
        f.candidates.iter().map(|c| (c.model_id.as_str(), c.k1, c.k2, c.k3, c.first_failed)).collect();
    assert_eq!(
        k,
        [
            ("fall_d10_v0_addsale", false, false, true, Some("k1")),
            ("fall_d10_v0_h99", false, false, true, Some("k1")),
            ("fall_d10_v0_pooled", true, false, true, Some("k2")),
        ],
        "k1: kasa birincil · k2: V1.5'e karşı üst uç < 0 · k3: yakın dönem"
    );
    // fonksiyon skor hesaplamaz: gövdesinde istatistik ya da toplama çağrısı yok
    let src = std::fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/commands/scores.rs")).unwrap();
    let body = &src[src.find("pub fn featured_fall").unwrap()..];
    let body = &body[..body.find("\n}\n").unwrap()];
    for banned in ["mean", "sum(", "fold(", "sqrt", "resampl", "bootstrap"] {
        assert!(!body.contains(banned), "featured_fall: {banned}");
    }
}

fn row_of<'a>(s: &'a fl::FallSummary, id: &str) -> &'a borsai_app_lib::commands::fall::FallRow {
    s.rows.iter().find(|r| r.model_id == id).unwrap_or_else(|| panic!("{id} satırı yok"))
}

/// U79 + K-P4-1/K-P4-2: kart fixture'ları Rust'ın gerçek çıktısından (NETGL/VEYAS `predict_all`; gerçek ve sentetik skor
/// dosyaları). Gerçek dosyalarla: öne çıkan yok; satır sırası addsale, h99, pooled, @ZERO, base_rate, v1_5_h99; ilk
/// sağlanmayan koşul; zaman-dışı ve yakın dönem sütunları dosyadan; P(D_h ≤ arz) = 1 − p_up ve %k + %(100 − k) = 100.
#[test]
fn fall_summary_fixtures() {
    let refs = model_refs();
    let t = registry_t("NETGL");
    let netgl = runs(&netgl(), &record_f6("NETGL"), Some(&t));
    let veyas = runs(&registry_inputs("VEYAS"), &record_f6("VEYAS"), Some(&registry_t("VEYAS")));
    let state = AppState::from_embedded();
    let tufe = borsai_app_lib::commands::predict::tufe_info_value(&state, Some(&t));
    let (sc, oot) = (real_scores(), real_oot());
    let s = fl::fall_summary_value(&summary_models(&netgl), false, None, &refs, Some((&sc, "REPO", "FIXTURE")), Some(&oot), tufe.clone())
        .expect("(C) gömülü");
    assert_eq!((s.featured.model_id.as_deref(), s.featured.reason), (None, "RULE_5_5_NONE_ELIGIBLE"));
    assert!(s.integrity.is_none());
    let order: Vec<(&str, &str)> = s.rows.iter().map(|r| (r.model_id.as_str(), r.role)).collect();
    assert_eq!(
        order,
        FALL_ROWS.iter().copied().zip(["CANDIDATE", "CANDIDATE", "CANDIDATE", "RULE", "COMPARATOR", "COMPARATOR"]).collect::<Vec<_>>()
    );
    for (id, failed, vault) in [
        ("fall_d10_v0_addsale", "k1", "ayırt edilemiyor"),
        ("fall_d10_v0_h99", "k1", "ayırt edilemiyor"),
        ("fall_d10_v0_pooled", "k2", "geçiyor"),
    ] {
        let r = row_of(&s, id);
        assert_eq!(r.first_failed, Some(failed), "{id}");
        assert_eq!((r.vault.status, r.vault.verdict.as_deref(), r.vault.rule_id.as_deref()), ("OPEN", Some(vault), Some("base_rate")), "{id}");
        assert_eq!(r.live.n_scored, Some(0), "{id}: canlı n");
    }
    for (id, label, cmp) in [
        ("fall_d10_v0_h99", "tolerans içinde", "base_rate"),
        ("fall_d10_v0_pooled", "belirsiz", "fall_d10_v0_h99"),
        ("fall_d10_v0_addsale", "belirsiz", "base_rate"),
        ("fall_d10_v0_pooled@ZERO", "tolerans içinde", "base_rate"),
    ] {
        let n = row_of(&s, id).near_era.clone().expect("yakın dönem bloğu");
        assert_eq!((n.label.as_deref(), n.comparator.as_deref()), (Some(label), Some(cmp)), "{id}");
    }
    assert_eq!(row_of(&s, "fall_d10_v0_pooled@ZERO").vault.verdict, None, "kural satırının kasa birincil hücresi yok: —");
    for c in ["base_rate", "v1_5_h99"] {
        let r = row_of(&s, c);
        assert!(r.near_era.is_none() && r.vault.status == "NONE" && r.live.n_scored.is_none() && r.card.is_none(), "{c}");
    }
    // değerler predict_all çıktısından: 1 − p_up ve tamamlayan yüzde
    for id in FALL_ROWS {
        let run = netgl.iter().find(|r| r["model_id"] == json!(id)).unwrap();
        let r = row_of(&s, id);
        for (h, c) in [("D10", &r.d10), ("D5", &r.d5)] {
            let p_up = run["output"][h]["p_up"].as_f64().unwrap();
            assert_eq!((c.p_up, c.p_fall), (Some(p_up), Some(1.0 - p_up)), "{id} {h}");
            assert_eq!(c.pct_fall.unwrap() + c.pct_up.unwrap(), 100);
        }
    }
    let card = row_of(&s, "fall_d10_v0_h99").card.clone().unwrap();
    assert_eq!((card.training_n, card.params_sha256_8.as_deref()), (Some(json!(94)), Some("b15eaa8c")));
    assert!(card.description.is_some() && card.primary_cell.is_some());
    fixture_opt("summary_fall_real_netgl.json", &serde_json::to_value(&s).unwrap(), false);
    // VEYAS (f3 boş): h99 ve pooled F3_MISSING; addsale ve @ZERO dolu
    let v = fl::fall_summary_value(&summary_models(&veyas), false, None, &refs, Some((&sc, "REPO", "FIXTURE")), Some(&oot), None).unwrap();
    for id in ["fall_d10_v0_h99", "fall_d10_v0_pooled"] {
        assert_eq!(row_of(&v, id).refused.as_ref().unwrap()["code"], json!("F3_MISSING"), "{id}");
        assert!(row_of(&v, id).d10.pct_fall.is_none());
    }
    assert!(row_of(&v, "fall_d10_v0_addsale").d10.pct_fall.is_some() && row_of(&v, "fall_d10_v0_pooled@ZERO").d10.pct_fall.is_some());
    fixture_opt("summary_fall_real_veyas.json", &serde_json::to_value(&v).unwrap(), false);

    // sentetik: kasa kapalı ("kasa: bekliyor"; öne çıkan yok)
    let near = fall_near_ok();
    let closed = d::scores_oot_value(&fall_oot(false));
    let c = fl::fall_summary_value(&summary_models(&netgl), false, None, &refs, Some((&near, "REPO", "FIXTURE")), Some(&closed), tufe.clone()).unwrap();
    assert_eq!((c.featured.model_id.as_deref(), c.featured.reason), (None, "VAULT_CLOSED"));
    assert!(c.rows.iter().filter(|r| r.role != "COMPARATOR").all(|r| r.vault.status == "CLOSED"));
    fixture("summary_fall_closed_netgl.json", &serde_json::to_value(&c).unwrap());
    // sentetik: kasa açık, h99 uygun → öne çıkan h99 (büyük satır)
    let open = d::scores_oot_value(&fall_oot(true));
    let o = fl::fall_summary_value(&summary_models(&netgl), false, None, &refs, Some((&near, "REPO", "FIXTURE")), Some(&open), tufe).unwrap();
    assert_eq!((o.featured.model_id.as_deref(), o.rows[0].model_id.as_str(), o.rows[0].role), (Some("fall_d10_v0_h99"), "fall_d10_v0_h99", "FEATURED"));
    fixture("summary_fall_featured_netgl.json", &serde_json::to_value(&o).unwrap());
    // (C) gömülü değilse kart yok
    let no_fall: Vec<borsai_predict::ModelRef> = refs.iter().filter(|m| !m.model_id.starts_with("fall_")).cloned().collect();
    assert!(fl::fall_summary_value(&summary_models(&netgl), false, None, &no_fall, None, None, None).is_none());
}
