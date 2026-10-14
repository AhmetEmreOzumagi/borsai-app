//! Aşama 3 (SPEC_APP §7) Rust tarafı: girdi belgesi yazıcı (bayt-eşitlik), `validate_inputs` portu,
//! kaynak belge kopyalama + MANIFEST, parite raporu, sicil ekranı ve arz sayfası (U38).
//!
//! Ayrıca vitest'in sicil/dondur fixture'larını üretir ve güncelliğini sınar:
//!   BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage3
mod fixture_cmp;

use borsai_app_lib::commands::freeze::{cancel_todo_commands, preflight_at, preflight_in, todo_commands, FreezeResult};
use borsai_app_lib::commands::inputs_doc::{
    inputs_rel_path, preview_inputs_doc_in, validate_inputs, InputsDocReq,
};
use borsai_app_lib::commands::parity::compare_record;
use borsai_app_lib::commands::registry::{record_ceiling_in, registry_view_in};
use borsai_app_lib::commands::scenario::pretty;
use borsai_app_lib::commands::source_docs::{copy_source_docs_in, SourceDocReq, SOURCE_DOC_CONFLICT};
use borsai_app_lib::json_out::pretty_json_bytes;
use borsai_app_lib::state::{AppState, RepoCtx};
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

fn app_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").canonicalize().unwrap()
}

fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

/// Komut bloğu testleri için repo bağlamı (dosya sistemine dokunulmaz): kök geçici dizinde, Python `default_python`
/// (FAZ9_WINDOWS K-WIN-1); `PY_REL` bloklarda görünen göreli yorumlayıcı yoludur.
fn tmp_repo_ctx(name: &str) -> RepoCtx {
    let root = std::env::temp_dir().join(name);
    RepoCtx { python: borsai_app_lib::commands::config::default_python(&root), root }
}

#[cfg(not(windows))]
const PY_REL: &str = ".venv/bin/python";
#[cfg(windows)]
const PY_REL: &str = ".venv\\Scripts\\python.exe";

fn tmp_dir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("borsai_stage3_{name}_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d.canonicalize().unwrap()
}

fn fixture(name: &str, v: &Value) {
    let path = app_dir().join("tests").join("fixtures").join("ui").join(name);
    let text = pretty(v);
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&path, &text).unwrap();
        return;
    }
    let disk = std::fs::read_to_string(&path).unwrap_or_default();
    // FAZ9_WINDOWS K-WIN-5: macOS'ta bayt bayt (bit-eşitlik); öbür sistemlerde yapı/metin birebir, sayılar 1e-9 (fixture_cmp)
    if cfg!(target_os = "macos") {
        assert!(
            disk == text,
            "{} güncel değil; BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage3 ile yeniden üretin",
            path.display()
        );
    } else {
        fixture_cmp::assert_close(name, &disk, &text, "BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage3 ile yeniden üretin");
    }
}

/// Gerçek skor dosyalarına bağlı fixture: güncellemede yazılır, aksi hâlde yalnız varlığı denetlenir (bayt karşılaştırılmaz).
fn fixture_opt(name: &str, v: &Value, compare: bool) {
    if compare {
        return fixture(name, v);
    }
    let path = app_dir().join("tests").join("fixtures").join("ui").join(name);
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        std::fs::write(&path, pretty(v)).unwrap();
        return;
    }
    assert!(path.is_file(), "{} yok; BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test stage3 ile üretin", path.display());
}

fn supported() -> Vec<String> {
    let state = AppState::from_embedded();
    let models = state.models.as_ref().unwrap();
    models.models.iter().map(|m| m.model_id.clone()).collect()
}

/// Gömülü (model_id, params_sha256) çiftleri: kayıttaki sha ile karşılaştırma (EK 2 §4.3).
fn shas() -> Vec<(String, String)> {
    let state = AppState::from_embedded();
    let models = state.models.as_ref().unwrap();
    models.models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect()
}

// ---------------------------------------------------------------- §3e adım 3: bayt-eşit yazıcı

/// Python `borsai.provenance.pretty_json_bytes`'in aynı belge için ürettiği baytlar (BORSAI_REPO'nun
/// `.venv` Python'u; yoksa test KIRMIZI).
fn python_pretty(repo: &Path, file: &Path) -> Vec<u8> {
    let python = PathBuf::from(std::env::var("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"))
        .join(".venv/bin/python");
    let out = std::process::Command::new(python)
        .current_dir(repo)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .args([
            "-c",
            "import json,sys; from borsai.provenance import pretty_json_bytes; \
             sys.stdout.buffer.write(pretty_json_bytes(json.load(open(sys.argv[1], encoding='utf-8'))))",
            &file.display().to_string(),
        ])
        .output()
        .expect("Python çalıştırılamadı");
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    out.stdout
}

/// Yazıcının iki denetiminde okunan sicil dosyaları: kayıtlar, MANIFEST, INDEX.
fn pretty_written_files(repo: &Path) -> Vec<PathBuf> {
    let mut files: Vec<PathBuf> = vec![repo.join("registry/source_docs/NETGL/MANIFEST.json"), repo.join("models/INDEX.json")];
    for t in ["NETGL", "VEYAS"] {
        files.extend(std::fs::read_dir(repo.join("registry/records").join(t)).unwrap().flatten().map(|e| e.path()));
    }
    files
}

/// Yazıcı Python `pretty_json_bytes` ile BAYT-EŞİT (1): `pretty_json_bytes` ile YAZILMIŞ dosyalar
/// (kayıtlar, MANIFEST, INDEX) diskten okunup yeniden yazıldığında bayt-eşit çıkar. Ortam istemez.
#[test]
fn inputs_doc_bytes_roundtrip() {
    let repo = repo_dir();
    let mut roundtrip = 0;
    let files = pretty_written_files(&repo);
    for path in &files {
        let bytes = std::fs::read(path).unwrap();
        let doc: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(pretty_json_bytes(&doc).unwrap(), bytes, "{}: yeniden yazım bayt-eşit değil", path.display());
        roundtrip += 1;
    }
    assert!(roundtrip >= 4);
}

/// Yazıcı Python `pretty_json_bytes` ile BAYT-EŞİT (2): sicildeki girdi belgeleri
/// (`registry/inputs/*.json`) elle yazıldığı için anahtar sırası `sort_keys` değildir; onlar ve (1)'deki
/// dosyalar Python'un AYNI belge için ürettiği baytlarla karşılaştırılır.
#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn inputs_doc_bytes_match_python() {
    let repo = repo_dir();
    let files = pretty_written_files(&repo);
    let inputs: Vec<PathBuf> = ["NETGL", "VEYAS", "CITAS", "BKRGY"].iter().map(|t| repo.join(format!("registry/inputs/{t}.json"))).collect();
    let mut compared = 0;
    for path in files.iter().chain(&inputs) {
        let doc: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let py = python_pretty(&repo, path);
        assert_eq!(pretty_json_bytes(&doc).unwrap(), py, "{}: Python pretty_json_bytes ile bayt-eşit değil", path.display());
        compared += 1;
    }
    assert!(compared >= 8, "{compared}");
}

/// `validate_inputs` portu: sicildeki belgeler temiz; bozulan belgeler Python'la aynı sorunu verir.
#[test]
fn validate_inputs_port() {
    let repo = repo_dir();
    let doc: Value = serde_json::from_slice(&std::fs::read(repo.join("registry/inputs/NETGL.json")).unwrap()).unwrap();
    assert_eq!(validate_inputs(&doc), Vec::<String>::new());

    let mut bad = doc.clone();
    bad["fields"]["ipo_price_tl"]["source_sha256"] = json!("00");
    assert_eq!(validate_inputs(&bad), vec!["ipo_price_tl: source_sha256 kaynak tablosuyla uyuşmuyor"]);

    let mut bad = doc.clone();
    bad["fields"]["ipo_price_tl"]["value"] = Value::Null;
    assert_eq!(validate_inputs(&bad), vec!["ipo_price_tl: boş alan missing_reason taşımıyor"]);

    let mut bad = doc.clone();
    bad["fields"]["total_demand_multiple"]["origin"] = json!("GUESS");
    assert_eq!(validate_inputs(&bad), vec!["total_demand_multiple: origin 'GUESS'"]);

    let mut bad = doc.clone();
    bad["fields"]["first_trading_date"]["value"] = json!("17.09.2026");
    assert_eq!(validate_inputs(&bad), vec!["first_trading_date: ISO tarih değil ('17.09.2026')"]);

    let mut bad = doc.clone();
    bad["fields"].as_object_mut().unwrap().remove("ipo_size_tl");
    assert_eq!(validate_inputs(&bad), vec!["ipo_size_tl: alan yok"]);

    let mut bad = doc.clone();
    bad["schema_version"] = json!("borsai.inputs/0");
    assert_eq!(validate_inputs(&bad), vec!["schema_version 'borsai.inputs/0'"]);

    let mut bad = doc;
    bad["fields"]["ipo_price_tl"]["source_id"] = json!("YOK");
    assert!(validate_inputs(&bad).iter().any(|p| p == "ipo_price_tl: kaynak 'YOK' kaynak tablosunda yok"));
}

// ---------------------------------------------------------------- §3e adım 2 + 3: kurgusal arz

fn pdf(text: &str) -> Vec<u8> {
    format!("%PDF-1.4\n% {text}\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n").into_bytes()
}

fn doc_req(dir: &Path, id: &str, kind: &str, name: &str, published: &str) -> SourceDocReq {
    let p = dir.join(name);
    std::fs::write(&p, pdf(id)).unwrap();
    SourceDocReq {
        source_id: id.into(),
        kind: kind.into(),
        document_id: format!("KAP {id}"),
        published_at: published.into(),
        published_at_basis: "TEST_FIXTURE".into(),
        path: p.display().to_string(),
        file_name: Some(name.into()),
        title: Some("Test".into()),
        url: None,
        issuer: None,
    }
}

fn field(value: Option<&str>, source: &str, extra: Value) -> Value {
    let mut v = match value {
        Some(v) => json!({"value": v, "source_id": source, "quote": format!("belgede: {v}")}),
        None => json!({"value": null, "missing_reason": "kurgusal arz: alan yok"}),
    };
    if let Some(e) = extra.as_object() {
        for (k, val) in e {
            v[k] = val.clone();
        }
    }
    v
}

fn synthetic_inputs_req(ticker: &str, stage: &str, t: Option<&str>, f3: Option<&str>) -> InputsDocReq {
    let mut fields = Map::new();
    let filled: [(&str, &str); 14] = [
        ("ipo_price_tl", "25.52"),
        ("shares_offered", "87500000"),
        ("post_ipo_share_capital", "312500000"),
        ("capital_increase_shares", "62500000"),
        ("existing_share_sale_shares", "25000000"),
        ("additional_sale_shares", "0"),
        ("ipo_size_tl", "2233000000"),
        ("ipo_price_try", "25.52"),
        ("planned_pre_ipo_capital", "250000000"),
        ("planned_post_ipo_capital", "312500000"),
        ("planned_capital_increase_shares", "62500000"),
        ("planned_existing_share_sale", "25000000"),
        ("planned_base_offer_shares", "87500000"),
        ("planned_max_offer_shares", "87500000"),
    ];
    for (k, v) in filled {
        fields.insert(k.into(), field(Some(v), "KAP_TEST_1", json!({})));
    }
    fields.insert("planned_additional_sale_ceiling".into(), field(Some("0"), "SPK_TEST", json!({})));
    match f3 {
        Some(v) => {
            fields.insert("total_demand_multiple".into(), field(Some(v), "KAP_TEST_2", json!({"origin": "SOURCE_REPORTED"})));
            fields.insert("total_demand_filter_status".into(), field(Some("NOT_SPECIFIED"), "KAP_TEST_2", json!({})));
        }
        None => {
            fields.insert("total_demand_multiple".into(), field(None, "", json!({})));
            fields.insert("total_demand_filter_status".into(), field(None, "", json!({})));
        }
    }
    match t {
        Some(t) => fields.insert("first_trading_date".into(), field(Some(t), "KAP_TEST_1", json!({}))),
        None => fields.insert("first_trading_date".into(), field(None, "", json!({}))),
    };
    fields.insert("bookbuilding_start".into(), field(Some("2030-01-02"), "SPK_TEST", json!({})));
    fields.insert("bookbuilding_end".into(), field(Some("2030-01-03"), "SPK_TEST", json!({})));
    InputsDocReq {
        ticker: ticker.into(),
        company: "Sentetik Test A.Ş.".into(),
        stage: stage.into(),
        first_trading_date_source: Some("KAP_TEST_1".into()),
        collection_rules: vec!["Kurgusal arz: yalnız test.".into()],
        fields: fields.into_iter().collect(),
        collected_at: Some("2030-01-05T10:00:00+03:00".into()),
    }
}

/// Kaynak belgeler kopyalanır ve MANIFEST'e eklenir; var olan giriş değişmez, farklı sha DUR eder.
#[test]
fn source_docs_copy_and_manifest() {
    let repo = tmp_dir("srcdocs");
    let src = repo.join("downloads");
    std::fs::create_dir_all(&src).unwrap();
    let docs = vec![
        doc_req(&src, "KAP_TEST_1", "KAP_NOTIFICATION_PDF", "kap_test_1.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "KAP_TEST_2", "KAP_ATTACHMENT_PDF", "kap_test_2.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "SPK_TEST", "SPK_BULLETIN", "spk_test.pdf", "2030-01-01T10:00:00+03:00"),
    ];
    let v = copy_source_docs_in(&repo, "SNTA1", &docs).unwrap();
    assert_eq!(v.documents.iter().map(|d| d.file_state).collect::<Vec<_>>(), ["NEW", "NEW", "NEW"]);
    assert!(repo.join("registry/source_docs/SNTA1/kap_test_1.pdf").is_file());
    let manifest: Value =
        serde_json::from_slice(&std::fs::read(repo.join("registry/source_docs/SNTA1/MANIFEST.json")).unwrap()).unwrap();
    assert_eq!(manifest["schema_version"], json!("borsai.source_docs/1"));
    assert_eq!(manifest["documents"].as_object().unwrap().len(), 3);
    let downloaded = manifest["documents"]["KAP_TEST_1"]["downloaded_at"].clone();

    // ikinci kez: dosya aynı, MANIFEST girişi korunur (downloaded_at değişmez)
    let again = copy_source_docs_in(&repo, "SNTA1", &docs).unwrap();
    assert_eq!(again.documents[0].file_state, "SAME");
    assert_eq!(again.documents[0].manifest_state, "KEPT");
    assert_eq!(again.manifest["documents"]["KAP_TEST_1"]["downloaded_at"], downloaded);

    // aynı ad, farklı içerik → DUR
    let mut conflict = docs[0].clone();
    let other = src.join("other.pdf");
    std::fs::write(&other, pdf("BASKA")).unwrap();
    conflict.path = other.display().to_string();
    assert_eq!(copy_source_docs_in(&repo, "SNTA1", &[conflict]).unwrap_err().code, SOURCE_DOC_CONFLICT);
    let _ = std::fs::remove_dir_all(&repo);
}

