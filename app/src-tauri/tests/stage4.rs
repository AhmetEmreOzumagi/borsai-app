//! Aşama 4 (SPEC_APP §7): `scores.json` okuyucu, §2.5 sürüm davranışı ve §2.3 fail-closed bütünlük
//! denetimi (U24, U35'in scores kısmı). Ayrıca doğruluk paneli vitest'lerinin görünüm fixture'larını
//! GERÇEK okuyucudan üretir; ön uç testleri elle yazılmış başlık/karar kullanmaz:
//!
//!   BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage4   # app/tests/fixtures/ui/scores_views.json
use borsai_app_lib::commands::scores::{check_integrity, rules, scores_view_from};
use borsai_app_lib::embedded;
use serde_json::{json, Map, Value};
use std::path::PathBuf;

fn app_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").canonicalize().unwrap()
}

fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

fn scores_text(name: &str) -> String {
    let p = app_dir().join("tests").join("fixtures").join("scores").join(format!("{name}.json"));
    std::fs::read_to_string(&p).unwrap_or_else(|e| panic!("{} okunamadı: {e}", p.display()))
}

fn doc_of(name: &str) -> Value {
    serde_json::from_str(&scores_text(name)).unwrap()
}

fn text_of(doc: &Value) -> String {
    serde_json::to_string(doc).unwrap()
}

fn live_mut<'a>(doc: &'a mut Value, i: usize) -> &'a mut Value {
    doc.get_mut("models").unwrap().get_mut(i).unwrap().get_mut("live").unwrap()
}

/// Bir ihlalin hangi kuralı tetiklediğini sınar ve ihlalli metni geri verir (fixture üretimi için).
fn violation(doc: &Value, rule: &str) -> String {
    let text = text_of(doc);
    let v = scores_view_from(&text, "REPO", embedded::BUILD_INFO.index_sha256).unwrap();
    let p = v.integrity.unwrap_or_else(|| panic!("{rule}: ihlal yakalanmadı"));
    assert_eq!(p.rule, rule, "beklenen kural: {rule}, gelen: {} ({})", p.rule, p.detail);
    assert!(v.doc.is_none(), "{rule}: ihlalde belge gösterilmemeli (fail-closed)");
    text
}

/// §2.3 + görev kararı olarak eklenen iki kural: her ihlal panel yerine hata verir.
#[test]
fn integrity_is_fail_closed() {
    // n < 10 iken canlı hücre (diskteki kasten bozulmuş kopya; ekran görüntüsü de bunu kullanır)
    violation(&doc_of("bad_live_cells"), rules::LIVE_CELLS_BELOW_MIN_N);

    // n < 10 iken betimleyici ölçü (görev kararı)
    let mut d = doc_of("n7");
    live_mut(&mut d, 0)["descriptive"] = doc_of("n35").get("models").unwrap()[0]["live"]["descriptive"].clone();
    violation(&d, rules::LIVE_DESCRIPTIVE_BELOW_MIN_N);

    // n_self_reported_scored < 10 iken self-reported hücre (görev kararı)
    let mut d = doc_of("n12");
    live_mut(&mut d, 0)["self_reported_cells"] = doc_of("n35").get("models").unwrap()[0]["live"]["cells"].clone();
    violation(&d, rules::SELF_REPORTED_CELLS_BELOW_MIN_N);

    // n_live + n_late ≠ n_scored
    let mut d = doc_of("n7");
    live_mut(&mut d, 0)["n_live"] = json!(3);
    violation(&d, rules::LIVE_N_SPLIT);

    // hüküm ama n < 30 (n12'nin hücresi "geçiyor" yapılır)
    let mut d = doc_of("n12");
    live_mut(&mut d, 0)["cells"][0]["verdict"] = json!("geçiyor");
    live_mut(&mut d, 0)["cells"][0]["ci95"] = json!([-0.01, -0.002]);
    violation(&d, rules::VERDICT_WITHOUT_INTERVAL);

    // hüküm ama aralık 0'ı içeriyor (n35, n ≥ 30)
    let mut d = doc_of("n35");
    live_mut(&mut d, 0)["cells"][1]["ci95"] = json!([-0.009, 0.001]);
    violation(&d, rules::VERDICT_WITHOUT_INTERVAL);

    // hüküm ama aralık yok
    let mut d = doc_of("n35");
    live_mut(&mut d, 0)["cells"][1]["ci95"] = Value::Null;
    violation(&d, rules::VERDICT_WITHOUT_INTERVAL);

    // "ayırt edilemiyor" ama aralık 0'ı dışlıyor
    let mut d = doc_of("n35");
    live_mut(&mut d, 0)["cells"][2]["ci95"] = json!([0.001, 0.004]);
    violation(&d, rules::UNDECIDED_WITH_INTERVAL);

    // backtest hücresi de aynı kurala girer (iki terazi aynı denetim)
    let mut d = doc_of("n7");
    d["models"][0]["backtest"]["cells"][0]["n"] = json!(12);
    violation(&d, rules::VERDICT_WITHOUT_INTERVAL);

    // koşullu blok: j'nin kendi n'i < 10 iken hücre (EK 2 §5)
    let mut d = doc_of("conditional");
    let cell = d["models"][0]["conditional"]["by_j"][1]["cells"][0].clone();
    d["models"][0]["conditional"]["by_j"][0]["cells"] = json!([cell]);
    violation(&d, rules::CONDITIONAL_CELLS_BELOW_MIN_N);

    let mut d = doc_of("conditional");
    d["models"][0]["conditional"]["by_j"][1]["n_live"] = json!(0);
    violation(&d, rules::CONDITIONAL_N_SPLIT);

    // sürümü desteklenmeyen koşullu blok denetime girmez (blok gösterilmez, panel açık kalır)
    let d = doc_of("conditional_bad_version");
    assert!(check_integrity(&d).is_none());
}

