//! Resmi "dondur" akışı (SPEC_APP §3e): ön koşullar, yetkili denetim, `borsai.freeze` çağrısı,
//! parite denetimi, "Şimdi yapılacaklar" komut bloğu ve iptal.
//!
//! Kayıt yazıcı Python `borsai.freeze`'dir; uygulama kayıt YAZMAZ. Uygulama `git commit`, `push`,
//! `add`, `tag` ÇALIŞTIRMAZ: komutlar yalnız kopyalanabilir metin olarak gösterilir (U32).
use serde::Serialize;
use serde_json::Value;
use std::path::{Path, PathBuf};

use super::config::{canonical, plain_path};
use super::git::git_readonly;
use super::inputs_doc::valid_ticker;
use super::models::sha256_hex;
use super::parity::{compare_record, write_incident, ParityReport};
use super::predict::{embedded_deflator_pins, tufe_for_inputs, tufe_source_repo, TufeInfo, TUFE_REASON_MONTH_MISSING};
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::clock::today_istanbul;
use crate::python::run_python;
use crate::state::{AppState, RepoCtx};

/// Yetkili girdi denetimi (SPEC_APP §3e adım 4), şartnamedeki komut birebir.
pub const PY_PIT: &str = "import json,sys; from borsai import registry as r; d,_=r.load_inputs(sys.argv[1]); \
print(json.dumps(r.inputs_pit_problems(d)))";
/// `borsai.__file__`'in hedef repo altında olduğunu doğrular (PYTHONPATH sızıntısı denetimi).
pub const PY_WHERE: &str = "import borsai, os; print(os.path.realpath(borsai.__file__))";

pub const FREEZE_DUPLICATE_RECORD: &str = "FREEZE_DUPLICATE_RECORD";
pub const FREEZE_CANCEL_AFTER_T: &str = "FREEZE_CANCEL_AFTER_T";
pub const FREEZE_FAILED: &str = "FREEZE_FAILED";
/// Dondurma anında ön koşullar (adım 1) sağlanmıyor; Python çağrılmadı (B3).
pub const FREEZE_PREFLIGHT_BLOCKED: &str = "FREEZE_PREFLIGHT_BLOCKED";
pub const RECORD_INVALID: &str = "RECORD_INVALID";
pub const BORSAI_OUTSIDE_REPO: &str = "BORSAI_OUTSIDE_REPO";
pub const RECORD_SCHEMA: &str = "borsai.record/1";

// ---------------------------------------------------------------- adım 1: ön koşullar

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Preflight {
    pub repo_root: String,
    pub python_path: String,
    pub git_head: Option<String>,
    /// `GIT_OPTIONAL_LOCKS=0 git status --porcelain -- registry` (kirli olabilir; yalnız bilgi).
    pub git_status_registry: String,
    pub index_sha_repo: Option<String>,
    pub index_sha_embedded: String,
    pub index_match: bool,
    /// `borsai.__file__` (hedef repo altında olmalı).
    pub borsai_file: Option<String>,
    pub borsai_in_repo: bool,
    pub today_istanbul: String,
    pub t: Option<String>,
    /// RED: bugün ≥ T · YELLOW: T bilinmiyor · NONE
    pub t_level: &'static str,
    pub ok: bool,
    /// Durduran nedenler (kod): REPO_DIR · GIT_HEAD · INDEX_SHA · BORSAI_IMPORT · TUFE_MONTH
    pub blockers: Vec<&'static str>,
    /// Gömülü kümede deflatörlü model varsa repo TÜFE tablosunun T için durumu (EK 3 §3.4). Yalnız ay eksikliği
    /// engeldir (`TUFE_MONTH`; Python `TufeMissing` kayıt yazmaz); TUFE_NOT_PIT ve TUFE_FILE_MISMATCH sarı bilgi
    /// satırıdır (Python kaydı yazar, deflatörlü hücreler RET); T boşsa engel değil (T_UNKNOWN reddi).
    pub tufe: Option<TufeInfo>,
}

pub fn preflight_in(repo: &RepoCtx, embedded_index_sha: &str, t: Option<&str>) -> Preflight {
    preflight_at(repo, embedded_index_sha, t, &today_istanbul())
}

