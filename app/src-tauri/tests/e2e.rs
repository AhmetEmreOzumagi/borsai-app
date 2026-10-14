//! Uçtan uca dondur akışı ve kişisel kayıt izolasyonu (SPEC_APP §5.4: U27–U32, U39).
//!
//! Bu testler YALNIZ `BORSAI_E2E_REPO` ile verilen GEÇİCİ KLONA karşı koşar (`git clone --local`);
//! asıl repo'ya hiçbir şey yazılmaz. Çağıran betikler:
//!   app/tests/e2e_freeze_tmp_repo.sh      (freeze_flow)
//!   app/tests/e2e_personal_isolation.sh   (personal_isolation)
//! Bu testler `#[ignore]`'dır: yalın `cargo test`'te "ignored" görünür (sessizce "ok" değil); betikler
//! `--ignored` ile koşar. Env yoksa test KIRMIZI olur (atlanmaz).
use borsai_app_lib::clock::istanbul;
use borsai_app_lib::commands::ceiling::streak_view_in;
use borsai_app_lib::commands::freeze::{cancel_in, freeze_in, inputs_pit_in, preflight_in};
use borsai_app_lib::commands::inputs_doc::{preview_inputs_doc_in, validate_inputs, InputsDocReq};
use borsai_app_lib::commands::parity::compare_record;
use borsai_app_lib::commands::registry::{record_ceiling_in, registry_view_in};
use borsai_app_lib::commands::scenario::{
    export_all_scenarios_in, export_scenario_in, list_scenarios_in, save_scenario_in, F6Doc, ObservedStreakUser,
    SaveScenarioReq,
};
use borsai_app_lib::state::{AppState, RepoCtx};
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------- ortam

struct Env {
    repo: PathBuf,
    data: PathBuf,
    ctx: RepoCtx,
    state: AppState,
}

fn env() -> Env {
    let repo = PathBuf::from(std::env::var("BORSAI_E2E_REPO").expect("BORSAI_E2E_REPO (geçici klon) gerekli; betikler verir"))
        .canonicalize()
        .expect("geçici klon");
    let data = PathBuf::from(std::env::var("BORSAI_E2E_DATA").expect("BORSAI_E2E_DATA"));
    let python = PathBuf::from(std::env::var("BORSAI_E2E_PYTHON").expect("BORSAI_E2E_PYTHON"));
    std::fs::create_dir_all(&data).expect("uygulama verisi dizini");
    let ctx = RepoCtx { root: repo.clone(), python };
    Env { repo, data: data.canonicalize().expect("data"), ctx, state: AppState::from_embedded() }
}

fn say(line: &str) {
    println!("E2E| {line}");
}

fn day(offset: i64) -> String {
    let now = SystemTime::now().duration_since(UNIX_EPOCH).expect("saat").as_secs() as i64;
    istanbul(now + offset * 86_400).0
}

fn sha_list(dir: &Path) -> Vec<(String, String)> {
    fn walk(p: &Path, out: &mut Vec<PathBuf>) {
        let Ok(rd) = std::fs::read_dir(p) else { return };
        for e in rd.flatten() {
            let path = e.path();
            if path.is_dir() {
                walk(&path, out);
            } else {
                out.push(path);
            }
        }
    }
    let mut files = Vec::new();
    walk(dir, &mut files);
    files.sort();
    files
        .iter()
        .map(|f| {
            let bytes = std::fs::read(f).unwrap_or_default();
            (f.display().to_string(), borsai_app_lib::commands::models::sha256_hex(&bytes))
        })
        .collect()
}

/// Uygulamanın kopyalayacağı küçük PDF'ler (betik yerine test üretir; içerik kurgusaldır).
fn write_pdf(path: &Path, tag: &str) {
    let body = format!("%PDF-1.4\n% BorsAi e2e {tag}\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n");
    std::fs::create_dir_all(path.parent().expect("dizin")).expect("dizin");
    std::fs::write(path, body).expect("pdf");
}

fn doc(dir: &Path, id: &str, kind: &str, name: &str, published_day: &str) -> borsai_app_lib::commands::source_docs::SourceDocReq {
    let p = dir.join(name);
    write_pdf(&p, id);
    borsai_app_lib::commands::source_docs::SourceDocReq {
        source_id: id.into(),
        kind: kind.into(),
        document_id: format!("KURGUSAL {id}"),
        published_at: format!("{published_day}T10:00:00+03:00"),
        published_at_basis: "E2E_FIXTURE: kurgusal belge, yayın zamanı betikte sabit".into(),
        path: p.display().to_string(),
        file_name: Some(name.into()),
        title: Some("Kurgusal test belgesi".into()),
        url: None,
        issuer: None,
    }
}

// ---------------------------------------------------------------- girdi belgesi taslağı

fn f(value: Option<&str>, source: &str, quote: &str, extra: Value) -> Value {
    let mut v = match value {
        Some(v) => json!({"value": v, "source_id": source, "quote": quote}),
        None => json!({"value": null, "missing_reason": quote}),
    };
    if let Some(o) = extra.as_object() {
        for (k, val) in o {
            v[k] = val.clone();
        }
    }
    v
}

/// Kurgusal arz: PB aşamasında talep sonrası alanlar boş, POST aşamasında dolu.
fn inputs_req(ticker: &str, stage: &str, t: &str, pub_day: &str) -> InputsDocReq {
    let pb = stage == "PRE_BOOKBUILD";
    let kap = "KAP_E2E_SONUC";
    let spk = "SPK_E2E_BULTEN";
    let ek = "KAP_E2E_EK";
    let q = |name: &str| format!("kurgusal belgede: {name}");
    let mut fields = Map::new();
    let mut put = |k: &str, v: Value| {
        fields.insert(k.to_string(), v);
    };
    let empty_pb = "talep toplama henüz yapılmadı (PB aşaması)";
    put("ipo_price_tl", f(Some("25.52"), kap, &q("HALKA ARZ FİYATI"), json!({})));
    put("post_ipo_share_capital", f(Some("312500000"), kap, &q("yeni sermaye"), json!({})));
    put("capital_increase_shares", f(Some("62500000"), kap, &q("bedelli"), json!({})));
    for (k, v) in [("shares_offered", "87500000"), ("existing_share_sale_shares", "25000000"), ("additional_sale_shares", "0")] {
        put(k, if pb { f(None, "", empty_pb, json!({})) } else { f(Some(v), kap, &q(k), json!({})) });
    }
    put("ipo_size_tl", if pb { f(None, "", empty_pb, json!({})) } else { f(Some("2233000000"), kap, &q("büyüklük"), json!({})) });
    put(
        "total_demand_multiple",
        if pb {
            f(None, "", empty_pb, json!({}))
        } else {
            f(Some("2.84"), ek, &q("toplamda 2,84 katı talep"), json!({"origin": "SOURCE_REPORTED"}))
        },
    );
    put(
        "total_demand_filter_status",
        if pb { f(None, "", "f3 yok; filtre durumu uygulanamaz", json!({})) } else { f(Some("NOT_SPECIFIED"), ek, &q("filtre ifadesi yok"), json!({})) },
    );
    for (k, v) in [
        ("ipo_price_try", "25.52"),
        ("planned_pre_ipo_capital", "250000000"),
        ("planned_post_ipo_capital", "312500000"),
        ("planned_capital_increase_shares", "62500000"),
        ("planned_existing_share_sale", "25000000"),
        ("planned_base_offer_shares", "87500000"),
        ("planned_additional_sale_ceiling", "0"),
        ("planned_max_offer_shares", "87500000"),
    ] {
        put(k, f(Some(v), spk, &q(k), json!({})));
    }
    put("first_trading_date", f(Some(t), kap, &q("ilk işlem günü"), json!({})));
    put("bookbuilding_start", f(Some(&day(-3)), spk, &q("talep toplama başlangıcı"), json!({})));
    put("bookbuilding_end", f(Some(&day(-1)), spk, &q("talep toplama bitişi"), json!({})));
    let _ = pub_day;
    InputsDocReq {
        ticker: ticker.into(),
        company: "Kurgusal Sentetik A.Ş. (e2e)".into(),
        stage: stage.into(),
        first_trading_date_source: Some(kap.into()),
        collection_rules: vec!["Kurgusal arz: belgeler betik tarafından üretildi; yalnız uçtan uca akış testi.".into()],
        fields: fields.into_iter().collect(),
        collected_at: None,
    }
}

