//! Girdi belgesi (`borsai.inputs/1`): OKUMA (senaryo formuna kopya) ve YAZMA (dondur akışı §3e adım 3).
//!
//! - Yazılan baytlar `borsai.provenance.pretty_json_bytes` ile bayt-eşittir (`crate::json_out`).
//! - `validate_inputs` Python `borsai/registry.py:159-202`'nin portudur; sorun metinleri birebir aynıdır
//!   (e2e betiği Rust ve Python listelerini karşılaştırır). YETKİLİ denetim yine Python'dur (§3e adım 4).
//! - Dosya adı (FAZ3_APP_STAGE01 kararı): `PRE_BOOKBUILD` → `registry/inputs/<T>.PB.json`,
//!   `POST_BOOKBUILD_PRE_LISTING` → `registry/inputs/<T>.json`.
//! - Var olan dosyanın üzerine ancak kullanıcı farkı görüp onayladıktan sonra yazılır.
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::path::Path;

use super::form::{DATE_FIELDS, FORM_FIELDS, PB_FIELDS, STAGES, V15_FIELDS};
use super::source_docs::read_manifest;
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::clock::{is_iso_date, now_istanbul};
use crate::json_out::pretty_json_bytes;
use crate::state::AppState;

pub const INPUTS_SCHEMA: &str = "borsai.inputs/1";
pub const INPUTS_SCHEMA_UNSUPPORTED: &str = "INPUTS_SCHEMA_UNSUPPORTED";
pub const INPUTS_DOC_EXISTS: &str = "INPUTS_DOC_EXISTS";
pub const INPUTS_DOC_INVALID: &str = "INPUTS_DOC_INVALID";
pub const COLLECTED_AT_BASIS: &str = "LOCAL_CLOCK_SELF_REPORTED";

/// Python `registry.INPUT_FIELDS` sırası: 9 V1.5 + 8 PB + 3 tarih (sorun listesinin sırası buna bağlı).
pub fn input_fields() -> impl Iterator<Item = &'static str> {
    V15_FIELDS.iter().chain(PB_FIELDS.iter()).chain(DATE_FIELDS.iter()).copied()
}

pub const FIELD_SOURCE_KEYS: [&str; 5] = ["source_id", "source_document", "source_published_at", "source_sha256", "source_path"];
pub const F3_ORIGINS: [&str; 4] =
    ["SOURCE_REPORTED", "SOURCE_REPORTED_APPROX", "CALCULATED_FROM_SOURCE_TOTALS", "CALCULATED_FROM_PRIMARY_TOTALS"];
pub const FILTER_STATUSES: [&str; 3] = ["NOT_SPECIFIED", "UNFILTERED", "FILTERED"];

/// Arz kodu: yol parçası olarak güvenli (büyük harf ve rakam).
pub fn valid_ticker(t: &str) -> bool {
    (2..=12).contains(&t.len()) && t.bytes().all(|b| b.is_ascii_uppercase() || b.is_ascii_digit())
}

/// Python `_iso_datetime_with_offset`: `datetime.fromisoformat` geçerli ve `tzinfo` var.
pub fn iso_datetime_with_offset(value: &str) -> bool {
    let b = value.as_bytes();
    if b.len() < 11 || !is_iso_date(&value[..10]) || !(b[10] == b'T' || b[10] == b' ') {
        return false;
    }
    let rest = &value[11..];
    let (time, tz) = match rest.rfind(['+', '-']) {
        Some(i) if i > 0 => (&rest[..i], &rest[i..]),
        _ if rest.ends_with('Z') || rest.ends_with('z') => (&rest[..rest.len() - 1], "Z"),
        _ => return false,
    };
    let (hms, frac) = time.split_once('.').unwrap_or((time, ""));
    let parts: Vec<&str> = hms.split(':').collect();
    let two = |s: &str| s.len() == 2 && s.bytes().all(|c| c.is_ascii_digit());
    if !(2..=3).contains(&parts.len()) || !parts.iter().all(|p| two(p)) {
        return false;
    }
    if !frac.is_empty() && (frac.len() > 6 || !frac.bytes().all(|c| c.is_ascii_digit())) {
        return false;
    }
    if tz == "Z" {
        return true;
    }
    let off = &tz[1..];
    let digits: Vec<&str> = off.split(':').collect();
    (1..=3).contains(&digits.len()) && digits.iter().all(|p| two(p))
}

