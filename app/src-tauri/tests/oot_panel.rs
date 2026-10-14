//! EK 3 P3 (§7; K-P3-1, K-P3-2): "Zaman-dışı test (eski kohort)" panelinin Rust tarafı — `scores_oot_view` /
//! `scores_oot_model` görünümleri, satır görünürlüğü (yalnız açık küme bloğunda `open == true`), RETRO süzgeci, fail-closed
//! bütünlük (U73), kasa alt bölümleri (U74) ve gerçek dosya (U75). Vitest fixture'larını gerçek okuyucudan üretir:
//!
//!   BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test oot_panel   # app/tests/fixtures/ui/scores_oot_panel_*.json
//!
//! Kasa (SEALED) kodu hiçbir çıktıya yazılmaz: gerçek dosya testi kohort dosyasının SEALED kodlarını yalnız sayar.
use borsai_app_lib::commands::scores_oot::{
    model_detail, panel_view, scores_oot_path_in, scores_oot_repo, scores_oot_value, ScoresOotDoc, BLOCKS,
};
use serde_json::{json, Map, Value};
use std::path::PathBuf;

fn app_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").canonicalize().unwrap()
}

fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

fn fixture(name: &str, v: &Value, compare: bool) {
    let path = app_dir().join("tests").join("fixtures").join("ui").join(name);
    let text = serde_json::to_string_pretty(v).unwrap() + "\n";
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&path, &text).unwrap();
        return;
    }
    let disk = std::fs::read_to_string(&path).unwrap_or_default();
    if !compare {
        assert!(!disk.is_empty(), "{} yok", path.display());
        return;
    }
    assert!(disk == text, "{} güncel değil; BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test oot_panel ile yeniden üretin", path.display());
}

// ---------------------------------------------------------------- sentetik dosya (kurgusal kodlar)

const OPEN_A: &str = "SNTO1";
const OPEN_B: &str = "SNTO2";
/// Sentetik kasa/kayıt dışı kodlar: hiçbir görünümde geçmemeli.
const HIDDEN: [&str; 4] = ["SNTS1", "SNTP1", "SNTX1", "SNTZ9"];

#[allow(clippy::too_many_arguments)]
fn cell(label: &str, output: &str, h: Value, metric: &str, rule: &str, n: u64, mv: f64, rv: f64, ci: Option<[f64; 2]>, verdict: Option<&str>) -> Value {
    json!({"label": label, "output": output, "horizon_or_k": h, "metric": metric, "rule_id": rule, "n": n, "n_blocks": 12,
           "model_value": mv, "rule_value": rv, "diff": ci.map(|c| (c[0] + c[1]) / 2.0), "ci95": ci, "verdict": verdict,
           "wins": 20, "losses": 15, "ties": 0, "n_live": 0, "n_late": 0, "scale": "OOT_PRE_H99"})
}

fn brk(subset: &str, label: &str, n: u64, ci: Option<[f64; 2]>, verdict: Option<&str>) -> Value {
    let v = |x: f64| if ci.is_some() { json!(x) } else { Value::Null };
    json!({"subset": subset, "label": label, "n": n, "n_blocks": 3, "rule_id": "base_km_expanding", "model_value": v(0.27),
           "rule_value": v(0.2), "diff": ci.map(|c| (c[0] + c[1]) / 2.0), "ci95": ci, "verdict": verdict, "wins": Value::Null,
           "losses": Value::Null, "ties": Value::Null, "n_live": 0, "n_late": 0, "scale": "OOT_PRE_H99"})
}

fn row(ticker: &str, open: bool, vault: &str, pred: Value) -> Value {
    json!({"ticker": ticker, "d1": "2021-03-04", "year": 2021, "open": open, "vault": vault, "class": "OOT_BLIND",
           "class_evidence": {"model_push_proof_created_at": "2026-09-22T14:06:03Z", "oot_ingest_push_proof_created_at": "2026-09-25T13:05:56Z"},
           "status": "SCORED", "cell_status": "PREDICTED", "prediction": pred, "record_id": "20260924T221306Z_aaaaaaaaaaaa.json",
           "regime_tags": {"ALLOC_REGIME": "PRE_20211111"},
           "realized": {"L": 3, "R": {"D5": "0.61051"}}, "rules": {}, "targets": {}})
}