fn prepare(e: &Env, ticker: &str, pub_day: &str) {
    let downloads = e.data.join("downloads").join(ticker);
    let docs = vec![
        doc(&downloads, "KAP_E2E_SONUC", "KAP_NOTIFICATION_PDF", "kap_e2e_sonuc.pdf", pub_day),
        doc(&downloads, "KAP_E2E_EK", "KAP_ATTACHMENT_PDF", "kap_e2e_ek.pdf", pub_day),
        doc(&downloads, "SPK_E2E_BULTEN", "SPK_BULLETIN", "spk_e2e_bulten.pdf", pub_day),
    ];
    let v = borsai_app_lib::commands::source_docs::copy_source_docs_in(&e.repo, ticker, &docs).expect("adım 2");
    say(&format!("adım 2 kaynak belgeler: {} dosya → {}", v.documents.len(), v.rel_dir));
}

fn write_doc(e: &Env, req: &InputsDocReq, confirm: bool) -> String {
    let p = preview_inputs_doc_in(&e.repo, req, true, confirm).expect("adım 3");
    assert!(p.problems.is_empty(), "Rust validate_inputs: {:?}", p.problems);
    let doc: Value = serde_json::from_slice(&std::fs::read(e.repo.join(&p.rel_path)).expect("belge")).expect("json");
    assert_eq!(validate_inputs(&doc), Vec::<String>::new());
    say(&format!("adım 3 girdi belgesi: {} (sha {}…)", p.rel_path, &p.sha256[..12]));
    let pit = inputs_pit_in(&e.ctx, &p.rel_path).expect("adım 4");
    assert!(pit.is_empty(), "Python inputs_pit_problems: {pit:?}");
    say(&format!("adım 4 yetkili denetim (Python): sorun yok ({})", p.rel_path));
    p.rel_path
}

/// Geçici klonun TÜFE tablosu verilen T'lerin ayını (T − 2) kapsamıyorsa ay sonuna kurgusal satır ekler (YALNIZ klonda;
/// önek pini ekleme ile değişmez, EK 3 §3.1). Bugün (2026-09/10) gerekmez; tablo bir ay geride kalınca akış sürer.
fn ensure_tufe_months(repo: &Path, ts: &[&str]) {
    use borsai_predict::tufe;
    let path = borsai_app_lib::commands::predict::tufe_path_in(repo);
    let mut text = std::fs::read_to_string(&path).expect("klonun TÜFE tablosu");
    let need = ts.iter().filter_map(|t| tufe::month_for(t)).max().unwrap_or_default();
    loop {
        let table = tufe::parse(text.as_bytes()).expect("klonun TÜFE tablosu ayrıştırılır");
        if table.last_month() >= need.as_str() {
            break;
        }
        let m = tufe::month_add(table.last_month(), 1);
        let rel = format!("{}-03", tufe::month_add(&m, 1));
        text.push_str(&format!("{m},100,{rel},1,https://example.invalid/e2e,{}\n", "0".repeat(64)));
        say(&format!("klon TÜFE tablosuna kurgusal {m} satırı eklendi (yalnız klonda)"));
    }
    std::fs::write(&path, text).expect("klon TÜFE tablosu");
}

// ---------------------------------------------------------------- U28, U30, U31, U32