/// §2.5: scores sürümü farklıysa panel kapalı ve kısmi gösterim yok.
#[test]
fn unsupported_schema_version_closes_panel() {
    let v = scores_view_from(&scores_text("bad_schema_version"), "REPO", embedded::BUILD_INFO.index_sha256).unwrap();
    assert_eq!(v.unsupported_version.as_deref(), Some("borsai.scores/2"));
    assert!(v.doc.is_none() && v.integrity.is_none());
}

/// Başlık alanları (§2.3): kaynak, üretim zamanı, as-of, sha ilk 12, INDEX uyuşmazlığı.
#[test]
fn header_fields_and_index_mismatch() {
    let text = scores_text("n7");
    let v = scores_view_from(&text, "EMBEDDED", embedded::BUILD_INFO.index_sha256).unwrap();
    assert_eq!(v.source, "EMBEDDED");
    assert_eq!(v.generated_at_utc.as_deref(), Some("2027-01-01T00:00:00Z"));
    assert_eq!(v.as_of_session.as_deref(), Some("2027-12-31"));
    assert_eq!(v.sha12.len(), 12);
    assert!(v.synthetic, "sentetik fixture kendini ilan eder");
    assert!(v.index_mismatch, "fixture'ın models_index_sha256'sı gömülü INDEX'ten farklı");
    assert!(v.doc.is_some());

    // Aynı dosya, INDEX sha'sı dosyadakiyle eşitlenince uyarı düşer.
    let sha = doc_of("n7")["inputs"]["models_index_sha256"].as_str().unwrap().to_string();
    assert!(!scores_view_from(&text, "REPO", &sha).unwrap().index_mismatch);
}

/// Gerçek `scores/scores.json` (salt okuma): bütünlük denetimini geçer, 27 model, birincil hücre.
#[test]
fn real_scores_file_passes_integrity() {
    let p = repo_dir().join("scores").join("scores.json");
    let text = std::fs::read_to_string(&p).unwrap();
    let v = scores_view_from(&text, "REPO", embedded::BUILD_INFO.index_sha256).unwrap();
    assert_eq!(v.integrity, None, "gerçek dosya §2.3 kurallarını çiğnememeli");
    let doc = v.doc.unwrap();
    let models = doc["models"].as_array().unwrap();
    assert_eq!(models.len(), 27);
    // Canlı taraf: hiçbir modelde n ≥ 10 yok -> hiçbir blokta hücre olamaz (§8).
    for m in models {
        let live = &m["live"];
        assert!(live["n_scored"].as_u64().unwrap() < 10, "{}", m["model_id"]);
        assert_eq!(live["cells"].as_array().unwrap().len(), 0, "{}", m["model_id"]);
        assert_eq!(live["descriptive"].as_array().unwrap().len(), 0, "{}", m["model_id"]);
    }
    let path = models.iter().find(|m| m["model_id"] == "ceiling_path_v0").unwrap();
    let primary = path["backtest"]["cells"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["label"] == "birincil")
        .unwrap();
    assert_eq!(primary["output"], "return");
    assert_eq!(primary["horizon_or_k"], "D5");
    assert_eq!(primary["metric"], "MAE");
    assert_eq!(primary["rule_id"], "base_train_median");
    assert_eq!(primary["n"], 85);
    assert_eq!(primary["diff"].as_f64().unwrap(), -0.11584504217482987);
    assert_eq!(primary["ci95"][0].as_f64().unwrap(), -0.16113888842455296);
    assert_eq!(primary["ci95"][1].as_f64().unwrap(), -0.07382121777510785);
}

