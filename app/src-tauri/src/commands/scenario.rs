//! Kişisel kayıtlar (`borsai.app_scenario/1`, SPEC_APP §2.4, §3c, §3f). Yalnız
//! `<app_data_dir>/scenarios/<ULID>.json`; hedef yol repo altındaysa `SCENARIO_PATH_INSIDE_REPO`, gömülü sicil anlık
//! görüntüsünün altındaysa (`<app_data_dir>/snapshot/`; FAZ9_SNAPSHOT K-SNAP-2) `SCENARIO_PATH_INSIDE_SNAPSHOT`.
//!
//! Dosyada `record_type` anahtarı YOKTUR ve `official: false` sabittir: kazara sicil dizinine düşse
//! bile Python `active_records` onu saymaz. Çıktılar kayıt anında Rust `predict_all` ile aynı girdi
//! ve f6'dan üretilir (ön uçtan sayı alınmaz). Yüklenen senaryonun çıktısı olduğu gibi gösterilir;
//! gömülü INDEX sha'sı farklıysa bu bayrakla bildirilir, çıktı yeniden hesaplanmaz (U36).
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use super::config::is_within;
use super::form::{model_input_fields, DATE_FIELDS, STAGES};
use super::predict::{predict_all_value, F6Arg};
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::clock::{now_istanbul, unix_millis};
use crate::embedded;
use crate::state::AppState;