fn s_pred() -> Value {
    json!({"S": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1], "P_close_ceiling": vec![0.9; 10]})
}

fn model(id: &str, kind: &str, n_scored: u64, cells: Vec<Value>, by_year: Vec<Value>, by_regime: Vec<Value>, rows: Vec<Value>, retro: u64) -> Value {
    json!({"model_id": id, "kind": kind, "scale": "OOT_PRE_H99", "subset": "oot_pre_h99",
           "primary_cell": {"output": "S", "horizon_or_k": null, "metric": "RPS", "rule_ids": ["base_km_expanding"]},
           "cells": cells, "by_year": by_year, "by_regime": by_regime, "rows": rows, "n_scored": n_scored, "n_refused": 1,
           "n_skipped": 0, "n_target_unavailable": 0, "n_pending": 0, "n_not_applicable_regime": 0, "n_oot_retro": retro})
}

fn counts(n_in_table: u64) -> Map<String, Value> {
    json!({"n_member": 135, "n_open": 71, "n_sealed": 64, "n_out_of_scope": 1, "n_pending_membership": 0, "n_exposed_archive": 4,
           "n_exposed_codex": 1, "n_in_table": n_in_table, "n_spk_corporate_action_seen": 14, "n_spk_corporate_action_seen_cohort_total": 28})
    .as_object()
    .unwrap()
    .clone()
}

fn post_d1_block(title: &str, ticker: &str, n_rows: u64) -> Value {
    json!({"title": title, "scale": "OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED", "models": [{
        "model_id": "post_d1_hazard_v0", "scale": "OOT_PRE_H99_POST_D1_MACHINE_SEQUENCED", "exposure_class": "MACHINE_SEQUENCED",
        "primary_cell": {"output": "S_cond", "horizon_or_k": null, "metric": "RPS", "rule_ids": ["ceiling_hazard_v0"]},
        "cells": [], "n_rows": n_rows, "n_scored": n_rows, "n_refused": 0, "n_not_applicable": 1, "n_d1_label_na": 0, "n_no_record": 0,
        "n_oot_retro": 0, "n_pending": 0, "n_skipped": 0, "n_target_unavailable": 0,
        "rows": [{"ticker": ticker, "base_record": format!("registry/oot/records/{ticker}/x.json"), "class": "OOT_BLIND"}],
        "retro_info": [{"model_id": "post_d1_hazard_v0", "ticker": ticker}]}]})
}