/// Python `repr(str)`: sorun metinlerinde değer gösterimi (tek tırnak).
fn repr(s: &str) -> String {
    if s.contains('\'') && !s.contains('"') {
        format!("\"{s}\"")
    } else {
        format!("'{}'", s.replace('\\', "\\\\").replace('\'', "\\'"))
    }
}

fn truthy(v: Option<&Value>) -> bool {
    match v {
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Null) | None => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
        Some(Value::Number(n)) => n.as_f64() != Some(0.0),
    }
}

/// `borsai/registry.py: validate_inputs` portu. Boş liste = yapısal olarak geçerli.
pub fn validate_inputs(doc: &Value) -> Vec<String> {
    let mut problems: Vec<String> = Vec::new();
    if doc.get("schema_version").and_then(Value::as_str) != Some(INPUTS_SCHEMA) {
        let v = doc.get("schema_version").map(|v| match v {
            Value::String(s) => repr(s),
            other => other.to_string(),
        });
        return vec![format!("schema_version {}", v.unwrap_or_else(|| "None".into()))];
    }
    if !truthy(doc.get("ticker")) {
        problems.push("ticker yok".into());
    }
    let empty = Map::new();
    let fields = doc.get("fields").and_then(Value::as_object).unwrap_or(&empty);
    let sources = doc.get("sources").and_then(Value::as_object).unwrap_or(&empty);
    for name in input_fields() {
        let Some(f) = fields.get(name) else {
            problems.push(format!("{name}: alan yok"));
            continue;
        };
        let value = f.get("value");
        if value.is_none() || value == Some(&Value::Null) {
            if !truthy(f.get("missing_reason")) {
                problems.push(format!("{name}: boş alan missing_reason taşımıyor"));
            }
            continue;
        }
        let value = value.expect("value");
        if !value.is_string() {
            problems.push(format!("{name}: değer metin değil ({value})"));
        }
        for key in FIELD_SOURCE_KEYS {
            if !truthy(f.get(key)) {
                problems.push(format!("{name}: {key} yok"));
            }
        }
        let sid = f.get("source_id").and_then(Value::as_str);
        let Some(src) = sid.and_then(|s| sources.get(s)) else {
            problems.push(format!("{name}: kaynak {} kaynak tablosunda yok", sid.map(repr).unwrap_or_else(|| "None".into())));
            continue;
        };
        for (fk, sk) in [("source_published_at", "published_at"), ("source_sha256", "sha256"), ("source_path", "path")] {
            if f.get(fk).unwrap_or(&Value::Null) != src.get(sk).unwrap_or(&Value::Null) {
                problems.push(format!("{name}: {fk} kaynak tablosuyla uyuşmuyor"));
            }
        }
        if !iso_datetime_with_offset(f.get("source_published_at").and_then(Value::as_str).unwrap_or("")) {
            problems.push(format!("{name}: yayın zamanı ISO + saat dilimi değil"));
        }
    }
    for name in DATE_FIELDS {
        let v = fields.get(name).and_then(|f| f.get("value"));
        match v {
            None | Some(Value::Null) => {}
            Some(Value::String(s)) if is_iso_date(s) => {}
            Some(Value::String(s)) => problems.push(format!("{name}: ISO tarih değil ({})", repr(s))),
            Some(other) => problems.push(format!("{name}: ISO tarih değil ({other})")),
        }
    }
    let f3 = fields.get("total_demand_multiple");
    let f3_value = f3.and_then(|f| f.get("value"));
    if f3_value.is_some() && f3_value != Some(&Value::Null) {
        let origin = f3.and_then(|f| f.get("origin")).and_then(Value::as_str);
        if !origin.is_some_and(|o| F3_ORIGINS.contains(&o)) {
            problems.push(format!(
                "total_demand_multiple: origin {}",
                origin.map(repr).unwrap_or_else(|| "None".into())
            ));
        }
    }
    let fs = fields.get("total_demand_filter_status").and_then(|f| f.get("value"));
    match fs {
        None | Some(Value::Null) => {}
        Some(Value::String(s)) if FILTER_STATUSES.contains(&s.as_str()) => {}
        Some(Value::String(s)) => problems.push(format!("total_demand_filter_status {}", repr(s))),
        Some(other) => problems.push(format!("total_demand_filter_status {other}")),
    }
    problems
}

