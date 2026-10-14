//! D1 sonrası güncelleme (`post_d1_hazard_v0`) kayıtları ve "D1 sonrası kayıt" sihirbazı (SPEC_APP EK 3 §6.5–§6.6;
//! SPEC_POST_D1_V0 §7.4).
//!
//! - Okuyucu YALNIZ `registry/post_d1/<T>/` dizinini okur (şema `borsai.post_d1_record/1`). Eski kohortun POST_D1
//!   kayıtları (`registry/oot/`) hiçbir komutta okunmaz ve gösterilmez (kasa hijyeni).
//! - "D1 sonrası" satırının S'i yalnız kaydın `models[post_d1_hazard_v0].output.S`'inden gelir (U38 kalıbı); model
//!   yeniden çalıştırılmaz. Koşullu görünüm aynı `ceiling_display` ile (S_cond[k]/S_cond[j] = S_k/S_j); yalnız j ≥ 1.
//! - Sihirbaz: ön koşullar (`post_d1_preflight`), kaydın yazıcısı Python'dur (`borsai.freeze --post-d1`; K-P2-1 S4:
//!   uygulama çalıştırır, parite anında görünür), Rust paritesi (`parity::compare_post_d1_record`), komut blokları
//!   (`post_d1_commands`; K-P2-2: tek fonksiyon). Bülten indirme ve commit/push YALNIZ komut metnidir: uygulama ağa
//!   çıkmaz, bülten okumaz, etiket üretmez, `git commit/push` çalıştırmaz (git beyaz listesi değişmez).
//! - Sınıf (LIVE / LATE_RECORD) burada HESAPLANMAZ: zaman kanıtı push kanıtıdır, sınıf skorlamada tarihlerden.
use serde::Serialize;
use serde_json::{Map, Value};
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use super::ceiling::{ceiling_display_value, outcome_day1_in, CeilingRow, SVector};
use super::config::{canonical, plain_path};
use super::freeze::{python_display, read_record, PY_WHERE};
use super::git::git_readonly;
use super::inputs_doc::valid_ticker;
use super::models::{sha256_hex, VerifiedModels};
use super::parity::{check_comparators_conditional, compare_post_d1_record, write_incident, ParityCell, ParityReport};
use super::registry::{read_proofs, CancelledBy, PushProof, RECORD_CANCELLATION, RECORD_PREDICTION};
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::python::run_python;
use crate::state::{AppState, RepoCtx};

pub const POST_D1_RECORD_SCHEMA: &str = "borsai.post_d1_record/1";
pub const POST_D1_MODEL_ID: &str = "post_d1_hazard_v0";
pub const BASE_MODEL_ID: &str = "ceiling_hazard_v0";
/// İkinci dizin (repo içi yol bileşenleri; `Path::join` ile kurulur).
pub const INDEX_POST_D1_REL: [&str; 2] = ["models", "INDEX_POST_D1.json"];

pub const POST_D1_RECORD_INVALID: &str = "POST_D1_RECORD_INVALID";
pub const POST_D1_RECORD_NOT_ACTIVE: &str = "POST_D1_RECORD_NOT_ACTIVE";
pub const POST_D1_PREFLIGHT_BLOCKED: &str = "POST_D1_PREFLIGHT_BLOCKED";
pub const POST_D1_FREEZE_FAILED: &str = "POST_D1_FREEZE_FAILED";
/// Python hataları (stderr'den sınıflanır; metin tr.ts'te).
pub const POST_D1_NOT_TRADED: &str = "POST_D1_NOT_TRADED";
pub const POST_D1_CALENDAR_NOT_AVAILABLE: &str = "POST_D1_CALENDAR_NOT_AVAILABLE";
pub const POST_D1_NO_BASE_RECORD: &str = "POST_D1_NO_BASE_RECORD";
pub const POST_D1_DUPLICATE_RECORD: &str = "POST_D1_DUPLICATE_RECORD";
pub const POST_D1_CANCEL_AFTER_T_OPEN: &str = "POST_D1_CANCEL_AFTER_T_OPEN";

/// T_open = D2_cal 09:40 Europe/Istanbul (Python `registry.t_open`; H31). Uygulama takvimi kendisi okumaz.
pub const PY_T_OPEN: &str = "from borsai import registry as r, outcomes as o; import sys; \
print(r.t_open(sys.argv[1], o.load_calendar()).isoformat())";

// ---------------------------------------------------------------- yol denetimi

/// `registry/post_d1/<T>/<dosya>.json` biçiminde güvenli göreli yol.
fn safe_post_rel(rel: &str) -> Result<String, AppError> {
    let clean = rel.trim().replace('\\', "/");
    let parts: Vec<&str> = clean.split('/').collect();
    let ok = parts.len() == 4
        && parts[0] == "registry"
        && parts[1] == "post_d1"
        && valid_ticker(parts[2])
        && parts[3].ends_with(".json")
        && !clean.contains("..")
        && parts[3].chars().all(|c| c.is_ascii_alphanumeric() || "._-".contains(c));
    if !ok {
        return Err(AppError::new(INVALID_ARGUMENT, format!("yol {rel:?} (registry/post_d1/<T>/<dosya>.json bekleniyor)")));
    }
    Ok(clean)
}

