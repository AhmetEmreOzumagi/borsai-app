//! Dondur akışı adım 2 (SPEC_APP §3e): kaynak belgeleri `<repo>/registry/source_docs/<T>/` altına
//! kopyalar ve `MANIFEST.json`'a ekler.
//!
//! Kurallar:
//! - Var olan aynı adlı dosya ancak sha256 eşitse kabul edilir; farklıysa DUR (`SOURCE_DOC_CONFLICT`).
//! - MANIFEST'teki var olan giriş DEĞİŞTİRİLMEZ (aynı `source_id` yeniden yazılmaz, `KEPT` raporlanır).
//! - Alan adları NETGL MANIFEST'indeki biçimdir [ÖLÇTÜM `registry/source_docs/NETGL/MANIFEST.json`].
//! - MANIFEST baytları `pretty_json_bytes` biçimindedir (Python'la bayt-eşit).
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::path::{Path, PathBuf};

use super::inputs_doc::valid_ticker;
use super::models::sha256_hex;
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::clock::now_istanbul;
use crate::json_out::pretty_json_bytes;
use crate::state::AppState;

pub const SOURCE_DOCS_SCHEMA: &str = "borsai.source_docs/1";
pub const SOURCE_DOC_CONFLICT: &str = "SOURCE_DOC_CONFLICT";
pub const MANIFEST_INVALID: &str = "MANIFEST_INVALID";
/// `borsai.registry` kaynak türleri (SPEC_APP §2.2).
pub const SOURCE_KINDS: [&str; 3] = ["KAP_NOTIFICATION_PDF", "KAP_ATTACHMENT_PDF", "SPK_BULLETIN"];

#[derive(Debug, Clone, Deserialize)]
pub struct SourceDocReq {
    pub source_id: String,
    pub kind: String,
    pub document_id: String,
    /// ISO + saat dilimi (belgenin yayın zamanı).
    pub published_at: String,
    /// Yayın zamanının nereden ölçüldüğü (serbest metin; boş olamaz).
    pub published_at_basis: String,
    /// Kopyalanacak yerel dosya (dosya seçiciden).
    pub path: String,
    /// Hedef dosya adı; verilmezse kaynak dosyanın adı.
    pub file_name: Option<String>,
    pub title: Option<String>,
    pub url: Option<String>,
    pub issuer: Option<String>,
}

/// NEW: kopyalandı · SAME: aynı sha ile zaten vardı · KEPT: MANIFEST girişi korundu.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SourceDocResult {
    pub source_id: String,
    pub file_name: String,
    pub rel_path: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub file_state: &'static str,
    pub manifest_state: &'static str,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SourceDocsView {
    pub ticker: String,
    pub rel_dir: String,
    pub manifest_rel_path: String,
    pub documents: Vec<SourceDocResult>,
    /// MANIFEST'teki bütün belgeler (girdi belgesi adımında kaynak seçimi için).
    pub manifest: Value,
}

fn safe_file_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 120
        && !name.starts_with('.')
        && !name.contains('/')
        && !name.contains('\\')
        && name.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-+@".contains(&b))
}

fn safe_source_id(id: &str) -> bool {
    !id.is_empty() && id.len() <= 64 && id.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
}

pub fn source_docs_dir(repo: &Path, ticker: &str) -> PathBuf {
    repo.join("registry").join("source_docs").join(ticker)
}

/// MANIFEST.json (yoksa boş iskelet). Sürümü farklıysa `MANIFEST_INVALID`.
pub fn read_manifest(repo: &Path, ticker: &str) -> Result<Value, AppError> {
    let path = source_docs_dir(repo, ticker).join("MANIFEST.json");
    let Ok(bytes) = std::fs::read(&path) else {
        return Ok(serde_json::json!({"schema_version": SOURCE_DOCS_SCHEMA, "ticker": ticker, "documents": {}}));
    };
    let doc: Value = serde_json::from_slice(&bytes).map_err(|e| AppError::new(MANIFEST_INVALID, e.to_string()))?;
    if doc.get("schema_version").and_then(Value::as_str) != Some(SOURCE_DOCS_SCHEMA) {
        return Err(AppError::new(MANIFEST_INVALID, format!("schema_version {SOURCE_DOCS_SCHEMA} değil")));
    }
    if !doc.get("documents").is_some_and(Value::is_object) {
        return Err(AppError::new(MANIFEST_INVALID, "documents nesnesi yok"));
    }
    Ok(doc)
}

