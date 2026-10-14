//! Sicil ekranı ve arz sayfası (SPEC_APP §3e sonu, §3g resmi görünüm).
//!
//! - Sicilin kopyası uygulama verisinde TUTULMAZ: her açılışta `<repo>/registry/records/**` (ve D1 sonrası kayıt sayısı
//!   için `<repo>/registry/post_d1/<T>/`; EK 3 §6.6) okunur. Eski kohort dizini (`registry/oot/`) okunmaz.
//! - Uygulama sicile YAZMAZ; yalnız `borsai.freeze`'in yazdığını okur.
//! - Koşullu görünümün S vektörleri YALNIZ dondurulmuş kayıttaki `models[].output.S`'ten gelir; model
//!   yeniden çalıştırılmaz (U38). Bu yüzden arz sayfası tek komuttur (`record_ceiling`) ve `predict_all`
//!   yolunu hiç çağırmaz.
//! - Push kanıtı yalnız gösterge: kaydı ekleyen commit (varsa) için `registry/push_proofs/<sha>.json`
//!   bakılır. SINIF (LIVE / LATE_RECORD / RETRO) BURADA HESAPLANMAZ (SPEC_SCORING §5; Faz 2B).
//! - Kişisel modda kök gömülü sicil anlık görüntüsüdür (FAZ9_SNAPSHOT K-SNAP-2; `AppState::read_root`): orada git
//!   çağrılmaz, izlenen kayıtlar, kaydı ekleyen commit ve `git status` derleme anında dondurulmuş bilgiden okunur.
use serde::Serialize;
use serde_json::{Map, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use super::ceiling::{ceiling_display_value, CeilingDisplay, SVector};
use super::freeze::{read_record, RECORD_SCHEMA};
use super::git::git_readonly;
use super::inputs_doc::valid_ticker;
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::state::AppState;

pub const RECORD_PREDICTION: &str = "PREDICTION";
pub const RECORD_CANCELLATION: &str = "CANCELLATION";
pub const RECORD_NOT_ACTIVE: &str = "RECORD_NOT_ACTIVE";
pub const RECORD_NO_CEILING: &str = "RECORD_NO_CEILING";

// ---------------------------------------------------------------- küçük CSV okuyucu (RFC 4180)

fn read_csv(text: &str) -> (Vec<String>, Vec<Vec<String>>) {
    let mut rows: Vec<Vec<String>> = Vec::new();
    let mut row: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut quoted = false;
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
    if rows.is_empty() {
        return (Vec::new(), Vec::new());
    }
    let header = rows.remove(0);
    (header, rows)
}

// ---------------------------------------------------------------- görünüm tipleri

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PushProof {
    pub sha: String,
    pub created_at: Option<String>,
    pub rel_path: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CancelledBy {
    pub file: String,
    pub reason: String,
    pub recorded_at_istanbul: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RecordModelRef {
    pub model_id: String,
    pub params_sha256: String,
    pub status: String,
    /// Kayıt bu modelin çıktısında S taşıyor mu (tavan serisi).
    pub has_s: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RecordRow {
    pub file: String,
    pub rel_path: String,
    /// OK | UNSUPPORTED_VERSION | UNREADABLE
    pub status: &'static str,
    pub schema_version: Option<String>,
    pub record_type: Option<String>,
    pub ticker: Option<String>,
    pub recorded_at_utc: Option<String>,
    pub recorded_at_istanbul: Option<String>,
    pub git_head: Option<String>,
    pub input_sha256: Option<String>,
    pub models_index_sha256: Option<String>,
    pub inputs_path: Option<String>,
    pub first_trading_date: Option<String>,
    pub n_models: usize,
    pub summary: Value,
    /// Uygulamanın gösterebildiği modeller (gömülü kümeden).
    pub models: Vec<RecordModelRef>,
    /// Kayıtta olup uygulamada henüz olmayan modeller (Faz 4 portu ile gelecek).
    pub unsupported_models: Vec<RecordModelRef>,
    /// Tavan serisi (S) taşıyan desteklenen model sayısı.
    pub n_ceiling_models: usize,
    /// İptal kaydıysa: iptal edilen dosya ve neden.
    pub cancels: Option<String>,
    pub reason: Option<String>,
    /// Tahmin kaydıysa ve iptal edilmişse.
    pub cancelled_by: Option<CancelledBy>,
    pub tracked: bool,
    pub added_commit: Option<String>,
    pub push_proof: Option<PushProof>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct TickerRow {
    pub ticker: String,
    pub company: Option<String>,
    pub first_trading_date: Option<String>,
    pub ipo_status: Option<String>,
    pub records: Vec<RecordRow>,
    pub n_active: usize,
    /// D1 sonrası kayıtlar (`registry/post_d1/<T>/`; EK 3 §6.6): dosya sayısı ve etkin tahmin kaydı sayısı. Eski kohort
    /// dizini (`registry/oot/`) okunmaz.
    pub n_post_d1_files: usize,
    pub n_post_d1_active: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RegistryView {
    pub repo_root: String,
    /// Bugün (Europe/Istanbul): iptal kuralını ekranda önceden göstermek için (son söz Python'undur).
    pub today_istanbul: String,
    /// `git status --porcelain -- registry` (bilgi).
    pub git_status_registry: String,
    pub tickers: Vec<TickerRow>,
    /// `registry/ipos.csv` satırları (payda).
    pub ipos: Vec<Map<String, Value>>,
    pub proofs: Vec<PushProof>,
    /// Gömülü (desteklenen) model kümesi — kodda sayı sabiti yok.
    pub supported_models: Vec<String>,
    /// Kişisel modda gömülü anlık görüntünün künyesi (K-SNAP-3); repo modunda alan yok.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snapshot: Option<super::registry_snapshot::SnapshotInfo>,
}

pub fn read_proofs(repo: &Path) -> Vec<PushProof> {
    let dir = repo.join("registry").join("push_proofs");
    let Ok(entries) = std::fs::read_dir(&dir) else { return Vec::new() };
    let mut out: Vec<PushProof> = entries
        .flatten()
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().to_string();
            let sha = name.strip_suffix(".json")?.to_string();
            let doc: Value = std::fs::read(e.path()).ok().and_then(|b| serde_json::from_slice(&b).ok())?;
            Some(PushProof {
                created_at: doc.get("created_at").and_then(Value::as_str).map(str::to_string),
                rel_path: format!("registry/push_proofs/{name}"),
                sha,
            })
        })
        .collect();
    out.sort_by(|a, b| a.created_at.cmp(&b.created_at).then(a.sha.cmp(&b.sha)));
    out
}

fn record_row(repo: &Path, ticker: &str, file: &str, supported: &BTreeSet<String>) -> RecordRow {
    let rel = format!("registry/records/{ticker}/{file}");
    let mut row = RecordRow {
        file: file.to_string(),
        rel_path: rel.clone(),
        status: "UNREADABLE",
        schema_version: None,
        record_type: None,
        ticker: None,
        recorded_at_utc: None,
        recorded_at_istanbul: None,
        git_head: None,
        input_sha256: None,
        models_index_sha256: None,
        inputs_path: None,
        first_trading_date: None,
        n_models: 0,
        summary: Value::Null,
        models: Vec::new(),
        unsupported_models: Vec::new(),
        n_ceiling_models: 0,
        cancels: None,
        reason: None,
        cancelled_by: None,
        tracked: false,
        added_commit: None,
        push_proof: None,
        error: None,
    };
    let doc: Value = match std::fs::read(repo.join(&rel)).map_err(|e| e.to_string()).and_then(|b| {
        serde_json::from_slice::<Value>(&b).map_err(|e| e.to_string())
    }) {
        Ok(d) => d,
        Err(e) => {
            row.error = Some(e);
            return row;
        }
    };
    let text = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    row.schema_version = text("schema_version");
    if row.schema_version.as_deref() != Some(RECORD_SCHEMA) {
        row.status = "UNSUPPORTED_VERSION";
        return row;
    }
    row.status = "OK";
    row.record_type = text("record_type");
    row.ticker = text("ticker");
    row.recorded_at_utc = text("recorded_at_utc");
    row.recorded_at_istanbul = text("recorded_at_istanbul");
    row.git_head = doc.pointer("/code/git_head").and_then(Value::as_str).map(str::to_string);
    row.input_sha256 = text("input_sha256");
    row.models_index_sha256 = doc.pointer("/models_index/sha256").and_then(Value::as_str).map(str::to_string);
    row.inputs_path = doc.pointer("/inputs/path").and_then(Value::as_str).map(str::to_string);
    row.first_trading_date = doc
        .pointer("/inputs/document/fields/first_trading_date/value")
        .and_then(Value::as_str)
        .map(str::to_string);
    row.cancels = doc.pointer("/cancels/file").and_then(Value::as_str).map(str::to_string);
    row.reason = text("reason");
    row.summary = doc.get("summary").cloned().unwrap_or(Value::Null);
    if let Some(cells) = doc.get("models").and_then(Value::as_array) {
        row.n_models = cells.len();
        for c in cells {
            let m = RecordModelRef {
                model_id: c["model_id"].as_str().unwrap_or("?").to_string(),
                params_sha256: c["params_sha256"].as_str().unwrap_or_default().to_string(),
                status: c["status"].as_str().unwrap_or_default().to_string(),
                has_s: c.pointer("/output/S").is_some_and(Value::is_array),
            };
            if supported.contains(&m.model_id) {
                row.n_ceiling_models += usize::from(m.has_s);
                row.models.push(m);
            } else {
                row.unsupported_models.push(m);
            }
        }
    }
    row
}

pub fn registry_view_in(repo: &Path, supported: &[String]) -> Result<RegistryView, AppError> {
    let set: BTreeSet<String> = supported.iter().cloned().collect();
    let records_dir = repo.join("registry").join("records");
    let mut by_ticker: BTreeMap<String, Vec<RecordRow>> = BTreeMap::new();
    if let Ok(dirs) = std::fs::read_dir(&records_dir) {
        for d in dirs.flatten().filter(|d| d.path().is_dir()) {
            let ticker = d.file_name().to_string_lossy().to_string();
            if !valid_ticker(&ticker) {
                continue;
            }
            let mut files: Vec<String> = std::fs::read_dir(d.path())
                .map_err(|e| io_error("registry/records", e))?
                .flatten()
                .filter_map(|f| f.file_name().to_str().filter(|n| n.ends_with(".json")).map(str::to_string))
                .collect();
            files.sort();
            let rows: Vec<RecordRow> = files.iter().map(|f| record_row(repo, &ticker, f, &set)).collect();
            by_ticker.insert(ticker, rows);
        }
    }
    // iptal bağları: CANCELLATION kayıtları hangi dosyayı iptal ediyor
    for rows in by_ticker.values_mut() {
        let cancels: Vec<(String, String, String)> = rows
            .iter()
            .filter(|r| r.record_type.as_deref() == Some(RECORD_CANCELLATION))
            .filter_map(|r| {
                Some((
                    r.cancels.clone()?,
                    r.reason.clone().unwrap_or_default(),
                    r.recorded_at_istanbul.clone().unwrap_or_default(),
                ))
            })
            .collect();
        for r in rows.iter_mut() {
            if r.record_type.as_deref() != Some(RECORD_PREDICTION) {
                continue;
            }
            if let Some((_, reason, at)) = cancels.iter().find(|(f, _, _)| *f == r.file) {
                r.cancelled_by = Some(CancelledBy { file: r.file.clone(), reason: reason.clone(), recorded_at_istanbul: at.clone() });
            }
        }
    }
    // git: izlenen dosyalar ve kaydı ekleyen commit (salt okuma beyaz listesi); anlık görüntüde derleme anının bilgisi
    let frozen = super::registry_snapshot::frozen_git(repo);
    let tracked: BTreeSet<String> = match &frozen {
        Some(f) => f.tracked(),
        None => git_readonly(repo, &["ls-files", "--", "registry/records"]).unwrap_or_default().lines().map(str::to_string).collect(),
    };
    let proofs = read_proofs(repo);
    for rows in by_ticker.values_mut() {
        for r in rows.iter_mut() {
            r.tracked = tracked.contains(&r.rel_path);
            if r.tracked {
                r.added_commit = match &frozen {
                    Some(f) => f.added_commit(&r.rel_path),
                    None => git_readonly(repo, &["log", "--diff-filter=A", "--format=%H", "-1", "--", &r.rel_path])
                        .ok()
                        .map(|s| s.trim().to_string())
                        .filter(|s| !s.is_empty()),
                };
            }
            r.push_proof = r.added_commit.as_ref().and_then(|c| proofs.iter().find(|p| &p.sha == c).cloned());
        }
    }
    // payda (ipos.csv)
    let mut ipos = Vec::new();
    let mut meta: BTreeMap<String, (Option<String>, Option<String>, Option<String>)> = BTreeMap::new();
    if let Ok(text) = std::fs::read_to_string(repo.join("registry").join("ipos.csv")) {
        let (header, rows) = read_csv(&text);
        for row in rows {
            let mut m = Map::new();
            for (i, h) in header.iter().enumerate() {
                m.insert(h.clone(), Value::String(row.get(i).cloned().unwrap_or_default()));
            }
            let get = |k: &str| m.get(k).and_then(Value::as_str).filter(|s| !s.is_empty()).map(str::to_string);
            if let Some(t) = get("ticker") {
                meta.entry(t).or_insert((get("company"), get("first_trading_date"), get("status")));
            }
            ipos.push(m);
        }
    }
    let tickers = by_ticker
        .into_iter()
        .map(|(ticker, records)| {
            let (company, ftd, status) = meta.get(&ticker).cloned().unwrap_or((None, None, None));
            let n_active = records
                .iter()
                .filter(|r| r.record_type.as_deref() == Some(RECORD_PREDICTION) && r.cancelled_by.is_none())
                .count();
            let first_trading_date = ftd.or_else(|| records.iter().find_map(|r| r.first_trading_date.clone()));
            let post = super::post_d1::post_d1_records_in(repo, &ticker).unwrap_or_default();
            let n_post_d1_active = super::post_d1::active_files(&post).len();
            TickerRow { ticker, company, first_trading_date, ipo_status: status, records, n_active, n_post_d1_files: post.len(), n_post_d1_active }
        })
        .collect();
    Ok(RegistryView {
        repo_root: repo.display().to_string(),
        today_istanbul: crate::clock::today_istanbul(),
        git_status_registry: match &frozen {
            Some(f) => f.status(&["registry"]),
            None => git_readonly(repo, &["status", "--porcelain", "--", "registry"]).unwrap_or_default(),
        },
        tickers,
        ipos,
        proofs,
        supported_models: supported.to_vec(),
        snapshot: None,
    })
}

// ---------------------------------------------------------------- arz sayfası (U38)

/// Kayıttaki bir `ceiling_path` modelinin çıktısı (Grup A/C render'ı; U38: yalnız kayıttan).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RecordPathModel {
    pub model_id: String,
    pub params_sha256: String,
    pub status: String,
    /// Kayıttaki sha gömülü parametre sha'sıyla eşit mi (değilse koşullu getiri hesaplanmaz).
    pub sha_matches_embedded: bool,
    pub refusal: Value,
    pub output: Value,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RecordCeiling {
    pub ticker: String,
    pub file: String,
    pub rel_path: String,
    pub recorded_at_istanbul: String,
    pub first_trading_date: Option<String>,
    pub ipo_price_tl: Option<String>,
    /// Gösterilen modeller (kayıttaki S ile; params sha kayıttan).
    pub models: Vec<RecordModelRef>,
    /// Kayıtta olup uygulamada henüz olmayan modeller: adıyla listelenir, çıktısı render EDİLMEZ.
    pub unsupported_models: Vec<RecordModelRef>,
    /// Kayıttaki tavan yolu modelleri (boşsa kayıt INDEX'ten eskidir: Faz 4 modelleri yok).
    pub path_models: Vec<RecordPathModel>,
    pub display: CeilingDisplay,
}

/// Kayıttaki S vektörlerinden koşullu görünüm. Model yeniden çalıştırılmaz; `predict_all` çağrılmaz.
pub fn record_ceiling_in(
    repo: &Path,
    ticker: &str,
    file: &str,
    j: usize,
    supported: &[String],
    embedded_shas: &[(String, String)],
) -> Result<RecordCeiling, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let rel = format!("registry/records/{ticker}/{file}");
    let doc = read_record(repo, &rel)?;
    if doc["record_type"].as_str() != Some(RECORD_PREDICTION) {
        return Err(AppError::new(RECORD_NOT_ACTIVE, format!("{file}: tahmin kaydı değil")));
    }
    // iptal edilmiş kayıtta koşullu görünüm yoktur (§3g)
    let cancelled = std::fs::read_dir(repo.join("registry").join("records").join(ticker))
        .map(|d| {
            d.flatten().any(|e| {
                std::fs::read(e.path())
                    .ok()
                    .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
                    .is_some_and(|v| v["record_type"] == RECORD_CANCELLATION && v["cancels"]["file"] == *file)
            })
        })
        .unwrap_or(false);
    if cancelled {
        return Err(AppError::new(RECORD_NOT_ACTIVE, format!("{file}: iptal edilmiş kayıt")));
    }
    let set: BTreeSet<&str> = supported.iter().map(String::as_str).collect();
    let mut models = Vec::new();
    let mut unsupported = Vec::new();
    let mut vectors = Vec::new();
    let mut path_models = Vec::new();
    for c in doc["models"].as_array().cloned().unwrap_or_default() {
        let model_id = c["model_id"].as_str().unwrap_or("?").to_string();
        let sha = c["params_sha256"].as_str().unwrap_or_default().to_string();
        let status = c["status"].as_str().unwrap_or_default().to_string();
        let is_path = c["kind"].as_str() == Some("ceiling_path");
        let s: Option<Vec<f64>> = c.pointer("/output/S").and_then(|v| serde_json::from_value(v.clone()).ok());
        let m = RecordModelRef {
            params_sha256: sha.clone(),
            status: status.clone(),
            has_s: s.is_some(),
            model_id: model_id.clone(),
        };
        if !set.contains(model_id.as_str()) {
            unsupported.push(m);
            continue;
        }
        if is_path {
            // Grup A/C kayıt değerleriyle çizilir (EK 2 §4.4); sha gömülüyle eşit değilse koşullu
            // getiri hesaplanmaz (kayıt yine gösterilir).
            path_models.push(RecordPathModel {
                sha_matches_embedded: embedded_shas.iter().any(|(id, x)| id == &model_id && x == &sha),
                model_id: model_id.clone(),
                params_sha256: sha,
                status,
                refusal: c["refusal"].clone(),
                output: c["output"].clone(),
            });
        }
        if let Some(s) = s {
            // `ceiling_path` modellerinin S'i gömülü seri modelinin bit-eşit kopyasıdır (U45):
            // Grup B'de ikinci kez çizilmez (SPEC_APP EK 2 §4.1 [KARAR]); kayıt sha satırında kalır.
            if !is_path {
                vectors.push(SVector { model_id, s });
            }
            models.push(m);
        }
    }
    if vectors.is_empty() {
        return Err(AppError::new(RECORD_NO_CEILING, format!("{file}: kayıtta tavan serisi (S) yok")));
    }
    let price = doc.pointer("/model_inputs/ipo_price_tl").and_then(Value::as_str).map(str::to_string);
    let display = ceiling_display_value(&vectors, j, price.as_deref())?;
    Ok(RecordCeiling {
        ticker: ticker.to_string(),
        file: file.to_string(),
        rel_path: rel,
        recorded_at_istanbul: doc["recorded_at_istanbul"].as_str().unwrap_or_default().to_string(),
        first_trading_date: doc
            .pointer("/inputs/document/fields/first_trading_date/value")
            .and_then(Value::as_str)
            .map(str::to_string),
        ipo_price_tl: price,
        models,
        unsupported_models: unsupported,
        path_models,
        display,
    })
}

// ---------------------------------------------------------------- komutlar

fn supported_ids(state: &AppState) -> Result<Vec<String>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    Ok(models.models.iter().map(|m| m.model_id.clone()).collect())
}

/// (model_id, params_sha256) gömülü kümeden: kayıttaki sha ile karşılaştırma için.
pub fn embedded_shas(state: &AppState) -> Result<Vec<(String, String)>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    Ok(models.models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect())
}

/// Sicil görünümü: repo ya da kişisel modda gömülü anlık görüntü (K-SNAP-2).
pub fn registry_view_value(state: &AppState) -> Result<RegistryView, AppError> {
    let root = state.read_root()?;
    let mut v = registry_view_in(&root.root, &supported_ids(state)?)?;
    v.snapshot = root.snapshot;
    Ok(v)
}

#[tauri::command]
pub fn registry_view(state: tauri::State<'_, AppState>) -> Result<RegistryView, AppError> {
    registry_view_value(&state)
}

pub fn record_ceiling_value(state: &AppState, ticker: &str, file: &str, j: usize) -> Result<RecordCeiling, AppError> {
    let root = state.read_root()?;
    let mut r = record_ceiling_in(&root.root, ticker, file, j, &supported_ids(state)?, &embedded_shas(state)?)?;
    // hesaplayıcı eki (K-FIX-3): kural değeri kayıttaki S'ten (aynı display), n ve gün grupları gömülü dosyadan
    if let Ok(m) = state.models.as_ref() {
        super::ceiling::attach_calc(&mut r.display, &m.models);
    }
    Ok(r)
}

#[tauri::command]
pub fn record_ceiling(
    state: tauri::State<'_, AppState>,
    ticker: String,
    file: String,
    j: usize,
) -> Result<RecordCeiling, AppError> {
    record_ceiling_value(&state, &ticker, &file, j)
}

/// Kaydın tamamı (arz sayfasında "ham kayıt" açılır kutusu; salt okuma).
pub fn read_record_json_value(state: &AppState, ticker: &str, file: &str) -> Result<Value, AppError> {
    let root = state.read_root()?;
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    read_record(&root.root, &format!("registry/records/{ticker}/{file}"))
}

#[tauri::command]
pub fn read_record_json(state: tauri::State<'_, AppState>, ticker: String, file: String) -> Result<Value, AppError> {
    read_record_json_value(&state, &ticker, &file)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn csv_with_quotes() {
        let (h, rows) = read_csv("a,b\n1,\"x, y\"\n2,\"çift \"\"tırnak\"\"\"\n");
        assert_eq!(h, vec!["a", "b"]);
        assert_eq!(rows[0], vec!["1", "x, y"]);
        assert_eq!(rows[1], vec!["2", "çift \"tırnak\""]);
    }
}