// Repo modu ve sembolik bağ vakaları (B1): yalnız unix (FAZ9_WINDOWS K-WIN-3, K-WIN-4).
#[cfg(unix)]
#[test]
#[ignore = "BORSAI_E2E_REPO/DATA/PYTHON (geçici klon) ister: bash app/tests/e2e_freeze_tmp_repo.sh --ignored ile koşar"]
fn freeze_flow() {
    let e = env();
    let registry_before = sha_list(&e.repo.join("registry"));
    let t_future = day(5);
    ensure_tufe_months(&e.repo, &[&t_future, &day(-1)]);

    // adım 1: ön koşullar. borsai GEÇİCİ KLONDAN yüklenmeli (PYTHONPATH sızıntısı = asıl repoya yazma).
    let pre = preflight_in(&e.ctx, &e.state.embedded_index_sha(), Some(&t_future));
    assert!(pre.borsai_in_repo, "DUR: borsai {:?} geçici klon altında değil", pre.borsai_file);
    assert!(pre.index_match, "gömülü INDEX repo ile eşit değil");
    assert!(pre.ok, "ön koşullar: {:?}", pre.blockers);
    say(&format!(
        "adım 1 ön koşullar: git HEAD {}, INDEX sha eşit, borsai = {}",
        &pre.git_head.clone().unwrap_or_default()[..12],
        pre.borsai_file.clone().unwrap_or_default()
    ));
    say(&format!("adım 1 git status -- registry: {:?}", pre.git_status_registry.trim()));
    assert_eq!(pre.t_level, "NONE");

    // --- 1. kayıt: PB (talep toplama öncesi)
    prepare(&e, "SNTA1", &day(-1));
    let pb_rel = write_doc(&e, &inputs_req("SNTA1", "PRE_BOOKBUILD", &t_future, &day(-1)), false);
    assert_eq!(pb_rel, "registry/inputs/SNTA1.PB.json");
    let pb = freeze_in(&e.state, &e.ctx, &e.state.embedded_index_sha(), &pb_rel).expect("PB dondur");
    say(&format!("adım 6 kayıt (PB): {} · model sayısı: {}", pb.record_rel_path, pb.n_models));
    say(&parity_line(&pb.parity));
    assert!(pb.parity.ok(), "parite uyuşmazlığı: {:?}", pb.parity.mismatches);
    assert_eq!(pb.parity.n_supported, e.state.models.as_ref().unwrap().models.len());
    assert_eq!(pb.parity.n_matched, pb.parity.n_supported);
    assert_eq!(pb.n_models, pb.parity.n_supported + pb.parity.unsupported.len());
    // dosya adı içerik sha'sıyla tutarlı
    let bytes = std::fs::read(e.repo.join(&pb.record_rel_path)).expect("kayıt");
    let sha12 = &borsai_app_lib::commands::models::sha256_hex(&bytes)[..12];
    assert!(pb.record_file.contains(sha12), "{} dosya adı içerik sha'sını taşımalı", pb.record_file);
    // U30: uygulama verisinde kaydın kopyası YOK (sicil yalnız repoda)
    let copies = sha_list(&e.data).into_iter().filter(|(p, _)| p.ends_with(&pb.record_file)).count();
    assert_eq!(copies, 0, "kayıt kopyası uygulama verisinde olmamalı");
    say(&format!("U30 uygulama verisinde kayıt kopyası: {copies}"));
    // U32: komut bloğu
    let todo = pb.todo.join("\n");
    assert!(todo.contains("git rev-parse HEAD") && todo.contains("-m borsai.push_proof"), "{todo}");
    assert!(!todo.contains("\n#") && !todo.starts_with('#'), "komut bloğunda yorum satırı olmaz");
    assert!(todo.contains(&pb_rel), "git add doğru girdi dosyasını göstermeli:\n{todo}");
    say("adım 6 'Şimdi yapılacaklar' bloğu:");
    for l in &pb.todo {
        say(&format!("    {l}"));
    }

    // --- 2. kayıt: talep katlı (aynı arz, ikinci aşama)
    let post_rel = write_doc(&e, &inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", &t_future, &day(-1)), false);
    assert_eq!(post_rel, "registry/inputs/SNTA1.json");
    let post = freeze_in(&e.state, &e.ctx, &e.state.embedded_index_sha(), &post_rel).expect("POST dondur");
    say(&format!("ikinci kayıt (talep katlı) yazıldı: {} · model sayısı: {}", post.record_rel_path, post.n_models));
    say(&parity_line(&post.parity));
    assert!(post.parity.ok());

    // --- aynı girdi + aynı INDEX ile üçüncü çağrı: DUPLICATE_RECORD
    let dup = freeze_in(&e.state, &e.ctx, &e.state.embedded_index_sha(), &post_rel).expect_err("aynı girdi ikinci kez reddedilmeli");
    assert_eq!(dup.code, "FREEZE_DUPLICATE_RECORD");
    say(&format!("DUPLICATE_RECORD: {}", dup.detail.clone().unwrap_or_default().trim().lines().last().unwrap_or_default()));

    // --- iptal (T gelecekte olduğu için Python kabul eder)
    let cancel = cancel_in(&e.ctx, &post.record_rel_path, "kurgusal: e2e testi, ikinci kayıt geri alınıyor").expect("iptal");
    say(&format!("iptal kaydı: {} · iptal edilen: {} · neden: {}", cancel.cancel_rel_path, cancel.cancels, cancel.reason));
    assert_eq!(cancel.cancels, post.record_file);
    assert_eq!(cancel_in(&e.ctx, &post.record_rel_path, "   ").unwrap_err().code, "INVALID_ARGUMENT", "boş neden reddedilir");

    // --- U31: T = dün → kırmızı uyarı; iptal Python tarafından reddedilir
    let t_past = day(-1);
    let pre_red = preflight_in(&e.ctx, &e.state.embedded_index_sha(), Some(&t_past));
    assert_eq!(pre_red.t_level, "RED");
    say(&format!("U31 adım 5: T = {t_past} ≤ bugün ({}) → KIRMIZI uyarı", pre_red.today_istanbul));
    prepare(&e, "SNTB2", &day(-4));
    let late_rel = write_doc(&e, &inputs_req("SNTB2", "POST_BOOKBUILD_PRE_LISTING", &t_past, &day(-4)), false);
    let late = freeze_in(&e.state, &e.ctx, &e.state.embedded_index_sha(), &late_rel).expect("geç kayıt");
    say(&format!("U31 geç kayıt yazıldı: {} · model sayısı: {}", late.record_rel_path, late.n_models));
    let err = cancel_in(&e.ctx, &late.record_rel_path, "kurgusal: geç kayıt iptali").unwrap_err();
    assert_eq!(err.code, "FREEZE_CANCEL_AFTER_T");
    say(&format!("U31 iptal reddi (Python): {}", err.detail.clone().unwrap_or_default().trim().lines().last().unwrap_or_default()));

    // --- sicil ekranı: kayıtlar, iptal bağı, desteklenmeyen modeller
    let ids: Vec<String> = e.state.models.as_ref().unwrap().models.iter().map(|m| m.model_id.clone()).collect();
    let shas: Vec<(String, String)> =
        e.state.models.as_ref().unwrap().models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect();
    let view = registry_view_in(&e.repo, &ids).expect("sicil");
    let snta1 = view.tickers.iter().find(|t| t.ticker == "SNTA1").expect("SNTA1");
    assert_eq!(snta1.records.len(), 3, "2 tahmin + 1 iptal");
    assert_eq!(snta1.n_active, 1, "ikinci kayıt iptal edildi");
    let active = snta1.records.iter().find(|r| r.file == pb.record_file).expect("PB kaydı");
    assert!(active.cancelled_by.is_none() && !active.tracked, "kayıt commit edilmemiş (uygulama commit atmaz)");
    assert_eq!(active.unsupported_models.len(), pb.parity.unsupported.len());
    say(&format!(
        "sicil: SNTA1 {} kayıt, etkin {}; desteklenmeyen model: {}",
        snta1.records.len(),
        snta1.n_active,
        active.unsupported_models.iter().map(|m| m.model_id.as_str()).collect::<Vec<_>>().join(", ")
    ));
    // U38 yolu: koşullu değerler kayıttaki S'ten
    let rc = record_ceiling_in(&e.repo, "SNTA1", &pb.record_file, 2, &ids, &shas).expect("arz sayfası");
    assert!(!rc.models.is_empty() && rc.unsupported_models.len() == pb.parity.unsupported.len());
    say(&format!(
        "arz sayfası: {} model render (tavan serisi eğrisi {} model), uygulamada olmayan {}",
        rc.models.len(),
        rc.display.rows.len() - 1,
        rc.unsupported_models.len()
    ));

    // U50 → U59 (EK 3 §10.1) → U80 (P4): yeni kayıt INDEX'teki 27 modeli içerir; Rust parite 27/27 (kayıttaki tufe_index
    // ile), uygulamada olmayan yok; `tufe` bloğu ve `model_inputs.tufe_index`. Eski 7 kayıt "16/16 + kayıtta yok: 11".
    assert_eq!(pb.n_models, 27, "yeni kayıt INDEX'teki 27 modeli içerir");
    assert_eq!((pb.parity.n_supported, pb.parity.n_matched), (27, 27), "parite 27/27");
    assert!(pb.parity.unsupported.is_empty(), "uygulamada olmayan model yok: {:?}", pb.parity.unsupported);
    assert!(pb.parity.missing_in_record.is_empty(), "yeni kayıtta eksik model yok");
    let rec: Value = serde_json::from_slice(&std::fs::read(e.repo.join(&pb.record_rel_path)).expect("kayıt")).expect("json");
    let tb = &rec["tufe"];
    assert!(tb.is_object() && tb["refusal"].is_null(), "kayıt tufe bloğu: {tb}");
    assert_eq!(rec["model_inputs"]["tufe_index"], tb["index"], "model_inputs.tufe_index = tufe bloğunun endeksi");
    assert!(rec["model_inputs"]["tufe_index"].is_string());
    // PB kaydında V1.5 girdileri yok: v1 üçü girdi reddi verir (TÜFE'den önce; TUFE_* değil); talep katlı kayıtta
    // real/pooled TÜFE ile dolu
    for id in ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"] {
        let c = rec["models"].as_array().unwrap().iter().find(|c| c["model_id"] == json!(id)).expect("hücre");
        let code = c["refusal"]["code"].as_str().unwrap_or("");
        assert!(c["status"] == json!("REFUSED") && !code.starts_with("TUFE_"), "PB {id}: {code}");
    }
    let rec2: Value = serde_json::from_slice(&std::fs::read(e.repo.join(&post.record_rel_path)).expect("kayıt")).expect("json");
    assert_eq!(rec2["model_inputs"]["tufe_index"], rec2["tufe"]["index"]);
    for id in ["ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"] {
        let c = rec2["models"].as_array().unwrap().iter().find(|c| c["model_id"] == json!(id)).expect("hücre");
        assert_eq!(c["status"], json!("PREDICTED"), "{id}");
        assert_eq!(c["output"]["tufe_index_used"], rec2["tufe"]["index"], "{id}");
    }
    say(&format!(
        "U59 yeni kayıt: {} model · tufe {} = {} (yayım {}) · {}",
        pb.n_models, tb["month"], tb["index"], tb["release_date"], parity_line(&pb.parity)
    ));
    for t in &view.tickers {
        for r in t.records.iter().filter(|r| r.record_type.as_deref() == Some("PREDICTION") && r.file != pb.record_file) {
            let rec: Value =
                serde_json::from_slice(&std::fs::read(e.repo.join(&r.rel_path)).expect("kayıt")).expect("json");
            if rec["models"].as_array().map(Vec::len) != Some(16) {
                continue;
            }
            let old = compare_record(&rec, &e.state.models.as_ref().unwrap().models);
            assert!(old.ok() && old.missing_in_record.len() == 11 && old.unsupported.is_empty(), "{:?}", old.mismatches);
            say(&format!("U50 eski kayıt {}: {}", r.file, parity_line(&old)));
            break;
        }
    }

    // --- U28: kişisel kayıtlar sicile dokunmaz
    // Kişisel kayıt bölümünün kendi öncesi: dondur akışı registry'ye zaten yazdı.
    let scen_before = sha_list(&e.repo.join("registry"));
    for i in 1..=3 {
        save_scenario_in(&e.state, &e.data, &[e.repo.clone()], &scenario_req(&format!("e2e senaryo {i}"))).expect("senaryo");
    }
    let list = list_scenarios_in(&e.data, &e.state.embedded_index_sha()).expect("liste");
    assert_eq!(list.len(), 3);
    let target = e.data.join("disa_aktarim.json");
    export_scenario_in(&e.data, &[e.repo.clone()], &list[0].scenario_id, &target).expect("dışa aktarma");
    assert!(target.is_file());
    let inside = e.repo.join("registry").join("records").join("kacak.json");
    assert_eq!(
        export_scenario_in(&e.data, &[e.repo.clone()], &list[0].scenario_id, &inside).unwrap_err().code,
        "SCENARIO_PATH_INSIDE_REPO"
    );
    assert!(!inside.exists());
    // tümünü dışa aktarma (§3f): tek JSON dizisi, okunabilen her kayıt; repo altı yine reddedilir
    let all_target = e.data.join("disa_aktarim_tumu.json");
    let all = export_all_scenarios_in(&e.data, &[e.repo.clone()], &all_target).expect("tümünü dışa aktarma");
    assert_eq!((all.n_exported, all.n_unreadable), (list.len(), 0));
    let arr: Value = serde_json::from_slice(&std::fs::read(&all_target).expect("çıktı")).expect("json");
    let items = arr.as_array().expect("tek JSON dizisi");
    assert_eq!(items.len(), list.len());
    for d in items {
        assert_eq!(d["official"], Value::Bool(false));
        assert!(d.get("record_type").is_none(), "kişisel kayıtta record_type olmaz");
    }
    let all_inside = e.repo.join("registry").join("records").join("hepsi.json");
    assert_eq!(
        export_all_scenarios_in(&e.data, &[e.repo.clone()], &all_inside).unwrap_err().code,
        "SCENARIO_PATH_INSIDE_REPO"
    );
    assert!(!all_inside.exists());
    say(&format!(
        "U28: 3 kişisel kayıt saklandı, 1'i ve tümü ({} kayıt) dışa aktarıldı; repo altına tekli ve toplu dışa aktarma reddedildi",
        all.n_exported
    ));
    // B1: sembolik bağ ve `..` hedefleri. Bağlar uygulama verisinde (klonun dışında), hedefleri klonun
    // registry/ ağacında ve henüz YOK; bağ izlenirse kişisel kayıt sicile düşer.
    let links = e.data.join("baglar");
    std::fs::create_dir_all(&links).expect("bağ dizini");
    let reg = e.repo.join("registry");
    let dangling_file = links.join("askida_bag.json");
    std::os::unix::fs::symlink(reg.join("records").join("SNTA1").join("kacak_bag.json"), &dangling_file).expect("bağ");
    let dangling_dir = links.join("askida_dizin");
    std::os::unix::fs::symlink(reg.join("records").join("SNTZ9"), &dangling_dir).expect("bağ");
    let dir_link = links.join("repo_bagi");
    std::os::unix::fs::symlink(&e.repo, &dir_link).expect("bağ");
    let data_link = links.join("appdata_askida");
    std::os::unix::fs::symlink(reg.join("appdata"), &data_link).expect("bağ");
    let hostile: Vec<(&str, PathBuf)> = vec![
        ("askıda dosya bağı", dangling_file),
        ("askıda dizin bağı", dangling_dir.join("kacak.json")),
        ("dizin bağı", dir_link.join("registry").join("records").join("kacak_dizin.json")),
        ("var olmayan ara dizinli ..", dir_link.join("registry").join("yok").join("..").join("records").join("kacak_nokta.json")),
    ];
    let mut bad: Vec<String> = Vec::new();
    let code = |r: Result<String, String>| r.map(|_| "Ok".to_string()).unwrap_or_else(|c| c);
    for (name, t) in &hostile {
        let one = code(export_scenario_in(&e.data, &[e.repo.clone()], &list[0].scenario_id, t).map_err(|x| x.code));
        let many = code(export_all_scenarios_in(&e.data, &[e.repo.clone()], t).map(|r| r.path).map_err(|x| x.code));
        say(&format!("B1 dışa aktarma [{name}]: tekli {one} · toplu {many}"));
        for (what, got) in [("tekli", one), ("toplu", many)] {
            if got != "SCENARIO_PATH_INSIDE_REPO" {
                bad.push(format!("{what} dışa aktarma [{name}] -> {got}"));
            }
        }
    }
    for (name, d) in [
        ("askıda uygulama verisi bağı", data_link),
        ("var olmayan ara dizinli ..", dir_link.join("registry").join("yok").join("..").join("appdata")),
    ] {
        let got = code(save_scenario_in(&e.state, &d, &[e.repo.clone()], &scenario_req("B1")).map(|s| s.scenario_id).map_err(|x| x.code));
        say(&format!("B1 kaydetme [{name}]: {got}"));
        if got != "SCENARIO_PATH_INSIDE_REPO" {
            bad.push(format!("kaydetme [{name}] -> {got}"));
        }
    }
    let reg_now = sha_list(&e.repo.join("registry"));
    if reg_now != scen_before {
        let new: Vec<&String> = reg_now.iter().filter(|x| !scen_before.contains(x)).map(|(p, _)| p).collect();
        bad.push(format!("registry/ değişti: {new:?}"));
    }
    assert!(bad.is_empty(), "B1 yol bekçisi {} vakada açık:\n  {}", bad.len(), bad.join("\n  "));
    say("B1: askıda dosya/dizin bağı, dizin bağı ve `..` hedefleri tekli, toplu ve kaydetmede reddedildi");
    // U28: kişisel kayıt işlemleri geçici klonun registry/ ağacına dokunmadı
    assert_eq!(scen_before, sha_list(&e.repo.join("registry")), "kişisel kayıt işlemleri registry'yi değiştirdi");
    say("U28: kişisel kayıt ve dışa aktarma sonrası registry/ sha listesi öncesiyle aynı");

    // geçici klonun registry'si yalnız dondur akışıyla değişti; asıl repo denetimi betiktedir
    let after = sha_list(&e.repo.join("registry"));
    let changed: Vec<&str> = after
        .iter()
        .filter(|(p, s)| !registry_before.iter().any(|(p2, s2)| p2 == p && s2 == s))
        .map(|(p, _)| p.as_str())
        .collect();
    say(&format!("geçici klon registry: {} yeni/değişen dosya", changed.len()));
    assert!(changed.iter().all(|p| p.contains("/registry/")));
}