// ---------------------------------------------------------------- okuma (aşama 2'den)

#[derive(Debug, Clone, Serialize)]
pub struct InputDocument {
    pub ticker: String,
    pub company: Option<String>,
    pub stage: Option<String>,
    pub rel_path: String,
    /// Form alanı → metin ya da null.
    pub values: Map<String, Value>,
    /// Boş alanların `missing_reason`'ı.
    pub missing_reasons: Map<String, Value>,
}

/// `registry/inputs/` altındaki girdi belgeleri: `<T>.json` ve `<T>.PB.json`.
pub fn list_input_documents_in(repo: &Path) -> Result<Vec<String>, AppError> {
    let dir = repo.join("registry").join("inputs");
    let mut out: Vec<String> = std::fs::read_dir(&dir)
        .map_err(|e| io_error("registry/inputs okunamadı", e))?
        .filter_map(|e| e.ok())
        .filter_map(|e| e.file_name().to_str().and_then(|n| n.strip_suffix(".json")).map(str::to_string))
        .filter(|t| valid_ticker(t))
        .collect();
    out.sort();
    Ok(out)
}

pub fn read_input_document_in(repo: &Path, ticker: &str) -> Result<InputDocument, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let rel = format!("registry/inputs/{ticker}.json");
    let bytes = std::fs::read(repo.join(&rel)).map_err(|e| io_error(&rel, e))?;
    let doc: Value = serde_json::from_slice(&bytes).map_err(|e| io_error(&rel, e))?;
    let version = doc.get("schema_version").and_then(Value::as_str).unwrap_or("");
    if version != INPUTS_SCHEMA {
        return Err(AppError::new(INPUTS_SCHEMA_UNSUPPORTED, format!("{rel}: sürüm {version:?}")));
    }
    let fields = doc.get("fields").and_then(Value::as_object).cloned().unwrap_or_default();
    let mut values = Map::new();
    let mut missing_reasons = Map::new();
    for f in FORM_FIELDS {
        let entry = fields.get(f);
        let v = entry.and_then(|e| e.get("value")).filter(|v| v.is_string()).cloned().unwrap_or(Value::Null);
        if v.is_null() {
            if let Some(r) = entry.and_then(|e| e.get("missing_reason")).filter(|r| r.is_string()) {
                missing_reasons.insert(f.into(), r.clone());
            }
        }
        values.insert(f.into(), v);
    }
    let text = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    Ok(InputDocument { ticker: ticker.into(), company: text("company"), stage: text("stage"), rel_path: rel, values, missing_reasons })
}

// ---------------------------------------------------------------- yazma (§3e adım 3)