/// vitest görünüm fixture'ları: başlık ve §2.3/§2.5 kararları gerçek okuyucudan; belge dosyası
/// `doc_file` ile gösterilir (aynı JSON iki kez saklanmaz).
#[test]
fn ui_view_fixtures() {
    let mut cases: Vec<(&str, String)> = Vec::new();
    for name in ["n7", "n7_accuracy_rule_null", "n12", "n35", "conditional", "conditional_bad_version", "bad_schema_version"] {
        cases.push((name, scores_text(name)));
    }
    // Öteki bütünlük ihlalleri yalnız burada üretilir (diskte kopyası yoktur).
    cases.push(("bad_live_cells", violation(&doc_of("bad_live_cells"), rules::LIVE_CELLS_BELOW_MIN_N)));

    let mut d = doc_of("n7");
    live_mut(&mut d, 0)["descriptive"] = doc_of("n35")["models"][0]["live"]["descriptive"].clone();
    cases.push(("bad_descriptive", violation(&d, rules::LIVE_DESCRIPTIVE_BELOW_MIN_N)));

    let mut d = doc_of("n12");
    live_mut(&mut d, 0)["self_reported_cells"] = doc_of("n35")["models"][0]["live"]["cells"].clone();
    cases.push(("bad_self_cells", violation(&d, rules::SELF_REPORTED_CELLS_BELOW_MIN_N)));

    let mut d = doc_of("n7");
    live_mut(&mut d, 0)["n_live"] = json!(3);
    cases.push(("bad_split", violation(&d, rules::LIVE_N_SPLIT)));

    let mut d = doc_of("n12");
    live_mut(&mut d, 0)["cells"][0]["verdict"] = json!("geçiyor");
    live_mut(&mut d, 0)["cells"][0]["ci95"] = json!([-0.01, -0.002]);
    cases.push(("bad_verdict_small_n", violation(&d, rules::VERDICT_WITHOUT_INTERVAL)));

    let mut d = doc_of("n35");
    live_mut(&mut d, 0)["cells"][1]["ci95"] = json!([-0.009, 0.001]);
    cases.push(("bad_verdict_ci_zero", violation(&d, rules::VERDICT_WITHOUT_INTERVAL)));

    let mut out = Map::new();
    for (name, text) in cases {
        let v = scores_view_from(&text, "REPO", embedded::BUILD_INFO.index_sha256).unwrap();
        let mut m = serde_json::to_value(&v).unwrap();
        let has_doc = m["doc"].is_object();
        m.as_object_mut().unwrap().remove("doc");
        // Belge diskteki kaynak fixture'dır; ihlalli ve sürümü bozuk örneklerde belge YOKTUR.
        m["doc_file"] = if has_doc { json!(format!("{name}.json")) } else { Value::Null };
        out.insert(name.to_string(), m);
    }
    let path = app_dir().join("tests").join("fixtures").join("ui").join("scores_views.json");
    let text = borsai_app_lib::commands::scenario::pretty(&Value::Object(out));
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&path, &text).unwrap();
        return;
    }
    let disk = std::fs::read_to_string(&path).unwrap_or_default();
    assert!(
        disk == text,
        "{} güncel değil; BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage4 ile yeniden üretin",
        path.display()
    );
}

// ---------------------------------------------------------------- EK 3 §6.5 (U70 Rust tarafı): scores_post_d1.json