fn post_dir(repo: &Path, ticker: &str) -> PathBuf {
    repo.join("registry").join("post_d1").join(ticker)
}

/// Kayıt dosyası (şema denetimli).
pub fn read_post_d1_record(repo: &Path, rel: &str) -> Result<Value, AppError> {
    let rel = safe_post_rel(rel)?;
    let path = rel.split('/').fold(repo.to_path_buf(), |p, c| p.join(c));
    let bytes = std::fs::read(&path).map_err(|e| io_error(&rel, e))?;
    let doc: Value = serde_json::from_slice(&bytes).map_err(|e| AppError::new(POST_D1_RECORD_INVALID, e.to_string()))?;
    let version = doc.get("schema_version").and_then(Value::as_str).unwrap_or("");
    if version != POST_D1_RECORD_SCHEMA {
        return Err(AppError::new(POST_D1_RECORD_INVALID, format!("{rel}: sürüm {version:?}")));
    }
    Ok(doc)
}

// ---------------------------------------------------------------- kayıt satırları

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1Cell {
    pub model_id: String,
    pub params_sha256: String,
    /// PREDICTED | REFUSED | NOT_APPLICABLE
    pub status: String,
    pub refusal: Value,
    pub has_s: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1RecordRow {
    pub file: String,
    pub rel_path: String,
    /// OK | UNSUPPORTED_VERSION | UNREADABLE
    pub status: &'static str,
    pub record_type: Option<String>,
    pub ticker: Option<String>,
    pub recorded_at_utc: Option<String>,
    pub recorded_at_istanbul: Option<String>,
    pub d1_session_date: Option<String>,
    pub base_record_file: Option<String>,
    /// Bülten sha'larının ilk 8 hanesi (dosya adı yazılmaz).
    pub thb_sha8: Option<String>,
    pub thm_sha8: Option<String>,
    pub models_index_sha256: Option<String>,
    pub cells: Vec<PostD1Cell>,
    pub summary: Value,
    pub cancels: Option<String>,
    pub reason: Option<String>,
    pub cancelled_by: Option<CancelledBy>,
    pub tracked: bool,
    pub added_commit: Option<String>,
    pub push_proof: Option<PushProof>,
    pub error: Option<String>,
}

fn sha8(v: Option<&Value>) -> Option<String> {
    v.and_then(Value::as_str).map(|s| s.chars().take(8).collect())
}

fn record_row(repo: &Path, ticker: &str, file: &str) -> PostD1RecordRow {
    let rel = format!("registry/post_d1/{ticker}/{file}");
    let mut row = PostD1RecordRow {
        file: file.to_string(),
        rel_path: rel.clone(),
        status: "UNREADABLE",
        record_type: None,
        ticker: None,
        recorded_at_utc: None,
        recorded_at_istanbul: None,
        d1_session_date: None,
        base_record_file: None,
        thb_sha8: None,
        thm_sha8: None,
        models_index_sha256: None,
        cells: Vec::new(),
        summary: Value::Null,
        cancels: None,
        reason: None,
        cancelled_by: None,
        tracked: false,
        added_commit: None,
        push_proof: None,
        error: None,
    };
    let doc = match read_post_d1_record(repo, &rel) {
        Ok(d) => d,
        Err(e) if e.code == POST_D1_RECORD_INVALID && e.message.contains("sürüm") => {
            row.status = "UNSUPPORTED_VERSION";
            return row;
        }
        Err(e) => {
            row.error = Some(e.message);
            return row;
        }
    };
    let text = |p: &str| doc.pointer(p).and_then(Value::as_str).map(str::to_string);
    row.status = "OK";
    row.record_type = text("/record_type");
    row.ticker = text("/ticker");
    row.recorded_at_utc = text("/recorded_at_utc");
    row.recorded_at_istanbul = text("/recorded_at_istanbul");
    row.d1_session_date = text("/d1/session_date");
    row.base_record_file = text("/base_record/file");
    row.thb_sha8 = sha8(doc.pointer("/d1/thb/sha256"));
    row.thm_sha8 = sha8(doc.pointer("/d1/thm/sha256"));
    row.models_index_sha256 = text("/models_index/sha256");
    row.summary = doc.get("summary").cloned().unwrap_or(Value::Null);
    row.cancels = text("/cancels/file");
    row.reason = text("/reason");
    for c in doc.get("models").and_then(Value::as_array).into_iter().flatten() {
        row.cells.push(PostD1Cell {
            model_id: c["model_id"].as_str().unwrap_or("?").to_string(),
            params_sha256: c["params_sha256"].as_str().unwrap_or_default().to_string(),
            status: c["status"].as_str().unwrap_or_default().to_string(),
            refusal: c["refusal"].clone(),
            has_s: c.pointer("/output/S").is_some_and(Value::is_array),
        });
    }
    row
}

/// Arzın bütün POST_D1 kayıtları (dosya adı sırası), iptal bağları, git izleme ve push kanıtı göstergesi.
pub fn post_d1_records_in(repo: &Path, ticker: &str) -> Result<Vec<PostD1RecordRow>, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let dir = post_dir(repo, ticker);
    let Ok(entries) = std::fs::read_dir(&dir) else { return Ok(Vec::new()) };
    let mut files: Vec<String> = entries
        .flatten()
        .filter_map(|f| f.file_name().to_str().filter(|n| n.ends_with(".json")).map(str::to_string))
        .collect();
    files.sort();
    let mut rows: Vec<PostD1RecordRow> = files.iter().map(|f| record_row(repo, ticker, f)).collect();
    let cancels: Vec<(String, String, String)> = rows
        .iter()
        .filter(|r| r.record_type.as_deref() == Some(RECORD_CANCELLATION))
        .filter_map(|r| Some((r.cancels.clone()?, r.reason.clone().unwrap_or_default(), r.recorded_at_istanbul.clone().unwrap_or_default())))
        .collect();
    for r in rows.iter_mut().filter(|r| r.record_type.as_deref() == Some(RECORD_PREDICTION)) {
        if let Some((_, reason, at)) = cancels.iter().find(|(f, _, _)| *f == r.file) {
            r.cancelled_by = Some(CancelledBy { file: r.file.clone(), reason: reason.clone(), recorded_at_istanbul: at.clone() });
        }
    }
    let rel_dir = format!("registry/post_d1/{ticker}");
    let tracked: BTreeSet<String> =
        git_readonly(repo, &["ls-files", "--", &rel_dir]).unwrap_or_default().lines().map(str::to_string).collect();
    let proofs = read_proofs(repo);
    for r in rows.iter_mut() {
        r.tracked = tracked.contains(&r.rel_path);
        if r.tracked {
            r.added_commit = git_readonly(repo, &["log", "--diff-filter=A", "--format=%H", "-1", "--", &r.rel_path])
                .ok()
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty());
        }
        r.push_proof = r.added_commit.as_ref().and_then(|c| proofs.iter().find(|p| &p.sha == c).cloned());
    }
    Ok(rows)
}