/// Ekrandaki parite satırının aynısı (EK 2 §3.7): yeni kayıtlarda `27/27`, eski 16 modelli kayıtlarda
/// `16/16 + kayıtta yok: 11`.
fn parity_line(r: &borsai_app_lib::commands::parity::ParityReport) -> String {
    let mut s = format!("parite: {}/{} desteklenen model, |Δ|max = {:e}", r.n_matched, r.n_supported, r.max_abs);
    if !r.unsupported.is_empty() {
        s += &format!("; uygulamada henüz olmayan: {} ({})", r.unsupported.len(), r.unsupported.join(", "));
    }
    if !r.missing_in_record.is_empty() {
        s += &format!(
            " · kayıt INDEX'ten eski: {} model kayıtta yok ({})",
            r.missing_in_record.len(),
            r.missing_in_record.join(", ")
        );
    }
    s
}

fn scenario_req(title: &str) -> SaveScenarioReq {
    let mut inputs = Map::new();
    for (k, v) in [
        ("ipo_price_tl", "25.52"),
        ("shares_offered", "87500000"),
        ("post_ipo_share_capital", "312500000"),
        ("capital_increase_shares", "62500000"),
        ("existing_share_sale_shares", "25000000"),
        ("additional_sale_shares", "0"),
        ("total_demand_multiple", "2.84"),
        ("total_demand_filter_status", "NOT_SPECIFIED"),
        ("ipo_size_tl", "2233000000"),
        ("ipo_price_try", "25.52"),
        ("planned_pre_ipo_capital", "250000000"),
        ("planned_post_ipo_capital", "312500000"),
        ("planned_capital_increase_shares", "62500000"),
        ("planned_existing_share_sale", "25000000"),
        ("planned_base_offer_shares", "87500000"),
        ("planned_additional_sale_ceiling", "0"),
        ("planned_max_offer_shares", "87500000"),
    ] {
        inputs.insert(k.into(), json!(v));
    }
    SaveScenarioReq {
        title: title.into(),
        stage: "POST_BOOKBUILD_PRE_LISTING".into(),
        ticker_label: Some("SNTA1".into()),
        inputs,
        input_dates: Map::new(),
        f6: F6Doc { origin: "NONE".into(), ..Default::default() },
        observed_streak_user: Some(ObservedStreakUser {
            // U52: tek beyan türü "seri sürüyor" (CEILING); NOT_CEILING/PENDING artık kabul edilmez.
            ticker: Some("SNTA1".into()),
            days: vec![Some("CEILING".into()), Some("CEILING".into()), None],
        }),
    }
}