/// Girdi belgesi yazıcı: dosya adı aşamaya göre, kaynak alanları MANIFEST'ten, üzerine yazma onay ister.
#[test]
fn inputs_doc_writer() {
    let repo = tmp_dir("inputsdoc");
    let src = repo.join("downloads");
    std::fs::create_dir_all(&src).unwrap();
    let docs = vec![
        doc_req(&src, "KAP_TEST_1", "KAP_NOTIFICATION_PDF", "kap_test_1.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "KAP_TEST_2", "KAP_ATTACHMENT_PDF", "kap_test_2.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "SPK_TEST", "SPK_BULLETIN", "spk_test.pdf", "2030-01-01T10:00:00+03:00"),
    ];
    copy_source_docs_in(&repo, "SNTA1", &docs).unwrap();

    assert_eq!(inputs_rel_path("SNTA1", "PRE_BOOKBUILD"), "registry/inputs/SNTA1.PB.json");
    assert_eq!(inputs_rel_path("SNTA1", "POST_BOOKBUILD_PRE_LISTING"), "registry/inputs/SNTA1.json");

    let pb = preview_inputs_doc_in(&repo, &synthetic_inputs_req("SNTA1", "PRE_BOOKBUILD", Some("2030-01-10"), None), true, false).unwrap();
    assert_eq!(pb.rel_path, "registry/inputs/SNTA1.PB.json");
    assert!(pb.problems.is_empty() && pb.written && !pb.exists);
    let written: Value = serde_json::from_slice(&std::fs::read(repo.join(&pb.rel_path)).unwrap()).unwrap();
    assert_eq!(validate_inputs(&written), Vec::<String>::new());
    assert_eq!(
        written["fields"]["ipo_price_tl"]["source_path"],
        json!("registry/source_docs/SNTA1/kap_test_1.pdf")
    );
    assert_eq!(written["sources"]["KAP_TEST_1"]["kind"], json!("KAP_NOTIFICATION_PDF"));
    assert!(written["sources"].as_object().unwrap().get("KAP_TEST_2").is_none(), "kullanılmayan kaynak tabloya girmez");
    assert_eq!(std::fs::read(repo.join(&pb.rel_path)).unwrap(), pretty_json_bytes(&written).unwrap());

    // ikinci aşama ayrı dosyaya
    let post = preview_inputs_doc_in(&repo, &synthetic_inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", Some("2030-01-10"), Some("2.84")), true, false).unwrap();
    assert_eq!(post.rel_path, "registry/inputs/SNTA1.json");
    assert!(post.written);

    // aynı istek yeniden: bayt-eşit, fark yok
    let same = preview_inputs_doc_in(&repo, &synthetic_inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", Some("2030-01-10"), Some("2.84")), false, false).unwrap();
    assert!(same.exists && same.identical && same.diff.is_empty());

    // değişen istek: onaysız yazılmaz, fark gösterilir
    let changed = synthetic_inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", Some("2030-01-10"), Some("3.14"));
    let prev = preview_inputs_doc_in(&repo, &changed, false, false).unwrap();
    assert!(prev.exists && !prev.identical && prev.diff.iter().any(|l| l.contains("3.14")));
    assert_eq!(preview_inputs_doc_in(&repo, &changed, true, false).unwrap_err().code, "INPUTS_DOC_EXISTS");
    assert!(preview_inputs_doc_in(&repo, &changed, true, true).unwrap().written);

    // eksik missing_reason / kaynak → belge kurulmaz
    let mut broken = synthetic_inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", Some("2030-01-10"), Some("2.84"));
    broken.fields.insert("ipo_size_tl".into(), json!({"value": null}));
    assert_eq!(preview_inputs_doc_in(&repo, &broken, false, false).unwrap_err().code, "INPUTS_DOC_INVALID");
    let _ = std::fs::remove_dir_all(&repo);
}

// ---------------------------------------------------------------- parite (değişen 1)

/// Parite yalnız desteklenen modelleri karşılaştırır; kayıttaki diğerleri adıyla listelenir (uyuşmazlık değil).
#[test]
fn parity_counts_only_supported_models() {
    let repo = repo_dir();
    let state = AppState::from_embedded();
    let models = &state.models.as_ref().unwrap().models;
    let path = std::fs::read_dir(repo.join("registry/records/NETGL")).unwrap().flatten().next().unwrap().path();
    let mut record: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();

    let report = compare_record(&record, models);
    assert!(report.ok(), "{:?}", report.mismatches);
    // bu kayıt 16 modelli (Faz 4 öncesi): 16/16 karşılaştırılır, 11 model "kayıtta yok" (EK 2 §3.7; EK 3 U59, P4)
    assert_eq!(report.n_supported, report.n_record_models);
    assert_eq!(report.n_matched, report.n_supported);
    assert!(report.unsupported.is_empty());
    assert_eq!(
        report.missing_in_record,
        vec![
            "ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0", "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real",
            "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF", "fall_d10_v0_h99", "fall_d10_v0_pooled",
            "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"
        ],
        "kayıt INDEX'ten eski"
    );
    assert!(report.max_abs <= 1e-9);

    // kayıtta uygulamada olmayan model: sayılmaz, adıyla listelenir
    let cells = record["models"].as_array_mut().unwrap();
    cells.push(json!({"model_id": "zzz_future_model", "params_sha256": "ff", "status": "PREDICTED", "output": {}, "refusal": null}));
    let with_new = compare_record(&record, models);
    assert_eq!(with_new.unsupported, vec!["zzz_future_model"]);
    assert_eq!(with_new.n_supported, with_new.n_record_models - 1);
    assert!(with_new.ok());
    assert_eq!(with_new.n_record_models, 16 + 1, "16 modelli kayıt + kurgusal ek");

    // kasten bozulmuş hücre → uyuşmazlık
    record["models"][0]["output"]["D1"]["return"] = json!(0.5);
    let bad = compare_record(&record, models);
    assert!(!bad.ok() && bad.mismatches[0].model_id == "v1_5_h99");
    assert!(bad.mismatches[0].failures.iter().any(|f| f.contains("D1.return")));
}

// ---------------------------------------------------------------- sicil ekranı ve arz sayfası

fn cell(model_id: &str, s: Option<[f64; 10]>) -> Value {
    json!({
        "model_id": model_id,
        "params_sha256": format!("{:0<64}", model_id.len()),
        "algorithm": "TEST",
        "kind": if s.is_some() { "hazard" } else { "linear" },
        "status": "PREDICTED",
        "refusal": null,
        "output": match s {
            Some(s) => json!({"model_id": model_id, "S": s.to_vec(), "refused": null, "warnings": []}),
            None => json!({"model_id": model_id, "refused": null, "warnings": []}),
        }
    })
}

/// `0.5^k`: Rust `predict_all`'ın üreteceğinden kasten farklı S (U38).
fn half_powers() -> [f64; 10] {
    let mut s = [0.0; 10];
    for (k, v) in s.iter_mut().enumerate() {
        *v = 0.5f64.powi(k as i32 + 1);
    }
    s
}

fn synthetic_record(ticker: &str, at: &str, supported: &[String]) -> Value {
    let mut cells: Vec<Value> = supported
        .iter()
        .map(|m| cell(m, (m.contains("ceiling") || m.contains("km")).then(half_powers)))
        .collect();
    // Uygulamada olmayan (gelecek sürüm) modeller: sicilde adıyla listelenir, render edilmez.
    for m in ["zzz_future_a", "zzz_future_b", "zzz_future_c"] {
        cells.push(cell(m, Some(half_powers())));
    }
    json!({
        "schema_version": "borsai.record/1",
        "record_type": "PREDICTION",
        "ticker": ticker,
        "recorded_at_utc": at,
        "recorded_at_istanbul": "2030-01-05T13:00:00+03:00",
        "code": {"git_head": "0".repeat(40), "borsai_dirty": false},
        "input_sha256": "a".repeat(64),
        "inputs": {"path": format!("registry/inputs/{ticker}.json"), "sha256": "a".repeat(64),
                   "document": {"fields": {"first_trading_date": {"value": "2030-01-10"}}}},
        "model_inputs": {"ipo_price_tl": "25.52"},
        "models_index": {"path": "models/INDEX.json", "sha256": "b".repeat(64)},
        "models": cells,
        "summary": {"n_models": 19, "n_predicted": 19, "n_refused": 0, "refusals": {}}
    })
}

fn write_json(path: &Path, v: &Value) {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, pretty_json_bytes(v).unwrap()).unwrap();
}

/// U52 fixture'ları: resmi sicil görünümü (arz sayfası) j = 2 (resmi) ve j = 3 (beyanlı) için.
/// S kasten geometrik DEĞİL: 0.5^k olsaydı S_k/S_2 ve S_k/S_3 kümeleri çakışır ve U52'nin arama
/// kümesi "aynı ekranda başka kaynaktan da üretilen metinler" kuralıyla boşalırdı.
#[test]
fn u52_record_fixtures() {
    let repo = tmp_dir("u52");
    let ids = supported();
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let curve = [0.83, 0.74, 0.66, 0.53, 0.42, 0.33, 0.25, 0.18, 0.12, 0.07];
    let mut rec = synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids);
    for m in rec["models"].as_array_mut().unwrap() {
        if m["output"]["S"].is_array() {
            m["output"]["S"] = json!(curve.to_vec());
        }
    }
    write_json(&repo.join("registry/records/SNTA1").join(file), &rec);
    let j2 = record_ceiling_in(&repo, "SNTA1", file, 2, &ids, &shas()).unwrap();
    let j3 = record_ceiling_in(&repo, "SNTA1", file, 3, &ids, &shas()).unwrap();
    let row = |rc: &borsai_app_lib::commands::registry::RecordCeiling| {
        rc.display.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap().cond.clone().unwrap()
    };
    assert_ne!(row(&j2).s_cond[9], row(&j3).s_cond[9], "j = 2 ve j = 3 değerleri ayrışmalı");
    fixture("record_ceiling_u52_j2.json", &serde_json::to_value(&j2).unwrap());
    fixture("record_ceiling_u52_j3.json", &serde_json::to_value(&j3).unwrap());
    let _ = std::fs::remove_dir_all(&repo);
}

/// Sicil ekranı: kayıtlar, iptal bağı, desteklenmeyen modeller, okunamayan ve eski sürümlü dosyalar.
#[test]
fn registry_view_synthetic() {
    let repo = tmp_dir("registry");
    let ids = supported();
    let a = "20300105T100000Z_aaaaaaaaaaaa.json";
    let b = "20300105T110000Z_bbbbbbbbbbbb.json";
    let c = "20300105T120000Z_cccccccccccc.json";
    let dir = repo.join("registry/records/SNTA1");
    write_json(&dir.join(a), &synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids));
    write_json(&dir.join(b), &synthetic_record("SNTA1", "2030-01-05T11:00:00Z", &ids));
    write_json(
        &dir.join(c),
        &json!({"schema_version": "borsai.record/1", "record_type": "CANCELLATION", "ticker": "SNTA1",
                "recorded_at_utc": "2030-01-05T12:00:00Z", "recorded_at_istanbul": "2030-01-05T15:00:00+03:00",
                "code": {"git_head": "0".repeat(40)}, "cancels": {"file": b, "sha256": "c".repeat(64)},
                "reason": "kurgusal: girdi belgesinde hatalı f3"}),
    );
    let old = "20300105T130000Z_dddddddddddd.json";
    write_json(&dir.join(old), &json!({"schema_version": "borsai.record/0", "record_type": "PREDICTION"}));
    std::fs::create_dir_all(repo.join("registry/records/SNTB2")).unwrap();
    std::fs::write(repo.join("registry/records/SNTB2/20300105T140000Z_eeeeeeeeeeee.json"), b"{bozuk").unwrap();
    std::fs::create_dir_all(repo.join("registry/push_proofs")).unwrap();
    write_json(
        &repo.join("registry/push_proofs").join(format!("{}.json", "0".repeat(40))),
        &json!({"schema_version": "borsai.push_proof/1", "proven_commit_sha": "0".repeat(40),
                "created_at": "2030-01-05T13:05:00Z"}),
    );
    std::fs::create_dir_all(repo.join("registry")).unwrap();
    std::fs::write(
        repo.join("registry/ipos.csv"),
        "ticker,company,first_trading_date,listing_source_id,status,skip_reason,note,added_at\n\
         SNTA1,Sentetik Test A.Ş.,2030-01-10,KAP_1,FROZEN,,\"kurgusal, test\",2030-01-05T13:00:00+03:00\n",
    )
    .unwrap();

    let v = registry_view_in(&repo, &ids).unwrap();
    assert_eq!(v.tickers.len(), 2);
    let t = &v.tickers[0];
    assert_eq!((t.ticker.as_str(), t.n_active, t.records.len()), ("SNTA1", 1, 4));
    assert_eq!(t.company.as_deref(), Some("Sentetik Test A.Ş."));
    let ra = &t.records[0];
    assert_eq!(ra.n_models, ids.len() + 3);
    assert_eq!(ra.unsupported_models.len(), 3);
    assert_eq!(ra.unsupported_models[0].model_id, "zzz_future_a");
    assert!(ra.cancelled_by.is_none() && !ra.tracked && ra.push_proof.is_none());
    assert_eq!(t.records[1].cancelled_by.as_ref().unwrap().reason, "kurgusal: girdi belgesinde hatalı f3");
    assert_eq!(t.records[2].record_type.as_deref(), Some("CANCELLATION"));
    assert_eq!(t.records[3].status, "UNSUPPORTED_VERSION");
    assert_eq!(v.tickers[1].records[0].status, "UNREADABLE");
    assert_eq!(v.proofs.len(), 1);
    assert_eq!(v.supported_models, ids);

    // U38: koşullu değerler yalnız kayıttaki S'ten (0.5^k → 0.5^(k−j))
    let rc = record_ceiling_in(&repo, "SNTA1", a, 3, &ids, &shas()).unwrap();
    assert!(!rc.models.is_empty());
    assert_eq!(rc.unsupported_models.len(), 3, "uygulamada olmayan modeller render edilmez, adıyla listelenir");
    assert!(rc.unsupported_models.iter().all(|m| m.has_s), "kayıtta S var ama gösterilmez");
    let row = rc.display.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap();
    for k in 4..=10 {
        let expected = 0.5f64.powi(k as i32) / 0.5f64.powi(3);
        assert_eq!(row.cond.as_ref().unwrap().s_cond[k - 1], Some(expected), "k = {k}");
    }
    assert_eq!(rc.ipo_price_tl.as_deref(), Some("25.52"));
    // iptal edilmiş kayıt ve iptal kaydı: koşullu görünüm yok
    assert_eq!(record_ceiling_in(&repo, "SNTA1", b, 0, &ids, &shas()).unwrap_err().code, "RECORD_NOT_ACTIVE");
    assert_eq!(record_ceiling_in(&repo, "SNTA1", c, 0, &ids, &shas()).unwrap_err().code, "RECORD_NOT_ACTIVE");

    let mut fx = serde_json::to_value(&v).unwrap();
    fx["repo_root"] = json!("FIXTURE");
    fx["today_istanbul"] = json!("2030-01-08");
    fixture("registry_synthetic.json", &fx);
    fixture("record_ceiling_j3.json", &serde_json::to_value(&rc).unwrap());
    fixture("record_ceiling_j0.json", &serde_json::to_value(record_ceiling_in(&repo, "SNTA1", a, 0, &ids, &shas()).unwrap()).unwrap());
    let _ = std::fs::remove_dir_all(&repo);
}