#[derive(Debug, Clone, Deserialize)]
pub struct CrossCheck {
    pub source_id: String,
    pub quote: String,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct FieldDraft {
    /// Dolu alan: normalize metin. Boş/`null`: alan boştur.
    #[serde(default)]
    pub value: Option<String>,
    #[serde(default)]
    pub missing_reason: Option<String>,
    #[serde(default)]
    pub source_id: Option<String>,
    #[serde(default)]
    pub quote: Option<String>,
    /// Yalnız `total_demand_multiple` (f3).
    #[serde(default)]
    pub origin: Option<String>,
    #[serde(default)]
    pub locator: Option<String>,
    #[serde(default)]
    pub cross_checks: Vec<CrossCheck>,
    #[serde(default)]
    pub checked_sources: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct InputsDocReq {
    pub ticker: String,
    pub company: String,
    pub stage: String,
    #[serde(default)]
    pub first_trading_date_source: Option<String>,
    #[serde(default)]
    pub collection_rules: Vec<String>,
    /// Alan adı → taslak (eksik alan boş sayılır).
    #[serde(default)]
    pub fields: Map<String, Value>,
    /// Belirtilmezse yerel saat (Istanbul).
    #[serde(default)]
    pub collected_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct InputsDocPreview {
    pub rel_path: String,
    pub text: String,
    /// Rust `validate_inputs` (yapısal). Yetkili denetim Python'dur.
    pub problems: Vec<String>,
    pub exists: bool,
    /// Var olan dosyayla bayt-eşit.
    pub identical: bool,
    /// Var olan dosyaya göre satır farkı (' ' bağlam, '-' eski, '+' yeni).
    pub diff: Vec<String>,
    pub written: bool,
    pub sha256: String,
}

/// Girdi belgesinin dosya adı (FAZ3_APP_STAGE01 kararı 3).
pub fn inputs_rel_path(ticker: &str, stage: &str) -> String {
    if stage == "PRE_BOOKBUILD" {
        format!("registry/inputs/{ticker}.PB.json")
    } else {
        format!("registry/inputs/{ticker}.json")
    }
}

fn text_or_none(s: &Option<String>) -> Option<String> {
    s.as_deref().map(str::trim).filter(|x| !x.is_empty()).map(str::to_string)
}

/// Girdi belgesini kurar. Dolu alanların kaynak alanları MANIFEST'ten doldurulur: `sources` tablosu ile
/// alanlar tanım gereği tutarlıdır.
pub fn build_inputs_doc(repo: &Path, req: &InputsDocReq) -> Result<(Value, String), AppError> {
    let ticker = req.ticker.trim();
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    if !STAGES.contains(&req.stage.as_str()) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("aşama {:?}", req.stage)));
    }
    let manifest = read_manifest(repo, ticker)?;
    let docs = manifest["documents"].as_object().cloned().unwrap_or_default();
    let source_of = |id: &str| -> Result<&Value, AppError> {
        docs.get(id).ok_or_else(|| AppError::new(INPUTS_DOC_INVALID, format!("kaynak {id} MANIFEST'te yok (adım 2)")))
    };
    let mut used: Vec<String> = Vec::new();
    let mut fields = Map::new();
    for name in input_fields() {
        let draft: FieldDraft = match req.fields.get(name) {
            Some(v) => serde_json::from_value(v.clone()).map_err(|e| AppError::new(INVALID_ARGUMENT, format!("{name}: {e}")))?,
            None => FieldDraft::default(),
        };
        let mut f = Map::new();
        match text_or_none(&draft.value) {
            Some(value) => {
                let sid = text_or_none(&draft.source_id)
                    .ok_or_else(|| AppError::new(INPUTS_DOC_INVALID, format!("{name}: dolu alan kaynak belgesi ister")))?;
                let src = source_of(&sid)?;
                let quote = text_or_none(&draft.quote)
                    .ok_or_else(|| AppError::new(INPUTS_DOC_INVALID, format!("{name}: dolu alan belgeden alıntı ister")))?;
                f.insert("value".into(), Value::String(value));
                f.insert("source_id".into(), Value::String(sid.clone()));
                f.insert("source_document".into(), src["document_id"].clone());
                f.insert("source_published_at".into(), src["published_at"].clone());
                f.insert("source_sha256".into(), src["sha256"].clone());
                f.insert("source_path".into(), src["path"].clone());
                f.insert("quote".into(), Value::String(quote));
                used.push(sid);
                if let Some(loc) = text_or_none(&draft.locator) {
                    f.insert("locator".into(), Value::String(loc));
                }
                if name == "total_demand_multiple" {
                    let origin = text_or_none(&draft.origin).unwrap_or_default();
                    if !F3_ORIGINS.contains(&origin.as_str()) {
                        return Err(AppError::new(INPUTS_DOC_INVALID, format!("total_demand_multiple: origin {origin:?}")));
                    }
                    f.insert("origin".into(), Value::String(origin));
                }
                if !draft.cross_checks.is_empty() {
                    let mut cc = Vec::new();
                    for c in &draft.cross_checks {
                        source_of(&c.source_id)?;
                        cc.push(serde_json::json!({"source_id": c.source_id, "quote": c.quote}));
                        used.push(c.source_id.clone());
                    }
                    f.insert("cross_checks".into(), Value::Array(cc));
                }
            }
            None => {
                let reason = text_or_none(&draft.missing_reason)
                    .ok_or_else(|| AppError::new(INPUTS_DOC_INVALID, format!("{name}: boş alan missing_reason ister")))?;
                f.insert("value".into(), Value::Null);
                f.insert("missing_reason".into(), Value::String(reason));
                if !draft.checked_sources.is_empty() {
                    for s in &draft.checked_sources {
                        source_of(s)?;
                        used.push(s.clone());
                    }
                    f.insert("checked_sources".into(), Value::Array(draft.checked_sources.iter().cloned().map(Value::String).collect()));
                }
            }
        }
        fields.insert(name.into(), Value::Object(f));
    }
    let ftds = text_or_none(&req.first_trading_date_source);
    if let Some(s) = &ftds {
        source_of(s)?;
        used.push(s.clone());
    }
    let mut sources = Map::new();
    used.sort();
    used.dedup();
    for id in &used {
        let src = source_of(id)?;
        sources.insert(
            id.clone(),
            serde_json::json!({
                "kind": src["kind"], "document_id": src["document_id"], "published_at": src["published_at"],
                "sha256": src["sha256"], "path": src["path"]
            }),
        );
    }
    let mut doc = Map::new();
    doc.insert("schema_version".into(), Value::String(INPUTS_SCHEMA.into()));
    doc.insert("ticker".into(), Value::String(ticker.into()));
    doc.insert("company".into(), Value::String(req.company.trim().into()));
    doc.insert("stage".into(), Value::String(req.stage.clone()));
    doc.insert("collected_at".into(), Value::String(text_or_none(&req.collected_at).unwrap_or_else(now_istanbul)));
    doc.insert("collected_at_basis".into(), Value::String(COLLECTED_AT_BASIS.into()));
    doc.insert(
        "collection_rules".into(),
        Value::Array(req.collection_rules.iter().map(|r| Value::String(r.trim().into())).filter(|r| r != &Value::String(String::new())).collect()),
    );
    doc.insert("first_trading_date_source".into(), ftds.map(Value::String).unwrap_or(Value::Null));
    doc.insert("fields".into(), Value::Object(fields));
    doc.insert("sources".into(), Value::Object(sources));
    Ok((Value::Object(doc), inputs_rel_path(ticker, &req.stage)))
}

