//! Gömülü model kümesi (SPEC_APP §1.4): U33 embedded_integrity, U12 integrity_fail_closed,
//! U5 predict_all_covers_index, U41 survival_model_integrity (SPEC_APP EK 2 §1), U58 (EK 3 §10.1: 27 model,
//! v1 parametre denetimi bütünlük yolunda), U67 post_d1_integrity (EK 3 §10.2: ikinci dizin, ebeveyn/tavan yolu zinciri);
//! FAZ9_SNAPSHOT K-SNAP-1/2: gömülü sicil anlık görüntüsünün manifesti ve bir bayt mutasyonunda fail-closed.
use borsai_app_lib::commands::models::{
    sha256_hex, verify, verify_post_d1, INTEGRITY_FAILED, POST_D1_PARENT_MISMATCH, SURVIVAL_MODEL_MISMATCH,
};
use borsai_app_lib::commands::predict::{predict_all_value, F6Arg};
use borsai_app_lib::embedded::{self, EmbeddedModel};
use borsai_app_lib::state::AppState;
use serde_json::{json, Map, Value};
use std::sync::Arc;

fn index() -> Value {
    serde_json::from_str(embedded::INDEX_JSON).unwrap()
}

fn netgl_inputs() -> Map<String, Value> {
    let v = json!({
        "additional_sale_shares": "0", "capital_increase_shares": "62500000", "existing_share_sale_shares": "25000000",
        "ipo_price_tl": "25.52", "ipo_price_try": "25.52", "ipo_size_tl": "2233000000",
        "planned_additional_sale_ceiling": "0", "planned_base_offer_shares": "87500000",
        "planned_capital_increase_shares": "62500000", "planned_existing_share_sale": "25000000",
        "planned_max_offer_shares": "87500000", "planned_post_ipo_capital": "312500000",
        "planned_pre_ipo_capital": "250000000", "post_ipo_share_capital": "312500000", "shares_offered": "87500000",
        "total_demand_filter_status": "NOT_SPECIFIED", "total_demand_multiple": "2.84"
    });
    v.as_object().unwrap().clone()
}

/// Gömülü küme (EK 3 §4.1): INDEX'in 27 kaydı (P4).
const N_EMBEDDED: usize = 27;
/// NETGL'in ilk işlem günü (registry/inputs/NETGL.json): TÜFE 2026-07 = 132.31 (EK 3 §11).
const NETGL_T: &str = "2026-09-17";

/// U33 + U58: gömülü her dosyanın sha256'sı = INDEX; INDEX sha = build_info; `_check_params` hepsinde geçer (v1 dalı dahil).
#[test]
fn embedded_integrity() {
    assert_eq!(sha256_hex(embedded::INDEX_JSON.as_bytes()), embedded::BUILD_INFO.index_sha256);
    let idx = index();
    let entries = idx["models"].as_array().unwrap();
    assert_eq!(embedded::EMBEDDED_MODELS.len(), N_EMBEDDED);
    for (i, m) in embedded::EMBEDDED_MODELS.iter().enumerate() {
        assert_eq!(entries[i]["model_id"].as_str(), Some(m.model_id));
        assert_eq!(entries[i]["sha256"].as_str(), Some(sha256_hex(m.json.as_bytes()).as_str()), "{}", m.model_id);
        let params: Value = serde_json::from_str(m.json).unwrap();
        borsai_predict::check_params(&params).unwrap_or_else(|e| panic!("{}: {e}", m.model_id));
    }
    let v = verify(embedded::INDEX_JSON, embedded::EMBEDDED_MODELS, embedded::BUILD_INFO.index_sha256).expect("bütünlük");
    assert_eq!(v.models.len(), N_EMBEDDED);
    assert!(AppState::from_embedded().models.is_ok());
    // EK 3 P4: INDEX'in bütün kayıtları gömülü (`ignored_model_ids == []`)
    assert!(embedded::BUILD_INFO.ignored_index_models.is_empty(), "{:?}", embedded::BUILD_INFO.ignored_index_models);
    // TÜFE tablosu gömülü (deflatörlü model var)
    assert!(embedded::TUFE_CSV.is_some());
}