/// Asıl repo (salt okuma): sicil ekranı gerçek kayıtları okur, git izleme ve push kanıtı göstergesi çalışır.
#[test]
fn registry_view_real_repo_readonly() {
    let repo = repo_dir();
    let before = std::fs::read_dir(repo.join("registry/records")).unwrap().count();
    let v = registry_view_in(&repo, &supported()).unwrap();
    assert_eq!(v.tickers.len(), before);
    let netgl = v.tickers.iter().find(|t| t.ticker == "NETGL").unwrap();
    assert_eq!(netgl.n_active, 1);
    let r = &netgl.records[0];
    assert_eq!(r.status, "OK");
    assert!(r.tracked && r.added_commit.is_some(), "kayıt git'te izleniyor");
    assert_eq!(r.n_models, 16, "bu kayıt Faz 4 öncesi: 16 model");
    assert!(r.unsupported_models.is_empty());
    assert!(r.n_ceiling_models >= 6);
    // arz sayfası: S kayıttan
    let rc = record_ceiling_in(&repo, "NETGL", &r.file, 3, &supported(), &shas()).unwrap();
    let record: Value = serde_json::from_slice(&std::fs::read(repo.join(&r.rel_path)).unwrap()).unwrap();
    let s: Vec<f64> = serde_json::from_value(
        record["models"].as_array().unwrap().iter().find(|c| c["model_id"] == "ceiling_hazard_v0").unwrap()["output"]["S"].clone(),
    )
    .unwrap();
    let row = rc.display.rows.iter().find(|x| x.model_id == "ceiling_hazard_v0").unwrap();
    assert_eq!(row.s, s, "S doğrudan kayıttan");
    assert_eq!(row.cond.as_ref().unwrap().s_cond[3], Some(s[3] / s[2]));
}

/// U32: "Şimdi yapılacaklar" bloğu; uygulama bu komutları ÇALIŞTIRMAZ.
#[test]
fn todo_block_shape() {
    let repo = tmp_repo_ctx("borsai_x");
    let todo = todo_commands(&repo, "SNTA1", "registry/inputs/SNTA1.PB.json", "registry/records/SNTA1/x.json");
    let text = todo.join("\n");
    assert!(text.contains("git rev-parse HEAD"), "{text}");
    assert!(text.contains("-m borsai.push_proof"), "{text}");
    assert!(text.contains(&format!("{PY_REL} -m borsai.push_proof")), "{text}");
    assert!(text.contains("git add registry/inputs/SNTA1.PB.json registry/source_docs/SNTA1/ registry/records/SNTA1/x.json"));
    assert!(todo.iter().all(|l| !l.trim_start().starts_with('#')), "komut bloğunda yorum satırı olmaz");
    for l in todo.iter().filter(|l| l.starts_with("git commit")) {
        assert!(l.contains(" -- "), "commit yollara sınırlanmalı: {l}");
    }
    // git add ve git commit aynı yolları sayar
    let add: Vec<&str> = todo.iter().find(|l| l.starts_with("git add ") && l.contains("records")).unwrap().split(' ').skip(2).collect();
    let commit = todo.iter().find(|l| l.starts_with("git commit") && l.contains("records")).unwrap();
    let after = commit.split(" -- ").nth(1).unwrap().split(' ').collect::<Vec<_>>();
    assert_eq!(add, after);
    let c = cancel_todo_commands(&repo, "SNTA1", "registry/records/SNTA1/y.json");
    assert!(c.iter().any(|l| l.contains("git add registry/records/SNTA1/y.json")));
}