/// Basit satır farkı (LCS): yalnız değişen satırlar ve bir satır bağlam.
pub fn line_diff(old: &str, new: &str) -> Vec<String> {
    let a: Vec<&str> = old.lines().collect();
    let b: Vec<&str> = new.lines().collect();
    let (n, m) = (a.len(), b.len());
    let mut lcs = vec![vec![0u32; m + 1]; n + 1];
    for i in (0..n).rev() {
        for j in (0..m).rev() {
            lcs[i][j] = if a[i] == b[j] { lcs[i + 1][j + 1] + 1 } else { lcs[i + 1][j].max(lcs[i][j + 1]) };
        }
    }
    let mut marks: Vec<(char, &str)> = Vec::new();
    let (mut i, mut j) = (0usize, 0usize);
    while i < n && j < m {
        if a[i] == b[j] {
            marks.push((' ', a[i]));
            i += 1;
            j += 1;
        } else if lcs[i + 1][j] >= lcs[i][j + 1] {
            marks.push(('-', a[i]));
            i += 1;
        } else {
            marks.push(('+', b[j]));
            j += 1;
        }
    }
    marks.extend(a[i..].iter().map(|l| ('-', *l)));
    marks.extend(b[j..].iter().map(|l| ('+', *l)));
    let keep: Vec<bool> = (0..marks.len())
        .map(|k| marks[k.saturating_sub(1)..(k + 2).min(marks.len())].iter().any(|(c, _)| *c != ' '))
        .collect();
    marks
        .iter()
        .zip(keep)
        .filter(|(_, k)| *k)
        .map(|((c, l), _)| format!("{c}{l}"))
        .collect()
}