/// Sentetik dosya: açık küme (iki açık kod, n = 35 hücreleri, küçük-n kırılımları), kasa ve toplam (kasa satırları
/// SEALED), üç D1 sonrası bloğu (satırlarında kod var: panelde görünmemeli), RETRO (bir açık, bir açık satırda geçmeyen kod).
fn synth(sealed: bool) -> Value {
    let v0_open = model(
        "ceiling_hazard_v0",
        "hazard",
        35,
        vec![
            cell("birincil", "S", Value::Null, "RPS", "base_km_expanding", 35, 0.25, 0.28, Some([-0.05, -0.01]), Some("geçiyor")),
            cell("keşif", "S", Value::Null, "RPS", "ceiling_hazard_v0@INF", 35, 0.25, 0.2, Some([0.001, 0.13]), Some("geçemiyor")),
            cell("keşif", "S", Value::Null, "RPS", "base_km_last10", 35, 0.25, 0.25, Some([-0.006, 0.004]), Some("ayırt edilemiyor")),
        ],
        vec![brk("2020", "ikincil", 1, None, None), brk("2021", "ikincil", 26, Some([-0.08, 0.02]), Some("yetersiz örnek"))],
        vec![brk("ALLOC_REGIME=PRE_20211111", "keşif", 34, Some([-0.02, 0.03]), Some("ayırt edilemiyor"))],
        vec![
            row(OPEN_A, true, "OPEN", s_pred()),
            row(OPEN_B, true, "EXPOSED_ARCHIVE", json!({"refused": {"code": "F3_MISSING", "field": "total_demand_multiple"}})),
        ],
        0,
    );
    let v15_open = model("v1_5_h99", "linear", 8, vec![], vec![], vec![], vec![row(OPEN_A, true, "OPEN", json!({"D5": {"return": 0.2, "p_up": 0.7}}))], 0);
    let clip_open = model("ceiling_hazard_v1_clip", "hazard", 0, vec![], vec![], vec![], vec![], 2);
    let mut open = counts(71);
    open.insert("title".into(), json!("Zaman-dışı test: H99 öncesi kohort (sentetik)"));
    open.insert("scale".into(), json!("OOT_PRE_H99"));
    open.insert("models".into(), json!([v0_open, v15_open, clip_open]));
    let mut d = json!({
        "schema_version": "borsai.scores_oot/1", "scale": "OOT_PRE_H99", "generated_at_utc": "2030-01-01T00:00:00Z",
        "code": {"git_head": "0123456789abcdef0123456789abcdef01234567"}, "cohort_sha256": "fedcba9876543210".repeat(4),
        "definitions": {"class": "OOT_BLIND = kayıt ve model sonuçtan önce push kanıtlı (sentetik tanım)"},
        "oot_pre_h99": open,
        "post_d1": post_d1_block("Zaman-dışı test, D1 sonrası (sentetik; makine sıralı)", OPEN_A, 3),
        "retro_info": [
            {"model_id": "ceiling_hazard_v1_clip", "ticker": OPEN_A, "record_id": "r1", "class_evidence": {}},
            {"model_id": "ceiling_hazard_v1_clip", "ticker": "SNTX1", "record_id": "r2", "class_evidence": {}},
        ],
    });
    if sealed {
        let sealed_row = row("SNTS1", false, "SEALED", s_pred());
        let mut sb = counts(64);
        sb.insert("title".into(), json!("Zaman-dışı test, kasa (sentetik)"));
        sb.insert("scale".into(), json!("OOT_PRE_H99"));
        sb.insert("models".into(), json!([model("ceiling_hazard_v0", "hazard", 34,
            vec![cell("birincil", "S", Value::Null, "RPS", "base_km_expanding", 34, 0.27, 0.26, Some([-0.01, 0.02]), Some("ayırt edilemiyor"))],
            vec![], vec![], vec![sealed_row.clone()], 0)]));
        let mut ab = counts(135);
        ab.insert("title".into(), json!("Zaman-dışı test, toplam (sentetik)"));
        ab.insert("scale".into(), json!("OOT_PRE_H99"));
        ab.insert("excluded_models".into(), json!([{"model_id": "ceiling_hazard_v1_clip", "n_open_oot_blind": 0, "n_open_oot_retro": 2,
            "reason": "açık küme satırları OOT_RETRO (sentetik)"}]));
        ab.insert("models".into(), json!([model("ceiling_hazard_v0", "hazard", 69,
            vec![cell("birincil", "S", Value::Null, "RPS", "base_km_expanding", 69, 0.26, 0.24, Some([0.01, 0.1]), Some("geçemiyor"))],
            vec![], vec![], vec![row(OPEN_A, true, "OPEN", s_pred()), sealed_row], 0)]));
        d["oot_pre_h99_sealed"] = Value::Object(sb);
        d["oot_pre_h99_all"] = Value::Object(ab);
        d["post_d1_sealed"] = post_d1_block("Zaman-dışı test, D1 sonrası, kasa (sentetik)", "SNTP1", 2);
        d["post_d1_all"] = post_d1_block("Zaman-dışı test, D1 sonrası, toplam (sentetik)", "SNTP1", 5);
    }
    d
}

/// Görünüm + her bloğun her modelinin ayrıntısı (fixture biçimi).
fn bundle(d: &ScoresOotDoc, repo_mode: bool) -> Value {
    let view = panel_view(Some(d), repo_mode);
    let mut details = Map::new();
    for b in &view.blocks {
        for m in &b.models {
            if let Some(x) = model_detail(d, b.key, &m.model_id) {
                details.insert(format!("{}/{}", b.key, m.model_id), serde_json::to_value(&x).unwrap());
            }
        }
    }
    json!({"view": view, "details": details})
}