/// Etkin (iptal edilmemiş) tahmin kayıtları, `recorded_at_utc` sırasıyla (en erken önce; eşitlikte dosya adı).
pub fn active_files(rows: &[PostD1RecordRow]) -> Vec<String> {
    let mut active: Vec<&PostD1RecordRow> = rows
        .iter()
        .filter(|r| r.status == "OK" && r.record_type.as_deref() == Some(RECORD_PREDICTION) && r.cancelled_by.is_none())
        .collect();
    active.sort_by(|a, b| a.recorded_at_utc.cmp(&b.recorded_at_utc).then(a.file.cmp(&b.file)));
    active.into_iter().map(|r| r.file.clone()).collect()
}

// ---------------------------------------------------------------- arz sayfası: "D1 sonrası" satırı (§6.5)

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1Source {
    pub file: String,
    pub rel_path: String,
    pub params_sha8: String,
    pub d1_session_date: Option<String>,
    pub thb_sha8: Option<String>,
    pub thm_sha8: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1View {
    pub ticker: String,
    pub j: usize,
    pub records: Vec<PostD1RecordRow>,
    /// Etkin kayıtlar, en erken önce (varsayılan sekme ilk öğe).
    pub active: Vec<String>,
    pub selected: Option<String>,
    /// NO_RECORD | J0 | PREDICTED | REFUSED | NOT_APPLICABLE | NO_CELL
    pub state: &'static str,
    pub refusal: Option<Value>,
    /// Kaydın S'inden `ceiling_display` satırı (yalnız j ≥ 1 ve PREDICTED; `cond` j ≥ 10 ya da S_j = 0'da null).
    pub row: Option<CeilingRow>,
    pub source: Option<PostD1Source>,
    /// Kaydın `path_conditional`'ı (ikincil; JSON aynen, `path::post_d1_path_card` ile sarılı) ve D_1 kapanışı.
    pub path_card: Option<super::path::PathConditional>,
    pub d1_close: Option<String>,
}

/// Resmi sicil görünümü (arz sayfası): S yalnız kayıttan; j = 0'da satır yok. `selected` verilmezse en erken etkin kayıt.
pub fn post_d1_view_in(repo: &Path, ticker: &str, j: usize, selected: Option<&str>) -> Result<PostD1View, AppError> {
    let records = post_d1_records_in(repo, ticker)?;
    let active = active_files(&records);
    let mut view = PostD1View {
        ticker: ticker.to_string(),
        j,
        records,
        active: active.clone(),
        selected: None,
        state: "NO_RECORD",
        refusal: None,
        row: None,
        source: None,
        path_card: None,
        d1_close: None,
    };
    let file = match selected {
        Some(f) if active.iter().any(|a| a == f) => f.to_string(),
        Some(f) => return Err(AppError::new(POST_D1_RECORD_NOT_ACTIVE, format!("{f}: etkin POST_D1 kaydı değil"))),
        None => match active.first() {
            Some(f) => f.clone(),
            None => return Ok(view),
        },
    };
    let rel = format!("registry/post_d1/{ticker}/{file}");
    let doc = read_post_d1_record(repo, &rel)?;
    let cell = doc
        .get("models")
        .and_then(Value::as_array)
        .and_then(|a| a.iter().find(|c| c["model_id"].as_str() == Some(POST_D1_MODEL_ID)))
        .cloned();
    let text = |p: &str| doc.pointer(p).and_then(Value::as_str).map(str::to_string);
    view.selected = Some(file.clone());
    view.d1_close = text("/d1/fields_raw/close");
    view.source = Some(PostD1Source {
        params_sha8: cell.as_ref().and_then(|c| c["params_sha256"].as_str()).unwrap_or("").chars().take(8).collect(),
        file,
        rel_path: rel,
        d1_session_date: text("/d1/session_date"),
        thb_sha8: sha8(doc.pointer("/d1/thb/sha256")),
        thm_sha8: sha8(doc.pointer("/d1/thm/sha256")),
    });
    let Some(cell) = cell else {
        view.state = "NO_CELL";
        return Ok(view);
    };
    match cell["status"].as_str() {
        Some("REFUSED") => {
            view.state = "REFUSED";
            view.refusal = Some(cell["refusal"].clone());
        }
        Some("NOT_APPLICABLE") => {
            view.state = "NOT_APPLICABLE";
            view.refusal = Some(cell["refusal"].clone());
        }
        Some("PREDICTED") if j == 0 => view.state = "J0",
        Some("PREDICTED") => {
            let s: Vec<f64> = serde_json::from_value(cell.pointer("/output/S").cloned().unwrap_or(Value::Null))
                .map_err(|e| AppError::new(POST_D1_RECORD_INVALID, format!("S okunamadı: {e}")))?;
            let display = ceiling_display_value(&[SVector { model_id: POST_D1_MODEL_ID.into(), s }], j, None)?;
            view.row = display.rows.into_iter().next();
            view.state = "PREDICTED";
            if let (Some(pc), Some(src), Some(close)) =
                (cell.pointer("/output/path_conditional").filter(|v| v.is_object()), view.source.as_ref(), view.d1_close.as_deref())
            {
                let sha = cell["params_sha256"].as_str().unwrap_or_default();
                view.path_card = Some(super::path::post_d1_path_card(&src.file, sha, close, src.d1_session_date.as_deref(), pc.clone()));
            }
        }
        _ => view.state = "NO_CELL",
    }
    Ok(view)
}

// ---------------------------------------------------------------- sihirbaz adım 1: ön koşullar (§6.6)

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1Preflight {
    pub ticker: String,
    pub repo_root: String,
    pub python_path: String,
    pub git_head: Option<String>,
    pub index_sha_repo: Option<String>,
    pub index_sha_embedded: String,
    pub index_match: bool,
    pub index_post_d1_sha_repo: Option<String>,
    pub index_post_d1_sha_embedded: String,
    pub index_post_d1_match: bool,
    pub borsai_file: Option<String>,
    pub borsai_in_repo: bool,
    /// Etkin listeleme öncesi kayıtlar (`ceiling_hazard_v0` hücresi PREDICTED); birincil seçim Python'dadır.
    pub base_records: Vec<String>,
    /// Kaydın girdi belgesindeki ilk işlem günü (adım 2 komutunun `--through` değeri D_1 henüz repoda yoksa).
    pub first_trading_date: Option<String>,
    /// `data/outcomes/<T>.csv` h = 1 satırı: durum aynen ve D_1 (OK ya da NA_LIMIT ve tarih doluysa).
    pub d1_status: Option<String>,
    pub d1: Option<String>,
    pub t_open: Option<String>,
    pub t_open_error: Option<String>,
    /// `GIT_OPTIONAL_LOCKS=0 git status --porcelain -- data registry/post_d1` (boşsa yeşil).
    pub git_status_pending: String,
    pub committed: bool,
    /// Yerel saat (yalnız bilgi; kanıt değildir): şimdi ve T_open'a kalan dakika.
    pub now_istanbul: String,
    pub minutes_to_t_open: Option<i64>,
    pub active_post_d1: Vec<String>,
    /// Durduran nedenler: GIT_HEAD · INDEX_SHA · INDEX_POST_D1_SHA · BORSAI_IMPORT · NO_PRE_LISTING_RECORD · D1_PENDING
    /// · CALENDAR_NOT_AVAILABLE
    pub blockers: Vec<&'static str>,
    /// Sarı uyarılar: UNCOMMITTED (freeze `sequence_guard`'a takılabilir) · T_OPEN_PASSED (yerel saate göre)
    pub warnings: Vec<&'static str>,
    pub ok: bool,
}

/// Arzın etkin listeleme öncesi kayıtları (`ceiling_hazard_v0` hücresi PREDICTED) ve girdi belgesindeki T.
fn base_records(repo: &Path, ticker: &str) -> (Vec<String>, Option<String>) {
    let dir = repo.join("registry").join("records").join(ticker);
    let Ok(entries) = std::fs::read_dir(&dir) else { return (Vec::new(), None) };
    let mut docs: Vec<(String, Value)> = entries
        .flatten()
        .filter_map(|e| {
            let name = e.file_name().to_str()?.to_string();
            let doc: Value = serde_json::from_slice(&std::fs::read(e.path()).ok()?).ok()?;
            name.ends_with(".json").then_some((name, doc))
        })
        .collect();
    docs.sort_by(|a, b| a.0.cmp(&b.0));
    let cancelled: BTreeSet<String> = docs
        .iter()
        .filter(|(_, d)| d["record_type"] == RECORD_CANCELLATION)
        .filter_map(|(_, d)| d.pointer("/cancels/file").and_then(Value::as_str).map(str::to_string))
        .collect();
    let mut t = None;
    let mut out = Vec::new();
    for (name, d) in &docs {
        if d["record_type"] != RECORD_PREDICTION || cancelled.contains(name) {
            continue;
        }
        t = t.or_else(|| d.pointer("/inputs/document/fields/first_trading_date/value").and_then(Value::as_str).map(str::to_string));
        let v0 = d["models"].as_array().into_iter().flatten().any(|c| c["model_id"] == BASE_MODEL_ID && c["status"] == "PREDICTED");
        if v0 {
            out.push(name.clone());
        }
    }
    (out, t)
}

/// "YYYY-MM-DDTHH:MM:SS+03:00" → Unix saniyesi (yalnız sabit +03:00 ofsetli Python çıktısı).
fn unix_of_istanbul(stamp: &str) -> Option<i64> {
    let (date, rest) = stamp.split_once('T')?;
    let time = rest.strip_suffix("+03:00")?;
    let mut d = date.split('-').map(|x| x.parse::<i64>().ok());
    let (y, m, dd) = (d.next()??, d.next()??, d.next()??);
    let mut t = time.split(':').map(|x| x.parse::<i64>().ok());
    let (hh, mm, ss) = (t.next()??, t.next()??, t.next()??);
    // days_from_civil (Howard Hinnant)
    let y2 = if m <= 2 { y - 1 } else { y };
    let era = y2.div_euclid(400);
    let yoe = y2 - era * 400;
    let mp = (m + 9) % 12;
    let doy = (153 * mp + 2) / 5 + dd - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146_097 + doe - 719_468;
    Some(days * 86_400 + hh * 3600 + mm * 60 + ss - crate::clock::ISTANBUL_OFFSET_SECS)
}

pub fn post_d1_preflight_at(
    repo: &RepoCtx,
    ticker: &str,
    embedded_index_sha: &str,
    embedded_post_index_sha: &str,
    now_unix: i64,
) -> Result<PostD1Preflight, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let root = &repo.root;
    let mut blockers = Vec::new();
    let mut warnings = Vec::new();
    let git_head = git_readonly(root, &["rev-parse", "HEAD"]).ok().map(|h| h.trim().to_string());
    if git_head.is_none() {
        blockers.push("GIT_HEAD");
    }
    let file_sha = |rel: &[&str]| std::fs::read(rel.iter().fold(root.clone(), |p, c| p.join(c))).ok().map(|b| sha256_hex(&b));
    let index_sha_repo = file_sha(&["models", "INDEX.json"]);
    let index_match = index_sha_repo.as_deref() == Some(embedded_index_sha);
    if !index_match {
        blockers.push("INDEX_SHA");
    }
    let index_post_d1_sha_repo = file_sha(&INDEX_POST_D1_REL);
    let index_post_d1_match = index_post_d1_sha_repo.as_deref() == Some(embedded_post_index_sha);
    if !index_post_d1_match {
        blockers.push("INDEX_POST_D1_SHA");
    }
    let borsai_file = run_python(&repo.python, root, &["-c", PY_WHERE]).ok().map(|s| s.trim().to_string());
    let borsai_in_repo = borsai_file
        .as_deref()
        .map(PathBuf::from)
        .is_some_and(|p| canonical(root).map(|r| plain_path(p).starts_with(r)).unwrap_or(false));
    if !borsai_in_repo {
        blockers.push("BORSAI_IMPORT");
    }
    let (bases, first_trading_date) = base_records(root, ticker);
    if bases.is_empty() {
        blockers.push("NO_PRE_LISTING_RECORD");
    }
    let day1 = outcome_day1_in(&root.join("data").join("outcomes"), ticker)?;
    let d1_status = day1.as_ref().map(|(s, _)| s.clone());
    let d1 = day1.and_then(|(s, d)| (s == "OK" || s == "NA_LIMIT").then_some(d).flatten());
    let (mut t_open, mut t_open_error) = (None, None);
    match &d1 {
        None => blockers.push("D1_PENDING"),
        Some(d) => match run_python(&repo.python, root, &["-c", PY_T_OPEN, d]) {
            Ok(out) => t_open = Some(out.trim().to_string()),
            Err(e) => {
                blockers.push("CALENDAR_NOT_AVAILABLE");
                t_open_error = Some(e.detail.unwrap_or(e.message));
            }
        },
    }
    let git_status_pending = git_readonly(root, &["status", "--porcelain", "--", "data", "registry/post_d1"]).unwrap_or_default();
    let committed = git_status_pending.trim().is_empty();
    if !committed {
        warnings.push("UNCOMMITTED");
    }
    let minutes_to_t_open = t_open.as_deref().and_then(unix_of_istanbul).map(|t| (t - now_unix).div_euclid(60));
    if minutes_to_t_open.is_some_and(|m| m < 0) {
        warnings.push("T_OPEN_PASSED");
    }
    let active_post_d1 = active_files(&post_d1_records_in(root, ticker)?);
    Ok(PostD1Preflight {
        ticker: ticker.to_string(),
        repo_root: root.display().to_string(),
        python_path: repo.python.display().to_string(),
        git_head,
        index_sha_repo,
        index_sha_embedded: embedded_index_sha.to_string(),
        index_match,
        index_post_d1_sha_repo,
        index_post_d1_sha_embedded: embedded_post_index_sha.to_string(),
        index_post_d1_match,
        borsai_file,
        borsai_in_repo,
        base_records: bases,
        first_trading_date,
        d1_status,
        d1,
        t_open,
        t_open_error,
        git_status_pending,
        committed,
        now_istanbul: crate::clock::istanbul(now_unix).1,
        minutes_to_t_open,
        active_post_d1,
        ok: blockers.is_empty(),
        blockers,
        warnings,
    })
}