/// U58: v1 JSON'unun `preprocessing.winsor.f2` silinmiş test-içi kopyası (sha INDEX'e uyarlanmış) → PARAMS_INVALID →
/// INTEGRITY_FAILED; tahmin komutu hata döner.
#[test]
fn v1_params_integrity() {
    let (idx, files) = tampered(
        "ceiling_hazard_v1_clip",
        |p| {
            p["preprocessing"]["winsor"].as_object_mut().unwrap().remove("f2");
        },
        true,
    );
    let err = verify(&idx, &files, &sha256_hex(idx.as_bytes())).unwrap_err();
    assert_eq!((err.model_id.as_deref(), err.reason_code.as_str()), (Some("ceiling_hazard_v1_clip"), "PARAMS_INVALID"));
    let state = AppState { models: Err(err), runtime: Default::default() };
    let e = predict_all_value(&state, &netgl_inputs(), &F6Arg::default(), Some(NETGL_T)).unwrap_err();
    assert_eq!(e.code, INTEGRITY_FAILED);
    // rejim bloğu bozulmuş pooled kopyası da
    let (idx, files) = tampered("ceiling_hazard_v1_pooled", |p| p["regime"]["penalized"] = json!(true), true);
    let err = verify(&idx, &files, &sha256_hex(idx.as_bytes())).unwrap_err();
    assert_eq!((err.model_id.as_deref(), err.reason_code.as_str()), (Some("ceiling_hazard_v1_pooled"), "PARAMS_INVALID"));
}

fn leak(s: String) -> &'static str {
    Box::leak(s.into_boxed_str())
}

/// Test içi kopya: bir modelin JSON'u değiştirilir; `fix_index` ise INDEX sha'sı yeni dosyaya uyarlanır.
fn tampered(model_id: &str, edit: impl Fn(&mut Value), fix_index: bool) -> (String, Vec<EmbeddedModel>) {
    let mut idx = index();
    let mut files = Vec::new();
    for (i, m) in embedded::EMBEDDED_MODELS.iter().enumerate() {
        if m.model_id != model_id {
            files.push(*m);
            continue;
        }
        let mut p: Value = serde_json::from_str(m.json).unwrap();
        edit(&mut p);
        let json = leak(serde_json::to_string_pretty(&p).unwrap());
        if fix_index {
            idx["models"][i]["sha256"] = json!(sha256_hex(json.as_bytes()));
        }
        files.push(EmbeddedModel { model_id: m.model_id, file: m.file, json });
    }
    (serde_json::to_string_pretty(&idx).unwrap(), files)
}

/// U12: coef uzunluğu değiştirilmiş kopya → PARAMS_INVALID → INTEGRITY_FAILED; tahmin komutu hata döner.
#[test]
fn integrity_fail_closed() {
    let shorten = |p: &mut Value| {
        p["horizons"]["D1"]["return"]["coef"].as_array_mut().unwrap().pop();
    };
    // sha INDEX'e uyarlanmış: sha denetimi geçer, parametre denetimi yakalar
    let (idx, files) = tampered("v1_5_h99", shorten, true);
    let err = verify(&idx, &files, &sha256_hex(idx.as_bytes())).unwrap_err();
    assert_eq!(err.model_id.as_deref(), Some("v1_5_h99"));
    assert_eq!(err.reason_code, "PARAMS_INVALID");
    let state = AppState { models: Err(err.clone()), runtime: Default::default() };
    let e = predict_all_value(&state, &netgl_inputs(), &F6Arg::default(), None).unwrap_err();
    assert_eq!(e.code, INTEGRITY_FAILED);
    assert!(e.message.contains("v1_5_h99"), "{}", e.message);
    // sha uyarlanmamış: dosya sha'sı INDEX'le uyuşmaz
    let (idx, files) = tampered("pb_v0", |p| p["horizons"]["D1"]["return"]["intercept"] = json!(0.5), false);
    let err = verify(&idx, &files, &sha256_hex(idx.as_bytes())).unwrap_err();
    assert_eq!((err.model_id.as_deref(), err.reason_code.as_str()), (Some("pb_v0"), "MODEL_SHA_MISMATCH"));
    // INDEX'in kendisi build_info ile uyuşmuyor
    let err = verify(embedded::INDEX_JSON, embedded::EMBEDDED_MODELS, "0".repeat(64).as_str()).unwrap_err();
    assert_eq!((err.model_id, err.reason_code.as_str()), (None, "INDEX_SHA_MISMATCH"));
    // şema sürümü desteklenmiyor
    let (idx, files) = tampered("base_zero", |p| p["schema_version"] = json!("borsai.model/2"), true);
    let err = verify(&idx, &files, &sha256_hex(idx.as_bytes())).unwrap_err();
    assert_eq!(err.reason_code, "SCHEMA_UNSUPPORTED");
}