pub const SCENARIO_SCHEMA: &str = "borsai.app_scenario/1";
pub const SCENARIO_PATH_INSIDE_REPO: &str = "SCENARIO_PATH_INSIDE_REPO";
pub const SCENARIO_PATH_INSIDE_SNAPSHOT: &str = "SCENARIO_PATH_INSIDE_SNAPSHOT";
pub const SCENARIO_NOT_FOUND: &str = "SCENARIO_NOT_FOUND";
pub const SCENARIO_SCHEMA_UNSUPPORTED: &str = "SCENARIO_SCHEMA_UNSUPPORTED";
pub const F6_ORIGINS: [&str; 3] = ["REPO_PYTHON", "MANUAL", "NONE"];
/// Kabul edilen tek beyan türü: "seri sürüyor" (U52-2). Şema sürümü aynı kalır; eski dosyalardaki
/// NOT_CEILING/PENDING değerleri yüklemede yok sayılır (ön uç, `state.resetView`).
const USER_DAY_STATES: [&str; 1] = ["CEILING"];

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct F6Doc {
    pub value: Option<String>,
    pub refusal: Option<String>,
    pub origin: String,
    #[serde(rename = "S0_date")]
    pub s0_date: Option<String>,
    #[serde(rename = "S20_date")]
    pub s20_date: Option<String>,
    pub xu100_sha256: Option<String>,
    pub ref_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ObservedStreakUser {
    pub ticker: Option<String>,
    /// D1..D10: "CEILING" ("seri sürüyor") | null. Yalnız etiket; hiçbir hesaba girmez (U52).
    pub days: Vec<Option<String>>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SaveScenarioReq {
    pub title: String,
    pub stage: String,
    pub ticker_label: Option<String>,
    /// 17 model girdisi (metin | null).
    pub inputs: Map<String, Value>,
    /// first_trading_date, bookbuilding_start, bookbuilding_end (bilgi; modele girmez).
    #[serde(default)]
    pub input_dates: Map<String, Value>,
    pub f6: F6Doc,
    pub observed_streak_user: Option<ObservedStreakUser>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScenarioSummary {
    pub scenario_id: String,
    /// OK | OLD_VERSION | UNREADABLE
    pub status: &'static str,
    pub title: Option<String>,
    pub created_at_local: Option<String>,
    pub stage: Option<String>,
    pub ticker_label: Option<String>,
    pub app_version: Option<String>,
    pub models_index_sha256: Option<String>,
    pub same_index: bool,
    pub schema_version: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct LoadedScenario {
    pub doc: Value,
    pub same_index: bool,
    pub embedded_index_sha256: String,
}

// ---------------------------------------------------------------- ULID

const CROCKFORD: &[u8; 32] = b"0123456789ABCDEFGHJKMNPQRSTVWXYZ";
static COUNTER: AtomicU64 = AtomicU64::new(0);

fn random_u64() -> u64 {
    let mut h = RandomState::new().build_hasher();
    h.write_u64(COUNTER.fetch_add(1, Ordering::Relaxed));
    h.write_u128(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
    h.write_u32(std::process::id());
    h.finish()
}

/// 48 bit milisaniye + 80 bit rastgele, Crockford base32, 26 karakter.
pub fn ulid_at(ms: u64, rand80: u128) -> String {
    let v: u128 = ((ms as u128 & ((1 << 48) - 1)) << 80) | (rand80 & ((1u128 << 80) - 1));
    (0..26).rev().map(|i| CROCKFORD[((v >> (i * 5)) & 31) as usize] as char).collect()
}

pub fn new_ulid() -> String {
    ulid_at(unix_millis(), ((random_u64() as u128) << 64) | random_u64() as u128)
}

pub fn valid_scenario_id(id: &str) -> bool {
    id.len() == 26 && id.bytes().all(|b| CROCKFORD.contains(&b))
}

// ---------------------------------------------------------------- yol koruması (U27)

/// Kişisel kayıt yollarının TEK bekçisi (U27): yol fiziksel karşılığıyla (`resolve_path`: sembolik
/// bağlar — askıda olanlar dahil — izlenir, `..` çözülür) korunan köklerden birinin altındaysa ret.
/// Kaydetme (`scenarios_dir`), tekli ve toplu dışa aktarma (`check_export_target`) buradan geçer.
fn guard_outside(protected: &[PathBuf], p: &Path) -> Result<(), AppError> {
    for root in protected {
        if is_within(p, root) {
            return Err(AppError::new(SCENARIO_PATH_INSIDE_REPO, format!("{} repo altında: {}", p.display(), root.display())));
        }
    }
    Ok(())
}

/// Gömülü sicil anlık görüntüsü (`<data_dir>/snapshot/`) kişisel kayıt hedefi olamaz (K-SNAP-2). Repo kökü sayılmaz
/// (korunan kökler listesine girmez); kendi koduyla reddedilir.
fn guard_snapshot(data_dir: &Path, p: &Path) -> Result<(), AppError> {
    let snap = data_dir.join(super::registry_snapshot::SNAPSHOT_DIR);
    if is_within(p, &snap) {
        return Err(AppError::new(SCENARIO_PATH_INSIDE_SNAPSHOT, format!("{} anlık görüntü altında: {}", p.display(), snap.display())));
    }
    Ok(())
}

/// `<data_dir>/scenarios`; korunan köklerden birinin ya da anlık görüntünün altındaysa ret (`guard_outside`, `guard_snapshot`).
/// Denetim dizin oluşturulmadan ÖNCE yapılır (repo altında dizin bile açılmaz).
pub fn scenarios_dir(data_dir: &Path, protected_roots: &[PathBuf]) -> Result<PathBuf, AppError> {
    let dir = data_dir.join("scenarios");
    guard_outside(protected_roots, &dir)?;
    guard_snapshot(data_dir, &dir)?;
    Ok(dir)
}

// ---------------------------------------------------------------- kaydet / listele / yükle / sil

fn validate_req(req: &SaveScenarioReq) -> Result<(), AppError> {
    let bad = |m: String| Err(AppError::new(INVALID_ARGUMENT, m));
    if !STAGES.contains(&req.stage.as_str()) {
        return bad(format!("aşama {:?}", req.stage));
    }
    let allowed: Vec<&str> = model_input_fields().collect();
    for (k, v) in &req.inputs {
        if !allowed.contains(&k.as_str()) || !(v.is_string() || v.is_null()) {
            return bad(format!("girdi {k:?}"));
        }
    }
    for (k, v) in &req.input_dates {
        if !DATE_FIELDS.contains(&k.as_str()) || !(v.is_string() || v.is_null()) {
            return bad(format!("tarih alanı {k:?}"));
        }
    }
    if !F6_ORIGINS.contains(&req.f6.origin.as_str()) {
        return bad(format!("f6.origin {:?}", req.f6.origin));
    }
    if let Some(o) = &req.observed_streak_user {
        if o.days.len() > 10 || o.days.iter().flatten().any(|d| !USER_DAY_STATES.contains(&d.as_str())) {
            return bad("observed_streak_user.days".into());
        }
    }
    Ok(())
}

/// Senaryo belgesi: çıktılar burada, Rust `predict_all` ile üretilir.
pub fn build_scenario_doc(state: &AppState, req: &SaveScenarioReq, scenario_id: &str, created_at: &str) -> Result<Value, AppError> {
    validate_req(req)?;
    let inputs: Map<String, Value> = model_input_fields().map(|f| (f.to_string(), req.inputs.get(f).cloned().unwrap_or(Value::Null))).collect();
    let f6 = F6Arg { value: req.f6.value.clone().map(Value::String), refusal: req.f6.refusal.clone() };
    // TÜFE ayı ilk işlem gününden türetilir (EK 3 §3.3); elle TÜFE girdisi yoktur
    let t = req.input_dates.get("first_trading_date").and_then(Value::as_str);
    let runs = predict_all_value(state, &inputs, &f6, t)?;
    let mut outputs = Map::new();
    for r in runs {
        let id = r["model_id"].as_str().unwrap_or_default().to_string();
        outputs.insert(
            id,
            json!({"params_sha256": r["params_sha256"], "kind": r["kind"], "status": r["status"],
                   "refusal": r["refusal"], "output": r["output"]}),
        );
    }
    let mut doc = json!({
        "schema_version": SCENARIO_SCHEMA,
        "official": false,
        "scenario_id": scenario_id,
        "title": req.title.trim(),
        "created_at_local": created_at,
        "app_version": env!("CARGO_PKG_VERSION"),
        "build_git_head": embedded::BUILD_INFO.git_head,
        "stage": req.stage,
        "ticker_label": req.ticker_label.as_deref().map(str::trim).unwrap_or(""),
        "inputs": inputs,
        "input_dates": req.input_dates,
        "f6": req.f6,
        "models_index_sha256": state.embedded_index_sha(),
        "outputs": outputs,
    });
    if let Some(o) = &req.observed_streak_user {
        doc["observed_streak_user"] = serde_json::to_value(o).expect("serde");
    }
    Ok(doc)
}

pub fn pretty(doc: &Value) -> String {
    let mut s = serde_json::to_string_pretty(doc).expect("serde");
    s.push('\n');
    s
}

pub fn save_scenario_in(state: &AppState, data_dir: &Path, protected: &[PathBuf], req: &SaveScenarioReq) -> Result<ScenarioSummary, AppError> {
    let dir = scenarios_dir(data_dir, protected)?;
    let id = new_ulid();
    let doc = build_scenario_doc(state, req, &id, &now_istanbul())?;
    std::fs::create_dir_all(&dir).map_err(|e| io_error("scenarios dizini", e))?;
    let path = dir.join(format!("{id}.json"));
    write_new(&path, pretty(&doc).as_bytes()).map_err(|e| io_error("senaryo yazılamadı", e))?;
    Ok(summary(&id, Some(&doc), &state.embedded_index_sha()))
}

fn summary(id: &str, doc: Option<&Value>, embedded_sha: &str) -> ScenarioSummary {
    let s = |k: &str| doc.and_then(|d| d.get(k)).and_then(Value::as_str).map(str::to_string);
    let version = s("schema_version");
    let status = match (doc, version.as_deref()) {
        (None, _) => "UNREADABLE",
        (Some(_), Some(SCENARIO_SCHEMA)) => "OK",
        _ => "OLD_VERSION",
    };
    let sha = s("models_index_sha256");
    ScenarioSummary {
        scenario_id: id.into(),
        status,
        title: s("title"),
        created_at_local: s("created_at_local"),
        stage: s("stage"),
        ticker_label: s("ticker_label"),
        app_version: s("app_version"),
        same_index: sha.as_deref() == Some(embedded_sha),
        models_index_sha256: sha,
        schema_version: version,
    }
}

pub fn list_scenarios_in(data_dir: &Path, embedded_sha: &str) -> Result<Vec<ScenarioSummary>, AppError> {
    let dir = data_dir.join("scenarios");
    if !dir.is_dir() {
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    for e in std::fs::read_dir(&dir).map_err(|e| io_error("scenarios dizini", e))?.flatten() {
        let name = e.file_name();
        let Some(id) = name.to_str().and_then(|n| n.strip_suffix(".json")) else { continue };
        if !valid_scenario_id(id) {
            continue;
        }
        let doc = std::fs::read(e.path()).ok().and_then(|b| serde_json::from_slice::<Value>(&b).ok()).filter(Value::is_object);
        out.push(summary(id, doc.as_ref(), embedded_sha));
    }
    out.sort_by(|a, b| b.scenario_id.cmp(&a.scenario_id));
    Ok(out)
}

fn scenario_path(data_dir: &Path, id: &str) -> Result<PathBuf, AppError> {
    if !valid_scenario_id(id) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("senaryo kimliği {id:?}")));
    }
    let p = data_dir.join("scenarios").join(format!("{id}.json"));
    if !p.is_file() {
        return Err(AppError::new(SCENARIO_NOT_FOUND, id.to_string()));
    }
    Ok(p)
}

pub fn load_scenario_in(data_dir: &Path, id: &str, embedded_sha: &str) -> Result<LoadedScenario, AppError> {
    let p = scenario_path(data_dir, id)?;
    let doc: Value = std::fs::read(&p)
        .map_err(|e| io_error("senaryo okunamadı", e))
        .and_then(|b| serde_json::from_slice(&b).map_err(|e| io_error("senaryo okunamadı", e)))?;
    let version = doc.get("schema_version").and_then(Value::as_str).unwrap_or("");
    if version != SCENARIO_SCHEMA || !doc.get("outputs").is_some_and(Value::is_object) {
        return Err(AppError::new(SCENARIO_SCHEMA_UNSUPPORTED, format!("sürüm {version:?}")));
    }
    let same_index = doc.get("models_index_sha256").and_then(Value::as_str) == Some(embedded_sha);
    Ok(LoadedScenario { doc, same_index, embedded_index_sha256: embedded_sha.into() })
}

pub fn delete_scenario_in(data_dir: &Path, id: &str) -> Result<(), AppError> {
    let p = scenario_path(data_dir, id)?;
    std::fs::remove_file(p).map_err(|e| io_error("senaryo silinemedi", e))
}

/// Dışa aktarma hedefi bekçisi (U27): repo altına hiçbir kişisel kayıt yazılmaz. Tekli ve toplu
/// dışa aktarmanın TEK kod yoludur; ikinci bir yol denetimi yazılmaz. Hedefin kendisi sembolik bağsa
/// (nereyi gösterirse göstersin) reddedilir: kişisel kayıt bir bağın içinden yazılmaz.
fn check_export_target(protected: &[PathBuf], target: &Path) -> Result<(), AppError> {
    guard_outside(protected, target)?;
    if std::fs::symlink_metadata(target).is_ok_and(|m| m.file_type().is_symlink()) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("{} sembolik bağ; dışa aktarma bağı izlemez", target.display())));
    }
    Ok(())
}