// ---------------------------------------------------------------- U39

/// Kullanıcı beyanı ve senaryo hiçbir yoldan `data/outcomes`, `registry`, `scores`'a yazılmaz.
#[test]
#[ignore = "BORSAI_E2E_REPO/DATA/PYTHON (geçici klon) ister: bash app/tests/e2e_personal_isolation.sh --ignored ile koşar"]
fn personal_isolation() {
    let e = env();
    let before: Vec<Vec<(String, String)>> =
        ["data/outcomes", "registry", "scores"].iter().map(|d| sha_list(&e.repo.join(d))).collect();

    // şerit: resmi j YALNIZ dosyadan (U52); beyan Rust'a hiç geçmez, imzada parametresi yok
    let outcomes = e.repo.join("data").join("outcomes");
    let first = std::fs::read_dir(&outcomes)
        .ok()
        .and_then(|d| {
            let mut names: Vec<String> = d
                .flatten()
                .filter_map(|x| x.file_name().to_str().and_then(|n| n.strip_suffix(".csv")).map(str::to_string))
                .collect();
            names.sort();
            names.into_iter().next()
        })
        .unwrap_or_else(|| "SNTA1".into());
    let view = streak_view_in(Some(&outcomes), Some(&first)).expect("şerit");
    say(&format!(
        "U39 şerit {first}: j = {:?}, bozuldu = {}, dosya durumu = {} (kaynak yalnız dosya)",
        view.j_observed, view.broken, view.file_status
    ));

    // kişisel kayıt: beyan yalnız uygulama verisinde
    let s = save_scenario_in(&e.state, &e.data, &[e.repo.clone()], &scenario_req("U39 beyanlı senaryo")).expect("senaryo");
    let path = e.data.join("scenarios").join(format!("{}.json", s.scenario_id));
    let text = std::fs::read_to_string(&path).expect("senaryo dosyası");
    assert!(text.contains("observed_streak_user"), "beyan kişisel kayıtta");
    say(&format!("U39 kişisel kayıt: {}", path.display()));

    // resmi kayıt görüntüleme (varsa): yalnız okuma
    let ids: Vec<String> = e.state.models.as_ref().unwrap().models.iter().map(|m| m.model_id.clone()).collect();
    let shas: Vec<(String, String)> =
        e.state.models.as_ref().unwrap().models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect();
    let rv = registry_view_in(&e.repo, &ids).expect("sicil");
    if let Some((t, r)) = rv.tickers.iter().find_map(|t| {
        t.records.iter().find(|r| r.n_ceiling_models > 0 && r.cancelled_by.is_none()).map(|r| (t.ticker.clone(), r.clone()))
    }) {
        let rc = record_ceiling_in(&e.repo, &t, &r.file, 2, &ids, &shas).expect("arz sayfası");
        say(&format!("U39 resmi kayıt görüntülendi: {} ({} model)", rc.rel_path, rc.models.len()));
    }

    let after: Vec<Vec<(String, String)>> =
        ["data/outcomes", "registry", "scores"].iter().map(|d| sha_list(&e.repo.join(d))).collect();
    for (i, name) in ["data/outcomes", "registry", "scores"].iter().enumerate() {
        assert_eq!(before[i], after[i], "{name} değişti");
        say(&format!("U39 {name}: {} dosya, sha listesi aynı", after[i].len()));
    }
}

// ---------------------------------------------------------------- FAZ9_SNAPSHOT K-SNAP-4

/// Uygulama verisi altındaki dosyalar: (göreli yol `/` ayırıcılı, sha256).
fn rel_sha_list(dir: &Path) -> Vec<(String, String)> {
    let prefix = dir.display().to_string();
    sha_list(dir)
        .into_iter()
        .map(|(p, h)| (p.strip_prefix(&prefix).unwrap_or(&p).trim_start_matches(['/', '\\']).replace('\\', "/"), h))
        .collect()
}