pub fn preview_inputs_doc_in(repo: &Path, req: &InputsDocReq, write: bool, confirm: bool) -> Result<InputsDocPreview, AppError> {
    let (doc, rel) = build_inputs_doc(repo, req)?;
    let payload = pretty_json_bytes(&doc).map_err(|e| AppError::new(INPUTS_DOC_INVALID, e))?;
    let text = String::from_utf8(payload.clone()).map_err(|e| AppError::new(INPUTS_DOC_INVALID, e.to_string()))?;
    let problems = validate_inputs(&doc);
    let path = repo.join(&rel);
    let existing = std::fs::read(&path).ok();
    let identical = existing.as_deref() == Some(payload.as_slice());
    let diff = match &existing {
        Some(old) if !identical => line_diff(&String::from_utf8_lossy(old), &text),
        _ => Vec::new(),
    };
    let mut out = InputsDocPreview {
        sha256: super::models::sha256_hex(&payload),
        rel_path: rel.clone(),
        text,
        problems,
        exists: existing.is_some(),
        identical,
        diff,
        written: false,
    };
    if write {
        if !out.problems.is_empty() {
            return Err(AppError::new(INPUTS_DOC_INVALID, out.problems.join("; ")));
        }
        if out.exists && !out.identical && !confirm {
            return Err(AppError::new(INPUTS_DOC_EXISTS, format!("{rel} var; farkı onaylayın")));
        }
        std::fs::create_dir_all(path.parent().expect("inputs dizini")).map_err(|e| io_error("registry/inputs", e))?;
        std::fs::write(&path, &payload).map_err(|e| io_error(&rel, e))?;
        out.written = true;
    }
    Ok(out)
}

// ---------------------------------------------------------------- komutlar

#[tauri::command]
pub fn list_input_documents(state: tauri::State<'_, AppState>) -> Result<Vec<String>, AppError> {
    list_input_documents_in(&state.require_repo()?.root)
}

#[tauri::command]
pub fn read_input_document(state: tauri::State<'_, AppState>, ticker: String) -> Result<InputDocument, AppError> {
    read_input_document_in(&state.require_repo()?.root, &ticker)
}

#[tauri::command]
pub fn preview_inputs_doc(state: tauri::State<'_, AppState>, req: InputsDocReq) -> Result<InputsDocPreview, AppError> {
    preview_inputs_doc_in(&state.require_repo()?.root, &req, false, false)
}

#[tauri::command]
pub fn write_inputs_doc(state: tauri::State<'_, AppState>, req: InputsDocReq, confirm: bool) -> Result<InputsDocPreview, AppError> {
    preview_inputs_doc_in(&state.require_repo()?.root, &req, true, confirm)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn iso_datetime_shapes() {
        assert!(iso_datetime_with_offset("2026-09-13T17:30:28+03:00"));
        assert!(iso_datetime_with_offset("2026-09-03T17:46:05Z"));
        assert!(iso_datetime_with_offset("2026-09-03T17:46:05.123456+03:00"));
        assert!(!iso_datetime_with_offset("2026-09-13T17:30:28"));
        assert!(!iso_datetime_with_offset("2026-09-13"));
        assert!(!iso_datetime_with_offset("2026-13-01T00:00:00+03:00"));
    }

    #[test]
    fn diff_marks_changed_lines() {
        let d = line_diff("a\nb\nc\n", "a\nx\nc\n");
        assert_eq!(d, vec![" a", "-b", "+x", " c"]);
        assert!(line_diff("a\n", "a\n").is_empty());
    }
}