/// U5 + U63: `predict_all` gömülü INDEX'teki her model için tam bir sütun üretir (27/27), sıra INDEX sırası,
/// `params_sha256` INDEX ile eşit. NETGL T = 2026-09-17 → TÜFE 2026-07 = 132.31: real ve pooled dolu.
#[test]
fn predict_all_covers_index() {
    let state = AppState::from_embedded();
    let f6 = F6Arg { value: Some(json!("-0.092426990008977120101141297657234466055005263165174860190691")), refusal: None };
    let runs = predict_all_value(&state, &netgl_inputs(), &f6, Some(NETGL_T)).unwrap();
    let idx = index();
    let entries = &idx["models"].as_array().unwrap()[..N_EMBEDDED];
    assert_eq!(runs.len(), N_EMBEDDED);
    for (r, e) in runs.iter().zip(entries) {
        assert_eq!(r["model_id"], e["model_id"]);
        assert_eq!(r["params_sha256"], e["sha256"]);
        assert_eq!(r["status"], json!("PREDICTED"), "{}", r["model_id"]);
        assert!(r["output"].is_object());
    }
    let v = state.models.as_ref().map(Arc::clone).unwrap();
    assert_eq!(v.index_sha256, embedded::BUILD_INFO.index_sha256);
    for id in ["ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "fall_d10_v0_h99", "fall_d10_v0_pooled"] {
        let out = &runs.iter().find(|r| r["model_id"] == json!(id)).unwrap()["output"];
        assert_eq!(out["tufe_index_used"], json!("132.31"), "{id}");
    }
    // (C) türü "fall"; ek satış "0" → add_sale_used 0
    for id in ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"] {
        let r = runs.iter().find(|r| r["model_id"] == json!(id)).unwrap();
        assert_eq!(r["kind"], json!("fall"), "{id}");
    }
    // f3 boş: 10 model F3_MISSING (TÜFE'den önce; (C) h99/pooled dahil), 17 model tahmin verir (U7 → U63 → P4)
    let mut no_f3 = netgl_inputs();
    no_f3.insert("total_demand_multiple".into(), Value::Null);
    let runs = predict_all_value(&state, &no_f3, &f6, Some(NETGL_T)).unwrap();
    let refused: Vec<&str> = runs
        .iter()
        .filter(|r| r["status"] == json!("REFUSED"))
        .map(|r| r["model_id"].as_str().unwrap())
        .collect();
    assert_eq!(
        refused,
        vec![
            "v1_5_h99", "v1_6_h99", "v1_5_market20_v0", "ceiling_hazard_v0", "ceiling_path_v0", "ceiling_hazard_v1_clip",
            "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "fall_d10_v0_h99", "fall_d10_v0_pooled"
        ]
    );
    assert!(runs.iter().filter(|r| r["status"] == json!("REFUSED")).all(|r| r["refusal"]["code"] == json!("F3_MISSING")));
    // T yok: yalnız deflatörlü modeller TUFE_MISSING (v1 real/pooled, (C) h99/pooled; clip, @INF, addsale, @ZERO TÜFE istemez)
    let runs = predict_all_value(&state, &netgl_inputs(), &f6, None).unwrap();
    let refused: Vec<(&str, &str)> = runs
        .iter()
        .filter(|r| r["status"] == json!("REFUSED"))
        .map(|r| (r["model_id"].as_str().unwrap(), r["refusal"]["code"].as_str().unwrap()))
        .collect();
    assert_eq!(
        refused,
        [
            ("ceiling_hazard_v1_real", "TUFE_MISSING"),
            ("ceiling_hazard_v1_pooled", "TUFE_MISSING"),
            ("fall_d10_v0_h99", "TUFE_MISSING"),
            ("fall_d10_v0_pooled", "TUFE_MISSING")
        ]
    );
}