/// K-SNAP-4 (U39 eki): kişisel modda gömülü sicil anlık görüntüsü açılışta yazılır; dört ekran (Monitör, Analiz, Sicil,
/// Performans) ve kırılma kartı açılıp beyanlı kişisel kayıt saklandıktan sonra anlık görüntüdeki dosyaların sha'ları aynı,
/// uygulama verisinde `scenarios/` dışında hiçbir dosya değişmez; anlık görüntüye kişisel kayıt yazılamaz; repo'nun
/// `registry`, `data`, `scores` ağaçlarında git durumu değişmez. Ortam istemez (yalnız geçici uygulama verisi;
/// `BORSAI_E2E_SNAP_DATA` verilirse orası); `app/tests/e2e_personal_isolation.sh` de koşturur.
#[test]
fn personal_snapshot_isolation() {
    use borsai_app_lib::commands::ceiling::record_summary_value;
    use borsai_app_lib::commands::registry::{read_record_json_value, record_ceiling_value, registry_view_value};
    use borsai_app_lib::commands::registry_snapshot::SNAPSHOT_DIR;
    use borsai_app_lib::commands::sade::{arz_streak_value, arz_view_value, headline_gate_value, load, monitor_view_value, perf_view_value};
    use borsai_app_lib::commands::sade_break::break_view_value;
    use borsai_app_lib::commands::scenario::SCENARIO_PATH_INSIDE_SNAPSHOT;

    let repo = borsai_app_lib::commands::config::build_repo_root().expect("derleme repo kökü");
    let git_status = || borsai_app_lib::commands::git::git_readonly(&repo, &["status", "--porcelain", "--", "registry", "data", "scores"]).ok();
    let repo_before = git_status();
    let data = match std::env::var_os("BORSAI_E2E_SNAP_DATA") {
        Some(d) => PathBuf::from(d),
        None => std::env::temp_dir().join(format!("borsai_e2e_snap_{}", std::process::id())),
    };
    let _ = std::fs::remove_dir_all(&data);
    std::fs::create_dir_all(&data).expect("uygulama verisi");
    let data = data.canonicalize().expect("uygulama verisi");

    // açılış: kişisel mod (repo ayarı boş) → anlık görüntü yazılır ve doğrulanır
    let state = AppState::from_embedded();
    state.attach_data_dir(&data);
    state.prepare_snapshot();
    let root = state.read_root().expect("anlık görüntü");
    let info = root.snapshot.clone().expect("künye");
    say(&format!(
        "K-SNAP-4 anlık görüntü: {} dosya, {} bayt, derleme {}, son sonuç {:?}, durum {}",
        info.n_files, info.bytes, info.build_sha7, info.last_session, info.status
    ));
    let before = rel_sha_list(&data);
    let snap_prefix = format!("{SNAPSHOT_DIR}/");
    assert!(before.iter().all(|(p, _)| p.starts_with(&snap_prefix)), "açılışta yalnız anlık görüntü yazılır: {before:?}");
    assert_eq!(before.len(), info.n_files + 1, "dosyalar + manifest kopyası");

    // dört ekran ve kırılma kartı (yalnız okuma)
    let m = monitor_view_value(&state).expect("Monitör");
    assert_eq!(m.rows.len(), 7);
    let reg = registry_view_value(&state).expect("Sicil");
    let mut n_calls = 2;
    for row in &m.rows {
        let t = row.ticker.as_str();
        arz_view_value(&state, t).expect("Analiz");
        let brk = break_view_value(&state, t).expect("kırılma kartı");
        let st = arz_streak_value(&state, t).expect("seri");
        let file = row.record_file.as_deref().expect("kayıt");
        let j = st.j_observed.unwrap_or(0);
        record_ceiling_value(&state, t, file, j).expect("koşullu görünüm");
        record_summary_value(&state, t, file, j, st.j_observed).expect("kayıt kartı");
        read_record_json_value(&state, t, file).expect("ham kayıt");
        assert_eq!(brk.status, "OK", "{t}");
        n_calls += 6;
    }
    let loaded = load(&state);
    let perf = perf_view_value(&loaded.docs());
    let gate = headline_gate_value(&loaded.docs());
    assert!(perf.has_post_d1 && perf.has_break);
    n_calls += 2;
    say(&format!(
        "K-SNAP-4 ekranlar: Monitör {} arz, Sicil {} arz / {} kanıt, Performans {} satır, kapı {} çıktı; {n_calls} okuma komutu",
        m.rows.len(),
        reg.tickers.len(),
        reg.proofs.len(),
        perf.rows.len(),
        gate.entries.len()
    ));

    // beyanlı kişisel kayıt: yalnız scenarios/; anlık görüntüye yazılamaz
    let s = save_scenario_in(&state, &data, &state.protected_roots(), &scenario_req("K-SNAP-4 beyanlı senaryo")).expect("senaryo");
    let text = std::fs::read_to_string(data.join("scenarios").join(format!("{}.json", s.scenario_id))).expect("senaryo dosyası");
    assert!(text.contains("observed_streak_user"), "beyan kişisel kayıtta");
    for target in [root.root.join("k.json"), root.root.join("registry").join("records").join("x.json")] {
        let e = export_scenario_in(&data, &state.protected_roots(), &s.scenario_id, &target).unwrap_err();
        assert_eq!(e.code, SCENARIO_PATH_INSIDE_SNAPSHOT, "{}", target.display());
        let e = export_all_scenarios_in(&data, &state.protected_roots(), &target).unwrap_err();
        assert_eq!(e.code, SCENARIO_PATH_INSIDE_SNAPSHOT);
        assert!(!target.exists());
    }

    let after = rel_sha_list(&data);
    let snap = |v: &[(String, String)]| v.iter().filter(|(p, _)| p.starts_with(&snap_prefix)).cloned().collect::<Vec<_>>();
    assert_eq!(snap(&before), snap(&after), "anlık görüntü sha listesi değişmedi");
    let changed: Vec<&(String, String)> =
        after.iter().filter(|x| !before.contains(x)).chain(before.iter().filter(|x| !after.contains(x))).collect();
    assert!(!changed.is_empty() && changed.iter().all(|(p, _)| p.starts_with("scenarios/")), "scenarios/ dışında yazma: {changed:?}");
    say(&format!(
        "K-SNAP-4 anlık görüntü: {} dosyanın sha'sı aynı; değişen yalnız {:?}",
        snap(&after).len(),
        changed.iter().map(|(p, _)| p.as_str()).collect::<Vec<_>>()
    ));
    assert_eq!(git_status(), repo_before, "repo registry/ data/ scores/ git durumu değişmedi");
    say(&format!("K-SNAP-4 repo git status -- registry data scores: {:?} (öncesiyle aynı)", repo_before.as_deref().unwrap_or("git yok")));
    if std::env::var_os("BORSAI_E2E_SNAP_DATA").is_none() {
        let _ = std::fs::remove_dir_all(&data);
    }
}

// ---------------------------------------------------------------- statik tarama (U39)

/// `observed_streak_user` Rust'ta yalnız `commands/scenario.rs`'de geçer; skor/sicil/dondur okuyucuları
/// bu alanı hiçbir yerde okumaz.
#[test]
fn observed_streak_user_only_in_scenario_module() {
    let src = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut files = Vec::new();
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
    walk(&src, &mut files);
    let hits: Vec<String> = files
        .iter()
        .filter(|f| std::fs::read_to_string(f).unwrap_or_default().contains("observed_streak_user"))
        // Windows'ta ayırıcı '\\'; beklenen yol '/' ile yazılı (FAZ9_WINDOWS: yalnız ayırıcı, iddia aynı)
        .map(|f| f.strip_prefix(&src).unwrap_or(f).display().to_string().replace('\\', "/"))
        .collect();
    assert_eq!(hits, vec!["commands/scenario.rs"], "beyan alanı yalnız senaryo modülünde geçmeli");
}

// ---------------------------------------------------------------- ekran görüntüsü hazırlığı

/// YALNIZ `app/scripts/screens.sh`: geçici klona kurgusal `SNTC3` kaynak belgelerini kopyalar,
/// böylece sihirbaz ekran görüntüleri gerçek bir MANIFEST üzerinden alınabilir. Asıl repo'ya
/// dokunulmaz (hedef her zaman `BORSAI_E2E_REPO`).
#[test]
#[ignore = "BORSAI_E2E_REPO/DATA/PYTHON + BORSAI_E2E_SCREENS=1 ister: app/scripts/screens.sh ve bash app/tests/e2e_freeze_tmp_repo.sh --ignored ile koşar"]
fn prepare_screens() {
    let e = env();
    assert_eq!(std::env::var("BORSAI_E2E_SCREENS").as_deref(), Ok("1"), "BORSAI_E2E_SCREENS=1 gerekli (yalnız geçici klon)");
    prepare(&e, "SNTC3", "2026-09-10");
    let m = borsai_app_lib::commands::source_docs::read_manifest(&e.repo, "SNTC3").expect("manifest");
    say(&format!("SNTC3 MANIFEST: {} belge", m["documents"].as_object().map(|o| o.len()).unwrap_or(0)));
}

// ---------------------------------------------------------------- U69 (EK 3 §10.2): D1 sonrası kayıt sihirbazı

/// Geçici klonda Python (uygulamanın kendisi değil, test düzeneği): klonun `.venv` Python'u, cwd = klon.
fn py(e: &Env, code: &str, args: &[&str]) -> String {
    let out = std::process::Command::new(&e.ctx.python)
        .current_dir(&e.repo)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .arg("-c")
        .arg(code)
        .args(args)
        .output()
        .expect("Python çalıştırılamadı");
    assert!(out.status.success(), "Python: {}", String::from_utf8_lossy(&out.stderr));
    String::from_utf8_lossy(&out.stdout).trim().to_string()
}

/// Test düzeneğinin git'i (yalnız klonda): proje sahibinin adım 2 commit'ini taklit eder. Uygulama git'e yazmaz.
fn harness_git(e: &Env, args: &[&str]) -> String {
    let out = std::process::Command::new("git")
        .current_dir(&e.repo)
        .env("GIT_OPTIONAL_LOCKS", "0")
        .args(["-c", "user.name=e2e", "-c", "user.email=e2e@local"])
        .args(args)
        .output()
        .expect("git");
    assert!(out.status.success(), "git {args:?}: {}", String::from_utf8_lossy(&out.stderr));
    String::from_utf8_lossy(&out.stdout).trim().to_string()
}