/// Ön koşullar: gömülü INDEX sha'sı repo'nunkiyle eşit, `borsai` repo altından yükleniyor, T uyarısı.
#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn preflight_real_repo() {
    let root = PathBuf::from(std::env::var("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let ctx = RepoCtx { python: root.join(".venv/bin/python"), root };
    let state = AppState::from_embedded();
    // TÜFE tablosunun son ayını kapsayan T (T'nin ayı − 2 = son ay): ay eksikliği engeli yok
    let table = borsai_predict::tufe::parse(&std::fs::read(borsai_app_lib::commands::predict::tufe_path_in(&ctx.root)).unwrap()).unwrap();
    let t_ok = format!("{}-15", borsai_predict::tufe::month_add(table.last_month(), 2));
    let p = preflight_in(&ctx, &state.embedded_index_sha(), Some(&t_ok));
    assert!(p.index_match, "gömülü INDEX repo ile eşit: {p:?}");
    assert!(p.borsai_in_repo, "{:?}", p.borsai_file);
    assert!(p.git_head.is_some());
    assert!(p.ok && p.blockers.is_empty(), "{:?}", p.blockers);
    let info = p.tufe.as_ref().expect("deflatörlü model var: TÜFE satırı");
    assert_eq!((info.refusal, info.pin_ok, info.month.as_deref()), (None, Some(true), Some(table.last_month())));
    // uzak gelecek: TÜFE ayı dosyada yok → TUFE_MONTH (EK 3 §3.4; Python TufeMissing kayıt yazmaz)
    let far = preflight_in(&ctx, &state.embedded_index_sha(), Some("2999-01-01"));
    assert_eq!((far.blockers.clone(), far.t_level), (vec!["TUFE_MONTH"], "NONE"));
    assert!(far.tufe.as_ref().unwrap().append_command.as_deref().unwrap().contains("--append-month 2998-11 "));
    // T yok: engel değil (T_UNKNOWN reddi), sarı uyarı
    let none = preflight_in(&ctx, &state.embedded_index_sha(), None);
    assert_eq!((none.t_level, none.blockers.is_empty()), ("YELLOW", true));
    assert_eq!(preflight_at(&ctx, &state.embedded_index_sha(), Some("2026-09-17"), "2026-10-05").t_level, "RED");
    // gömülü INDEX'ten farklı repo → DUR
    let bad = preflight_in(&ctx, "0".repeat(64).as_str(), Some(&t_ok));
    assert!(!bad.ok && bad.blockers.contains(&"INDEX_SHA"));
}

/// B3 (§3e adım 1): dondurma, ön koşullar sağlanmadan ÇALIŞMAZ; komut ön uçtan bağımsız olarak
/// ön koşulları kendisi yeniden denetler. Geçici git deposu (INDEX = gömülü INDEX) ve sahte Python:
/// her çağrı günlüğe düşer (gerçek sayaç); `-m borsai.freeze` gerçek yazıcı gibi bir kayıt yazar ve
/// yolunu basar. Sahte gömülü sha (INDEX_SHA) ve repo dışından yüklenen borsai (BORSAI_IMPORT) →
/// `FREEZE_PREFLIGHT_BLOCKED`; Python'un dondurma çağrısı yok, `registry/records` ve
/// `app/parity/incidents` oluşmaz. Pozitif kontrol: doğru sha ile aynı kurulum Python'a ulaşır.
#[cfg(unix)]
#[test]
fn freeze_refuses_when_preflight_blocked() {
    use borsai_app_lib::commands::freeze::freeze_in;
    use std::os::unix::fs::PermissionsExt;
    let repo = tmp_dir("b3_repo");
    let aux = tmp_dir("b3_aux");
    std::fs::create_dir_all(repo.join("models")).unwrap();
    std::fs::write(repo.join("models/INDEX.json"), borsai_app_lib::embedded::INDEX_JSON).unwrap();
    write_json(&repo.join("registry/inputs/SNTP1.json"), &json!({"fields": {"first_trading_date": {"value": "2030-01-10"}}}));
    for args in [&["init", "-q"][..], &["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "t"]] {
        let st = std::process::Command::new("git").current_dir(&repo).args(args).status().unwrap();
        assert!(st.success(), "git {args:?}");
    }
    let state = AppState::from_embedded();
    write_json(&aux.join("record.json"), &synthetic_record("SNTP1", "2030-01-05T10:00:00Z", &supported()));
    let log = aux.join("python_calls.log");
    let python = aux.join("python");
    std::fs::write(
        &python,
        format!(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{log}'\n\
             if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"borsai.freeze\" ]; then\n\
             mkdir -p registry/records/SNTP1 && cp '{rec}' registry/records/SNTP1/20300105T100000Z_aaaaaaaaaaaa.json\n\
             echo \"$PWD/registry/records/SNTP1/20300105T100000Z_aaaaaaaaaaaa.json\"; exit 0; fi\n\
             if [ -e '{outside}' ]; then echo /opt/elsewhere/borsai/__init__.py; else echo \"$PWD/borsai/__init__.py\"; fi\n",
            log = log.display(),
            rec = aux.join("record.json").display(),
            outside = aux.join("borsai_outside").display(),
        ),
    )
    .unwrap();
    std::fs::set_permissions(&python, std::fs::Permissions::from_mode(0o755)).unwrap();
    let ctx = RepoCtx { root: repo.clone(), python };
    let calls = || std::fs::read_to_string(&log).unwrap_or_default();
    let freeze_calls = || calls().lines().filter(|l| l.contains("borsai.freeze")).count();
    let rel = "registry/inputs/SNTP1.json";

    // Bütün vakalar koşar, sapmalar birlikte raporlanır.
    let mut bad: Vec<String> = Vec::new();
    let fake_sha = "0".repeat(64);
    let good_sha = state.embedded_index_sha();
    for (name, sha, outside, blocker) in [
        ("sahte gömülü sha", fake_sha.as_str(), false, "INDEX_SHA"),
        ("borsai repo dışından", good_sha.as_str(), true, "BORSAI_IMPORT"),
    ] {
        if outside {
            std::fs::write(aux.join("borsai_outside"), "").unwrap();
        } else {
            let _ = std::fs::remove_file(aux.join("borsai_outside"));
        }
        let before = freeze_calls();
        let got = match freeze_in(&state, &ctx, sha, rel) {
            Ok(r) => format!("Ok({})", r.record_rel_path),
            Err(e) => format!("{} {} {}", e.code, e.message, e.detail.unwrap_or_default()),
        };
        println!("B3 [{name}] freeze_in -> {got}");
        if !got.starts_with("FREEZE_PREFLIGHT_BLOCKED") || !got.contains(blocker) {
            bad.push(format!("[{name}] freeze_in -> {got} (beklenen FREEZE_PREFLIGHT_BLOCKED + {blocker})"));
        }
        if freeze_calls() != before {
            bad.push(format!("[{name}] Python `-m borsai.freeze` çağrıldı"));
        }
        for d in ["registry/records", "app/parity/incidents"] {
            if repo.join(d).exists() {
                bad.push(format!("[{name}] {d} oluştu: {:?}", std::fs::read_dir(repo.join(d)).unwrap().flatten().map(|e| e.file_name()).collect::<Vec<_>>()));
            }
        }
        let _ = std::fs::remove_dir_all(repo.join("registry/records"));
        let _ = std::fs::remove_dir_all(repo.join("app"));
    }
    println!("B3 Python çağrıları (dondurma dışı ön koşul çağrıları dahil):\n{}", calls());
    assert!(bad.is_empty(), "B3 dondurma ön koşulsuz açık, {} sapma:\n  {}", bad.len(), bad.join("\n  "));

    // pozitif kontrol: aynı kurulum, doğru sha → Python'a ulaşılır, kayıt okunur
    let _ = std::fs::remove_file(aux.join("borsai_outside"));
    let ok = freeze_in(&state, &ctx, &state.embedded_index_sha(), rel).expect("ön koşullar sağlanınca dondurma çalışır");
    assert_eq!(ok.record_rel_path, "registry/records/SNTP1/20300105T100000Z_aaaaaaaaaaaa.json");
    assert_eq!(freeze_calls(), 1, "{}", calls());
    let _ = std::fs::remove_dir_all(&repo);
    let _ = std::fs::remove_dir_all(&aux);
}


// ---------------------------------------------------------------- sihirbaz fixture'ları (vitest)

/// Ön koşul, girdi belgesi önizlemesi ve dondur sonucu: hepsi gerçek Rust işlevlerinden üretilir;
/// yalnız yola/zamana bağlı alanlar sabitlenir (vitest render testleri elle yazılmış sayı kullanmaz).
#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn wizard_fixtures() {
    let root = PathBuf::from(std::env::var("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let ctx = RepoCtx { python: root.join(".venv/bin/python"), root: root.clone() };
    let state = AppState::from_embedded();
    let models = &state.models.as_ref().unwrap().models;

    // TÜFE satırının dosyaya bağlı alanları (yol, sha, son ay) aylık eklemeyle değişir: sabitlenir.
    let norm = |p: &borsai_app_lib::commands::freeze::Preflight| {
        let mut v = serde_json::to_value(p).unwrap();
        for k in ["repo_root", "python_path", "borsai_file"] {
            v[k] = json!("FIXTURE");
        }
        v["git_head"] = json!("0".repeat(40));
        v["git_status_registry"] = json!("");
        for k in ["path", "file_sha256", "through_month"] {
            v["tufe"][k] = json!("FIXTURE");
        }
        v
    };
    // Tarih saatten bağımsız (`preflight_at`): T = 2026-10-15 → TÜFE 2026-08 (pin ayı; dosyada kalıcı)
    let ok = preflight_at(&ctx, &state.embedded_index_sha(), Some("2026-10-15"), "2026-10-05");
    assert!(ok.ok, "{:?}", ok.blockers);
    fixture("preflight_ok.json", &norm(&ok));
    let blocked = preflight_at(&ctx, &"0".repeat(64), Some("2026-09-17"), "2026-10-05");
    assert_eq!((blocked.blockers.clone(), blocked.t_level), (vec!["INDEX_SHA"], "RED"));
    fixture("preflight_blocked.json", &norm(&blocked));
    // TÜFE ayı eksik: TUFE_MONTH engeli ve ekleme komutu (uygulama çalıştırmaz)
    let month = preflight_at(&ctx, &state.embedded_index_sha(), Some("2999-01-10"), "2999-01-05");
    assert_eq!(month.blockers, vec!["TUFE_MONTH"]);
    fixture("preflight_tufe_month.json", &norm(&month));

    // girdi belgesi önizlemesi (kurgusal arz, geçici repo)
    let tmp = tmp_dir("wizard");
    let src = tmp.join("downloads");
    std::fs::create_dir_all(&src).unwrap();
    let docs = vec![
        doc_req(&src, "KAP_TEST_1", "KAP_NOTIFICATION_PDF", "kap_test_1.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "KAP_TEST_2", "KAP_ATTACHMENT_PDF", "kap_test_2.pdf", "2030-01-04T10:00:00+03:00"),
        doc_req(&src, "SPK_TEST", "SPK_BULLETIN", "spk_test.pdf", "2030-01-01T10:00:00+03:00"),
    ];
    let copied = copy_source_docs_in(&tmp, "SNTA1", &docs).unwrap();
    let mut cv = serde_json::to_value(&copied).unwrap();
    for d in cv["documents"].as_array_mut().unwrap() {
        d["sha256"] = json!("0".repeat(64));
    }
    for (_, d) in cv["manifest"]["documents"].as_object_mut().unwrap() {
        d["sha256"] = json!("0".repeat(64));
        d["downloaded_at"] = json!("2030-01-05T13:00:00+03:00");
    }
    fixture("source_docs_copied.json", &cv);
    let mut req = synthetic_inputs_req("SNTA1", "POST_BOOKBUILD_PRE_LISTING", Some("2030-01-10"), Some("2.84"));
    let first = preview_inputs_doc_in(&tmp, &req, true, false).unwrap();
    assert!(first.written);
    req.fields.insert(
        "total_demand_multiple".into(),
        field(Some("3.14"), "KAP_TEST_2", json!({"origin": "SOURCE_REPORTED"})),
    );
    let mut pv = serde_json::to_value(preview_inputs_doc_in(&tmp, &req, false, false).unwrap()).unwrap();
    pv["sha256"] = json!("0".repeat(64));
    pv["text"] = json!("FIXTURE");
    fixture("inputs_preview_diff.json", &pv);
    let _ = std::fs::remove_dir_all(&tmp);

    // dondur sonucu: parite raporu gerçek kayıttan, komut bloğu gerçek üreticiden
    let path = std::fs::read_dir(root.join("registry/records/NETGL")).unwrap().flatten().next().unwrap().path();
    let mut record: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    // 16 modelli (Faz 4 öncesi) kayıt: 16/16 karşılaştırılır, 11 model "kayıtta yok" (EK 2 §3.7; EK 3 U59, P4)
    let old_parity = compare_record(&record, models);
    assert!(old_parity.ok() && old_parity.unsupported.is_empty());
    assert_eq!(old_parity.missing_in_record.len(), 11, "kayıt INDEX'ten eski");
    assert_eq!(old_parity.n_matched, 16);

    // Yeni kayıt (27 model): eksik on bir hücre gerçek çıktıyla tamamlanır → parite 27/27
    let inputs: Map<String, Value> = record["model_inputs"].as_object().cloned().unwrap_or_default();
    for id in &old_parity.missing_in_record {
        let m = models.iter().find(|x| &x.model_id == id).expect("gömülü model");
        let run = borsai_predict::run_model(&m.params, &inputs);
        record["models"].as_array_mut().unwrap().push(json!({
            "model_id": id,
            "params_sha256": m.params_sha256,
            "kind": run.kind.as_str(),
            "status": run.status,
            "refusal": run.refusal.as_ref().map(|r| json!({"code": r.code, "field": r.field, "reason": r.reason})),
            "output": run.output.as_ref().map(borsai_predict::Output::to_json),
        }));
    }
    let parity = compare_record(&record, models);
    assert!(parity.ok(), "{:?}", parity.mismatches);
    assert_eq!((parity.n_supported, parity.n_matched), (27, 27), "parite 27/27");
    assert!(parity.unsupported.is_empty() && parity.missing_in_record.is_empty());
    assert!(parity.max_abs <= 1e-9, "|Δ|max = {}", parity.max_abs);
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let rel = format!("registry/records/SNTA1/{file}");
    let fixed = RepoCtx { root: PathBuf::from("/tmp/borsai_repo"), python: PathBuf::from("/tmp/borsai_repo/.venv/bin/python") };
    let result = FreezeResult {
        record_rel_path: rel.clone(),
        record_file: file.into(),
        ticker: "SNTA1".into(),
        recorded_at_utc: "2030-01-05T10:00:00Z".into(),
        recorded_at_istanbul: "2030-01-05T13:00:00+03:00".into(),
        n_models: record["models"].as_array().unwrap().len(),
        model_ids: record["models"].as_array().unwrap().iter().map(|c| c["model_id"].as_str().unwrap().to_string()).collect(),
        summary: record["summary"].clone(),
        input_sha256: Some("a".repeat(64)),
        models_index_sha256: Some("b".repeat(64)),
        todo: todo_commands(&fixed, "SNTA1", "registry/inputs/SNTA1.json", &rel),
        parity,
    };
    fixture("freeze_result.json", &serde_json::to_value(&result).unwrap());

    // uyuşmazlıklı sürüm (kırmızı yol)
    record["models"][0]["output"]["D1"]["return"] = json!(0.5);
    let bad = compare_record(&record, models);
    assert!(!bad.ok());
    let mut bad_result = result;
    bad_result.parity = bad;
    bad_result.parity.incident_rel_path = Some("app/parity/incidents/20300105T100500Z.json".into());
    fixture("freeze_result_mismatch.json", &serde_json::to_value(&bad_result).unwrap());
}


/// U38: resmi görünüm YALNIZ dondurulmuş S'i kullanır. Kayıttaki `models[].output.S` kasten Rust
/// `predict_all`'ın üreteceğinden farklıdır (0.5^k); ekrandaki koşullu değerler 0.5^(k−j) çıkar ve
/// tahmin yolu hiç çağrılmaz (arz sayfası tek komuttur: `record_ceiling`).
#[test]
fn official_view_uses_record_only() {
    let repo = tmp_dir("u38");
    let ids = supported();
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    write_json(&repo.join("registry/records/SNTA1").join(file), &synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids));

    // aynı girdiyle Rust tahmini: kayıttaki S ile AYNI OLMAMALI (test anlamlı olsun diye)
    let inputs: Map<String, Value> = borsai_app_lib::commands::form::model_input_fields()
        .map(|f| (f.to_string(), Value::Null))
        .collect();
    let state = AppState::from_embedded();
    let runs = borsai_app_lib::commands::predict::predict_all_value(
        &state,
        &inputs,
        &borsai_app_lib::commands::predict::F6Arg::default(),
        None,
    )
    .unwrap();
    let predicted: Option<Vec<f64>> = runs
        .iter()
        .find(|r| r["model_id"] == json!("base_km_expanding"))
        .and_then(|r| serde_json::from_value(r["output"]["S"].clone()).ok());
    assert_ne!(predicted, Some(half_powers().to_vec()), "kurgusal S tahminle çakışmamalı");

    for j in [0usize, 1, 3, 9] {
        let rc = record_ceiling_in(&repo, "SNTA1", file, j, &ids, &shas()).unwrap();
        let row = rc.display.rows.iter().find(|r| r.model_id == "base_km_expanding").unwrap();
        assert_eq!(row.s, half_powers().to_vec(), "S doğrudan kayıttan");
        let cond = row.cond.as_ref().unwrap();
        for k in (j + 1)..=10 {
            let expected = 0.5f64.powi(k as i32) / if j == 0 { 1.0 } else { 0.5f64.powi(j as i32) };
            assert_eq!(cond.s_cond[k - 1], Some(expected), "j = {j}, k = {k}");
        }
        for k in 1..=j {
            assert_eq!(cond.s_cond[k - 1], None, "k ≤ j tanımsız");
        }
    }
    // j = 10 → tanımsız
    assert!(record_ceiling_in(&repo, "SNTA1", file, 10, &ids, &shas()).unwrap().display.rows.iter().all(|r| r.cond.is_none()));
    let _ = std::fs::remove_dir_all(&repo);
}

// ---------------------------------------------------------------- U49: koşullu getiri (EK 2 §4.3)

/// Kurgusal `data/outcomes/<T>.csv`: `closes` metinleri sırayla h = 1..n, kalanı PENDING.
fn write_outcomes(repo: &Path, ticker: &str, closes: &[&str], ceiling: &[u8]) {
    let mut text = String::from(
        "h,session_date,close_raw,upper_limit_raw,reference_raw,trade_count_raw,halt_flag,half_day,\
         shifted_by_suspension,ceiling_close,R_h,Y_h,ipo_price,thb_sha256,thm_sha256,status\n",
    );
    for h in 1..=10usize {
        if h <= closes.len() {
            text += &format!(
                "{h},2030-01-{:02},{},{},{},100,0,0,0,{},,,25.52,SYNTHETIC,SYNTHETIC,OK\n",
                h + 6,
                closes[h - 1],
                closes[h - 1],
                closes[h - 1],
                ceiling[h - 1],
            );
        } else {
            text += &format!("{h},,,,,,,,,,,,,,,PENDING\n");
        }
    }
    let dir = repo.join("data").join("outcomes");
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join(format!("{ticker}.csv")), text).unwrap();
}

/// Gerçek tavan yolu çıktılarını taşıyan kurgusal kayıt: girdi NETGL, S kasten `0.5^k` (U38/U49).
fn path_record(ticker: &str, s_override: bool) -> Value {
    let state = AppState::from_embedded();
    let models = &state.models.as_ref().unwrap().models;
    let inputs: Map<String, Value> = registry_inputs("NETGL");
    let mut cells: Vec<Value> = Vec::new();
    for m in models {
        let run = borsai_predict::run_model(&m.params, &inputs);
        let mut out = run.output.as_ref().map(borsai_predict::Output::to_json).unwrap_or(Value::Null);
        if s_override && out.get("S").is_some_and(|v| v.is_array()) {
            out["S"] = json!(half_powers().to_vec());
        }
        cells.push(json!({
            "model_id": m.model_id,
            "params_sha256": m.params_sha256,
            "kind": run.kind.as_str(),
            "status": run.status,
            "refusal": run.refusal.as_ref().map(|r| json!({"code": r.code, "field": r.field, "reason": r.reason})),
            "output": out,
        }));
    }
    let n = cells.len();
    json!({
        "schema_version": "borsai.record/1",
        "record_type": "PREDICTION",
        "ticker": ticker,
        "recorded_at_utc": "2030-01-05T10:00:00Z",
        "recorded_at_istanbul": "2030-01-05T13:00:00+03:00",
        "code": {"git_head": "0".repeat(40), "borsai_dirty": false},
        "input_sha256": "a".repeat(64),
        "inputs": {"path": format!("registry/inputs/{ticker}.json"), "sha256": "a".repeat(64),
                   "document": {"fields": {"first_trading_date": {"value": "2030-01-10"}}}},
        "model_inputs": {"ipo_price_tl": "25.52"},
        "models_index": {"path": "models/INDEX.json", "sha256": "b".repeat(64)},
        "models": cells,
        "summary": {"n_models": n, "n_predicted": n, "n_refused": 0, "refusals": {}}
    })
}

/// Sicil girdi belgesinden (salt okuma) model girdileri.
/// Kayıttaki `ceiling_path_v0` çıktısı (OUTPUT kaynağı sınamaları için).
fn live_output_for_b8(rec: &Value) -> Value {
    rec["models"].as_array().unwrap().iter().find(|m| m["model_id"] == json!("ceiling_path_v0")).unwrap()["output"].clone()
}

fn registry_inputs(ticker: &str) -> Map<String, Value> {
    let doc: Value =
        serde_json::from_slice(&std::fs::read(repo_dir().join(format!("registry/inputs/{ticker}.json"))).unwrap()).unwrap();
    borsai_app_lib::commands::form::model_input_fields()
        .map(|f| (f.to_string(), doc["fields"][f]["value"].clone()))
        .collect()
}

/// U49: resmi görünümde koşullu getiri YALNIZ kayıttaki `output` ve gömülü hücrelerden gelir.
/// `predict_all` çağrılmaz; kayıttaki `params_sha256` gömülüyle eşit değilse hesap yapılmaz.
#[test]
fn official_conditional_return_uses_record_only() {
    use borsai_app_lib::commands::path::{
        path_conditional_value, path_display_value, path_params_value, source_output, source_record, PathOutputArg,
        PATH_CLOSE_MISSING, PATH_MODEL_NOT_IN_RECORD, PATH_PARAMS_SHA_MISMATCH, STATE_AFTER_BREAK, STATE_STREAK_ONGOING,
    };
    let repo = tmp_dir("u49");
    let data = tmp_dir("u49_data");
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let mut rec = path_record("SNTA1", true);
    write_json(&repo.join("registry/records/SNTA1").join(file), &rec);
    // NETGL fiyatı 25.52 → C_1..C_3 = 28.06, 30.86, 33.94 (limit yolu); D4'te sapan kapanış.
    write_outcomes(&repo, "SNTA1", &["28.06", "30.86", "33.94"], &[1, 1, 1, 0, 0, 0, 0, 0, 0, 0]);
    let state = AppState::from_embedded().with_repo_for_tests(&data, &repo);

    // durum 1, j = 3: S kayıttan (0.5^k) → S_cond = 0.5^(k−3)
    let j3 = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", file), 3, STATE_STREAK_ONGOING)
        .expect("durum 1");
    for k in 4..=10usize {
        let got = j3.result["S_cond"][k.to_string()].as_f64().unwrap();
        assert_eq!(got, 0.5f64.powi(k as i32) / 0.5f64.powi(3), "S_cond[{k}] kayıttaki S'ten");
    }
    assert_eq!(j3.result["S_j"].as_f64(), Some(0.5f64.powi(3)));
    assert!(j3.closes.iter().all(|c| c.origin == "FILE") && !j3.assumed, "j = 3 resmi kapanışlarla");
    assert_eq!(j3.limit_path_mismatch, 0, "kapanışlar limit yolunda");
    assert_eq!(j3.result["D1"]["status"], json!("REALIZED"));
    assert!(j3.result["D5"]["return"].is_number(), "D5 koşullu dağılımdan");
    fixture("path_cond_record_j3.json", &serde_json::to_value(&j3).unwrap());
    // U52 taban çizgisi: resmi j = 2 (beyanlı j = 3'ün değerleri bu ekranda GEÇMEMELİ)
    let j2 = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", file), 2, STATE_STREAK_ONGOING)
        .expect("j = 2");
    assert_ne!(j2.result["D5"]["return"], j3.result["D5"]["return"], "j = 2 ve j = 3 ayrışmalı");
    fixture("path_cond_record_j2.json", &serde_json::to_value(&j2).unwrap());

    // varsayımsal j = 5 > resmi j = 3: eksik kapanışlar limit yolu varsayımıdır (etiketli)
    let j5 = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", file), 5, STATE_STREAK_ONGOING)
        .expect("varsayımsal j");
    assert!(j5.assumed && j5.closes.iter().filter(|c| c.origin == "LIMIT_PATH").count() == 2);
    assert_eq!(j5.closes[3].close, "37.32", "C_4 varsayımı");
    fixture("path_cond_hypothetical_j5.json", &serde_json::to_value(&j5).unwrap());

    // durum 2: seri D3'te bozuldu (t = 2) → kırılma günü kapanışı (D3) dosyadan gelmeli
    let t2 = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", file), 2, STATE_AFTER_BREAK)
        .expect("durum 2");
    assert_eq!(t2.result["state"], json!("AFTER_BREAK"));
    assert_eq!(t2.closes.len(), 3, "h = 1..t+1");
    assert!(t2.closes.iter().all(|c| c.origin == "FILE"));
    fixture("path_cond_break_t2.json", &serde_json::to_value(&t2).unwrap());

    // durum 2, kırılma günü kapanışı yoksa hesaplanmaz
    let err = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", file), 4, STATE_AFTER_BREAK)
        .unwrap_err();
    assert_eq!(err.code, PATH_CLOSE_MISSING);

    // limit yolundan sapan kapanış: sarı kutu değerleri (hesap yine yapılır)
    write_outcomes(&repo, "SNTB1", &["28.06", "30.00", "33.94"], &[1, 1, 1, 0, 0, 0, 0, 0, 0, 0]);
    let mut rec_b = rec.clone();
    rec_b["ticker"] = json!("SNTB1");
    write_json(&repo.join("registry/records/SNTB1").join(file), &rec_b);
    let mm = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTB1", file), 3, STATE_STREAK_ONGOING)
        .expect("sapan kapanış");
    assert_eq!(mm.limit_path_mismatch, 1);
    assert_eq!(mm.mismatch.as_ref().map(|x| (x.t, x.close.as_str(), x.c.as_str())), Some((2, "30.00", "30.86")));
    fixture("path_cond_mismatch.json", &serde_json::to_value(&mm).unwrap());

    // kayıt farklı parametreyle yazılmışsa hesap YOK
    for m in rec["models"].as_array_mut().unwrap() {
        if m["model_id"] == json!("ceiling_path_v0") {
            m["params_sha256"] = json!("f".repeat(64));
        }
    }
    let stale = "20300105T110000Z_bbbbbbbbbbbb.json";
    write_json(&repo.join("registry/records/SNTA1").join(stale), &rec);
    let err = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", stale), 3, STATE_STREAK_ONGOING)
        .unwrap_err();
    assert_eq!(err.code, PATH_PARAMS_SHA_MISMATCH);
    assert!(err.detail.unwrap_or_default().contains("gömülü sha"));

    // 16 modelli (Faz 4 öncesi) kayıt: model kayıtta hiç yok
    let ids = supported();
    let old = "20300105T120000Z_cccccccccccc.json";
    let mut old_rec = synthetic_record("SNTA1", "2030-01-05T12:00:00Z", &ids);
    old_rec["models"].as_array_mut().unwrap().retain(|m| !m["model_id"].as_str().unwrap_or_default().contains("path"));
    assert_eq!(old_rec["models"].as_array().unwrap().len(), ids.len() + 3 - 3, "üç tavan yolu modeli çıkarıldı");
    write_json(&repo.join("registry/records/SNTA1").join(old), &old_rec);
    let err = path_conditional_value(&state, "ceiling_path_v0", &source_record("SNTA1", old), 3, STATE_STREAK_ONGOING)
        .unwrap_err();
    assert_eq!(err.code, PATH_MODEL_NOT_IN_RECORD);

    // arz sayfası: kayıttaki tavan yolu çıktıları (Grup A/C render'ı) ve gösterim türevleri
    let rc = record_ceiling_in(&repo, "SNTA1", file, 3, &ids, &shas()).unwrap();
    assert_eq!(rc.path_models.len(), 3, "kayıtta üç tavan yolu modeli");
    assert!(rc.path_models.iter().all(|m| m.sha_matches_embedded));
    assert!(rc.display.rows.iter().all(|r| r.model_id != "ceiling_path_v0"), "Grup B'de çizilmez (U45)");
    fixture("record_ceiling_path_j3.json", &serde_json::to_value(&rc).unwrap());
    let args: Vec<PathOutputArg> = rc
        .path_models
        .iter()
        .filter(|m| m.status == "PREDICTED")
        .map(|m| PathOutputArg { model_id: m.model_id.clone(), output: m.output.clone() })
        .collect();
    fixture("path_display_record.json", &serde_json::to_value(path_display_value(&args)).unwrap());
    fixture("path_params.json", &serde_json::to_value(path_params_value(&state).unwrap()).unwrap());

    // senaryo / canlı sonuç yolu (OUTPUT kaynağı): aynı sayılar, kaynak satırı farklı
    let out = rec_b["models"]
        .as_array()
        .unwrap()
        .iter()
        .find(|m| m["model_id"] == json!("ceiling_path_v0"))
        .unwrap()["output"]
        .clone();
    let sha = shas().into_iter().find(|(id, _)| id == "ceiling_path_v0").unwrap().1;
    let live = path_conditional_value(
        &state,
        "ceiling_path_v0",
        &source_output(Some("SNTA1"), out, Some(&sha)),
        3,
        STATE_STREAK_ONGOING,
    )
    .expect("OUTPUT kaynağı");
    assert_eq!(live.result["S_cond"], j3.result["S_cond"], "aynı kayıt çıktısı → aynı sayılar");
    assert_eq!(live.source_kind, "OUTPUT");
    fixture("path_cond_output_j3.json", &serde_json::to_value(&live).unwrap());
    // B8: OUTPUT kaynağında parametre sha'sı zorunlu; verilmezse gömülü sha VARSAYILMAZ
    let no_sha = path_conditional_value(
        &state,
        "ceiling_path_v0",
        &source_output(Some("SNTA1"), live_output_for_b8(&rec_b), None),
        3,
        STATE_STREAK_ONGOING,
    );
    assert_eq!(no_sha.map(|_| "Ok".to_string()).unwrap_or_else(|e| e.code), "INVALID_ARGUMENT", "params_sha256 yoksa hata");
    let _ = std::fs::remove_dir_all(&repo);
    let _ = std::fs::remove_dir_all(&data);
}

// ---------------------------------------------------------------- U57: TÜFE kaynağı ve dondur engeli (EK 3 §3.1–§3.5)

/// Gerçek TÜFE dosyasının pin ayına (2026-08) kadarki öneki: durumlar aylık eklemeyle değişmez.
fn tufe_base_csv() -> String {
    let raw = std::fs::read(borsai_app_lib::commands::predict::tufe_path_in(&repo_dir())).unwrap();
    let t = borsai_predict::tufe::parse(&raw).unwrap();
    String::from_utf8(t.prefix_bytes("2026-08").unwrap()).unwrap()
}

const TUFE_2026_09: &str = "2026-09,136.5,2026-10-05,99999,https://example.invalid/tufe,0000000000000000000000000000000000000000000000000000000000000000";

fn netgl_model_inputs() -> Map<String, Value> {
    let doc: Value = serde_json::from_slice(&std::fs::read(repo_dir().join("registry/inputs/NETGL.json")).unwrap()).unwrap();
    borsai_app_lib::commands::form::model_input_fields().map(|f| (f.to_string(), doc["fields"][f]["value"].clone())).collect()
}

fn refusal_of<'a>(runs: &'a [Value], id: &str) -> Option<&'a str> {
    runs.iter().find(|r| r["model_id"] == json!(id)).and_then(|r| r["refusal"]["code"].as_str())
}