/// Gerçek `scores/scores_post_d1.json` (salt okuma) bütünlük denetimini geçer: hücre yok, n = 0, `retro_info` 7 (n'e girmez);
/// sentetik n = 12 / n = 35 geçer; n = 8 iken hücre → CONDITIONAL_CELLS_BELOW_MIN_N; küçük n'de "geçiyor" → hüküm kuralı;
/// sürüm farklı → belge yok. vitest görünümleri: `fixtures/ui/scores_post_d1_views.json` (`doc_file`).
#[test]
fn scores_post_d1_reader() {
    use borsai_app_lib::commands::scores::{post_d1_live_of, scores_post_d1_from};
    let real = repo_dir().join("scores").join("scores_post_d1.json");
    let v = scores_post_d1_from(&std::fs::read_to_string(&real).unwrap(), &real).unwrap();
    assert_eq!((v.status, v.integrity.clone(), v.unsupported_version.clone()), ("REPO", None, None));
    let doc = v.doc.unwrap();
    let b = &doc["models"][0]["conditional_j1"];
    assert_eq!((b["n_scored"].as_u64(), b["n_retro"].as_u64(), b["cells"].as_array().unwrap().len()), (Some(0), Some(7), 0));
    assert_eq!(doc["retro_info"].as_array().unwrap().len(), 7);
    assert_eq!(b["scale"], json!("live_post_d1"));
    let live = post_d1_live_of(&doc, "post_d1_hazard_v0");
    assert_eq!((live.n_scored, live.verdict), (Some(0), None));
    let card = &doc["models"][0]["card"];
    assert!(card.get("training_cutoff").is_none(), "H43: kartta training_cutoff yok");
    assert!(card["training_last_session_date"].is_string() && card["spec_training_cutoff"].is_string());

    let path = |n: &str| app_dir().join("tests").join("fixtures").join("scores").join(n);
    let mut out = Map::new();
    let mut add = |name: &str, text: String, file: Option<&str>| {
        let v = scores_post_d1_from(&text, &path(file.unwrap_or("x.json"))).unwrap();
        let mut m = serde_json::to_value(&v).unwrap();
        let has_doc = m["doc"].is_object();
        let o = m.as_object_mut().unwrap();
        o.remove("doc");
        o.insert("path".into(), json!(file.map(|f| format!("tests/fixtures/scores/{f}"))));
        o.insert("doc_file".into(), if has_doc { json!(file) } else { Value::Null });
        out.insert(name.to_string(), m);
        v
    };
    for n in ["post_d1_n12", "post_d1_n35"] {
        let f = format!("{n}.json");
        let v = add(n, std::fs::read_to_string(path(&f)).unwrap(), Some(&f));
        assert!(v.integrity.is_none() && v.doc.is_some(), "{n}: {:?}", v.integrity);
    }
    let bad = add("post_d1_bad_cells", std::fs::read_to_string(path("post_d1_bad_cells.json")).unwrap(), None);
    assert_eq!(bad.integrity.as_ref().map(|p| p.rule.as_str()), Some(rules::CONDITIONAL_CELLS_BELOW_MIN_N));
    let mut d: Value = serde_json::from_str(&std::fs::read_to_string(path("post_d1_n12.json")).unwrap()).unwrap();
    d["models"][0]["conditional_j1"]["cells"][0]["verdict"] = json!("geçiyor");
    d["models"][0]["conditional_j1"]["cells"][0]["ci95"] = json!([-0.05, -0.01]);
    let v = add("post_d1_bad_verdict", serde_json::to_string(&d).unwrap(), None);
    assert_eq!(v.integrity.as_ref().map(|p| p.rule.as_str()), Some(rules::VERDICT_WITHOUT_INTERVAL));
    let mut d: Value = serde_json::from_str(&std::fs::read_to_string(path("post_d1_n12.json")).unwrap()).unwrap();
    d["schema_version"] = json!("borsai.scores_post_d1/2");
    let v = add("post_d1_bad_version", serde_json::to_string(&d).unwrap(), None);
    assert_eq!((v.unsupported_version.as_deref(), v.doc.is_none()), (Some("borsai.scores_post_d1/2"), true));
    let n35: Value = serde_json::from_str(&std::fs::read_to_string(path("post_d1_n35.json")).unwrap()).unwrap();
    let live = post_d1_live_of(&n35, "post_d1_hazard_v0");
    assert_eq!((live.n_scored, live.verdict), (Some(30), Some(json!("geçiyor"))));

    let file = app_dir().join("tests").join("fixtures").join("ui").join("scores_post_d1_views.json");
    let text = borsai_app_lib::commands::scenario::pretty(&Value::Object(out));
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&file, &text).unwrap();
        return;
    }
    assert!(std::fs::read_to_string(&file).unwrap_or_default() == text, "{} güncel değil (BORSAI_UPDATE_UI_FIXTURES=1)", file.display());
}