/// `preflight_in`, bugünün tarihi verilerek (fixture üretimi saatten bağımsız olsun diye).
pub fn preflight_at(repo: &RepoCtx, embedded_index_sha: &str, t: Option<&str>, today: &str) -> Preflight {
    let mut blockers = Vec::new();
    let git_head = match git_readonly(&repo.root, &["rev-parse", "HEAD"]) {
        Ok(h) => Some(h.trim().to_string()),
        Err(_) => {
            blockers.push("GIT_HEAD");
            None
        }
    };
    let git_status_registry = git_readonly(&repo.root, &["status", "--porcelain", "--", "registry"]).unwrap_or_default();
    let index_sha_repo = std::fs::read(repo.root.join("models").join("INDEX.json")).ok().map(|b| sha256_hex(&b));
    let index_match = index_sha_repo.as_deref() == Some(embedded_index_sha);
    if !index_match {
        blockers.push("INDEX_SHA");
    }
    let borsai_file = run_python(&repo.python, &repo.root, &["-c", PY_WHERE]).ok().map(|s| s.trim().to_string());
    let borsai_in_repo = borsai_file
        .as_deref()
        .map(PathBuf::from)
        .is_some_and(|p| canonical(&repo.root).map(|r| plain_path(p).starts_with(r)).unwrap_or(false));
    if !borsai_in_repo {
        blockers.push("BORSAI_IMPORT");
    }
    let today = today.to_string();
    let t = t.map(str::trim).filter(|s| !s.is_empty()).map(str::to_string);
    let t_level = match &t {
        None => "YELLOW",
        Some(t) if today >= *t => "RED",
        Some(_) => "NONE",
    };
    let pins = embedded_deflator_pins();
    let tufe = (!pins.is_empty()).then(|| {
        let python = repo.python.strip_prefix(&repo.root).map(|p| p.display().to_string()).ok();
        tufe_for_inputs(t.as_deref(), &tufe_source_repo(&repo.root), pins, python.as_deref()).2
    });
    if tufe.as_ref().is_some_and(|i| i.reason == Some(TUFE_REASON_MONTH_MISSING)) {
        blockers.push("TUFE_MONTH");
    }
    Preflight {
        repo_root: repo.root.display().to_string(),
        python_path: repo.python.display().to_string(),
        git_head,
        git_status_registry,
        index_sha_repo,
        index_sha_embedded: embedded_index_sha.to_string(),
        index_match,
        borsai_file,
        borsai_in_repo,
        today_istanbul: today,
        t,
        t_level,
        ok: blockers.is_empty(),
        blockers,
        tufe,
    }
}

// ---------------------------------------------------------------- yol denetimi

/// Repo içi güvenli göreli yol: `..` yok, mutlak değil, istenen ön ekle başlıyor.
fn safe_rel(rel: &str, prefix: &str) -> Result<String, AppError> {
    let clean = rel.trim();
    let ok = clean.starts_with(prefix)
        && !clean.contains("..")
        && !clean.starts_with('/')
        && clean.ends_with(".json")
        && clean.chars().all(|c| c.is_ascii_alphanumeric() || "._-/@".contains(c));
    if !ok {
        return Err(AppError::new(INVALID_ARGUMENT, format!("yol {rel:?} ({prefix}… bekleniyor)")));
    }
    Ok(clean.to_string())
}

// ---------------------------------------------------------------- adım 4: yetkili denetim

pub fn inputs_pit_in(repo: &RepoCtx, rel: &str) -> Result<Vec<String>, AppError> {
    let rel = safe_rel(rel, "registry/inputs/")?;
    let out = run_python(&repo.python, &repo.root, &["-c", PY_PIT, &rel])?;
    serde_json::from_str(out.trim()).map_err(|e| AppError::new(FREEZE_FAILED, format!("Python çıktısı JSON değil: {e}")).with_detail(out))
}

// ---------------------------------------------------------------- adım 6: dondur

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FreezeResult {
    pub record_rel_path: String,
    pub record_file: String,
    pub ticker: String,
    pub recorded_at_utc: String,
    pub recorded_at_istanbul: String,
    pub n_models: usize,
    pub model_ids: Vec<String>,
    pub summary: Value,
    pub input_sha256: Option<String>,
    pub models_index_sha256: Option<String>,
    pub parity: ParityReport,
    /// "Şimdi yapılacaklar" (uygulama ÇALIŞTIRMAZ).
    pub todo: Vec<String>,
}

fn classify(e: AppError) -> AppError {
    let detail = e.detail.clone().unwrap_or_default();
    if detail.contains("DUPLICATE_RECORD") {
        return AppError::new(FREEZE_DUPLICATE_RECORD, e.message).with_detail(detail);
    }
    if detail.contains("iptal ilk işlem gününden") {
        return AppError::new(FREEZE_CANCEL_AFTER_T, e.message).with_detail(detail);
    }
    e
}