/// U57 (a)–(f): (a) repo dosyasından `index_for` → real/pooled tahmin; (b) 2026-09 satırı eklenmiş kopyada T =
/// 2026-11-10 ile ay bulunur (yeniden derleme yok: dosya her tahminde okunur); (c) 2026-09 yokken iki model RET
/// TUFE_MISSING, ekleme komutu, dondur `TUFE_MONTH` engeli ve `borsai.freeze` çağrısı 0; (d) T boş → T_UNKNOWN,
/// engel değil; (e) eski satırı değişmiş kopya → TUFE_FILE_MISMATCH, engel değil; (f) bağımsız mod: gömülü tablo.
#[cfg(unix)]
#[test]
fn tufe_source_and_blocker() {
    use borsai_app_lib::commands::freeze::freeze_in;
    use borsai_app_lib::commands::predict::{predict_all_value, tufe_info_value, F6Arg};
    use std::os::unix::fs::PermissionsExt;
    let repo = tmp_dir("u57_repo");
    let data = tmp_dir("u57_data");
    let csv = borsai_app_lib::commands::predict::tufe_path_in(&repo);
    std::fs::create_dir_all(csv.parent().unwrap()).unwrap();
    let base = tufe_base_csv();
    std::fs::write(&csv, &base).unwrap();
    std::fs::create_dir_all(repo.join("models")).unwrap();
    std::fs::write(repo.join("models/INDEX.json"), borsai_app_lib::embedded::INDEX_JSON).unwrap();
    write_json(&repo.join("registry/inputs/SNTU1.json"), &json!({"fields": {"first_trading_date": {"value": "2026-11-10"}}}));
    for args in [&["init", "-q"][..], &["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "t"]] {
        assert!(std::process::Command::new("git").current_dir(&repo).args(args).status().unwrap().success());
    }
    let log = data.join("python_calls.log");
    let python = data.join("python");
    std::fs::write(
        &python,
        format!("#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{}'\necho \"$PWD/borsai/__init__.py\"\n", log.display()),
    )
    .unwrap();
    std::fs::set_permissions(&python, std::fs::Permissions::from_mode(0o755)).unwrap();
    let state = AppState::from_embedded().with_repo_for_tests(&data, &repo);
    let ctx = RepoCtx { root: repo.clone(), python };
    let sha = state.embedded_index_sha();
    let inputs = netgl_model_inputs();
    let run = |t: Option<&str>| predict_all_value(&state, &inputs, &F6Arg::default(), t).unwrap();
    let deflated = ["ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"];

    // (a) repo dosyası: T = 2026-09-17 → 2026-07 = 132.31
    let r = run(Some("2026-09-17"));
    for id in deflated {
        assert_eq!(refusal_of(&r, id), None, "(a) {id}");
    }
    let info = tufe_info_value(&state, Some("2026-09-17")).unwrap();
    assert_eq!((info.source, info.index.as_deref(), info.pin_ok), ("REPO", Some("132.31"), Some(true)));

    // (c) 2026-09 yok: T = 2026-11-10 → RET TUFE_MISSING (clip ve @INF etkilenmez), komut, TUFE_MONTH engeli
    let r = run(Some("2026-11-10"));
    for id in deflated {
        assert_eq!(refusal_of(&r, id), Some("TUFE_MISSING"), "(c) {id}");
    }
    assert_eq!(refusal_of(&r, "ceiling_hazard_v1_clip"), None);
    assert_eq!(refusal_of(&r, "ceiling_hazard_v1_pooled@INF"), None);
    let info = tufe_info_value(&state, Some("2026-11-10")).unwrap();
    assert_eq!((info.reason, info.month.as_deref()), (Some("MONTH_MISSING"), Some("2026-09")));
    assert!(info.append_command.as_deref().unwrap().contains("build_tufe_csv.py --append-month 2026-09 "));
    let pre = preflight_in(&ctx, &sha, Some("2026-11-10"));
    assert_eq!(pre.blockers, vec!["TUFE_MONTH"]);
    let freeze_calls = || std::fs::read_to_string(&log).unwrap_or_default().lines().filter(|l| l.contains("borsai.freeze")).count();
    let err = freeze_in(&state, &ctx, &sha, "registry/inputs/SNTU1.json").unwrap_err();
    assert_eq!(err.code, "FREEZE_PREFLIGHT_BLOCKED");
    assert!(err.message.contains("TUFE_MONTH"), "{}", err.message);
    assert_eq!(freeze_calls(), 0, "TUFE_MONTH engelinde Python dondurması çağrılmaz");
    assert!(!repo.join("registry/records").exists());

    // (b) aynı dosyaya 2026-09 satırı eklenir: yeniden derleme yok, sonraki tahmin yeni ayı görür
    std::fs::write(&csv, format!("{base}{TUFE_2026_09}\n")).unwrap();
    let r = run(Some("2026-11-10"));
    for id in deflated {
        let out = &r.iter().find(|x| x["model_id"] == json!(id)).unwrap()["output"];
        assert_eq!((refusal_of(&r, id), &out["tufe_index_used"]), (None, &json!("136.5")), "(b) {id}");
    }
    assert!(preflight_in(&ctx, &sha, Some("2026-11-10")).blockers.is_empty(), "(b) engel kalktı");

    // (d) T boş → T_UNKNOWN reddi, engel değil
    let r = run(None);
    for id in deflated {
        assert_eq!(refusal_of(&r, id), Some("TUFE_MISSING"), "(d) {id}");
    }
    assert_eq!(tufe_info_value(&state, None).unwrap().reason, Some("T_UNKNOWN"));
    let pre = preflight_in(&ctx, &sha, None);
    assert!(pre.blockers.is_empty() && pre.t_level == "YELLOW");

    // (e) eski satırı değişmiş kopya → TUFE_FILE_MISMATCH (engel değil; sarı bilgi satırı)
    std::fs::write(&csv, base.replacen("2020-01,14.025066,", "2020-01,14.025067,", 1)).unwrap();
    let r = run(Some("2026-09-17"));
    for id in deflated {
        assert_eq!(refusal_of(&r, id), Some("TUFE_FILE_MISMATCH"), "(e) {id}");
    }
    let pre = preflight_in(&ctx, &sha, Some("2026-09-17"));
    assert!(pre.blockers.is_empty());
    assert_eq!(pre.tufe.as_ref().map(|i| (i.refusal, i.reason)), Some((Some("TUFE_FILE_MISMATCH"), Some("PIN_MISMATCH"))));

    // (f) bağımsız mod: gömülü tablo; Hakkında satırı gömülü tablonun son ayını ve pinleri taşır
    let standalone = AppState::from_embedded();
    let info = tufe_info_value(&standalone, Some("2026-09-17")).unwrap();
    assert_eq!((info.source, info.index.as_deref()), ("EMBEDDED", Some("132.31")));
    let about = borsai_app_lib::commands::models::app_info_value(&standalone);
    let emb = about.tufe_embedded.expect("gömülü TÜFE durumu");
    let real = borsai_predict::tufe::parse(&std::fs::read(borsai_app_lib::commands::predict::tufe_path_in(&repo_dir())).unwrap()).unwrap();
    assert_eq!((emb.source, emb.valid, emb.through_month.as_deref()), ("EMBEDDED", true, Some(real.last_month())));
    assert!(emb.pins.len() == 4 && emb.pins.iter().all(|p| p.ok), "v1 real/pooled ve (C) h99/pooled pinleri");
    let _ = std::fs::remove_dir_all(&repo);
    let _ = std::fs::remove_dir_all(&data);
}

// ---------------------------------------------------------------- U62: resmi görünümde kart yalnız kayıttan (EK 3 §5.4)

/// Kayıttaki `models[].output.S` kasten 0.5^k: kart satırları P(≥ 3) = 0.5^3, koşullu satırlar 0.5^(k−j); tahmin yolu
/// hiç çağrılmaz (komut saftır, `predict_all` imzada yok). 16 modelli (eski) kayıtta v1 satırları `in_record = false`
/// ("kayıt bu modeli içermiyor"). TÜFE satırı kaydın `tufe` bloğundandır.
#[test]
fn official_summary_uses_record_only() {
    use borsai_app_lib::commands::ceiling::record_summary_in;
    let repo = tmp_dir("u62");
    let ids = supported();
    let embedded = shas();
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let mut rec = synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids);
    rec["tufe"] = json!({"month": "2026-08", "index": "134.75", "release_date": "2026-09-03", "bulletin_id": "58290",
                         "refusal": null, "reason": null, "file": "data/raw/tuik/tufe_genel_2025_100.csv"});
    write_json(&repo.join("registry/records/SNTA1").join(file), &rec);
    let s = record_summary_in(&repo, "SNTA1", file, 2, Some(2), &embedded, None, None).unwrap();
    assert!(s.official && s.record_file.as_deref() == Some(file) && s.j_source == "OFFICIAL");
    for r in s.rows.iter().filter(|r| r.role != "CONSTANT" && r.status.as_deref() == Some("PREDICTED")) {
        assert_eq!((r.p_ge3, r.p_ge5, r.p_10), (Some(0.125), Some(0.03125), Some(0.5f64.powi(10))), "{}", r.model_id);
        let c = r.cond.as_ref().unwrap();
        assert_eq!((c.s_cond_5, c.s_cond_10, c.p_break_next), (Some(0.125), Some(0.5f64.powi(8)), 0.5), "{}", r.model_id);
        assert!(r.in_record);
    }
    let tufe = s.tufe.as_ref().expect("kaydın tufe bloğu");
    assert_eq!((tufe.source, tufe.index.as_deref()), ("RECORD", Some("134.75")));

    // 16 modelli kayıt: v1 satırları "kayıt bu modeli içermiyor"
    let old_ids: Vec<String> = ids[..16].to_vec();
    let file16 = "20300105T100000Z_bbbbbbbbbbbb.json";
    write_json(&repo.join("registry/records/SNTA1").join(file16), &synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &old_ids));
    let s16 = record_summary_in(&repo, "SNTA1", file16, 0, None, &embedded, None, None).unwrap();
    for id in ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"] {
        let r = s16.rows.iter().find(|r| r.model_id == id).expect("v1 satırı listede kalır (K4)");
        assert!(!r.in_record && r.p_ge3.is_none(), "{id}");
    }
    assert!(s16.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap().in_record);
    fixture("summary_record_j2.json", &serde_json::to_value(&s).unwrap());
    fixture("summary_record16_j0.json", &serde_json::to_value(&s16).unwrap());
    let _ = std::fs::remove_dir_all(&repo);
}