fn write_new(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    f.write_all(bytes)
}

/// Dışa aktarma yazımı (`check_export_target`'tan sonra); son bileşendeki sembolik bağ hiçbir koşulda
/// izlenmez:
/// - hedef yoksa `create_new` (O_CREAT|O_EXCL): denetimden sonra oraya bir bağ konmuşsa EEXIST, yazılmaz;
/// - hedef var olan NORMAL dosyaysa (bağ olmadığı `symlink_metadata` ile kanıtlanır) bugünkü davranış
///   korunur, üzerine yazılır (dosya seçici üzerine yazmayı zaten sorar). İçerik aynı dizinde
///   `create_new` ile açılan geçici dosyaya yazılır ve `rename` ile hedefin yerine konur; `rename`
///   son bileşendeki bağı izlemez, yarım yazılmış dosya da bırakmaz;
/// - bağ ya da dizin: ret.
fn write_export(target: &Path, bytes: &[u8], what: &str) -> Result<(), AppError> {
    match std::fs::symlink_metadata(target) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => write_new(target, bytes).map_err(|e| io_error(what, e)),
        Ok(m) if m.file_type().is_file() => {
            let name = target.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
            let tmp = target.with_file_name(format!(".{name}.{}.tmp", new_ulid()));
            write_new(&tmp, bytes).map_err(|e| io_error(what, e))?;
            std::fs::rename(&tmp, target).map_err(|e| {
                let _ = std::fs::remove_file(&tmp);
                io_error(what, e)
            })
        }
        Ok(m) if m.file_type().is_symlink() => {
            Err(AppError::new(INVALID_ARGUMENT, format!("{} sembolik bağ; dışa aktarma bağı izlemez", target.display())))
        }
        Ok(_) => Err(AppError::new(INVALID_ARGUMENT, format!("{} normal dosya değil", target.display()))),
        Err(e) => Err(io_error(what, e)),
    }
}