/// U41: `ceiling_path` modellerindeki gömülü seri modeli kopyası bozulmamış olmalı.
/// (a) `survival_model_sha256` = INDEX'teki seri modelinin sha256'sı, (b) o model gömülü kümede,
/// (c) kopya dosyanın ayrıştırılmış değerine yapısal olarak eşit. Tek uyuşmazlık → INTEGRITY_FAILED.
#[test]
fn survival_model_integrity() {
    let idx = index();
    let entries = idx["models"].as_array().unwrap();
    let sha_of = |id: &str| -> String {
        entries
            .iter()
            .find(|e| e["model_id"] == json!(id))
            .and_then(|e| e["sha256"].as_str())
            .unwrap_or_else(|| panic!("{id} INDEX'te yok"))
            .to_string()
    };
    let mut seen = 0usize;
    for m in embedded::EMBEDDED_MODELS.iter() {
        let p: Value = serde_json::from_str(m.json).unwrap();
        if p["algorithm"] != json!("CEILING_PATH_MIXTURE_EQ_V0") {
            continue;
        }
        seen += 1;
        let sid = p["survival_model_id"].as_str().expect("survival_model_id");
        assert_eq!(p["survival_model_sha256"].as_str(), Some(sha_of(sid).as_str()), "{}", m.model_id);
        let file = embedded::EMBEDDED_MODELS.iter().find(|x| x.model_id == sid).expect("gömülü seri modeli");
        let parsed: Value = serde_json::from_str(file.json).unwrap();
        assert_eq!(p["survival_model"], parsed, "{}: kopya dosyayla aynı değil", m.model_id);
    }
    assert_eq!(seen, 3, "üç tavan yolu modeli gömülü");

    // (1) kopyanın bir sayısı değiştirilmiş test-içi kopya → SURVIVAL_MODEL_MISMATCH
    let (i2, files) = tampered(
        "ceiling_path_v0",
        |p| {
            let g = p["survival_model"]["gamma"][0].as_f64().unwrap();
            p["survival_model"]["gamma"][0] = json!(g + 1e-9);
        },
        true,
    );
    let err = verify(&i2, &files, &sha256_hex(i2.as_bytes())).unwrap_err();
    assert_eq!((err.model_id.as_deref(), err.reason_code.as_str()), (Some("ceiling_path_v0"), SURVIVAL_MODEL_MISMATCH));

    // (2) INDEX'ten seri modeli çıkarılmış kopya → aynı kod
    let mut idx2 = index();
    let ids: Vec<String> =
        embedded::EMBEDDED_MODELS.iter().map(|m| m.model_id.to_string()).filter(|x| x != "ceiling_hazard_v0").collect();
    let models: Vec<Value> = idx2["models"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|e| e["model_id"] != json!("ceiling_hazard_v0"))
        .cloned()
        .collect();
    idx2["models"] = Value::Array(models);
    let files: Vec<EmbeddedModel> =
        embedded::EMBEDDED_MODELS.iter().filter(|m| ids.contains(&m.model_id.to_string())).copied().collect();
    let text = serde_json::to_string_pretty(&idx2).unwrap();
    let err = verify(&text, &files, &sha256_hex(text.as_bytes())).unwrap_err();
    assert_eq!(err.reason_code, SURVIVAL_MODEL_MISMATCH, "{err:?}");
}


// ---------------------------------------------------------------- U67: ikinci dizin (EK 3 §4.1, §6.1)

fn post_index() -> Value {
    serde_json::from_str(embedded::INDEX_POST_D1_JSON).unwrap()
}

/// Test içi kopya: D1 sonrası JSON'u ve/veya ikinci dizini değiştir; `fix_sha` ise dizindeki dosya sha'sı yeni dosyaya,
/// dönen dizin metninin sha'sı da `verify_post_d1`'e verilir (yalnız zincir denetimi kalır).
fn tampered_post(edit_model: impl Fn(&mut Value), edit_index: impl Fn(&mut Value), fix_sha: bool) -> (String, Vec<EmbeddedModel>) {
    let mut idx = post_index();
    let mut files = Vec::new();
    for (i, m) in embedded::EMBEDDED_POST_D1_MODELS.iter().enumerate() {
        let mut p: Value = serde_json::from_str(m.json).unwrap();
        edit_model(&mut p);
        let json = leak(serde_json::to_string_pretty(&p).unwrap());
        if fix_sha {
            idx["models"][i]["sha256"] = json!(sha256_hex(json.as_bytes()));
        }
        files.push(EmbeddedModel { model_id: m.model_id, file: m.file, json });
    }
    edit_index(&mut idx);
    (serde_json::to_string_pretty(&idx).unwrap(), files)
}