/// EK 3 §8.4 (U62 kalıbı): resmi görünümde düşüş kartı YALNIZ kaydın hücrelerinden. Kayıttaki (C) p_up'ları kasten
/// 0.6 (D10) ve 0.75 (D5) yapılır: kart %40 / %60 ve %25 / %75 gösterir (model yeniden çalıştırılmaz); 16 modelli
/// kayıtta (C) satırları "kayıt bu modeli içermiyor" (listeden kalkmaz, K4).
#[test]
fn official_fall_summary_uses_record_only() {
    use borsai_app_lib::commands::ceiling::record_fall_summary_in;
    let repo = tmp_dir("p4_fall");
    let ids = supported();
    let refs = AppState::from_embedded().models.as_ref().unwrap().models.clone();
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let mut rec = synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids);
    let fall_out = |id: &str| json!({"model_id": id, "D5": {"return": null, "return_unclipped": null, "return_clipped": null, "price": null,
        "p_up": 0.75, "direction": "UP"}, "D10": {"return": null, "return_unclipped": null, "return_clipped": null, "price": null,
        "p_up": 0.6, "direction": "UP"}, "warnings": [], "refused": null, "clipped": null, "clipped_features": null, "f1r_raw": null,
        "tufe_index_used": null, "add_sale_used": null});
    for c in rec["models"].as_array_mut().unwrap() {
        let id = c["model_id"].as_str().unwrap().to_string();
        if id.starts_with("fall_d10_v0") || id == "base_rate" || id == "v1_5_h99" {
            c["output"] = fall_out(&id);
        }
    }
    write_json(&repo.join("registry/records/SNTA1").join(file), &rec);
    let f = record_fall_summary_in(&repo, "SNTA1", file, &refs, None, None).unwrap().expect("(C) gömülü");
    assert!(f.official && f.record_file.as_deref() == Some(file));
    assert_eq!(f.featured.reason, "VAULT_CLOSED", "skor dosyası verilmedi: kasa bloğu yok");
    for r in &f.rows {
        assert!(r.in_record, "{}", r.model_id);
        assert_eq!((r.d10.pct_fall, r.d10.pct_up, r.d5.pct_fall, r.d5.pct_up), (Some(40), Some(60), Some(25), Some(75)), "{}", r.model_id);
    }
    fixture("summary_fall_record.json", &serde_json::to_value(&f).unwrap());
    let file16 = "20300105T100000Z_bbbbbbbbbbbb.json";
    write_json(&repo.join("registry/records/SNTA1").join(file16), &synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids[..16].to_vec()));
    let f16 = record_fall_summary_in(&repo, "SNTA1", file16, &refs, None, None).unwrap().unwrap();
    for id in ["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO"] {
        let r = f16.rows.iter().find(|r| r.model_id == id).expect("(C) satırı listede kalır (K4)");
        assert!(!r.in_record && r.d10.pct_fall.is_none(), "{id}");
    }
    assert!(f16.rows.iter().find(|r| r.model_id == "v1_5_h99").unwrap().in_record);
    let _ = std::fs::remove_dir_all(&repo);
}

// ---------------------------------------------------------------- EK 3 P2: D1 sonrası kayıt okuyucu (U68 Rust tarafı)

/// 0.6^k (k = 1..10): görüntü testinde koşullu satır 0.6^(k − j) olmalı.
fn powers06() -> [f64; 10] {
    let mut s = [0.0; 10];
    let mut x = 1.0;
    for v in s.iter_mut() {
        x *= 0.6;
        *v = x;
    }
    s
}

/// Sentetik POST_D1 kaydı (SPEC_POST_D1_V0 §7.4 anahtar kümesi birebir). Bülten alanlarında gerçek bülten adı YOK.
pub fn synthetic_post_d1_record(ticker: &str, at: &str, status: &str) -> Value {
    let s = powers06();
    let hz = vec![0.4f64; 10];
    let (refusal, output) = match status {
        "PREDICTED" => {
            let s_cond: Map<String, Value> = (2..=10).map(|k| (k.to_string(), json!(s[k - 1] / s[0]))).collect();
            (
                Value::Null,
                json!({"model_id": "post_d1_hazard_v0", "stage": "POST_D1", "refused": null, "not_applicable": null,
                       "warnings": [], "clipped": false, "hazard": hz, "S": s, "P_L": Value::Null, "P_close_ceiling": Value::Null,
                       "conditional_j1": {"S_cond": s_cond, "p_break_next": 0.4, "P_L_cond": {}},
                       "path_conditional": null, "d1_features": null}),
            )
        }
        "NOT_APPLICABLE" => (
            json!({"code": "D1_NOT_CEILING", "reason": "sentetik: D_1 kapanışı üst limit değil"}),
            json!({"model_id": "post_d1_hazard_v0", "stage": "POST_D1", "refused": null,
                   "not_applicable": {"code": "D1_NOT_CEILING", "reason": "sentetik"}, "warnings": [], "clipped": false,
                   "hazard": null, "S": null, "P_L": null, "P_close_ceiling": null, "conditional_j1": null, "path_conditional": null,
                   "d1_features": null}),
        ),
        _ => (
            json!({"code": "D1_LIMIT_NA", "field": "upper_limit", "reason": "sentetik"}),
            json!({"model_id": "post_d1_hazard_v0", "stage": "POST_D1", "refused": {"code": "D1_LIMIT_NA", "field": "upper_limit", "reason": "sentetik"},
                   "not_applicable": null, "warnings": [], "clipped": false, "hazard": null, "S": null, "P_L": null,
                   "P_close_ceiling": null, "conditional_j1": null, "path_conditional": null, "d1_features": null}),
        ),
    };
    let bulletin = |kind: &str, ch: &str| {
        json!({"file": format!("data/raw/bist/{kind}/2030/SENTETIK_{}.zip", kind.to_uppercase()), "sha256": ch.repeat(64),
               "url": "https://example.invalid/sentetik", "http_last_modified": "Mon, 07 Jan 2030 15:30:00 GMT",
               "downloaded_at": "2030-01-07T18:40:00+03:00", "internal_filename": "SENTETIK.csv"})
    };
    json!({
        "schema_version": "borsai.post_d1_record/1",
        "record_type": "PREDICTION",
        "record_stage": "POST_D1",
        "ticker": ticker,
        "recorded_at_utc": at,
        "recorded_at_istanbul": "2030-01-07T21:00:00+03:00",
        "recorded_at_basis": "LOCAL_CLOCK_SELF_REPORTED",
        "code": {"git_head": "0".repeat(40), "borsai_dirty": false, "borsai_source_sha256": "1".repeat(64)},
        "base_record": {"file": format!("registry/records/{ticker}/20300105T100000Z_aaaaaaaaaaaa.json"), "sha256": "2".repeat(64),
                        "model_inputs_sha256": "3".repeat(64), "selected_by": "SPEC_SCORING_6_PRIMARY_ceiling_hazard_v0_AT_POST_D1_TIME"},
        "d1": {"session_date": "2030-01-07", "session_h": 1, "half_day": 0, "halt_flag": 0, "thb": bulletin("thb", "a"), "thm": bulletin("thm", "b"),
               "fields_raw": {"open": "11.00", "high": "11.00", "low": "11.00", "close": "11.00", "volume": "1000000", "turnover": "11000000.00",
                              "aof": "11.00", "trade_count": "900", "halt": "0", "special_trade_volume": "0", "special_trade_turnover": "0",
                              "reference_price": "10.00", "upper_limit": "11.00", "lower_limit": "9.00"},
               "ceiling_close_D1": if status == "NOT_APPLICABLE" { json!(0) } else { json!(1) },
               "lock_consistency": {"open_at_U": true, "high_at_U": true, "close_at_U": true}},
        "d1_features": {"d1_lock": 1, "d1_turnover_ratio": "0.1", "d1_turnover_ln": -2.302585092994046, "clipped": false,
                        "z": {"d1_lock": 0.39, "d1_turnover": 0.6}, "warnings": []},
        "models_index": {"path": "models/INDEX_POST_D1.json", "sha256": "4".repeat(64), "model_ids": ["post_d1_hazard_v0"]},
        "models": [{"model_id": "post_d1_hazard_v0", "stage": "POST_D1", "file": "models/post_d1_hazard_v0.json",
                    "params_sha256": "3f7640267cd0f6b114ec88cf29e811587daa18c191866f9fa2d6910bc949e5dc", "spec_sha256": "5".repeat(64),
                    "algorithm": "discrete_time_hazard_offset_logit_l2", "kind": "post_d1", "status": status, "refusal": refusal,
                    "output": output}],
        "comparators_conditional": {},
        "summary": {"n_models": 1, "n_predicted": i32::from(status == "PREDICTED"), "n_refused": i32::from(status == "REFUSED"),
                    "n_not_applicable": i32::from(status == "NOT_APPLICABLE")},
    })
}