fn no_hidden(v: &Value, hidden: &[&str]) {
    let text = serde_json::to_string(v).unwrap();
    let n = hidden.iter().filter(|c| text.contains(*c)).count();
    assert_eq!(n, 0, "görünümde gizli olması gereken {n} kod var");
}

/// K-P3-1 + U74: satırlar YALNIZ açık küme bloğunda ve yalnız `open == true`; kasa / toplam / D1 sonrası bloklarında yalnız
/// hücre, kırılım ve sayaç; RETRO yalnız açık satırlarda geçen kodla (öteki yalnız sayı); kasa alt bölümleri.
#[test]
fn panel_view_rows_only_in_open_block() {
    let d = scores_oot_value(&synth(true));
    assert!(d.integrity.is_none(), "{:?}", d.integrity);
    let b = bundle(&d, true);
    let view = &b["view"];
    assert_eq!(view["status"], json!("OK"));
    assert_eq!(view["vault_open"], json!(true));
    let keys: Vec<&str> = view["blocks"].as_array().unwrap().iter().map(|x| x["key"].as_str().unwrap()).collect();
    assert_eq!(keys, BLOCKS.to_vec(), "altı blok dosyadaki sırayla");
    let det = |k: &str| &b["details"][k];
    let open = det("oot_pre_h99/ceiling_hazard_v0");
    let tickers: Vec<&str> = open["rows"].as_array().unwrap().iter().map(|r| r["ticker"].as_str().unwrap()).collect();
    assert_eq!(tickers, [OPEN_A, OPEN_B]);
    assert_eq!((open["rows_block"].clone(), open["rows_available"].clone()), (json!(true), json!(true)));
    assert_eq!(open["rows"][0]["pred_kind"], json!("S"));
    assert_eq!(open["rows"][0]["pred_s"], json!([0.9, 0.5, 0.1]), "S_1, S_5, S_10 dosyadan seçilir");
    assert_eq!((open["rows"][1]["pred_kind"].clone(), open["rows"][1]["refused_code"].clone()), (json!("REFUSED"), json!("F3_MISSING")));
    assert_eq!(det("oot_pre_h99/v1_5_h99")["rows"][0]["pred_d5_p_up"], json!(0.7));
    for k in ["oot_pre_h99_sealed/ceiling_hazard_v0", "oot_pre_h99_all/ceiling_hazard_v0", "post_d1/post_d1_hazard_v0",
              "post_d1_sealed/post_d1_hazard_v0", "post_d1_all/post_d1_hazard_v0"] {
        assert_eq!((det(k)["rows"].clone(), det(k)["rows_block"].clone()), (json!([]), json!(false)), "{k}: satır yok");
    }
    // RETRO: açık satırda geçen kod çizilir, geçmeyen yalnız sayı
    assert_eq!(view["retro"]["groups"][0]["tickers"], json!([OPEN_A]));
    assert_eq!((view["retro"]["n"].clone(), view["retro"]["n_not_drawn"].clone()), (json!(2), json!(1)));
    // kasa / toplam sayaçları ve birleştirilmeyen modeller
    assert_eq!(view["blocks"][1]["counters"]["n_in_table"], json!(64));
    assert_eq!(view["blocks"][2]["excluded_models"][0]["model_id"], json!("ceiling_hazard_v1_clip"));
    assert_eq!(view["blocks"][3]["models"][0]["exposure_class"], json!("MACHINE_SEQUENCED"));
    no_hidden(&b, &HIDDEN);
    // bağımsız mod (gömülü satırsız kopya): satır tablosu yok, RETRO yok
    let mut emb = synth(true);
    emb["embedded_copy"] = json!({"rows_embedded": false});
    let e = scores_oot_value(&emb);
    let eb = bundle(&e, false);
    assert_eq!(eb["details"]["oot_pre_h99/ceiling_hazard_v0"]["rows_available"], json!(false));
    assert_eq!(eb["details"]["oot_pre_h99/ceiling_hazard_v0"]["rows"], json!([]));
    assert_eq!(eb["view"]["retro"]["n"], json!(0));
    // kasa kapalı: yalnız açık küme ve D1 sonrası
    let c = scores_oot_value(&synth(false));
    let cb = bundle(&c, true);
    assert_eq!(cb["view"]["vault_open"], json!(false));
    assert_eq!(cb["view"]["blocks"].as_array().unwrap().len(), 2);

    let mut out = Map::new();
    out.insert("ok".into(), b);
    out.insert("closed".into(), cb);
    out.insert("embedded".into(), eb);
    // U73: fail-closed ihlaller (panel yerine kural; kod basılmaz)
    let viol = |f: &dyn Fn(&mut Value)| {
        let mut x = synth(true);
        f(&mut x);
        serde_json::to_value(panel_view(Some(&scores_oot_value(&x)), true)).unwrap()
    };
    let cases: [(&str, &str, Box<dyn Fn(&mut Value)>); 4] = [
        ("row_not_open", "OOT_ROW_NOT_OPEN", Box::new(|x: &mut Value| {
            x["oot_pre_h99"]["models"][0]["rows"].as_array_mut().unwrap().push(row("SNTZ9", false, "OPEN", s_pred()))
        })),
        ("min_n", "OOT_CELLS_BELOW_MIN_N", Box::new(|x: &mut Value| {
            x["oot_pre_h99"]["models"][1]["cells"] = json!([cell("keşif", "return", json!("D5"), "MAE", "base_train_median", 8, 0.2, 0.25, None, None)])
        })),
        ("verdict_n20", "VERDICT_WITHOUT_INTERVAL", Box::new(|x: &mut Value| {
            x["oot_pre_h99"]["models"][0]["cells"][0]["n"] = json!(20)
        })),
        ("live", "OOT_LIVE_COUNTS_NONZERO", Box::new(|x: &mut Value| x["oot_pre_h99_sealed"]["models"][0]["cells"][0]["n_live"] = json!(1))),
    ];
    for (name, rule, f) in cases {
        let v = viol(&*f);
        assert_eq!((v["status"].clone(), v["integrity"]["rule"].clone()), (json!("INTEGRITY"), json!(rule)), "{name}");
        assert_eq!(v["blocks"], json!([]), "{name}: ihlalde blok gösterilmez");
        no_hidden(&v, &HIDDEN);
        out.insert(format!("integrity_{name}"), json!({"view": v}));
    }
    let v = viol(&|x: &mut Value| x["schema_version"] = json!("borsai.scores_oot/2"));
    assert_eq!((v["status"].clone(), v["unsupported_version"].clone()), (json!("UNSUPPORTED"), json!("borsai.scores_oot/2")));
    out.insert("unsupported".into(), json!({"view": v}));
    out.insert("no_file".into(), json!({"view": panel_view(None, true)}));
    out.insert("repo_only".into(), json!({"view": panel_view(None, false)}));
    assert_eq!(out["no_file"]["view"]["status"], json!("NO_FILE"));
    assert_eq!(out["repo_only"]["view"]["status"], json!("REPO_ONLY"));
    fixture("scores_oot_panel_synth.json", &Value::Object(out), true);
}