/// U67: gömülü `post_d1_hazard_v0.json` sha = INDEX_POST_D1; dizin sha = derleme bilgisi; ebeveyn ve tavan yolu sha zinciri
/// (dizin `parent_sha256` = INDEX `ceiling_hazard_v0` = gömülü dosya = JSON `parent.sha256`; `path_secondary.sha256` =
/// INDEX `ceiling_path_v0`); `parent.gamma[0]` bozulmuş test-içi kopya → INTEGRITY_FAILED / POST_D1_PARENT_MISMATCH ve
/// tahmin komutu hata döner; `predict_all` bu türü ÇALIŞTIRMAZ (27 sütun).
#[test]
fn post_d1_integrity() {
    let b = embedded::BUILD_INFO;
    assert_eq!(sha256_hex(embedded::INDEX_POST_D1_JSON.as_bytes()), b.index_post_d1_sha256);
    let pidx = post_index();
    let entries = pidx["models"].as_array().unwrap();
    assert_eq!(embedded::EMBEDDED_POST_D1_MODELS.len(), 1);
    assert_eq!(entries.len(), 1);
    let m = &embedded::EMBEDDED_POST_D1_MODELS[0];
    assert_eq!((m.model_id, entries[0]["model_id"].as_str()), ("post_d1_hazard_v0", Some("post_d1_hazard_v0")));
    assert_eq!(entries[0]["sha256"].as_str(), Some(sha256_hex(m.json.as_bytes()).as_str()));
    let idx = index();
    let sha_of = |id: &str| idx["models"].as_array().unwrap().iter().find(|e| e["model_id"] == json!(id)).unwrap()["sha256"].clone();
    let params: Value = serde_json::from_str(m.json).unwrap();
    assert_eq!(entries[0]["parent_sha256"], sha_of("ceiling_hazard_v0"));
    assert_eq!(params["parent"]["sha256"], sha_of("ceiling_hazard_v0"));
    assert_eq!(params["path_secondary"]["sha256"], sha_of("ceiling_path_v0"));
    let state = AppState::from_embedded();
    let v = state.models.as_ref().expect("bütünlük (iki dizin)");
    assert_eq!(v.post_d1.len(), 1);
    assert_eq!(v.index_post_d1_sha256.as_deref(), Some(b.index_post_d1_sha256));
    assert_eq!(borsai_predict::model_kind(&v.post_d1[0].params), borsai_predict::Kind::PostD1);

    let base = || verify(embedded::INDEX_JSON, embedded::EMBEDDED_MODELS, b.index_sha256).unwrap();
    let check = |idx_text: &str, files: &[EmbeddedModel]| verify_post_d1(idx_text, files, &sha256_hex(idx_text.as_bytes()), base());
    // pozitif: değişmemiş kopya geçer
    let (t, f) = tampered_post(|_| {}, |_| {}, true);
    assert!(check(&t, &f).is_ok());
    // (1) parent.gamma[0] bozulmuş kopya (dosya sha dizine uyarlanmış): JSON kopyası ebeveynle aynı değil
    let (t, f) = tampered_post(|p| p["parent"]["gamma"][0] = json!(p["parent"]["gamma"][0].as_f64().unwrap() + 1e-9), |_| {}, true);
    let err = check(&t, &f).unwrap_err();
    assert_eq!((err.model_id.as_deref(), err.reason_code.as_str()), (Some("post_d1_hazard_v0"), POST_D1_PARENT_MISMATCH));
    let st = AppState { models: Err(err), runtime: Default::default() };
    let e = predict_all_value(&st, &netgl_inputs(), &F6Arg::default(), Some(NETGL_T)).unwrap_err();
    assert_eq!(e.code, INTEGRITY_FAILED);
    // (2) dizin parent_sha256 başka bir sha
    let (t, f) = tampered_post(|_| {}, |i| i["models"][0]["parent_sha256"] = json!("0".repeat(64)), true);
    assert_eq!(check(&t, &f).unwrap_err().reason_code, POST_D1_PARENT_MISMATCH);
    // (3) path_secondary.sha256 başka bir sha
    let (t, f) = tampered_post(|p| p["path_secondary"]["sha256"] = json!("1".repeat(64)), |_| {}, true);
    assert_eq!(check(&t, &f).unwrap_err().reason_code, POST_D1_PARENT_MISMATCH);
    // (4) dosya sha dizine uyarlanmamış
    let (t, f) = tampered_post(|p| p["delta"]["d1_lock"] = json!(0.0), |_| {}, false);
    assert_eq!(check(&t, &f).unwrap_err().reason_code, POST_D1_PARENT_MISMATCH);
    // (5) dizin sha'sı derleme bilgisiyle uyuşmuyor
    let err = verify_post_d1(embedded::INDEX_POST_D1_JSON, embedded::EMBEDDED_POST_D1_MODELS, &"0".repeat(64), base()).unwrap_err();
    assert_eq!((err.model_id, err.reason_code.as_str()), (None, POST_D1_PARENT_MISMATCH));
    // (6) parametre denetimi (sıra bozuk kolon) bütünlük yolunda
    let (t, f) = tampered_post(|p| p["d1_preprocessing"]["columns"] = json!(["d1_turnover", "d1_lock"]), |_| {}, true);
    let err = check(&t, &f).unwrap_err();
    assert!(err.reason_code == POST_D1_PARENT_MISMATCH && err.message.contains("PARAMS_INVALID"), "{err:?}");

    // predict_all bu türü çalıştırmaz: 27 sütun, hiçbiri post_d1
    let f6 = F6Arg { value: Some(json!("0.01")), refusal: None };
    let runs = predict_all_value(&state, &netgl_inputs(), &f6, Some(NETGL_T)).unwrap();
    assert_eq!(runs.len(), N_EMBEDDED);
    assert!(runs.iter().all(|r| r["model_id"] != json!("post_d1_hazard_v0") && r["kind"] != json!("post_d1")));
}