fn post_d1_cancellation(ticker: &str, cancels: &str) -> Value {
    json!({"schema_version": "borsai.post_d1_record/1", "record_type": "CANCELLATION", "record_stage": "POST_D1", "ticker": ticker,
           "recorded_at_utc": "2030-01-07T18:30:00Z", "recorded_at_istanbul": "2030-01-07T21:30:00+03:00",
           "recorded_at_basis": "LOCAL_CLOCK_SELF_REPORTED", "code": {"git_head": "0".repeat(40), "borsai_dirty": false,
           "borsai_source_sha256": "1".repeat(64)}, "cancels": {"file": cancels, "sha256": "6".repeat(64)}, "reason": "sentetik iptal"})
}

/// Sentetik sicil: SNTA1 (etkin PREDICTED 0.6^k + iptal edilmiş ikinci kayıt), SNTA2 (NOT_APPLICABLE), SNTA3 (REFUSED
/// D1_LIMIT_NA), SNTA4 (iki etkin kayıt: sekmeler), SNTA5 (kayıt yok). Eski kohort dizini (`registry/oot/post_d1`) de
/// yazılır: okuyucu ona HİÇ bakmamalı.
fn post_d1_repo(name: &str) -> PathBuf {
    let repo = tmp_dir(name);
    let w = |t: &str, f: &str, v: &Value| write_json(&repo.join("registry/post_d1").join(t).join(f), v);
    w("SNTA1", "20300107T180000Z_aaaaaaaaaaaa.json", &synthetic_post_d1_record("SNTA1", "2030-01-07T18:00:00Z", "PREDICTED"));
    w("SNTA1", "20300107T181000Z_bbbbbbbbbbbb.json", &synthetic_post_d1_record("SNTA1", "2030-01-07T18:10:00Z", "PREDICTED"));
    w("SNTA1", "20300107T183000Z_cccccccccccc.json", &post_d1_cancellation("SNTA1", "20300107T181000Z_bbbbbbbbbbbb.json"));
    w("SNTA2", "20300107T180000Z_dddddddddddd.json", &synthetic_post_d1_record("SNTA2", "2030-01-07T18:00:00Z", "NOT_APPLICABLE"));
    w("SNTA3", "20300107T180000Z_eeeeeeeeeeee.json", &synthetic_post_d1_record("SNTA3", "2030-01-07T18:00:00Z", "REFUSED"));
    w("SNTA4", "20300107T190000Z_ffffffffffff.json", &synthetic_post_d1_record("SNTA4", "2030-01-07T19:00:00Z", "PREDICTED"));
    w("SNTA4", "20300107T180500Z_999999999999.json", &synthetic_post_d1_record("SNTA4", "2030-01-07T18:05:00Z", "PREDICTED"));
    write_json(&repo.join("registry/oot/post_d1/SNTA5/20300107T180000Z_000000000000.json"),
               &synthetic_post_d1_record("SNTA5", "2030-01-07T18:00:00Z", "PREDICTED"));
    repo
}

/// U68 (Rust): `post_d1_records` / `post_d1_view` — etkin kayıt ve iptal bağı; j = 0'da satır yok (J0); j = 2'de satır
/// 0.6^(k − 2) (S yalnız kayıttan); REFUSED/NOT_APPLICABLE durumları; iki etkin kayıtta en erken varsayılan ve sekmeler;
/// eski kohort dizini okunmaz; vitest fixture'ları (`post_d1_view_*.json`).
#[test]
fn post_d1_records_reader() {
    use borsai_app_lib::commands::post_d1::{active_files, post_d1_records_in, post_d1_view_in};
    let repo = post_d1_repo("post_d1_reader");
    let rows = post_d1_records_in(&repo, "SNTA1").unwrap();
    assert_eq!(rows.len(), 3);
    assert_eq!(active_files(&rows), ["20300107T180000Z_aaaaaaaaaaaa.json"]);
    let cancelled = rows.iter().find(|r| r.file.starts_with("20300107T181000Z")).unwrap();
    assert_eq!(cancelled.cancelled_by.as_ref().unwrap().reason, "sentetik iptal");
    assert_eq!((rows[0].thb_sha8.as_deref(), rows[0].thm_sha8.as_deref()), (Some("aaaaaaaa"), Some("bbbbbbbb")));

    let j0 = post_d1_view_in(&repo, "SNTA1", 0, None).unwrap();
    assert_eq!((j0.state, j0.row.is_none(), j0.selected.as_deref()), ("J0", true, Some("20300107T180000Z_aaaaaaaaaaaa.json")));
    let j2 = post_d1_view_in(&repo, "SNTA1", 2, None).unwrap();
    assert_eq!(j2.state, "PREDICTED");
    let row = j2.row.as_ref().unwrap();
    let s = powers06();
    assert_eq!(row.s, s.to_vec(), "S yalnız kayıttan");
    let cond = row.cond.as_ref().unwrap();
    for k in 3..=10 {
        assert_eq!(cond.s_cond[k - 1], Some(s[k - 1] / s[1]), "S_cond[{k}] = 0.6^(k−2)");
        assert!((cond.s_cond[k - 1].unwrap() - 0.6f64.powi(k as i32 - 2)).abs() < 1e-12);
    }
    assert!((cond.p_break_next - 0.4).abs() < 1e-12);
    let src = j2.source.as_ref().unwrap();
    assert_eq!((src.params_sha8.as_str(), src.d1_session_date.as_deref()), ("3f764026", Some("2030-01-07")));
    let na = post_d1_view_in(&repo, "SNTA2", 1, None).unwrap();
    assert_eq!((na.state, na.refusal.as_ref().unwrap()["code"].as_str()), ("NOT_APPLICABLE", Some("D1_NOT_CEILING")));
    let refused = post_d1_view_in(&repo, "SNTA3", 1, None).unwrap();
    assert_eq!((refused.state, refused.refusal.as_ref().unwrap()["code"].as_str()), ("REFUSED", Some("D1_LIMIT_NA")));
    let two = post_d1_view_in(&repo, "SNTA4", 1, None).unwrap();
    assert_eq!(two.active, ["20300107T180500Z_999999999999.json", "20300107T190000Z_ffffffffffff.json"], "en erken önce");
    assert_eq!(two.selected.as_deref(), Some("20300107T180500Z_999999999999.json"));
    let tab = post_d1_view_in(&repo, "SNTA4", 1, Some("20300107T190000Z_ffffffffffff.json")).unwrap();
    assert_eq!(tab.selected.as_deref(), Some("20300107T190000Z_ffffffffffff.json"));
    assert!(post_d1_view_in(&repo, "SNTA1", 1, Some("20300107T181000Z_bbbbbbbbbbbb.json")).is_err(), "iptal edilmiş kayıt sekme değil");
    // eski kohort dizini okunmaz
    let none = post_d1_view_in(&repo, "SNTA5", 2, None).unwrap();
    assert_eq!((none.state, none.records.len()), ("NO_RECORD", 0));
    let src_text = std::fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/commands/post_d1.rs")).unwrap();
    assert!(!src_text.contains("\"oot\""), "okuyucu eski kohort dizinine bakmaz");
    for (name, v) in [("post_d1_view_j0.json", &j0), ("post_d1_view_j2.json", &j2), ("post_d1_view_na.json", &na),
                      ("post_d1_view_refused.json", &refused), ("post_d1_view_two.json", &two), ("post_d1_view_none.json", &none)] {
        fixture(name, &serde_json::to_value(v).unwrap());
    }
}

/// EK 3 §6.6 adım 1 (gerçek repo, salt okuma): NETGL'in listeleme öncesi kaydı var, D_1 2026-09-17, T_open Python'dan
/// 2026-09-18T09:40:00+03:00 (yerel saate göre geçmiş: sarı uyarı); kaydı olmayan kod → NO_PRE_LISTING_RECORD + D1_PENDING.
#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn post_d1_preflight_real_repo() {
    use borsai_app_lib::commands::post_d1::post_d1_preflight_at;
    let root = PathBuf::from(std::env::var("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let ctx = RepoCtx { python: root.join(".venv/bin/python"), root: root.clone() };
    let state = AppState::from_embedded();
    let post_sha = borsai_app_lib::embedded::BUILD_INFO.index_post_d1_sha256;
    let now = 1_790_026_200; // 2026-09-22T00:30:00+03:00
    let p = post_d1_preflight_at(&ctx, "NETGL", &state.embedded_index_sha(), post_sha, now).unwrap();
    assert!(p.index_match && p.index_post_d1_match && p.borsai_in_repo, "{p:?}");
    assert!(!p.base_records.is_empty());
    assert_eq!((p.d1.as_deref(), p.t_open.as_deref()), (Some("2026-09-17"), Some("2026-09-18T09:40:00+03:00")));
    assert!(p.blockers.is_empty(), "{:?}", p.blockers);
    assert!(p.warnings.contains(&"T_OPEN_PASSED"), "{:?}", p.warnings);
    assert!(p.minutes_to_t_open.unwrap() < 0);
    assert!(p.active_post_d1.is_empty(), "gerçek registry/post_d1 boş (H30)");
    let none = post_d1_preflight_at(&ctx, "ZZZZZ", &state.embedded_index_sha(), post_sha, now).unwrap();
    assert_eq!(none.blockers, vec!["NO_PRE_LISTING_RECORD", "D1_PENDING"]);
    let bad = post_d1_preflight_at(&ctx, "NETGL", &state.embedded_index_sha(), &"0".repeat(64), now).unwrap();
    assert_eq!(bad.blockers, vec!["INDEX_POST_D1_SHA"]);
}

/// U32 (P2 genişlemesi; EK 3 §6.6): sihirbazın komut blokları tek fonksiyondan, satır başına bir komut, `&&` yok, yorum yok,
/// her commit `--` ile yollara sınırlı; iptal `--cancel <dosya> --reason`. Uygulama bu komutları ÇALIŞTIRMAZ: `post_d1.rs`
/// git'i yalnız `git_readonly` ile çağırır ve `borsai.outcomes` / `borsai.push_proof`'u çalıştırmaz.
#[test]
fn post_d1_todo_block_shape() {
    use borsai_app_lib::commands::post_d1::{post_d1_commands, PostD1Todo};
    let repo = tmp_repo_ctx("borsai_x");
    let blocks = [
        post_d1_commands(&repo, &PostD1Todo::Outcomes { through: "2030-01-07" }),
        post_d1_commands(&repo, &PostD1Todo::Record { ticker: "SNTA1" }),
        post_d1_commands(&repo, &PostD1Todo::Cancel { ticker: "SNTA1", record_rel: "registry/post_d1/SNTA1/x.json", reason: "yanlış \"bülten\"" }),
    ];
    for b in &blocks {
        assert_eq!(b[0], format!("cd {}", repo.root.display()));
        assert!(b.iter().all(|l| !l.contains("&&") && !l.trim_start().starts_with('#')), "{b:?}");
        for l in b.iter().filter(|l| l.starts_with("git commit")) {
            assert!(l.contains(" -- "), "commit yollara sınırlanmalı: {l}");
        }
    }
    assert_eq!(blocks[0][1], format!("{PY_REL} -m borsai.outcomes update --through 2030-01-07"));
    assert!(blocks[1].iter().any(|l| l == "git add registry/post_d1/SNTA1/"));
    assert!(blocks[1].iter().any(|l| *l == format!("{PY_REL} -m borsai.push_proof $(git rev-parse HEAD)")));
    assert_eq!(blocks[1].iter().filter(|l| *l == "git push origin main").count(), 2);
    assert_eq!(blocks[2][1], format!("{PY_REL} -m borsai.freeze --cancel registry/post_d1/SNTA1/x.json --reason \"yanlış 'bülten'\""));
    let src = std::fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/commands/post_d1.rs")).unwrap();
    assert!(!src.contains("Command::new"), "post_d1.rs süreç başlatmaz (Python run_python, git git_readonly üzerinden)");
    for forbidden in ["\"borsai.outcomes\"", "\"borsai.push_proof\"", "\"commit\"", "\"push\""] {
        assert!(!src.contains(forbidden), "post_d1.rs {forbidden} çalıştırmaz");
    }
}

/// K-P2-3 (EK 3 §6.5): resmi görünümde kart; etkin POST_D1 kaydı ve j ≥ 1 varken "D1 sonrası" satırı (rol POST_D1, öne
/// çıkanın hemen altı), değerleri yalnız POST_D1 kaydının S'inden (0.6^k); terazi sütunları: yakın dönem yok, zaman-dışı
/// GERÇEK `scores_oot.json`'ın `post_d1_sealed` birincil hücresi ("ayırt edilemiyor", karşılaştırıcı ceiling_hazard_v0),
/// canlı GERÇEK `scores_post_d1.json` `n_live` (0). j = 0'da ve senaryoda satır yok. Fixture'lar gerçek skor dosyalarına
/// bağlı olduğundan bayt karşılaştırılmaz (`summary_real_*` kalıbı).
#[test]
fn official_summary_post_d1_row() {
    use borsai_app_lib::commands::ceiling::{add_post_d1_row, ceiling_summary_value, record_summary_in};
    use borsai_app_lib::commands::post_d1::post_d1_view_in;
    use borsai_app_lib::commands::scores::scores_post_d1_from;
    use borsai_app_lib::commands::scores_oot::scores_oot_repo;
    let repo = post_d1_repo("k_p2_3");
    let ids = supported();
    let embedded = shas();
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    write_json(&repo.join("registry/records/SNTA1").join(file), &synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &ids));
    let oot = scores_oot_repo(&repo_dir().join("scores").join("scores_oot.json")).expect("gerçek scores_oot.json").unwrap();
    let post_path = repo_dir().join("scores").join("scores_post_d1.json");
    let post = scores_post_d1_from(&std::fs::read_to_string(&post_path).unwrap(), &post_path).unwrap().doc.unwrap();
    let summary = |j: usize| {
        let mut s = record_summary_in(&repo, "SNTA1", file, j, Some(j), &embedded, None, Some(&oot)).unwrap();
        add_post_d1_row(&mut s, &post_d1_view_in(&repo, "SNTA1", j, None).unwrap(), Some(&oot), Some(&post));
        s
    };
    let s = summary(2);
    let i = s.rows.iter().position(|r| r.role == "POST_D1").expect("POST_D1 satırı");
    assert_eq!(s.rows[i - 1].role, "FEATURED", "öne çıkanın hemen altında");
    let r = &s.rows[i];
    assert_eq!((r.model_id.as_str(), r.status.as_deref(), r.in_record), ("post_d1_hazard_v0", Some("PREDICTED"), true));
    let p = |k: i32| 0.6f64.powi(k);
    // beklenen: kayda yazılan S'in kendisi (powers06, ardışık çarpım); powi Windows'ta son basamakta farklı (FAZ9_WINDOWS K-WIN-5)
    let s06 = powers06();
    assert_eq!((r.p_ge3, r.p_ge5, r.p_10), (Some(s06[2]), Some(s06[4]), Some(s06[9])), "S yalnız kayıttan");
    let c = r.cond.as_ref().unwrap();
    assert!((c.p_break_next - 0.4).abs() < 1e-12 && (c.s_cond_5.unwrap() - p(3)).abs() < 1e-12);
    assert!(r.near_era.is_none(), "yakın dönem: —");
    assert_eq!((r.vault.status, r.vault.verdict.as_deref(), r.vault.rule_id.as_deref(), r.vault.n), ("OPEN", Some("ayırt edilemiyor"), Some("ceiling_hazard_v0"), Some(45)));
    assert_eq!((r.live.n_scored, r.live.verdict.clone()), (Some(0), None), "canlı: n_live");
    // öteki satırlar değişmedi; POST_D1 satırı tek
    assert_eq!(s.rows.iter().filter(|x| x.role == "POST_D1").count(), 1);
    // j = 0: satır yok
    assert!(summary(0).rows.iter().all(|x| x.role != "POST_D1"));
    // senaryo (resmi değil): satır yok
    let models: Vec<borsai_app_lib::commands::ceiling::SummaryModel> = vec![];
    let mut sc = ceiling_summary_value(&models, 2, Some(2), false, None, &embedded, None, Some(&oot), None);
    add_post_d1_row(&mut sc, &post_d1_view_in(&repo, "SNTA1", 2, None).unwrap(), Some(&oot), Some(&post));
    assert!(sc.rows.iter().all(|x| x.role != "POST_D1"), "senaryoda D1 sonrası satırı yok");
    // NOT_APPLICABLE kaydı: satır var, sayı yok
    write_json(&repo.join("registry/records/SNTA2").join(file), &synthetic_record("SNTA2", "2030-01-05T10:00:00Z", &ids));
    let mut na = record_summary_in(&repo, "SNTA2", file, 1, Some(1), &embedded, None, Some(&oot)).unwrap();
    add_post_d1_row(&mut na, &post_d1_view_in(&repo, "SNTA2", 1, None).unwrap(), Some(&oot), Some(&post));
    let nr = na.rows.iter().find(|x| x.role == "POST_D1").unwrap();
    assert_eq!((nr.status.as_deref(), nr.p_ge3), (Some("NOT_APPLICABLE"), None));
    fixture_opt("summary_post_d1_j2.json", &serde_json::to_value(&s).unwrap(), false);
    fixture_opt("summary_post_d1_na_j1.json", &serde_json::to_value(&na).unwrap(), false);
}