/// Dışa aktarma: aynı içerik kullanıcının seçtiği yola. Hedef repo altındaysa REDDEDİLİR (U27).
pub fn export_scenario_in(data_dir: &Path, protected: &[PathBuf], id: &str, target: &Path) -> Result<String, AppError> {
    check_export_target(protected, target)?;
    guard_snapshot(data_dir, target)?;
    let src = scenario_path(data_dir, id)?;
    let bytes = std::fs::read(src).map_err(|e| io_error("senaryo okunamadı", e))?;
    write_export(target, &bytes, "senaryo dışa aktarılamadı")?;
    Ok(target.display().to_string())
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ExportAllResult {
    pub path: String,
    /// Diziye giren kayıt sayısı (OK ve OLD_VERSION).
    pub n_exported: usize,
    /// Okunamadığı için diziye girmeyen dosya sayısı.
    pub n_unreadable: usize,
}

/// Tümünü dışa aktarma (§3f): TEK JSON dizisi, okunabilen her kişisel kayıt dosyadaki değeriyle,
/// `scenario_id` sırasıyla. Okunamayan dosya diziye GİRMEZ, yalnız sayılır. Hedef bekçisi tekli
/// dışa aktarmanınkiyle aynıdır (U27).
pub fn export_all_scenarios_in(data_dir: &Path, protected: &[PathBuf], target: &Path) -> Result<ExportAllResult, AppError> {
    check_export_target(protected, target)?;
    guard_snapshot(data_dir, target)?;
    let dir = data_dir.join("scenarios");
    let mut ids: Vec<String> = Vec::new();
    if dir.is_dir() {
        for e in std::fs::read_dir(&dir).map_err(|e| io_error("scenarios dizini", e))?.flatten() {
            let name = e.file_name();
            let Some(id) = name.to_str().and_then(|n| n.strip_suffix(".json")) else { continue };
            if valid_scenario_id(id) {
                ids.push(id.to_string());
            }
        }
    }
    ids.sort();
    let mut docs: Vec<Value> = Vec::new();
    let mut unreadable = 0usize;
    for id in &ids {
        let doc = std::fs::read(dir.join(format!("{id}.json")))
            .ok()
            .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
            .filter(Value::is_object);
        match doc {
            Some(d) => docs.push(d),
            None => unreadable += 1,
        }
    }
    let n_exported = docs.len();
    write_export(target, pretty(&Value::Array(docs)).as_bytes(), "kişisel kayıtlar dışa aktarılamadı")?;
    Ok(ExportAllResult { path: target.display().to_string(), n_exported, n_unreadable: unreadable })
}

#[tauri::command]
pub fn save_scenario(state: tauri::State<'_, AppState>, req: SaveScenarioReq) -> Result<ScenarioSummary, AppError> {
    let data_dir = state.data_dir()?;
    save_scenario_in(&state, &data_dir, &state.protected_roots(), &req)
}

#[tauri::command]
pub fn list_scenarios(state: tauri::State<'_, AppState>) -> Result<Vec<ScenarioSummary>, AppError> {
    list_scenarios_in(&state.data_dir()?, &state.embedded_index_sha())
}

#[tauri::command]
pub fn load_scenario(state: tauri::State<'_, AppState>, id: String) -> Result<LoadedScenario, AppError> {
    load_scenario_in(&state.data_dir()?, &id, &state.embedded_index_sha())
}

#[tauri::command]
pub fn delete_scenario(state: tauri::State<'_, AppState>, id: String) -> Result<(), AppError> {
    delete_scenario_in(&state.data_dir()?, &id)
}

#[tauri::command]
pub fn export_scenario(state: tauri::State<'_, AppState>, id: String, target: String) -> Result<String, AppError> {
    let data_dir = state.data_dir()?;
    export_scenario_in(&data_dir, &state.protected_roots(), &id, Path::new(&target))
}

#[tauri::command]
pub fn export_all_scenarios(state: tauri::State<'_, AppState>, target: String) -> Result<ExportAllResult, AppError> {
    let data_dir = state.data_dir()?;
    export_all_scenarios_in(&data_dir, &state.protected_roots(), Path::new(&target))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A5-6 için geçici uygulama verisi: `<temp>/borsai_test_<etiket>_<pid>_<sayaç>/`.
    fn temp_data_dir(tag: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let d = std::env::temp_dir().join(format!("borsai_scn_{tag}_{}_{n}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("scenarios")).expect("geçici dizin");
        d
    }

    fn write_scenario(dir: &Path, id: &str, body: &str) {
        std::fs::write(dir.join("scenarios").join(format!("{id}.json")), body).expect("senaryo dosyası");
    }

    /// A5-6: tümünü dışa aktarma tek JSON dizisidir; okunamayan dosya diziye girmez, sayılır;
    /// repo altı hedef `SCENARIO_PATH_INSIDE_REPO` ile reddedilir (tekli dışa aktarmanın bekçisi).
    #[test]
    fn export_all_scenarios_array_and_guard() {
        let data = temp_data_dir("all");
        let repo = temp_data_dir("repo");
        // iki okunabilir (OK + OLD_VERSION) ve bir bozuk dosya; kimlikler sırasız yazılır
        let ok = "01ARYZ6S41ABCDEFGHJKMNPQRS";
        let old = "00ARYZ6S41ABCDEFGHJKMNPQRS";
        let broken = "02ARYZ6S41ABCDEFGHJKMNPQRS";
        write_scenario(&data, ok, r#"{"schema_version":"borsai.app_scenario/1","official":false,"scenario_id":"01ARYZ6S41ABCDEFGHJKMNPQRS","title":"yeni"}"#);
        write_scenario(&data, old, r#"{"schema_version":"borsai.app_scenario/0","official":false,"scenario_id":"00ARYZ6S41ABCDEFGHJKMNPQRS","title":"eski"}"#);
        write_scenario(&data, broken, "{bozuk");
        // ULID olmayan ad hiç sayılmaz
        write_scenario(&data, "not_a_ulid", "{}");

        let target = data.join("tumu.json");
        let res = export_all_scenarios_in(&data, &[repo.clone()], &target).expect("tümünü dışa aktar");
        assert_eq!((res.n_exported, res.n_unreadable), (2, 1));
        let arr: Value = serde_json::from_slice(&std::fs::read(&target).expect("çıktı")).expect("json");
        let items = arr.as_array().expect("tek JSON dizisi");
        assert_eq!(items.len(), res.n_exported);
        // scenario_id sırası (artan) ve her öğede official: false, record_type YOK
        assert_eq!(
            items.iter().map(|d| d["scenario_id"].as_str().unwrap_or_default()).collect::<Vec<_>>(),
            vec![old, ok]
        );
        for d in items {
            assert_eq!(d["official"], Value::Bool(false));
            assert!(d.get("record_type").is_none(), "kişisel kayıtta record_type olmaz");
        }

        // U27 bekçisi: repo altına tümünü dışa aktarma reddedilir, dosya oluşmaz
        let inside = repo.join("registry").join("records").join("hepsi.json");
        let err = export_all_scenarios_in(&data, &[repo.clone()], &inside).unwrap_err();
        assert_eq!(err.code, SCENARIO_PATH_INSIDE_REPO);
        assert!(!inside.exists());

        // boş dizin: boş dizi
        let empty = temp_data_dir("bos");
        let t2 = empty.join("bos.json");
        let res2 = export_all_scenarios_in(&empty, &[repo.clone()], &t2).expect("boş");
        assert_eq!((res2.n_exported, res2.n_unreadable), (0, 0));
        assert_eq!(serde_json::from_slice::<Value>(&std::fs::read(&t2).expect("çıktı")).expect("json"), json!([]));

        for d in [data, repo, empty] {
            let _ = std::fs::remove_dir_all(d);
        }
    }

    #[test]
    fn ulid_shape() {
        assert_eq!(ulid_at(0, 0), "00000000000000000000000000");
        assert_eq!(ulid_at(1_469_918_176_385, 0)[..10].to_string(), "01ARYZ6S41");
        let a = new_ulid();
        assert!(valid_scenario_id(&a), "{a}");
        assert!(!valid_scenario_id("../../registry/x"));
        assert_ne!(new_ulid()[10..], new_ulid()[10..]);
    }
}