fn rel_of(repo: &Path, printed: &str) -> Result<String, AppError> {
    let p = PathBuf::from(printed.trim());
    let root = canonical(repo).unwrap_or_else(|_| plain_path(repo.to_path_buf()));
    let abs = canonical(&p).unwrap_or_else(|_| plain_path(p));
    abs.strip_prefix(&root)
        .map(|r| r.to_string_lossy().replace('\\', "/"))
        .map_err(|_| AppError::new(FREEZE_FAILED, format!("kayıt yolu repo dışında: {printed}")))
}

pub fn read_record(repo: &Path, rel: &str) -> Result<Value, AppError> {
    let rel = safe_rel(rel, "registry/records/")?;
    let bytes = std::fs::read(repo.join(&rel)).map_err(|e| io_error(&rel, e))?;
    let doc: Value = serde_json::from_slice(&bytes).map_err(|e| AppError::new(RECORD_INVALID, e.to_string()))?;
    let version = doc.get("schema_version").and_then(Value::as_str).unwrap_or("");
    if version != RECORD_SCHEMA {
        return Err(AppError::new(RECORD_INVALID, format!("{rel}: sürüm {version:?}")));
    }
    Ok(doc)
}

/// Python yolunun komut bloğundaki gösterimi: repo içindeyse göreli (D1 sonrası sihirbazı da kullanır).
pub fn python_display(repo: &Path, python: &Path) -> String {
    python
        .strip_prefix(repo)
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| python.display().to_string())
}

/// §3e "Şimdi yapılacaklar". Yorum satırı yoktur; her `commit` `--` ile aynı yollara sınırlıdır.
pub fn todo_commands(repo: &RepoCtx, ticker: &str, inputs_rel: &str, record_rel: &str) -> Vec<String> {
    let paths = format!("{inputs_rel} registry/source_docs/{ticker}/ {record_rel}");
    let py = python_display(&repo.root, &repo.python);
    vec![
        format!("cd {}", repo.root.display()),
        format!("git add {paths}"),
        format!("git commit -m \"BORSAI_RECORD_{ticker}: prediction record before first trading day\" -- {paths}"),
        "git push origin main".into(),
        format!("{py} -m borsai.push_proof $(git rev-parse HEAD)"),
        "git add registry/push_proofs/".into(),
        "git commit -m \"BORSAI_PUSH_PROOF: $(git rev-parse HEAD)\" -- registry/push_proofs/".into(),
        "git push origin main".into(),
    ]
}

/// İptal kaydı için komut bloğu.
pub fn cancel_todo_commands(repo: &RepoCtx, ticker: &str, cancel_rel: &str) -> Vec<String> {
    vec![
        format!("cd {}", repo.root.display()),
        format!("git add {cancel_rel}"),
        format!("git commit -m \"BORSAI_CANCEL_{ticker}: cancellation record\" -- {cancel_rel}"),
        "git push origin main".into(),
    ]
}

/// Girdi belgesindeki T (ön koşul adımının T uyarısı için; okunamazsa `None`, engelleyici değildir).
fn inputs_t(repo: &Path, inputs_rel: &str) -> Option<String> {
    let doc: Value = serde_json::from_slice(&std::fs::read(repo.join(inputs_rel)).ok()?).ok()?;
    doc["fields"]["first_trading_date"]["value"].as_str().map(str::to_string)
}

/// Adım 6. Ön koşullar (adım 1) burada YENİDEN denetlenir: ön uç düğmesinden bağımsız olarak
/// engelleyici varsa (`INDEX_SHA`, `BORSAI_IMPORT`, `GIT_HEAD`, `TUFE_MONTH`) Python çağrılmaz, kayıt ve olay
/// dosyası yazılmaz (FAZ3_APP_AUDIT B3; EK 3 §3.4).
pub fn freeze_in(state: &AppState, repo: &RepoCtx, embedded_index_sha: &str, inputs_rel: &str) -> Result<FreezeResult, AppError> {
    let inputs_rel = safe_rel(inputs_rel, "registry/inputs/")?;
    let pre = preflight_in(repo, embedded_index_sha, inputs_t(&repo.root, &inputs_rel).as_deref());
    if !pre.ok {
        return Err(AppError::new(FREEZE_PREFLIGHT_BLOCKED, format!("ön koşullar sağlanmıyor: {}", pre.blockers.join(", ")))
            .with_detail(serde_json::to_string_pretty(&pre).unwrap_or_default()));
    }
    let out = run_python(&repo.python, &repo.root, &["-m", "borsai.freeze", &inputs_rel]).map_err(classify)?;
    let record_rel = rel_of(&repo.root, out.trim().lines().last().unwrap_or_default())?;
    let record = read_record(&repo.root, &record_rel)?;
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    let mut parity = compare_record(&record, &models.models);
    if !parity.ok() {
        parity.incident_rel_path = write_incident(&repo.root, &record_rel, &parity).ok();
    }
    let ticker = record["ticker"].as_str().unwrap_or_default().to_string();
    let cells = record["models"].as_array().cloned().unwrap_or_default();
    Ok(FreezeResult {
        record_file: Path::new(&record_rel).file_name().map(|f| f.to_string_lossy().to_string()).unwrap_or_default(),
        todo: todo_commands(repo, &ticker, &inputs_rel, &record_rel),
        record_rel_path: record_rel,
        ticker,
        recorded_at_utc: record["recorded_at_utc"].as_str().unwrap_or_default().to_string(),
        recorded_at_istanbul: record["recorded_at_istanbul"].as_str().unwrap_or_default().to_string(),
        n_models: cells.len(),
        model_ids: cells.iter().map(|c| c["model_id"].as_str().unwrap_or("?").to_string()).collect(),
        summary: record["summary"].clone(),
        input_sha256: record["input_sha256"].as_str().map(str::to_string),
        models_index_sha256: record["models_index"]["sha256"].as_str().map(str::to_string),
        parity,
    })
}