/// U69'un ön uç fixture'ları (EK 3 §6.6): sihirbaz görünümleri gerçek Rust fonksiyonlarından. Geçici git deposu (gömülü
/// iki dizin), sahte Python (borsai konumu ve T_open; başka çağrı yok), sabit saat (2030-01-07T20:00+03:00). Ön koşul:
/// kayıt yokken DUR, commit bekliyor (sarı), commit'li (yeşil), takvim dışı D_1. Kayıt sonucu: Rust `run_post_d1` ile
/// kurulmuş kayıt + `post_d1_parity_in` (1/1) ve bozulmuş S kopyası (uyuşmazlık); komut blokları tek fonksiyondan. Yollar
/// `/REPO`'ya normalleştirilir.
#[cfg(unix)]
#[test]
fn post_d1_wizard_fixtures() {
    use borsai_app_lib::commands::post_d1::{
        post_d1_commands, post_d1_parity_in, post_d1_preflight_at, PostD1CancelResult, PostD1FreezeResult, PostD1Todo,
    };
    use std::os::unix::fs::PermissionsExt;
    let repo = tmp_dir("pd1_wizard");
    let aux = tmp_dir("pd1_wizard_aux");
    let state = AppState::from_embedded();
    let verified = state.models.as_ref().unwrap().clone();
    std::fs::create_dir_all(repo.join("models")).unwrap();
    std::fs::write(repo.join("models/INDEX.json"), borsai_app_lib::embedded::INDEX_JSON).unwrap();
    std::fs::write(repo.join("models/INDEX_POST_D1.json"), borsai_app_lib::embedded::INDEX_POST_D1_JSON).unwrap();
    let git = |args: &[&str]| {
        let st = std::process::Command::new("git")
            .current_dir(&repo)
            .args(["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"])
            .args(args)
            .status()
            .unwrap();
        assert!(st.success(), "git {args:?}");
    };
    git(&["init", "-q"]);
    git(&["add", "models"]);
    git(&["commit", "-q", "-m", "t"]);
    let python = aux.join("python");
    std::fs::write(
        &python,
        "#!/bin/sh\ncase \"$2\" in\n  *borsai.__file__*) echo \"$PWD/borsai/__init__.py\"; exit 0;;\n  \
         *r.t_open*) if [ \"$3\" = \"2030-01-07\" ]; then echo 2030-01-08T09:40:00+03:00; exit 0; fi\n    \
         echo \"borsai.registry.CalendarNotAvailable: CALENDAR_NOT_AVAILABLE: D_1 $3 takvim dışında\" >&2; exit 1;;\nesac\nexit 2\n",
    )
    .unwrap();
    std::fs::set_permissions(&python, std::fs::Permissions::from_mode(0o755)).unwrap();
    let ctx = RepoCtx { root: repo.clone(), python };
    let now = 1_894_035_600; // 2030-01-07T20:00:00+03:00
    let (isha, psha) = (state.embedded_index_sha(), borsai_app_lib::embedded::BUILD_INFO.index_post_d1_sha256.to_string());
    let root_s = repo.display().to_string();
    let norm = |v: Value| -> Value {
        let text = serde_json::to_string(&v).unwrap().replace(&root_s, "/REPO").replace(&ctx.python.display().to_string(), "/REPO/.venv/bin/python");
        let mut v: Value = serde_json::from_str(&text).unwrap();
        if v.get("git_head").is_some_and(|g| !g.is_null()) {
            v["git_head"] = json!("1".repeat(40));
        }
        v
    };
    let pre = |t: &str| norm(serde_json::to_value(post_d1_preflight_at(&ctx, t, &isha, &psha, now).unwrap()).unwrap());

    // kayıt yokken: DUR
    let blocked = pre("SNTA1");
    assert_eq!(blocked["blockers"], json!(["NO_PRE_LISTING_RECORD", "D1_PENDING"]));
    // listeleme öncesi kayıt + D_1 sonuç satırı (commit'siz → sarı)
    let file = "20300105T100000Z_aaaaaaaaaaaa.json";
    let mut base = synthetic_record("SNTA1", "2030-01-05T10:00:00Z", &supported());
    base["model_inputs"] = json!({
        "ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
        "capital_increase_shares": "62500000", "existing_share_sale_shares": "25000000", "total_demand_multiple": "2.84",
        "total_demand_filter_status": "NOT_SPECIFIED", "additional_sale_shares": "0", "ipo_size_tl": "2233000000",
        "ipo_price_try": "25.52"});
    base["inputs"]["document"]["fields"]["first_trading_date"]["value"] = json!("2030-01-07");
    write_json(&repo.join("registry/records/SNTA1").join(file), &base);
    let pending = app_dir().join("tests/fixtures/outcomes/pending/SNTA1.csv");
    std::fs::create_dir_all(repo.join("data/outcomes")).unwrap();
    std::fs::copy(&pending, repo.join("data/outcomes/SNTA1.csv")).unwrap();
    let uncommitted = pre("SNTA1");
    assert_eq!((uncommitted["ok"].clone(), uncommitted["committed"].clone()), (json!(true), json!(false)));
    assert_eq!(uncommitted["t_open"], json!("2030-01-08T09:40:00+03:00"));
    git(&["add", "data", "registry"]);
    git(&["commit", "-q", "-m", "t2"]);
    let ok = pre("SNTA1");
    assert_eq!((ok["ok"].clone(), ok["committed"].clone(), ok["blockers"].clone()), (json!(true), json!(true), json!([])));
    assert_eq!(ok["minutes_to_t_open"], json!(820));
    // takvim dışı D_1
    write_json(&repo.join("registry/records/SNTA2").join(file), &synthetic_record("SNTA2", "2030-01-05T10:00:00Z", &supported()));
    std::fs::write(repo.join("data/outcomes/SNTA2.csv"), std::fs::read_to_string(&pending).unwrap().replace("2030-01-0", "2031-01-0")).unwrap();
    let cal = pre("SNTA2");
    assert_eq!(cal["blockers"], json!(["CALENDAR_NOT_AVAILABLE"]));
    assert!(cal["t_open_error"].as_str().unwrap().contains("CALENDAR_NOT_AVAILABLE"));

    // kayıt: çıktı Rust `run_post_d1` ile (base kaydın model_inputs'u + sentetik D_1), parite gerçek fonksiyonla
    let post = &verified.post_d1[0];
    let by = |id: &str| verified.by_id(id).unwrap().params.clone();
    let d1 = json!({"fields_raw": {"open": "28.06", "high": "28.06", "low": "28.06", "close": "28.06", "volume": "8750000",
                    "turnover": "245525000.00", "aof": "28.06", "trade_count": "4000", "halt": "0", "special_trade_volume": "0",
                    "special_trade_turnover": "0", "reference_price": "25.52", "upper_limit": "28.06", "lower_limit": "22.98"},
                    "half_day": 0, "halt_flag": 0});
    let inputs = base["model_inputs"].as_object().unwrap().clone();
    let run = borsai_predict::post_d1::run_post_d1(&post.params, &by("ceiling_hazard_v0"), &inputs, &d1, Some(&by("ceiling_path_v0")));
    let base_sha = borsai_app_lib::commands::models::sha256_hex(&std::fs::read(repo.join("registry/records/SNTA1").join(file)).unwrap());
    let s = half_powers();
    let comparator = json!({"record_cell_sha256": null, "S": s.to_vec(),
                            "S_cond": (2..=10).map(|k| (k.to_string(), json!(s[k - 1] / s[0]))).collect::<Map<String, Value>>(),
                            "source": "base_record"});
    let mut record = synthetic_post_d1_record("SNTA1", "2030-01-07T17:00:00Z", "PREDICTED");
    record["base_record"]["file"] = json!(format!("registry/records/SNTA1/{file}"));
    record["base_record"]["sha256"] = json!(base_sha);
    for k in ["fields_raw", "half_day", "halt_flag"] {
        record["d1"][k] = d1[k].clone();
    }
    record["models"][0]["status"] = json!(run.status);
    record["models"][0]["output"] = run.output.as_ref().unwrap().to_json();
    record["comparators_conditional"] = json!({"ceiling_hazard_v0": comparator});
    let (parity, comps) = post_d1_parity_in(&repo, &record, &verified).unwrap();
    assert!(parity.ok() && parity.n_matched == 1, "{parity:?}");
    assert!(comps.failures.is_empty() && comps.n_checked == 1);
    let rel = "registry/post_d1/SNTA1/20300107T170000Z_cccccccccccc.json".to_string();
    let result = |parity, comparators| PostD1FreezeResult {
        record_rel_path: rel.clone(),
        record_file: "20300107T170000Z_cccccccccccc.json".into(),
        ticker: "SNTA1".into(),
        recorded_at_utc: "2030-01-07T17:00:00Z".into(),
        recorded_at_istanbul: "2030-01-07T20:00:00+03:00".into(),
        d1: Some("2030-01-07".into()),
        ceiling_close_d1: json!(1),
        summary: json!({"n_models": 1, "n_not_applicable": 0, "n_predicted": 1, "n_refused": 0}),
        t_open: Some("2030-01-08T09:40:00+03:00".into()),
        python_note: Some("T_open'dan ÖNCE: commit + push + push_proof (proje sahibi)".into()),
        base_record_file: Some(format!("registry/records/SNTA1/{file}")),
        parity,
        comparators,
        todo: post_d1_commands(&ctx, &PostD1Todo::Record { ticker: "SNTA1" }),
    };
    let frozen_ok = norm(serde_json::to_value(result(parity, comps)).unwrap());
    let mut bad = record.clone();
    let x = bad["models"][0]["output"]["S"][3].as_f64().unwrap();
    bad["models"][0]["output"]["S"][3] = json!(x + 1e-6);
    let (bp, bc) = post_d1_parity_in(&repo, &bad, &verified).unwrap();
    assert!(!bp.ok());
    let frozen_bad = norm(serde_json::to_value(result(bp, bc)).unwrap());
    let mut cancel_todo = post_d1_commands(&ctx, &PostD1Todo::Cancel { ticker: "SNTA1", record_rel: &rel, reason: "kurgusal" });
    cancel_todo.retain(|l| !l.contains("-m borsai.freeze --cancel"));
    let cancelled = norm(serde_json::to_value(PostD1CancelResult {
        cancel_rel_path: "registry/post_d1/SNTA1/20300107T173000Z_dddddddddddd.json".into(),
        cancels: "20300107T170000Z_cccccccccccc.json".into(),
        ticker: "SNTA1".into(),
        reason: "kurgusal".into(),
        recorded_at_istanbul: "2030-01-07T20:30:00+03:00".into(),
        todo: cancel_todo,
    }).unwrap());
    let outcomes_todo = norm(json!(post_d1_commands(&ctx, &PostD1Todo::Outcomes { through: "2030-01-07" })));
    for (name, v) in [
        ("post_d1_preflight_blocked.json", &blocked),
        ("post_d1_preflight_uncommitted.json", &uncommitted),
        ("post_d1_preflight_ok.json", &ok),
        ("post_d1_preflight_calendar.json", &cal),
        ("post_d1_frozen_ok.json", &frozen_ok),
        ("post_d1_frozen_mismatch.json", &frozen_bad),
        ("post_d1_cancelled.json", &cancelled),
        ("post_d1_outcomes_todo.json", &outcomes_todo),
    ] {
        fixture(name, v);
    }
    let _ = std::fs::remove_dir_all(&repo);
    let _ = std::fs::remove_dir_all(&aux);
}