// ---------------------------------------------------------------- FAZ9_SNAPSHOT: sicil anlık görüntüsü

use borsai_app_lib::commands::registry_snapshot::{
    self as snap, materialize, verify_embedded, verify_tree, MANIFEST_FILE, SNAPSHOT_DIR, SNAPSHOT_INTEGRITY_FAILED,
};
use borsai_app_lib::embedded::SnapshotFile;
use std::path::{Path, PathBuf};

fn snap_tmp(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("borsai_snap_integrity_{name}_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn disk(dir: &Path, rel: &str) -> PathBuf {
    rel.split('/').fold(dir.to_path_buf(), |p, c| p.join(c))
}

/// K-SNAP-1: manifest sha'sı = derleme bilgisi; her satır gömülü dosyanın yolu, sha256'sı ve bayt sayısı; dosyalar yol
/// sırasıyla; açılıştaki doğrulama geçer.
#[test]
fn snapshot_manifest_integrity() {
    let b = embedded::BUILD_INFO;
    let files = embedded::SNAPSHOT_FILES;
    assert!(!files.is_empty(), "derlemede anlık görüntü yok");
    assert_eq!(sha256_hex(b.snapshot_manifest.as_bytes()), b.snapshot_manifest_sha256);
    let lines: Vec<&str> = b.snapshot_manifest.lines().collect();
    assert_eq!(lines.len(), files.len());
    for (l, f) in lines.iter().zip(files) {
        assert_eq!(*l, format!("{}\t{}\t{}", f.rel, sha256_hex(f.bytes), f.bytes.len()));
        assert_eq!(f.sha256, sha256_hex(f.bytes), "{}", f.rel);
    }
    assert!(files.windows(2).all(|w| w[0].rel < w[1].rel), "yol sırası, tekil");
    verify_embedded(b.snapshot_manifest, b.snapshot_manifest_sha256, files).expect("gömülü anlık görüntü bütünlüğü");
    assert_eq!(snap::build_sha7().len(), 7);
}

/// K-SNAP-1/2: bir bayt mutasyonu → `SNAPSHOT_INTEGRITY_FAILED` (fail-closed). (a) gömülü kopyada: açılış doğrulaması;
/// (b) yazılmış dizinde: okuma doğrulaması ve dört ekran kapalı; yeniden açılış dizini siler ve yeniden yazar;
/// (c) fazla dosya da aynı; (d) manifestle uyuşmayan kopya hiç kullanılmaz; (e) korunan kök altına hiçbir şey yazılmaz.
#[test]
fn snapshot_one_byte_mutation_fails_closed() {
    let b = embedded::BUILD_INFO;
    let files = embedded::SNAPSHOT_FILES;
    let i = files.iter().position(|f| f.rel.starts_with("registry/records/")).expect("kayıt dosyası");
    // (a) gömülü kopyanın bir baytı değişmiş test-içi kopyası
    let mut bytes = files[i].bytes.to_vec();
    bytes[0] ^= 1;
    let mut bad: Vec<SnapshotFile> = files.to_vec();
    bad[i] = SnapshotFile { rel: files[i].rel, sha256: files[i].sha256, bytes: Box::leak(bytes.into_boxed_slice()) };
    let e = verify_embedded(b.snapshot_manifest, b.snapshot_manifest_sha256, &bad).unwrap_err();
    assert_eq!(e.code, SNAPSHOT_INTEGRITY_FAILED);
    assert!(e.message.contains(files[i].rel), "{}", e.message);
    assert_eq!(verify_embedded(b.snapshot_manifest, &"0".repeat(64), files).unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);
    // (d) manifestle uyuşmayan kopya yazılsa bile doğrulanmaz; dizin kullanılmaz
    let d0 = snap_tmp("d");
    assert_eq!(materialize(&d0, &[], "abc1234", &bad, b.snapshot_manifest).unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);

    // (b) kişisel mod: açılışta yazılır, doğrulanır; diskteki bir bayt değişince okuma kapanır
    let data = snap_tmp("b");
    let state = AppState::from_embedded();
    state.attach_data_dir(&data);
    state.prepare_snapshot();
    let root = state.read_root().expect("anlık görüntü");
    assert_eq!(root.root, data.join(SNAPSHOT_DIR).join(snap::build_sha7()));
    assert_eq!(root.snapshot.as_ref().map(|s| s.status), Some("READY"));
    verify_tree(&root.root, files, b.snapshot_manifest).unwrap();
    assert_eq!(std::fs::read(root.root.join(MANIFEST_FILE)).unwrap(), b.snapshot_manifest.as_bytes());
    let victim = disk(&root.root, files[i].rel);
    let mut on_disk = std::fs::read(&victim).unwrap();
    on_disk[0] ^= 1;
    std::fs::write(&victim, &on_disk).unwrap();
    assert_eq!(state.read_root().unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);
    assert_eq!(borsai_app_lib::commands::sade::monitor_view_value(&state).unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);
    assert_eq!(borsai_app_lib::commands::registry::registry_view_value(&state).unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);
    // aynı oturumda yeniden yazılmaz (yalnız açılışta üretilir)
    state.prepare_snapshot();
    assert_eq!(std::fs::read(&victim).unwrap(), on_disk);
    // yeniden açılış: tutmayan dizin silinir ve yeniden yazılır
    let again = AppState::from_embedded();
    again.attach_data_dir(&data);
    again.prepare_snapshot();
    assert_eq!(std::fs::read(&victim).unwrap(), files[i].bytes);
    assert!(again.read_root().is_ok());
    // (c) fazla dosya ve fazla (boş) arz dizini
    std::fs::create_dir_all(root.root.join("registry").join("records").join("ZZZZZ")).unwrap();
    assert_eq!(again.read_root().unwrap_err().code, SNAPSHOT_INTEGRITY_FAILED);
    std::fs::write(root.root.join("registry").join("records").join("ZZZZZ").join("x.json"), b"{}").unwrap();
    let third = AppState::from_embedded();
    third.attach_data_dir(&data);
    third.prepare_snapshot();
    assert!(!root.root.join("registry").join("records").join("ZZZZZ").exists());
    assert!(third.read_root().is_ok());
    // (e) uygulama verisi korunan bir kökün (repo) altındaysa hiçbir şey yazılmaz
    let repo_like = snap_tmp("e");
    let inside = repo_like.join("appdata");
    let e = materialize(&inside, &[repo_like.clone()], "abc1234", files, b.snapshot_manifest).unwrap_err();
    assert_eq!(e.code, SNAPSHOT_INTEGRITY_FAILED);
    assert!(!inside.exists(), "korunan kök altına yazılmadı");
    for d in [d0, data, repo_like] {
        let _ = std::fs::remove_dir_all(d);
    }
}