// ---------------------------------------------------------------- iptal

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CancelResult {
    pub cancel_rel_path: String,
    pub cancels: String,
    pub ticker: String,
    pub reason: String,
    pub recorded_at_istanbul: String,
    pub todo: Vec<String>,
}

pub fn cancel_in(repo: &RepoCtx, record_rel: &str, reason: &str) -> Result<CancelResult, AppError> {
    let record_rel = safe_rel(record_rel, "registry/records/")?;
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(AppError::new(INVALID_ARGUMENT, "iptal nedeni boş olamaz"));
    }
    let out = run_python(&repo.python, &repo.root, &["-m", "borsai.freeze", "--cancel", &record_rel, "--reason", reason])
        .map_err(classify)?;
    let cancel_rel = rel_of(&repo.root, out.trim().lines().last().unwrap_or_default())?;
    let doc = read_record(&repo.root, &cancel_rel)?;
    let ticker = doc["ticker"].as_str().unwrap_or_default().to_string();
    Ok(CancelResult {
        todo: cancel_todo_commands(repo, &ticker, &cancel_rel),
        cancel_rel_path: cancel_rel,
        cancels: doc["cancels"]["file"].as_str().unwrap_or_default().to_string(),
        ticker,
        reason: doc["reason"].as_str().unwrap_or_default().to_string(),
        recorded_at_istanbul: doc["recorded_at_istanbul"].as_str().unwrap_or_default().to_string(),
    })
}

// ---------------------------------------------------------------- komutlar

#[tauri::command]
pub async fn freeze_preflight(state: tauri::State<'_, AppState>, t: Option<String>) -> Result<Preflight, AppError> {
    let repo = state.require_repo()?;
    Ok(preflight_in(&repo, &state.embedded_index_sha(), t.as_deref()))
}

#[tauri::command]
pub async fn inputs_pit_check(state: tauri::State<'_, AppState>, rel_path: String) -> Result<Vec<String>, AppError> {
    inputs_pit_in(&state.require_repo()?, &rel_path)
}

#[tauri::command]
pub async fn freeze_record(state: tauri::State<'_, AppState>, rel_path: String) -> Result<FreezeResult, AppError> {
    let repo = state.require_repo()?;
    freeze_in(&state, &repo, &state.embedded_index_sha(), &rel_path)
}

#[tauri::command]
pub async fn cancel_record(state: tauri::State<'_, AppState>, rel_path: String, reason: String) -> Result<CancelResult, AppError> {
    let repo = state.require_repo()?;
    cancel_in(&repo, &rel_path, &reason)
}

/// Ekrandaki komut bloğu, dondurmadan önce de görülebilsin diye ayrı komut (U32).
#[tauri::command]
pub fn freeze_todo(
    state: tauri::State<'_, AppState>,
    ticker: String,
    inputs_rel_path: String,
    record_rel_path: String,
) -> Result<Vec<String>, AppError> {
    let repo = state.require_repo()?;
    if !valid_ticker(&ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    Ok(todo_commands(&repo, &ticker, &inputs_rel_path, &record_rel_path))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rel_paths_are_guarded() {
        assert!(safe_rel("registry/inputs/SNTA1.PB.json", "registry/inputs/").is_ok());
        assert!(safe_rel("registry/inputs/../../etc/x.json", "registry/inputs/").is_err());
        assert!(safe_rel("/etc/x.json", "registry/inputs/").is_err());
        assert!(safe_rel("registry/records/A/x.json", "registry/inputs/").is_err());
        assert!(safe_rel("registry/inputs/x.txt", "registry/inputs/").is_err());
    }
}