// ---------------------------------------------------------------- komut blokları (K-P2-2: tek fonksiyon)

/// Sihirbazın komut blokları. Uygulama bunların HİÇBİRİNİ çalıştırmaz (adım 2 ve 4; iptal kaydının kendisi hariç,
/// onu uygulama çalıştırır ve aynı metni gösterir). Satır başına bir komut, `&&` yok, yorum satırı yok; her `commit`
/// `--` ile aynı yollara sınırlı; Python yolu ayardan (`python_display`).
#[derive(Debug, Clone, PartialEq)]
pub enum PostD1Todo<'a> {
    /// Adım 2: D_1 bültenleri ve sonuç dosyası (Python; ağ), ardından commit.
    Outcomes { through: &'a str },
    /// Adım 4: kayıt commit + push + push kanıtı (T_open'dan önce).
    Record { ticker: &'a str },
    /// İptal: iptal kaydı (Python) + commit + push.
    Cancel { ticker: &'a str, record_rel: &'a str, reason: &'a str },
}

pub fn post_d1_commands(repo: &RepoCtx, todo: &PostD1Todo<'_>) -> Vec<String> {
    let py = python_display(&repo.root, &repo.python);
    let mut out = vec![format!("cd {}", repo.root.display())];
    match todo {
        PostD1Todo::Outcomes { through } => {
            let paths = "data/";
            out.push(format!("{py} -m borsai.outcomes update --through {through}"));
            out.push(format!("git add {paths}"));
            out.push(format!("git commit -m \"BORSAI_OUTCOMES_{through}: bulletins and outcomes through D_1\" -- {paths}"));
        }
        PostD1Todo::Record { ticker } => {
            let paths = format!("registry/post_d1/{ticker}/");
            out.push(format!("git add {paths}"));
            out.push(format!("git commit -m \"BORSAI_POST_D1_{ticker}: post-D1 record before T_open\" -- {paths}"));
            out.push("git push origin main".into());
            out.push(format!("{py} -m borsai.push_proof $(git rev-parse HEAD)"));
            out.push("git add registry/push_proofs/".into());
            out.push("git commit -m \"BORSAI_PUSH_PROOF: $(git rev-parse HEAD)\" -- registry/push_proofs/".into());
            out.push("git push origin main".into());
        }
        PostD1Todo::Cancel { ticker, record_rel, reason } => {
            let paths = format!("registry/post_d1/{ticker}/");
            out.push(format!("{py} -m borsai.freeze --cancel {record_rel} --reason \"{}\"", reason.replace('"', "'")));
            out.push(format!("git add {paths}"));
            out.push(format!("git commit -m \"BORSAI_POST_D1_CANCEL_{ticker}: cancellation record before T_open\" -- {paths}"));
            out.push("git push origin main".into());
        }
    }
    out
}

// ---------------------------------------------------------------- adım 3: kayıt (Python) + parite

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ComparatorCheck {
    pub n_checked: usize,
    pub max_abs: f64,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1FreezeResult {
    pub record_rel_path: String,
    pub record_file: String,
    pub ticker: String,
    pub recorded_at_utc: String,
    pub recorded_at_istanbul: String,
    pub d1: Option<String>,
    pub ceiling_close_d1: Value,
    pub summary: Value,
    /// Python'un bastığı T_open ve not (yerel saat; kanıt değildir).
    pub t_open: Option<String>,
    pub python_note: Option<String>,
    pub base_record_file: Option<String>,
    pub parity: ParityReport,
    pub comparators: ComparatorCheck,
    /// Adım 4 komut bloğu (uygulama ÇALIŞTIRMAZ).
    pub todo: Vec<String>,
}

/// Python hatalarının sınıfı (stderr; EK 3 §6.6 adım 3 Türkçe açıklamalar tr.ts'te).
fn classify(e: AppError) -> AppError {
    let detail = e.detail.clone().unwrap_or_default();
    let code = if detail.contains("DUPLICATE_RECORD") {
        POST_D1_DUPLICATE_RECORD
    } else if detail.contains("CALENDAR_NOT_AVAILABLE") {
        POST_D1_CALENDAR_NOT_AVAILABLE
    } else if detail.contains("NO_PRE_LISTING_RECORD") {
        POST_D1_NO_BASE_RECORD
    } else if detail.contains("D1_NOT_TRADED") {
        POST_D1_NOT_TRADED
    } else if detail.contains("iptali T_open") {
        POST_D1_CANCEL_AFTER_T_OPEN
    } else {
        return e;
    };
    AppError::new(code, e.message).with_detail(detail)
}

fn rel_of(repo: &Path, printed: &str) -> Result<String, AppError> {
    let p = PathBuf::from(printed.trim());
    let root = canonical(repo).unwrap_or_else(|_| plain_path(repo.to_path_buf()));
    let abs = canonical(&p).unwrap_or_else(|_| plain_path(p));
    abs.strip_prefix(&root)
        .map(|r| r.to_string_lossy().replace('\\', "/"))
        .map_err(|_| AppError::new(POST_D1_FREEZE_FAILED, format!("kayıt yolu repo dışında: {printed}")))
}

/// Kaydın paritesi: base kaydın `model_inputs`'u (girdi belgesi değil; H36) ve kaydın `d1` bloğuyla Rust'ta yeniden
/// koşum; base kaydın sha'sı kayıttakiyle aynı olmalı. Uyuşmazlık kaydı geçersiz kılmaz; raporlanır.
pub fn post_d1_parity_in(repo: &Path, record: &Value, verified: &VerifiedModels) -> Result<(ParityReport, ComparatorCheck), AppError> {
    let base_rel = record.pointer("/base_record/file").and_then(Value::as_str).unwrap_or_default().to_string();
    let base = read_record(repo, &base_rel)?;
    let base_bytes = std::fs::read(base_rel.split('/').fold(repo.to_path_buf(), |p, c| p.join(c))).map_err(|e| io_error(&base_rel, e))?;
    let inputs: Map<String, Value> = base.get("model_inputs").and_then(Value::as_object).cloned().unwrap_or_default();
    let cells = base.get("models").and_then(Value::as_array).cloned().unwrap_or_default();
    let mut report = compare_post_d1_record(record, &inputs, &cells, verified);
    let want = record.pointer("/base_record/sha256").and_then(Value::as_str).unwrap_or("");
    if sha256_hex(&base_bytes) != want {
        report.mismatches.push(ParityCell {
            model_id: "base_record".into(),
            ok: false,
            bit_equal: false,
            max_abs: 0.0,
            n_numbers: 0,
            failures: vec![format!("base_record sha256: kayıt {want}, dosya {}", sha256_hex(&base_bytes))],
        });
    }
    let (n_checked, max_abs, failures) = check_comparators_conditional(record);
    Ok((report, ComparatorCheck { n_checked, max_abs, failures }))
}

/// Adım 3. Ön koşullar burada YENİDEN denetlenir (ön uç düğmesinden bağımsız): engelleyici varsa Python çağrılmaz.
pub fn post_d1_freeze_in(state: &AppState, repo: &RepoCtx, ticker: &str, now_unix: i64) -> Result<PostD1FreezeResult, AppError> {
    let verified = state.models.as_ref().map_err(|e| e.to_app_error())?;
    let pre = post_d1_preflight_at(repo, ticker, &state.embedded_index_sha(), crate::embedded::BUILD_INFO.index_post_d1_sha256, now_unix)?;
    if !pre.ok {
        return Err(AppError::new(POST_D1_PREFLIGHT_BLOCKED, format!("ön koşullar sağlanmıyor: {}", pre.blockers.join(", ")))
            .with_detail(serde_json::to_string_pretty(&pre).unwrap_or_default()));
    }
    let out = run_python(&repo.python, &repo.root, &["-m", "borsai.freeze", "--post-d1", ticker]).map_err(classify)?;
    let printed: Value = serde_json::from_str(out.trim())
        .map_err(|e| AppError::new(POST_D1_FREEZE_FAILED, format!("Python çıktısı JSON değil: {e}")).with_detail(out.clone()))?;
    let record_rel = rel_of(&repo.root, printed["path"].as_str().unwrap_or_default())?;
    let record = read_post_d1_record(&repo.root, &record_rel)?;
    let (mut parity, comparators) = post_d1_parity_in(&repo.root, &record, verified)?;
    if !parity.ok() {
        parity.incident_rel_path = write_incident(&repo.root, &record_rel, &parity).ok();
    }
    let text = |p: &str| record.pointer(p).and_then(Value::as_str).map(str::to_string);
    Ok(PostD1FreezeResult {
        record_file: Path::new(&record_rel).file_name().map(|f| f.to_string_lossy().to_string()).unwrap_or_default(),
        todo: post_d1_commands(repo, &PostD1Todo::Record { ticker }),
        record_rel_path: record_rel,
        ticker: ticker.to_string(),
        recorded_at_utc: text("/recorded_at_utc").unwrap_or_default(),
        recorded_at_istanbul: text("/recorded_at_istanbul").unwrap_or_default(),
        d1: text("/d1/session_date"),
        ceiling_close_d1: record.pointer("/d1/ceiling_close_D1").cloned().unwrap_or(Value::Null),
        summary: record.get("summary").cloned().unwrap_or(Value::Null),
        t_open: printed["T_open"].as_str().map(str::to_string),
        python_note: printed["note"].as_str().map(str::to_string),
        base_record_file: text("/base_record/file"),
        parity,
        comparators,
    })
}

// ---------------------------------------------------------------- iptal

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PostD1CancelResult {
    pub cancel_rel_path: String,
    pub cancels: String,
    pub ticker: String,
    pub reason: String,
    pub recorded_at_istanbul: String,
    pub todo: Vec<String>,
}

/// İptal kaydı Python'da (`borsai.freeze --cancel <dosya> --reason "…"`); T_open'dan itibaren Python reddeder (aynen
/// gösterilir: `POST_D1_CANCEL_AFTER_T_OPEN`).
pub fn post_d1_cancel_in(repo: &RepoCtx, record_rel: &str, reason: &str) -> Result<PostD1CancelResult, AppError> {
    let record_rel = safe_post_rel(record_rel)?;
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(AppError::new(INVALID_ARGUMENT, "iptal nedeni boş olamaz"));
    }
    let out = run_python(&repo.python, &repo.root, &["-m", "borsai.freeze", "--cancel", &record_rel, "--reason", reason])
        .map_err(classify)?;
    let cancel_rel = rel_of(&repo.root, out.trim().lines().last().unwrap_or_default())?;
    let doc = read_post_d1_record(&repo.root, &cancel_rel)?;
    let ticker = doc["ticker"].as_str().unwrap_or_default().to_string();
    let mut todo = post_d1_commands(repo, &PostD1Todo::Cancel { ticker: &ticker, record_rel: &record_rel, reason });
    // iptal kaydı uygulama tarafından yazıldı: komut bloğunda Python satırı tekrar edilmez
    todo.retain(|l| !l.contains("-m borsai.freeze --cancel"));
    Ok(PostD1CancelResult {
        todo,
        cancel_rel_path: cancel_rel,
        cancels: doc["cancels"]["file"].as_str().unwrap_or_default().to_string(),
        ticker,
        reason: doc["reason"].as_str().unwrap_or_default().to_string(),
        recorded_at_istanbul: doc["recorded_at_istanbul"].as_str().unwrap_or_default().to_string(),
    })
}

// ---------------------------------------------------------------- komutlar

fn now_unix() -> i64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

#[tauri::command]
pub fn post_d1_records(state: tauri::State<'_, AppState>, ticker: String) -> Result<Vec<PostD1RecordRow>, AppError> {
    post_d1_records_in(&state.require_repo()?.root, &ticker)
}

#[tauri::command]
pub fn post_d1_view(
    state: tauri::State<'_, AppState>,
    ticker: String,
    j: usize,
    file: Option<String>,
) -> Result<PostD1View, AppError> {
    post_d1_view_in(&state.require_repo()?.root, &ticker, j, file.as_deref())
}

#[tauri::command]
pub async fn post_d1_preflight(state: tauri::State<'_, AppState>, ticker: String) -> Result<PostD1Preflight, AppError> {
    let repo = state.require_repo()?;
    post_d1_preflight_at(&repo, &ticker, &state.embedded_index_sha(), crate::embedded::BUILD_INFO.index_post_d1_sha256, now_unix())
}

#[tauri::command]
pub async fn post_d1_freeze(state: tauri::State<'_, AppState>, ticker: String) -> Result<PostD1FreezeResult, AppError> {
    let repo = state.require_repo()?;
    post_d1_freeze_in(&state, &repo, &ticker, now_unix())
}

#[tauri::command]
pub async fn post_d1_cancel(state: tauri::State<'_, AppState>, rel_path: String, reason: String) -> Result<PostD1CancelResult, AppError> {
    post_d1_cancel_in(&state.require_repo()?, &rel_path, &reason)
}

/// Komut bloğu (adım 2 ve 4), dondurmadan önce de görülebilsin diye ayrı komut. `kind`: OUTCOMES | RECORD.
#[tauri::command]
pub fn post_d1_todo(state: tauri::State<'_, AppState>, kind: String, ticker: String, through: Option<String>) -> Result<Vec<String>, AppError> {
    let repo = state.require_repo()?;
    if !valid_ticker(&ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    match kind.as_str() {
        "OUTCOMES" => {
            let through = through.filter(|t| crate::clock::is_iso_date(t)).ok_or_else(|| AppError::new(INVALID_ARGUMENT, "--through ISO tarih ister"))?;
            Ok(post_d1_commands(&repo, &PostD1Todo::Outcomes { through: &through }))
        }
        "RECORD" => Ok(post_d1_commands(&repo, &PostD1Todo::Record { ticker: &ticker })),
        other => Err(AppError::new(INVALID_ARGUMENT, format!("komut türü {other:?}"))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rel_guard() {
        assert!(safe_post_rel("registry/post_d1/SNTA1/20261001T190000Z_abc.json").is_ok());
        for bad in ["registry/post_d1/../x.json", "registry/records/SNTA1/x.json", "registry/oot/post_d1/A/x.json",
                    "/etc/x.json", "registry/post_d1/SNTA1/x.txt"] {
            assert!(safe_post_rel(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn t_open_unix() {
        // 2026-09-18T09:40:00+03:00 = 2026-09-18T06:40:00Z
        let t = unix_of_istanbul("2026-09-18T09:40:00+03:00").unwrap();
        assert_eq!(crate::clock::istanbul(t).1, "2026-09-18T09:40:00+03:00");
        assert!(unix_of_istanbul("2026-09-18T09:40:00Z").is_none());
    }
}