pub fn copy_source_docs_in(repo: &Path, ticker: &str, docs: &[SourceDocReq]) -> Result<SourceDocsView, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let dir = source_docs_dir(repo, ticker);
    let mut manifest = read_manifest(repo, ticker)?;
    let mut entries = manifest["documents"].as_object().cloned().unwrap_or_default();
    let now = now_istanbul();
    let mut out = Vec::with_capacity(docs.len());
    // Önce bütün dosyalar okunur ve çakışma denetlenir: tek DUR'da hiçbir şey yazılmaz.
    let mut staged: Vec<(SourceDocResult, Vec<u8>)> = Vec::with_capacity(docs.len());
    for d in docs {
        if !safe_source_id(&d.source_id) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("source_id {:?}", d.source_id)));
        }
        if !SOURCE_KINDS.contains(&d.kind.as_str()) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("kind {:?}", d.kind)));
        }
        for (name, v) in [("document_id", &d.document_id), ("published_at", &d.published_at), ("published_at_basis", &d.published_at_basis)] {
            if v.trim().is_empty() {
                return Err(AppError::new(INVALID_ARGUMENT, format!("{name} boş ({})", d.source_id)));
            }
        }
        if !super::inputs_doc::iso_datetime_with_offset(&d.published_at) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("{}: published_at ISO + saat dilimi değil", d.source_id)));
        }
        let src = PathBuf::from(&d.path);
        let file_name = d
            .file_name
            .clone()
            .or_else(|| src.file_name().map(|n| n.to_string_lossy().to_string()))
            .unwrap_or_default();
        if !safe_file_name(&file_name) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("dosya adı {file_name:?}")));
        }
        let bytes = std::fs::read(&src).map_err(|e| io_error(&d.path, e))?;
        let sha = sha256_hex(&bytes);
        let target = dir.join(&file_name);
        let file_state = match std::fs::read(&target) {
            Ok(existing) if sha256_hex(&existing) == sha => "SAME",
            Ok(_) => {
                return Err(AppError::new(
                    SOURCE_DOC_CONFLICT,
                    format!("{file_name}: aynı adlı dosya farklı içerikte; DUR (var olan dosya değiştirilmez)"),
                ))
            }
            Err(_) => "NEW",
        };
        let manifest_state = if entries.contains_key(&d.source_id) { "KEPT" } else { "NEW" };
        if manifest_state == "KEPT" {
            let old = &entries[&d.source_id];
            if old.get("sha256").and_then(Value::as_str) != Some(sha.as_str()) {
                return Err(AppError::new(
                    SOURCE_DOC_CONFLICT,
                    format!("{}: MANIFEST'te farklı sha256 ile kayıtlı; DUR (var olan giriş değiştirilmez)", d.source_id),
                ));
            }
        }
        staged.push((
            SourceDocResult {
                source_id: d.source_id.clone(),
                rel_path: format!("registry/source_docs/{ticker}/{file_name}"),
                file_name,
                size_bytes: bytes.len() as u64,
                sha256: sha,
                file_state,
                manifest_state,
            },
            bytes,
        ));
    }
    std::fs::create_dir_all(&dir).map_err(|e| io_error("source_docs dizini", e))?;
    for ((res, bytes), d) in staged.iter().zip(docs) {
        if res.file_state == "NEW" {
            std::fs::write(dir.join(&res.file_name), bytes).map_err(|e| io_error(&res.rel_path, e))?;
        }
        if res.manifest_state == "NEW" {
            let mut e = Map::new();
            e.insert("document_id".into(), Value::String(d.document_id.trim().into()));
            e.insert("downloaded_at".into(), Value::String(now.clone()));
            e.insert("kind".into(), Value::String(d.kind.clone()));
            e.insert("path".into(), Value::String(res.rel_path.clone()));
            e.insert("published_at".into(), Value::String(d.published_at.trim().into()));
            e.insert("published_at_basis".into(), Value::String(d.published_at_basis.trim().into()));
            e.insert("sha256".into(), Value::String(res.sha256.clone()));
            e.insert("size_bytes".into(), Value::Number(res.size_bytes.into()));
            for (k, v) in [("title", &d.title), ("url", &d.url), ("issuer", &d.issuer)] {
                if let Some(s) = v.as_deref().map(str::trim).filter(|s| !s.is_empty()) {
                    e.insert(k.into(), Value::String(s.into()));
                }
            }
            entries.insert(d.source_id.clone(), Value::Object(e));
        }
        out.push(res.clone());
    }
    manifest["schema_version"] = Value::String(SOURCE_DOCS_SCHEMA.into());
    manifest["ticker"] = Value::String(ticker.into());
    manifest["documents"] = Value::Object(entries);
    let manifest_rel = format!("registry/source_docs/{ticker}/MANIFEST.json");
    let payload = pretty_json_bytes(&manifest).map_err(|e| AppError::new(MANIFEST_INVALID, e))?;
    std::fs::write(dir.join("MANIFEST.json"), payload).map_err(|e| io_error(&manifest_rel, e))?;
    Ok(SourceDocsView {
        ticker: ticker.into(),
        rel_dir: format!("registry/source_docs/{ticker}"),
        manifest_rel_path: manifest_rel,
        documents: out,
        manifest,
    })
}

#[tauri::command]
pub fn copy_source_docs(
    state: tauri::State<'_, AppState>,
    ticker: String,
    docs: Vec<SourceDocReq>,
) -> Result<SourceDocsView, AppError> {
    copy_source_docs_in(&state.require_repo()?.root, &ticker, &docs)
}

/// Girdi belgesi adımında kaynak seçimi: var olan MANIFEST (salt okuma).
#[tauri::command]
pub fn read_source_manifest(state: tauri::State<'_, AppState>, ticker: String) -> Result<Value, AppError> {
    let repo = state.require_repo()?;
    if !valid_ticker(&ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    read_manifest(&repo.root, &ticker)
}