/// D_1: bugünden en az 3 gün sonraki ilk resmi seans (ardında seans olmalı: T_open hesaplanır). Takvim bittiyse (Python
/// takvim uzatması yapılmadıysa) test açık bir mesajla KIRMIZI olur.
const PY_NEXT_SESSION: &str = "from borsai import outcomes as o; import sys; c = o.load_calendar(); \
s = [x for x in c.sessions if x >= sys.argv[1]]; print(s[0] if len(s) >= 2 else 'NONE')";

/// Kurgusal arzın D_1 bültenleri (THB + THM; kod `<T>.E`, kapanış = üst limit = 28.06, kilitli) ve MANIFEST satırları, ardından
/// `data/outcomes/<T>.csv` (h = 1 OK, h = 2..10 PENDING; bülten sha'ları MANIFEST'le aynı). Python `borsai.outcomes`'un
/// yazıcı yardımcıları ve sabitleri kullanılır (`tests/test_outcomes.py::make_zip` kalıbı); Python kodu değişmez. Bülten
/// adları çalışma anında `local_path` / `internal_name`'den kurulur (metinde ad kalıbı yok).
const PY_SYNTH_D1: &str = r#"
import csv, hashlib, io, sys, zipfile
from borsai import outcomes as oc
d1, ticker = sys.argv[1], sys.argv[2]
code = oc.equity_code(ticker)
heads = {"thb": ["TARIH", "ISLEM  KODU", "BULTEN ADI", "KAPANIS FIYATI", "TOPLAM SOZLESME SAYISI", "GECICI DURDURMA"] + list(oc.THB_D1_COLUMNS.values()),
         "thm": ["TARIH", "ISLEM  KODU", "REFERANS FIYATI", "UST LIMIT FIYATI", "ALT LIMIT FIYATI"]}
rows = {"thb": [d1, code, "KURGUSAL SENTETIK", "28.06", "4000", "0", "28.06", "28.06", "28.06", "8750000", "245525000.00", "28.06", "0", "0"],
        "thm": [d1, code, "25.52", "28.06", "22.98"]}
