//! Gömülü model kümesi: açılış doğrulaması (SPEC_APP §1.4, §2.1, §2.5) ve derleme bilgisi.
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};

use super::AppError;
use crate::embedded::{self, EmbeddedModel};
use crate::state::AppState;

pub const INDEX_SCHEMA: &str = "borsai.model_index/1";
pub const INTEGRITY_FAILED: &str = "INTEGRITY_FAILED";

pub fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

/// Doğrulanmış model kümesi (INDEX sırasıyla).
#[derive(Debug, Clone)]
pub struct VerifiedModels {
    pub index_sha256: String,
    pub models: Vec<borsai_predict::ModelRef>,
    pub kinds: Vec<borsai_predict::Kind>,
    /// İkinci dizin (models/INDEX_POST_D1.json; EK 3 §4.1 P2): `verify_post_d1` doldurur; `predict_all` bunları
    /// ÇALIŞTIRMAZ (Python `run_model` ERROR); giriş `commands::post_d1`.
    pub post_d1: Vec<borsai_predict::ModelRef>,
    pub index_post_d1_sha256: Option<String>,
}

impl VerifiedModels {
    pub fn by_id(&self, model_id: &str) -> Option<&borsai_predict::ModelRef> {
        self.models.iter().find(|m| m.model_id == model_id)
    }