// ---------------------------------------------------------------- gerçek dosya (U75; K-P3-3)

/// RFC 4180 satırları (yalnız bu testin kohort okuyucusu).
fn csv_rows(text: &str) -> Vec<Vec<String>> {
    let mut rows = Vec::new();
    let (mut row, mut cur, mut quoted) = (Vec::new(), String::new(), false);
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        match (quoted, c) {
            (true, '"') if chars.peek() == Some(&'"') => {
                cur.push('"');
                chars.next();
            }
            (true, '"') => quoted = false,
            (true, c) => cur.push(c),
            (false, '"') if cur.is_empty() => quoted = true,
            (false, ',') => row.push(std::mem::take(&mut cur)),
            (false, '\n') => {
                row.push(std::mem::take(&mut cur));
                rows.push(std::mem::take(&mut row));
            }
            (false, '\r') => {}
            (false, c) => cur.push(c),
        }
    }
    if !cur.is_empty() || !row.is_empty() {
        row.push(cur);
        rows.push(row);
    }
    rows
}

/// Kohort dosyasının SEALED kodları (yerel değişken; hiçbir çıktıya yazılmaz).
fn sealed_codes() -> Vec<String> {
    let text = std::fs::read_to_string(repo_dir().join("registry").join("oot").join("cohort_pre_h99.csv")).unwrap();
    let rows = csv_rows(&text);
    let h = &rows[0];
    let col = |n: &str| h.iter().position(|x| x == n).unwrap();
    let (ct, cv) = (col("ticker"), col("vault"));
    rows[1..].iter().filter(|r| r.len() == h.len() && r[cv] == "SEALED").map(|r| r[ct].clone()).collect()
}