sha = {}
for kind in ("thb", "thm"):
    head = heads[kind]
    text = "\n".join(";".join(r) for r in [head, [h.lower() for h in head], rows[kind]]) + "\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(oc.internal_name(d1, kind), text.encode("cp1254"))
    data = buf.getvalue()
    path = oc.local_path(d1, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    sha[kind] = hashlib.sha256(data).hexdigest()
    oc._append_csv(oc.BIST_DIR / oc.MANIFEST_NAME, oc.MANIFEST_COLUMNS, {
        "date": d1, "kind": kind, "url": "https://example.invalid/e2e-sentetik", "sha256": sha[kind], "bytes": len(data),
        "internal_filename": oc.internal_name(d1, kind), "downloaded_at": "E2E_SENTETIK", "http_last_modified": ""})
out = io.StringIO(newline="")
w = csv.DictWriter(out, fieldnames=oc.OUTCOME_COLUMNS, lineterminator="\n")
w.writeheader()
w.writerow({"h": 1, "session_date": d1, "close_raw": "28.06", "upper_limit_raw": "28.06", "reference_raw": "25.52",
            "trade_count_raw": "4000", "halt_flag": 0, "half_day": 0, "shifted_by_suspension": 0, "ceiling_close": 1,
            "R_h": "0.0995297805642633", "Y_h": 1, "ipo_price": "25.52", "thb_sha256": sha["thb"], "thm_sha256": sha["thm"],
            "status": "OK"})
for h in range(2, 11):
    w.writerow({**{k: "" for k in oc.OUTCOME_COLUMNS}, "h": h, "status": "PENDING"})
p = oc.outcome_path(ticker)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(out.getvalue(), encoding="utf-8")
print(sha["thb"][:12], sha["thm"][:12])
"#;

#[test]
#[ignore = "BORSAI_E2E_REPO/DATA/PYTHON (geçici klon) ister: bash app/tests/e2e_post_d1_tmp_repo.sh --ignored ile koşar"]
fn post_d1_flow() {
    use borsai_app_lib::commands::post_d1::{
        post_d1_cancel_in, post_d1_commands, post_d1_freeze_in, post_d1_preflight_at, post_d1_view_in, PostD1Todo,
    };
    let e = env();
    let now = || SystemTime::now().duration_since(UNIX_EPOCH).expect("saat").as_secs() as i64;
    let post_sha = borsai_app_lib::embedded::BUILD_INFO.index_post_d1_sha256;
    let index_sha = e.state.embedded_index_sha();
    let ticker = "SNTA1";
    let d1 = py(&e, PY_NEXT_SESSION, &[&day(3)]);
    assert_ne!(d1, "NONE", "DUR: takvim (Python load_calendar) bugünden sonrasını kapsamıyor; takvim uzatılmalı");
    ensure_tufe_months(&e.repo, &[&d1]);
    say(&format!("U69 kurgusal arz {ticker}; D_1 (takvimden, bugün + 3 günden sonraki ilk seans) = {d1}"));
    let commits = || harness_git(&e, &["rev-list", "--count", "HEAD"]);

    // adım 1, listeleme öncesi kayıt YOKKEN: DUR (Python freeze çağrılmaz)
    let p0 = post_d1_preflight_at(&e.ctx, ticker, &index_sha, post_sha, now()).expect("ön koşullar");
    assert!(p0.borsai_in_repo && p0.index_match && p0.index_post_d1_match, "{p0:?}");
    assert_eq!(p0.blockers, vec!["NO_PRE_LISTING_RECORD", "D1_PENDING"]);
    let blocked = post_d1_freeze_in(&e.state, &e.ctx, ticker, now()).unwrap_err();
    assert_eq!(blocked.code, "POST_D1_PREFLIGHT_BLOCKED");
    assert!(!e.repo.join("registry/post_d1").exists(), "engelliyken Python çağrılmaz, kayıt yazılmaz");
    say(&format!("U69 adım 1 (kayıt yokken): DUR {:?}; freeze → {}", p0.blockers, blocked.code));

    // listeleme öncesi kayıt (mevcut dondur akışı; T = D_1)
    prepare(&e, ticker, &day(-1));
    let rel = write_doc(&e, &inputs_req(ticker, "POST_BOOKBUILD_PRE_LISTING", &d1, &day(-1)), false);
    let base = freeze_in(&e.state, &e.ctx, &index_sha, &rel).expect("listeleme öncesi kayıt");
    assert!(base.parity.ok());
    say(&format!("U69 listeleme öncesi kayıt: {} ({} model)", base.record_rel_path, base.n_models));
    let p1 = post_d1_preflight_at(&e.ctx, ticker, &index_sha, post_sha, now()).unwrap();
    assert_eq!((p1.base_records.len(), p1.blockers.clone()), (1, vec!["D1_PENDING"]));
    assert_eq!(p1.first_trading_date.as_deref(), Some(d1.as_str()));

    // adım 2: yalnız komut bloğu (uygulama çalıştırmaz). Proje sahibinin adımını test düzeneği taklit eder: sentetik bülten,
    // MANIFEST satırı, sonuç dosyası; sonra commit.
    let todo2 = post_d1_commands(&e.ctx, &PostD1Todo::Outcomes { through: &d1 });
    assert!(todo2.iter().any(|l| l.ends_with(&format!("-m borsai.outcomes update --through {d1}"))), "{todo2:?}");
    let shas = py(&e, PY_SYNTH_D1, &[&d1, ticker]);
    say(&format!("U69 adım 2 (düzenek): sentetik D_1 bültenleri ve sonuç satırı yazıldı (bülten sha {shas})"));
    let p2 = post_d1_preflight_at(&e.ctx, ticker, &index_sha, post_sha, now()).unwrap();
    assert!(p2.ok && p2.blockers.is_empty(), "{:?}", p2.blockers);
    assert_eq!((p2.d1.as_deref(), p2.d1_status.as_deref()), (Some(d1.as_str()), Some("OK")));
    assert!(!p2.committed && p2.warnings.contains(&"UNCOMMITTED"), "commit bekliyor (sarı)");
    let t_open = p2.t_open.clone().expect("T_open Python'dan");
    assert!(t_open.ends_with("T09:40:00+03:00"), "{t_open}");
    assert!(p2.minutes_to_t_open.unwrap() > 0, "D_1 gelecekte: T_open henüz gelmedi");
    say(&format!("U69 adım 1 (yeniden): T_open = {t_open} (Python registry.t_open; takvimden); kalan {} dk (yerel saat, bilgi)", p2.minutes_to_t_open.unwrap()));
    harness_git(&e, &["add", "data/"]);
    harness_git(&e, &["commit", "-q", "-m", "e2e: sentetik D_1 bültenleri ve sonuç (yalnız klon)", "--", "data/"]);
    let p3 = post_d1_preflight_at(&e.ctx, ticker, &index_sha, post_sha, now()).unwrap();
    assert!(p3.ok && p3.committed, "{p3:?}");
    let commits_before = commits();

    // adım 3: kayıt (Python freeze --post-d1) + Rust paritesi
    let r = post_d1_freeze_in(&e.state, &e.ctx, ticker, now()).expect("D1 sonrası kayıt");
    say(&format!("U69 adım 3 kayıt: {} · D_1 {} · ceiling_close_D1 {} · summary {}", r.record_rel_path, r.d1.clone().unwrap_or_default(),
        r.ceiling_close_d1, r.summary));
    assert!(r.record_rel_path.starts_with(&format!("registry/post_d1/{ticker}/")));
    assert_eq!((r.d1.as_deref(), r.ceiling_close_d1.as_i64()), (Some(d1.as_str()), Some(1)));
    assert_eq!(r.summary["n_predicted"], json!(1));
    assert!(r.parity.ok() && r.parity.n_supported == 1 && r.parity.n_matched == 1, "{:?}", r.parity);
    assert!(r.parity.max_abs <= 1e-9 && r.parity.unsupported.is_empty());
    assert!(r.comparators.failures.is_empty() && r.comparators.n_checked >= 4 && r.comparators.max_abs <= 1e-12, "{:?}", r.comparators);
    assert_eq!(r.t_open.as_deref(), Some(t_open.as_str()));
    say(&format!("U69 parite: {}/{} (maks |Δ| {:e}); comparators_conditional {} karşılaştırıcı, maks |Δ| {:e}",
        r.parity.n_matched, r.parity.n_supported, r.parity.max_abs, r.comparators.n_checked, r.comparators.max_abs));
    // kayıt untracked; uygulama commit atmadı
    let st = harness_git(&e, &["status", "--porcelain", "--", "registry/post_d1"]);
    assert!(st.starts_with("?? registry/post_d1/"), "kayıt git'te izlenmiyor olmalı: {st:?}");
    assert_eq!(commits(), commits_before, "uygulama git commit çalıştırmaz");
    say(&format!("U69 git status -- registry/post_d1: {st:?}; commit sayısı değişmedi ({commits_before})"));
    // adım 4: komut bloğu (uygulama çalıştırmaz)
    let text = r.todo.join("\n");
    assert!(text.contains(&format!("git add registry/post_d1/{ticker}/")) && text.contains("-m borsai.push_proof $(git rev-parse HEAD)"));
    assert!(!text.contains("&&") && r.todo.iter().filter(|l| l.starts_with("git commit")).all(|l| l.contains(" -- ")));
    for l in &r.todo {
        say(&format!("    {l}"));
    }
    // aynı bültenler + aynı base kayıt + aynı ikinci dizin: DUPLICATE_RECORD
    let dup = post_d1_freeze_in(&e.state, &e.ctx, ticker, now()).unwrap_err();
    assert_eq!(dup.code, "POST_D1_DUPLICATE_RECORD");
    // arz sayfası: D1 sonrası satırı kayıttan
    let v = post_d1_view_in(&e.repo, ticker, 1, None).unwrap();
    assert_eq!((v.state, v.active.len()), ("PREDICTED", 1));
    assert!(v.row.as_ref().unwrap().cond.is_some());
    say(&format!("U69 arz sayfası (j = 1): durum {}, yarın bozulma {:.4}", v.state, v.row.as_ref().unwrap().cond.as_ref().unwrap().p_break_next));

    // iptal: T_open'dan önce Python kabul eder
    let c = post_d1_cancel_in(&e.ctx, &r.record_rel_path, "kurgusal: e2e iptal denemesi").expect("T_open'dan önce iptal");
    assert_eq!(c.cancels, r.record_file);
    assert!(c.todo.iter().all(|l| !l.contains("--cancel")), "iptal kaydını uygulama yazdı; blokta tekrar yok");
    assert_eq!(post_d1_view_in(&e.repo, ticker, 1, None).unwrap().state, "NO_RECORD");
    say(&format!("U69 iptal (T_open'dan önce): {} → {}", c.cancel_rel_path, c.cancels));
    // T_open'dan sonra: geçmiş D_1'li kopya (yalnız klonda, düzenek) → Python reddeder; uygulama aynen gösterir
    let mut past: Value = serde_json::from_slice(&std::fs::read(e.repo.join(&r.record_rel_path)).unwrap()).unwrap();
    past["d1"]["session_date"] = json!(day(-30));
    let past_rel = format!("registry/post_d1/{ticker}/20000101T000000Z_000000000001.json");
    std::fs::write(e.repo.join(&past_rel), serde_json::to_vec_pretty(&past).unwrap()).unwrap();
    let late = post_d1_cancel_in(&e.ctx, &past_rel, "kurgusal: T_open sonrası iptal denemesi").unwrap_err();
    assert_eq!(late.code, "POST_D1_CANCEL_AFTER_T_OPEN", "{late:?}");
    say(&format!("U69 T_open sonrası iptal (Python reddi aynen): {}",
        late.detail.clone().unwrap_or_default().trim().lines().last().unwrap_or_default()));
    std::fs::remove_file(e.repo.join(&past_rel)).unwrap();
    assert_eq!(commits(), commits_before, "uygulama git commit çalıştırmaz");
}

/// YALNIZ GELİŞTİRME (EK 3 P2 ekran görüntüleri, `docs/app/p2/ekran`): geçici klonda kurgusal SNTA1 için listeleme öncesi
/// kayıt (mevcut dondur akışı) ve sentetik D_1 bültenleri + sonuç satırı; düzenek ikisini klonda commit'ler (proje sahibinin
/// adım 2'si). D1 sonrası kaydı demo, uygulamanın sihirbazıyla yazar. Asıl repoya dokunulmaz (hedef `BORSAI_E2E_REPO`).
#[test]
#[ignore = "BORSAI_E2E_REPO/DATA/PYTHON + BORSAI_E2E_SCREENS=1 ister: app/scripts/screens_p2.sh ile koşar"]
fn prepare_screens_p2() {
    let e = env();
    assert_eq!(std::env::var("BORSAI_E2E_SCREENS").as_deref(), Ok("1"), "BORSAI_E2E_SCREENS=1 gerekli (yalnız geçici klon)");
    let d1 = py(&e, PY_NEXT_SESSION, &[&day(3)]);
    assert_ne!(d1, "NONE", "takvim bugünden sonrasını kapsamıyor");
    ensure_tufe_months(&e.repo, &[&d1]);
    prepare(&e, "SNTA1", &day(-1));
    let rel = write_doc(&e, &inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", &d1, &day(-1)), false);
    let base = freeze_in(&e.state, &e.ctx, &e.state.embedded_index_sha(), &rel).expect("listeleme öncesi kayıt");
    let shas = py(&e, PY_SYNTH_D1, &[&d1, "SNTA1"]);
    harness_git(&e, &["add", "data/", "registry/"]);
    harness_git(&e, &["commit", "-q", "-m", "ekran: SNTA1 listeleme öncesi kayıt ve sentetik D_1 (yalnız klon)", "--", "data/", "registry/"]);
    say(&format!("SNTA1 hazır: D_1 {d1}; listeleme öncesi kayıt {}; bülten sha {shas}", base.record_rel_path));
}