    pub fn post_d1_by_id(&self, model_id: &str) -> Option<&borsai_predict::ModelRef> {
        self.post_d1.iter().find(|m| m.model_id == model_id)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct IntegrityError {
    /// Uyuşmayan model (INDEX'in kendisi için `None`).
    pub model_id: Option<String>,
    /// `INDEX_SHA_MISMATCH` | `INDEX_INVALID` | `MODEL_SHA_MISMATCH` | `MODEL_NOT_IN_INDEX` | `ORDER_MISMATCH`
    /// | `PARAMS_INVALID` | `SCHEMA_UNSUPPORTED` | `SURVIVAL_MODEL_MISMATCH`
    pub reason_code: String,
    pub message: String,
}

impl IntegrityError {
    fn new(model_id: Option<&str>, reason_code: &str, message: impl Into<String>) -> Self {
        IntegrityError { model_id: model_id.map(str::to_string), reason_code: reason_code.into(), message: message.into() }
    }

    pub fn to_app_error(&self) -> AppError {
        AppError {
            code: INTEGRITY_FAILED.into(),
            message: format!(
                "Gömülü model dosyası INDEX ile uyuşmuyor: {} ({})",
                self.model_id.as_deref().unwrap_or("models/INDEX.json"),
                self.reason_code
            ),
            detail: Some(self.message.clone()),
        }
    }
}

/// Her gömülü dosyanın sha256'sı INDEX'teki `sha256` ile, INDEX'in sha256'sı `build_info` ile;
/// sıra INDEX sırası; her dosya `_check_params` denetiminden geçer (PARAMS_INVALID bütünlük hatasıdır).
pub fn verify(index_json: &str, files: &[EmbeddedModel], expected_index_sha: &str) -> Result<VerifiedModels, IntegrityError> {
    let index_sha = sha256_hex(index_json.as_bytes());
    if index_sha != expected_index_sha {
        return Err(IntegrityError::new(None, "INDEX_SHA_MISMATCH", format!("{index_sha} != build_info {expected_index_sha}")));
    }
    let index: Value = serde_json::from_str(index_json)
        .map_err(|e| IntegrityError::new(None, "INDEX_INVALID", format!("INDEX.json ayrıştırılamadı: {e}")))?;
    if index.get("schema_version").and_then(Value::as_str) != Some(INDEX_SCHEMA) {
        return Err(IntegrityError::new(None, "INDEX_INVALID", format!("schema_version {INDEX_SCHEMA} değil")));
    }
    let entries = index
        .get("models")
        .and_then(Value::as_array)
        .ok_or_else(|| IntegrityError::new(None, "INDEX_INVALID", "models listesi yok"))?;
    let mut models = Vec::with_capacity(files.len());
    let mut kinds = Vec::with_capacity(files.len());
    for (i, f) in files.iter().enumerate() {
        let entry = entries.get(i).ok_or_else(|| IntegrityError::new(Some(f.model_id), "MODEL_NOT_IN_INDEX", "INDEX'te yok"))?;
        if entry.get("model_id").and_then(Value::as_str) != Some(f.model_id)
            || entry.get("file").and_then(Value::as_str) != Some(f.file)
        {
            return Err(IntegrityError::new(Some(f.model_id), "ORDER_MISMATCH", format!("INDEX kaydı {i}: {entry}")));
        }
        let sha = sha256_hex(f.json.as_bytes());
        if entry.get("sha256").and_then(Value::as_str) != Some(sha.as_str()) {
            return Err(IntegrityError::new(Some(f.model_id), "MODEL_SHA_MISMATCH", format!("dosya sha256 {sha}")));
        }
        let params: Value = serde_json::from_str(f.json)
            .map_err(|e| IntegrityError::new(Some(f.model_id), "PARAMS_INVALID", format!("JSON ayrıştırılamadı: {e}")))?;
        let kind = borsai_predict::check_params(&params)
            .map_err(|e| IntegrityError::new(Some(f.model_id), &e.code, e.message))?;
        kinds.push(kind);
        models.push(borsai_predict::ModelRef { model_id: f.model_id.to_string(), params_sha256: sha, params });
    }
    verify_survival_copies(entries, &models, &kinds)?;
    Ok(VerifiedModels { index_sha256: index_sha, models, kinds, post_d1: Vec::new(), index_post_d1_sha256: None })
}

pub const POST_D1_PARENT_MISMATCH: &str = "POST_D1_PARENT_MISMATCH";

/// U67 (EK 3 §4.1, §6.1): ikinci dizinin açılış denetimi. Dizin sha = derleme bilgisi; her dosya sha = dizindeki
/// `sha256`; dizin girişinin `parent_sha256` = INDEX'teki `ceiling_hazard_v0.sha256` = gömülü dosyanın sha'sı; JSON
/// `parent.sha256` aynı; `path_secondary.sha256` = INDEX'teki `ceiling_path_v0.sha256` = gömülü dosyanın sha'sı;
/// `parse_post_d1(post, parent, path)` ve ebeveynin kendi denetimi geçer. Tek uyuşmazlık → `INTEGRITY_FAILED /
/// POST_D1_PARENT_MISMATCH` (U41 kalıbı: ofsetin bit-eşitliği ebeveyn kopyasının bozulmamasına dayanır).
pub fn verify_post_d1(
    post_index_json: &str,
    files: &[EmbeddedModel],
    expected_post_index_sha: &str,
    verified: VerifiedModels,
) -> Result<VerifiedModels, IntegrityError> {
    let fail = |id: Option<&str>, msg: String| IntegrityError::new(id, POST_D1_PARENT_MISMATCH, msg);
    let sha = sha256_hex(post_index_json.as_bytes());
    if sha != expected_post_index_sha {
        return Err(fail(None, format!("INDEX_POST_D1 sha256 {sha} != build_info {expected_post_index_sha}")));
    }
    let index: Value = serde_json::from_str(post_index_json).map_err(|e| fail(None, format!("INDEX_POST_D1 ayrıştırılamadı: {e}")))?;
    if index.get("schema_version").and_then(Value::as_str) != Some(INDEX_SCHEMA) {
        return Err(fail(None, format!("INDEX_POST_D1 schema_version {INDEX_SCHEMA} değil")));
    }
    let entries = index.get("models").and_then(Value::as_array).ok_or_else(|| fail(None, "INDEX_POST_D1: models listesi yok".into()))?;
    if entries.len() != files.len() {
        return Err(fail(None, format!("INDEX_POST_D1 {} kayıt, gömülü {}", entries.len(), files.len())));
    }
    let text = |v: &Value, k: &str| v.get(k).and_then(Value::as_str).map(str::to_string);
    let mut post = Vec::with_capacity(files.len());
    for (entry, f) in entries.iter().zip(files) {
        let id = Some(f.model_id);
        if text(entry, "model_id").as_deref() != Some(f.model_id) || text(entry, "file").as_deref() != Some(f.file) {
            return Err(fail(id, format!("INDEX_POST_D1 kaydı: {entry}")));
        }
        let file_sha = sha256_hex(f.json.as_bytes());
        if text(entry, "sha256").as_deref() != Some(file_sha.as_str()) {
            return Err(fail(id, format!("dosya sha256 {file_sha} != INDEX_POST_D1")));
        }
        let params: Value = serde_json::from_str(f.json).map_err(|e| fail(id, format!("JSON ayrıştırılamadı: {e}")))?;
        // ebeveyn: dizin girişi ↔ INDEX ↔ gömülü dosya ↔ JSON kopyası
        let parent_id = text(entry, "parent_model_id").unwrap_or_default();
        let parent = verified.by_id(&parent_id).ok_or_else(|| fail(id, format!("ebeveyn gömülü kümede yok: {parent_id:?}")))?;
        let want = text(entry, "parent_sha256").unwrap_or_default();
        let copy_sha = params.pointer("/parent/sha256").and_then(Value::as_str).unwrap_or("");
        if want != parent.params_sha256 || copy_sha != want || params.pointer("/parent/model_id") != Some(&Value::from(parent_id.as_str())) {
            return Err(fail(id, format!("ebeveyn sha zinciri: dizin {want}, JSON {copy_sha}, gömülü {} ({parent_id})", parent.params_sha256)));
        }
        // ikincil tavan yolu: JSON `path_secondary` ↔ INDEX ↔ gömülü dosya
        let path_id = params.pointer("/path_secondary/model_id").and_then(Value::as_str).unwrap_or("");
        let path_sha = params.pointer("/path_secondary/sha256").and_then(Value::as_str).unwrap_or("");
        let path = verified.by_id(path_id).ok_or_else(|| fail(id, format!("tavan yolu gömülü kümede yok: {path_id:?}")))?;
        if path_sha != path.params_sha256 {
            return Err(fail(id, format!("path_secondary.sha256 {path_sha} != gömülü {} ({path_id})", path.params_sha256)));
        }
        borsai_predict::params::parse_post_d1(&params, &parent.params, Some(&path.params))
            .and_then(|_| borsai_predict::params::parse_hazard(&parent.params))
            .and_then(|_| borsai_predict::params::parse_path(&path.params))
            .map_err(|e| fail(id, format!("{}: {}", e.code, e.message)))?;
        post.push(borsai_predict::ModelRef { model_id: f.model_id.to_string(), params_sha256: file_sha, params });
    }
    Ok(VerifiedModels { post_d1: post, index_post_d1_sha256: Some(sha), ..verified })
}

/// Açılış: birinci dizin (`verify`) ve ikinci dizin (`verify_post_d1`); herhangi bir uyuşmazlık bütün uygulamayı
/// `INTEGRITY_FAILED`'a düşürür (kısmi çalışma yok; SPEC_APP §1.4).
pub fn verify_embedded() -> Result<VerifiedModels, IntegrityError> {
    let b = embedded::BUILD_INFO;
    let v = verify(embedded::INDEX_JSON, embedded::EMBEDDED_MODELS, b.index_sha256)?;
    verify_post_d1(embedded::INDEX_POST_D1_JSON, embedded::EMBEDDED_POST_D1_MODELS, b.index_post_d1_sha256, v)
}

pub const SURVIVAL_MODEL_MISMATCH: &str = "SURVIVAL_MODEL_MISMATCH";

/// U41: her `ceiling_path` modelinde gömülü seri modeli kopyası bozulmamış olmalı —
/// (a) `survival_model_sha256` INDEX'te `model_id == survival_model_id` olan kaydın sha256'sına eşit,
/// (b) o kayıt gömülü model kümesinde var ve dosya sha'sı aynı,
/// (c) `survival_model` JSON değeri o gömülü dosyanın ayrıştırılmış değerine YAPISAL olarak eşit.
/// Tek uyuşmazlık → `INTEGRITY_FAILED` / `SURVIVAL_MODEL_MISMATCH` (SPEC_APP §1.4 fail-closed).
fn verify_survival_copies(
    entries: &[Value],
    models: &[borsai_predict::ModelRef],
    kinds: &[borsai_predict::Kind],
) -> Result<(), IntegrityError> {
    for (m, kind) in models.iter().zip(kinds) {
        if *kind != borsai_predict::Kind::CeilingPath {
            continue;
        }
        let id = m.model_id.as_str();
        let fail = |msg: String| IntegrityError::new(Some(id), SURVIVAL_MODEL_MISMATCH, msg);
        let sid = m.params.get("survival_model_id").and_then(Value::as_str).unwrap_or("");
        let want = m.params.get("survival_model_sha256").and_then(Value::as_str).unwrap_or("");
        let index_sha = entries
            .iter()
            .find(|e| e.get("model_id").and_then(Value::as_str) == Some(sid))
            .and_then(|e| e.get("sha256"))
            .and_then(Value::as_str)
            .ok_or_else(|| fail(format!("seri modeli INDEX'te yok: {sid:?}")))?;
        if index_sha != want {
            return Err(fail(format!("survival_model_sha256 {want} != INDEX {index_sha} ({sid})")));
        }
        let embedded = models
            .iter()
            .find(|x| x.model_id == sid)
            .ok_or_else(|| fail(format!("seri modeli gömülü kümede yok: {sid:?}")))?;
        if embedded.params_sha256 != want {
            return Err(fail(format!("gömülü {sid} dosya sha256 {} != {want}", embedded.params_sha256)));
        }
        if m.params.get("survival_model") != Some(&embedded.params) {
            return Err(fail(format!("gömülü {sid} kopyası dosyadan farklı (yapısal eşitlik)")));
        }
    }
    Ok(())
}

#[derive(Debug, Clone, Serialize)]
pub struct ModelInfo {
    pub model_id: String,
    pub kind: &'static str,
    pub params_sha256: String,
    /// Model kartı "ne yapar" (parametre dosyasının `description`'ı).
    pub description: Option<String>,
    pub algorithm: Option<String>,
    /// INDEX kaydından.
    pub training_n: Option<u64>,
    pub training_cutoff_date: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AppInfo {
    pub app_version: &'static str,
    pub build_git_head: &'static str,
    pub build_git_status_models_scores: &'static str,
    pub index_sha256: &'static str,
    /// İkinci dizin (models/INDEX_POST_D1.json) sha256 ve gömülü D1 sonrası modeller (EK 3 §9 ABOUT.postD1Index).
    pub index_post_d1_sha256: &'static str,
    pub embedded_post_d1_models: Vec<&'static str>,
    pub embedded_models: Vec<&'static str>,
    pub ignored_index_models: Vec<&'static str>,
    pub scores_embedded: bool,
    /// Gömülü TÜFE tablosunun durumu (bağımsız modun kaynağı; EK 3 §3.5 Hakkında satırı); tablo gömülü değilse null.
    pub tufe_embedded: Option<super::predict::TufeStatus>,
    pub integrity_ok: bool,
    pub integrity_error: Option<AppError>,
    pub models: Vec<ModelInfo>,
}

fn index_entry(model_id: &str) -> Option<Value> {
    let index: Value = serde_json::from_str(embedded::INDEX_JSON).ok()?;
    index.get("models")?.as_array()?.iter().find(|e| e.get("model_id").and_then(Value::as_str) == Some(model_id)).cloned()
}

fn model_info(m: &borsai_predict::ModelRef, k: borsai_predict::Kind) -> ModelInfo {
    let entry = index_entry(&m.model_id);
    let text = |v: Option<&Value>| v.and_then(Value::as_str).map(str::to_string);
    ModelInfo {
        model_id: m.model_id.clone(),
        kind: k.as_str(),
        params_sha256: m.params_sha256.clone(),
        description: text(m.params.get("description")),
        algorithm: text(m.params.get("algorithm")),
        training_n: entry.as_ref().and_then(|e| e.get("training_n")).and_then(Value::as_u64),
        training_cutoff_date: text(entry.as_ref().and_then(|e| e.get("training_cutoff_date"))),
    }
}

pub fn app_info_value(state: &AppState) -> AppInfo {
    let b = embedded::BUILD_INFO;
    let (integrity_ok, integrity_error, models) = match &state.models {
        Ok(v) => (
            true,
            None,
            v.models
                .iter()
                .zip(&v.kinds)
                .map(|(m, k)| model_info(m, *k))
                .collect(),
        ),
        Err(e) => (false, Some(e.to_app_error()), Vec::new()),
    };
    AppInfo {
        app_version: env!("CARGO_PKG_VERSION"),
        build_git_head: b.git_head,
        build_git_status_models_scores: b.git_status_models_scores,
        index_sha256: b.index_sha256,
        index_post_d1_sha256: b.index_post_d1_sha256,
        embedded_post_d1_models: embedded::EMBEDDED_POST_D1_MODELS.iter().map(|m| m.model_id).collect(),
        embedded_models: embedded::EMBEDDED_MODELS.iter().map(|m| m.model_id).collect(),
        ignored_index_models: b.ignored_index_models.to_vec(),
        scores_embedded: embedded::SCORES_JSON.is_some(),
        tufe_embedded: super::predict::tufe_source_embedded()
            .map(|src| super::predict::tufe_status(&src, super::predict::embedded_deflator_pins())),
        integrity_ok,
        integrity_error,
        models,
    }
}

#[tauri::command]
pub fn app_info(state: tauri::State<'_, AppState>) -> Result<AppInfo, AppError> {
    Ok(app_info_value(&state))
}