/// U75 (K-P3-3): gerçek `scores/scores_oot.json` — altı blok; açık küme 27 model / 8 birincil, kasa 27 / 14, toplam 19 / 8,
/// D1 sonrası üç alt bölüm 1'er; açık küme satırları yalnız `open == true` (`ceiling_hazard_v0` 71); RETRO 568 çift, hepsi
/// açık satırda geçen kodlarla; görünümde ve bütün ayrıntılarda kasa kodu yok (yalnız sayı).
#[test]
fn panel_view_real_file() {
    let d = scores_oot_repo(&scores_oot_path_in(&repo_dir())).expect("scores/scores_oot.json var").expect("okunur");
    let b = bundle(&d, true);
    let view = &b["view"];
    assert_eq!((view["status"].clone(), view["vault_open"].clone(), view["rows_present"].clone()), (json!("OK"), json!(true), json!(true)));
    let per_block: Vec<(&str, usize, usize)> = view["blocks"]
        .as_array()
        .unwrap()
        .iter()
        .map(|x| {
            let ms = x["models"].as_array().unwrap();
            (x["key"].as_str().unwrap(), ms.len(), ms.iter().filter(|m| !m["primary"].is_null()).count())
        })
        .collect();
    assert_eq!(
        per_block,
        [("oot_pre_h99", 27, 8), ("oot_pre_h99_sealed", 27, 14), ("oot_pre_h99_all", 19, 8), ("post_d1", 1, 1), ("post_d1_sealed", 1, 1), ("post_d1_all", 1, 1)]
    );
    let open = &b["details"]["oot_pre_h99/ceiling_hazard_v0"];
    assert_eq!(open["rows"].as_array().unwrap().len(), 71, "açık küme satırları");
    for (k, x) in b["details"].as_object().unwrap() {
        if !k.starts_with("oot_pre_h99/") {
            assert_eq!(x["rows"], json!([]), "{k}: açık küme dışı blokta satır yok");
        }
    }
    assert_eq!((view["retro"]["n"].clone(), view["retro"]["n_not_drawn"].clone()), (json!(568), json!(0)));
    assert_eq!(view["retro"]["groups"].as_array().unwrap().len(), 8);
    // kasa kodu taraması (yalnız sayı)
    let sealed = sealed_codes();
    assert_eq!(sealed.len(), 64);
    let text = serde_json::to_string(&b).unwrap();
    let hits = sealed.iter().filter(|c| text.contains(&format!("\"{c}\""))).count();
    assert_eq!(hits, 0, "panel görünümünde {hits} kasa kodu var");
    // fixture: görünüm + birincil hücresi olan ilk modelin ayrıntısı (her blokta) + açık küme satır örneği
    let mut details = Map::new();
    for key in ["oot_pre_h99/ceiling_hazard_v0", "oot_pre_h99_sealed/ceiling_hazard_v0",
                "oot_pre_h99_sealed/fall_d10_v0_pooled", "oot_pre_h99_all/ceiling_hazard_v0", "post_d1/post_d1_hazard_v0",
                "post_d1_sealed/post_d1_hazard_v0", "post_d1_all/post_d1_hazard_v0"] {
        details.insert(key.into(), b["details"][key].clone());
    }
    let mut v = view.clone();
    v["sha12"] = json!("FIXTURE");
    fixture("scores_oot_panel_real.json", &json!({"view": v, "details": details}), false);
}
