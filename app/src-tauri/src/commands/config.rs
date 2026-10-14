//! Uygulama ayarı (`borsai.app_config/1`, SPEC_APP §2, §2.5, §6) ve repo modu doğrulaması.
//!
//! Repo modu = `repo_root` doğrulanmış: dizin var, uygulama verisi repo altında değil, `models/INDEX.json`
//! sha'sı gömülüyle eşit, `git rev-parse HEAD` başarılı, `python -c "import borsai"` repo içinden
//! başarılı. Pinli XU100 ve takvim son günleri yalnız bilgi amaçlıdır (derin doğrulama).
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};

use super::git::git_readonly;
use super::models::sha256_hex;
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::python::run_python;
use crate::state::AppState;

pub const CONFIG_SCHEMA: &str = "borsai.app_config/1";
pub const CONFIG_FILE: &str = "config.json";
pub const SCORES_SOURCES: [&str; 2] = ["REPO", "EMBEDDED"];
pub const DATA_DIR_INSIDE_REPO: &str = "DATA_DIR_INSIDE_REPO";
pub const CONFIG_RESET: &str = "CONFIG_RESET";

/// Görünüm (FAZ9_APP_UI K-UI-1): sade görünüm varsayılandır; ayrıntılı görünüm eski arayüzdür (aynen).
pub const UI_SADE: &str = "SADE";
pub const UI_AYRINTILI: &str = "AYRINTILI";
pub const UI_VIEWS: [&str; 2] = [UI_SADE, UI_AYRINTILI];

fn default_ui_view() -> String {
    UI_SADE.into()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AppConfig {
    pub schema_version: String,
    pub repo_root: Option<String>,
    pub python_path: Option<String>,
    pub scores_source: String,
    /// Geriye uyumlu ek alan (şema sürümü aynı): yoksa `SADE`; eski config dosyaları aynen okunur.
    #[serde(default = "default_ui_view")]
    pub ui_view: String,
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            schema_version: CONFIG_SCHEMA.into(),
            repo_root: None,
            python_path: None,
            scores_source: "REPO".into(),
            ui_view: default_ui_view(),
        }
    }
}

/// Derleme anındaki repo kökü (bu kaynak ağacı); Ayarlar'da öneri olarak ve senaryo yol korumasında.
pub fn build_repo_root() -> Option<PathBuf> {
    canonical(Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/../.."))).ok()
}

/// Dosya yoksa varsayılan. Ayrıştırılamayan ya da sürümü farklı dosya `config.json.bak` olarak
/// saklanır ve varsayılana dönülür (§2.5); ikinci değer bu durumun notudur.
pub fn load_config(data_dir: &Path) -> (AppConfig, Option<String>) {
    let path = data_dir.join(CONFIG_FILE);
    let Ok(bytes) = std::fs::read(&path) else {
        return (AppConfig::default(), None);
    };
    let parsed: Option<AppConfig> = serde_json::from_slice::<Value>(&bytes)
        .ok()
        .filter(|v| v.get("schema_version").and_then(Value::as_str) == Some(CONFIG_SCHEMA))
        .and_then(|v| serde_json::from_value(v).ok());
    match parsed {
        Some(mut c) if SCORES_SOURCES.contains(&c.scores_source.as_str()) => {
            // tanınmayan görünüm değeri ayarı sıfırlamaz: varsayılan görünüme döner (K-UI-1)
            if !UI_VIEWS.contains(&c.ui_view.as_str()) {
                c.ui_view = default_ui_view();
            }
            (c, None)
        }
        _ => {
            let _ = std::fs::rename(&path, data_dir.join("config.json.bak"));
            (AppConfig::default(), Some(CONFIG_RESET.into()))
        }
    }
}

pub fn save_config(data_dir: &Path, cfg: &AppConfig) -> Result<(), AppError> {
    std::fs::create_dir_all(data_dir).map_err(|e| io_error("uygulama verisi dizini", e))?;
    let mut text = serde_json::to_string_pretty(cfg).map_err(|e| io_error("config", e))?;
    text.push('\n');
    let tmp = data_dir.join("config.json.tmp");
    std::fs::write(&tmp, text).map_err(|e| io_error("config yazılamadı", e))?;
    std::fs::rename(&tmp, data_dir.join(CONFIG_FILE)).map_err(|e| io_error("config yazılamadı", e))
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Check {
    pub id: &'static str,
    pub ok: bool,
    /// false: yalnız bilgi (repo modunu kapatmaz).
    pub required: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RepoCheck {
    pub repo_root: String,
    pub python_path: String,
    pub ok: bool,
    pub checks: Vec<Check>,
    pub git_head: Option<String>,
    /// Derin doğrulamada: `{xu100_last, calendar_last, xu100_sha256}`.
    pub market20_sources: Option<Value>,
}

impl RepoCheck {
    pub fn data_dir_inside_repo(&self) -> bool {
        self.checks.iter().any(|c| c.id == "DATA_DIR_OUTSIDE_REPO" && !c.ok)
    }
}

/// Repo içindeki `.venv` yorumlayıcısı (FAZ9_WINDOWS K-WIN-1): Windows'ta `.venv\Scripts\python.exe`, öbür sistemlerde
/// `.venv/bin/python`.
pub fn default_python(repo: &Path) -> PathBuf {
    if cfg!(windows) {
        repo.join(".venv").join("Scripts").join("python.exe")
    } else {
        repo.join(".venv").join("bin").join("python")
    }
}

/// Windows'ta `canonicalize` yolu verbatim önekle döndürür (`\\?\C:\…`, `\\?\UNC\sunucu\pay\…`); aynı yolun öneksiz
/// yazımıyla `starts_with` yanlış `false` verir (FAZ9_WINDOWS K-WIN-3). Karşılaştırılan iki taraf da bu biçime getirilir:
/// verbatim disk ve UNC öneki düz yazıma çevrilir, öbür bileşenler aynen kalır. Windows dışında yol aynen döner.
pub fn plain_path(p: PathBuf) -> PathBuf {
    if cfg!(windows) {
        if let Some(s) = p.to_str().and_then(strip_verbatim_prefix) {
            return PathBuf::from(s);
        }
    }
    p
}

/// `\\?\C:\a` → `C:\a`; `\\?\UNC\sunucu\pay\a` → `\\sunucu\pay\a`; başka her yazım `None` (aynen kalır).
pub fn strip_verbatim_prefix(s: &str) -> Option<String> {
    if let Some(rest) = s.strip_prefix(r"\\?\UNC\") {
        return Some(format!(r"\\{rest}"));
    }
    let rest = s.strip_prefix(r"\\?\")?;
    let b = rest.as_bytes();
    let disk = b.len() >= 2 && b[0].is_ascii_alphabetic() && b[1] == b':' && (b.len() == 2 || b[2] == b'\\');
    disk.then(|| rest.to_string())
}

/// `canonicalize` + `plain_path`: diskteki ad, karşılaştırılabilir biçimde.
pub fn canonical(p: &Path) -> std::io::Result<PathBuf> {
    p.canonicalize().map(plain_path)
}

/// `a` fiziksel olarak `b`'nin altında mı (ya da eşit mi)? İki yol da `resolve_path` ile çözülür.
pub fn is_within(a: &Path, b: &Path) -> bool {
    resolve_path(a).starts_with(resolve_path(b))
}

/// Sembolik bağ sınırı: döngüde ya da çok uzun zincirde bağ daha fazla izlenmez (OS de ELOOP verir).
const MAX_LINKS: usize = 40;

/// Yolun fiziksel karşılığı (U27 yol bekçisi). Bileşenler soldan sağa yürünür: sembolik bağ —
/// hedefi olmayan (askıda) bağ dahil — `read_link` ile izlenir; `..` o ana dek çözülmüş fiziksel yolun
/// son bileşenini atar (var olmayan kuyrukta sözcüksel); var olmayan kuyruk olduğu gibi eklenir. Sonra
/// en yakın var olan ata `canonicalize` ile diskteki adına (büyük/küçük harf) çevrilir.
///
/// `canonicalize` tek başına yetmez: askıda bağda ya da var olmayan ara dizinli `..`'da en yakın var
/// olan ataya düşer ve bağın gösterdiği yeri görmez (FAZ3_APP_AUDIT B1).
///
/// Windows (FAZ9_WINDOWS K-WIN-3): sürücü/UNC öneki korunur (kök, son önekin kökü olur) ve sonuç `plain_path` biçimindedir;
/// unix'te önek bileşeni yoktur, kök `/`'dur ve davranış aynıdır.
pub fn resolve_path(p: &Path) -> PathBuf {
    use std::path::Component;
    enum Part {
        Prefix(std::ffi::OsString),
        Root,
        Parent,
        Name(std::ffi::OsString),
    }
    // Sonraki bileşen yığının SONUNDA durur.
    fn push_parts(stack: &mut Vec<Part>, p: &Path) {
        let parts: Vec<Part> = p
            .components()
            .filter_map(|c| match c {
                Component::Prefix(pre) => Some(Part::Prefix(plain_path(PathBuf::from(pre.as_os_str())).into_os_string())),
                Component::RootDir => Some(Part::Root),
                Component::CurDir => None,
                Component::ParentDir => Some(Part::Parent),
                Component::Normal(n) => Some(Part::Name(n.to_os_string())),
            })
            .collect();
        stack.extend(parts.into_iter().rev());
    }
    let abs = if p.is_absolute() { p.to_path_buf() } else { std::env::current_dir().unwrap_or_default().join(p) };
    let mut stack = Vec::new();
    push_parts(&mut stack, &abs);
    let mut prefix = std::ffi::OsString::new();
    let mut out = PathBuf::from("/");
    let mut links = 0;
    while let Some(part) = stack.pop() {
        match part {
            Part::Prefix(pre) => {
                prefix = pre;
                out = PathBuf::from(&prefix);
            }
            Part::Root => {
                let mut root = prefix.clone();
                root.push(std::path::MAIN_SEPARATOR_STR);
                out = PathBuf::from(root);
            }
            Part::Parent => {
                out.pop();
            }
            Part::Name(name) => {
                let next = out.join(&name);
                let is_link = std::fs::symlink_metadata(&next).is_ok_and(|m| m.file_type().is_symlink());
                match std::fs::read_link(&next) {
                    // bağın hedefi `out`'a (bağın dizinine) göre çözülür; mutlak hedef kökten başlar
                    Ok(target) if is_link && links < MAX_LINKS => {
                        links += 1;
                        push_parts(&mut stack, &target);
                    }
                    _ => out = next,
                }
            }
        }
    }
    // en yakın var olan ata kanonik (diskteki ad), kalanı olduğu gibi
    let mut cur = out.clone();
    let mut rest: Vec<std::ffi::OsString> = Vec::new();
    loop {
        if let Ok(c) = canonical(&cur) {
            return rest.into_iter().rev().fold(c, |acc, part| acc.join(part));
        }
        match (cur.file_name().map(|s| s.to_os_string()), cur.parent()) {
            (Some(name), Some(parent)) => {
                rest.push(name);
                cur = parent.to_path_buf();
            }
            _ => return plain_path(out),
        }
    }
}

const PY_IMPORT: &str = "import borsai, os; print(os.path.realpath(borsai.__file__))";
const PY_MARKET20_SOURCES: &str = "import json; from borsai import market20 as m; cal,recs,sha=m.load_live_sources(); \
print(json.dumps({'xu100_last': max(r.date for r in recs), 'calendar_last': cal.last_date, 'xu100_sha256': sha}))";

pub fn validate_repo_value(
    path: &str,
    python: Option<&str>,
    embedded_index_sha: &str,
    data_dir: Option<&Path>,
    deep: bool,
) -> RepoCheck {
    let mut checks = Vec::new();
    let mut push = |id: &'static str, ok: bool, required: bool, detail: String| checks.push(Check { id, ok, required, detail });
    let repo = canonical(Path::new(path)).ok().filter(|p| p.is_dir());
    let python_path = match (python.filter(|p| !p.trim().is_empty()), &repo) {
        (Some(p), _) => PathBuf::from(p),
        (None, Some(r)) => default_python(r),
        (None, None) => default_python(Path::new(path)),
    };
    let mut git_head = None;
    let mut market20_sources = None;
    match &repo {
        None => push("REPO_DIR", false, true, path.to_string()),
        Some(repo) => {
            push("REPO_DIR", true, true, repo.display().to_string());
            let inside = data_dir.is_some_and(|d| is_within(d, repo));
            push("DATA_DIR_OUTSIDE_REPO", !inside, true, data_dir.map(|d| d.display().to_string()).unwrap_or_default());
            match std::fs::read(repo.join("models").join("INDEX.json")) {
                Ok(b) => {
                    let sha = sha256_hex(&b);
                    push("INDEX_SHA", sha == embedded_index_sha, true, sha);
                }
                Err(e) => push("INDEX_SHA", false, true, e.to_string()),
            }
            match git_readonly(repo, &["rev-parse", "HEAD"]) {
                Ok(h) => {
                    git_head = Some(h.trim().to_string());
                    push("GIT_HEAD", true, true, h.trim().to_string());
                }
                Err(e) => push("GIT_HEAD", false, true, e.detail.unwrap_or(e.message)),
            }
            match run_python(&python_path, repo, &["-c", PY_IMPORT]) {
                Ok(out) => {
                    let file = plain_path(PathBuf::from(out.trim()));
                    push("PYTHON_IMPORT", file.starts_with(repo), true, out.trim().to_string());
                }
                Err(e) => push("PYTHON_IMPORT", false, true, e.detail.unwrap_or(e.message)),
            }
            let outcomes = repo.join("data").join("outcomes");
            push("OUTCOMES_DIR", outcomes.is_dir(), false, outcomes.display().to_string());
            // EK 3 §3.5: repo modunda TÜFE tablosu her tahminde buradan okunur; son ay ve pin (yalnız bilgi)
            let pins = super::predict::embedded_deflator_pins();
            if !pins.is_empty() {
                let st = super::predict::tufe_status(&super::predict::tufe_source_repo(repo), pins);
                let pin_ok = st.valid && st.pins.iter().all(|p| p.ok);
                let detail = match (&st.through_month, &st.error) {
                    (Some(m), _) => format!("{m} {}", if pin_ok { "✓" } else { "✗" }),
                    (None, Some(e)) => e.clone(),
                    _ => String::new(),
                };
                push("TUFE_TABLE", pin_ok, false, detail);
            }
            if deep {
                match run_python(&python_path, repo, &["-c", PY_MARKET20_SOURCES]) {
                    Ok(out) => match serde_json::from_str::<Value>(out.trim()) {
                        Ok(v) => {
                            push("MARKET20_SOURCES", true, false, out.trim().to_string());
                            market20_sources = Some(v);
                        }
                        Err(e) => push("MARKET20_SOURCES", false, false, e.to_string()),
                    },
                    Err(e) => push("MARKET20_SOURCES", false, false, e.detail.unwrap_or(e.message)),
                }
            }
        }
    }
    let ok = checks.iter().all(|c| c.ok || !c.required);
    RepoCheck {
        repo_root: repo.map(|r| r.display().to_string()).unwrap_or_else(|| path.to_string()),
        python_path: python_path.display().to_string(),
        ok,
        checks,
        git_head,
        market20_sources,
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ConfigView {
    pub config: AppConfig,
    /// `CONFIG_RESET`: eski/bozuk dosya config.json.bak olarak saklandı.
    pub config_note: Option<String>,
    pub repo: Option<RepoCheck>,
    pub repo_mode: bool,
    pub data_dir: Option<String>,
    pub suggested_repo_root: Option<String>,
    /// Kişisel modda gömülü sicil anlık görüntüsünün künyesi (FAZ9_SNAPSHOT K-SNAP-2); repo modunda alan yok.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snapshot: Option<super::registry_snapshot::SnapshotInfo>,
}

pub fn config_view(state: &AppState) -> ConfigView {
    let rt = state.runtime.lock().expect("runtime kilidi");
    let repo_mode = rt.repo.as_ref().is_some_and(|r| r.ok);
    ConfigView {
        config: rt.config.clone(),
        config_note: rt.config_note.clone(),
        repo: rt.repo.clone(),
        repo_mode,
        data_dir: rt.data_dir.as_ref().map(|d| d.display().to_string()),
        suggested_repo_root: build_repo_root().map(|p| p.display().to_string()),
        snapshot: (!repo_mode).then(|| super::registry_snapshot::info(rt.snapshot.as_ref())),
    }
}

/// Ayar kaydı: biçim denetimi, repo doğrulaması; uygulama verisi repo altına düşüyorsa ret (U27).
/// Diğer denetimler başarısızsa ayar yine kaydedilir, repo modu kapalı kalır (gerekçeler görünür).
pub fn set_config_value(state: &AppState, mut cfg: AppConfig) -> Result<ConfigView, AppError> {
    if cfg.schema_version != CONFIG_SCHEMA {
        return Err(AppError::new(INVALID_ARGUMENT, format!("schema_version {CONFIG_SCHEMA} olmalı")));
    }
    if !SCORES_SOURCES.contains(&cfg.scores_source.as_str()) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("scores_source {:?}", cfg.scores_source)));
    }
    if !UI_VIEWS.contains(&cfg.ui_view.as_str()) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("ui_view {:?}", cfg.ui_view)));
    }
    cfg.repo_root = cfg.repo_root.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    cfg.python_path = cfg.python_path.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    let data_dir = state.data_dir()?;
    let repo = cfg.repo_root.as_deref().map(|r| {
        validate_repo_value(r, cfg.python_path.as_deref(), &state.embedded_index_sha(), Some(&data_dir), false)
    });
    if repo.as_ref().is_some_and(RepoCheck::data_dir_inside_repo) {
        return Err(AppError::new(DATA_DIR_INSIDE_REPO, "uygulama verisi repo altında olamaz"));
    }
    save_config(&data_dir, &cfg)?;
    {
        let mut rt = state.runtime.lock().expect("runtime kilidi");
        rt.config = cfg;
        rt.config_note = None;
        rt.repo = repo;
    }
    Ok(config_view(state))
}

/// Yalnız görünüm seçimini değiştirir (K-UI-1); öbür alanlar ve repo doğrulaması aynen kalır.
pub fn set_ui_view_value(state: &AppState, view: &str) -> Result<ConfigView, AppError> {
    if !UI_VIEWS.contains(&view) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("ui_view {view:?}")));
    }
    let data_dir = state.data_dir()?;
    let mut cfg = state.runtime.lock().expect("runtime kilidi").config.clone();
    cfg.ui_view = view.to_string();
    save_config(&data_dir, &cfg)?;
    state.runtime.lock().expect("runtime kilidi").config = cfg;
    Ok(config_view(state))
}

#[tauri::command]
pub fn set_ui_view(state: tauri::State<'_, AppState>, view: String) -> Result<ConfigView, AppError> {
    set_ui_view_value(&state, &view)
}

#[tauri::command]
pub fn get_config(state: tauri::State<'_, AppState>) -> Result<ConfigView, AppError> {
    Ok(config_view(&state))
}

#[tauri::command]
pub async fn set_config(state: tauri::State<'_, AppState>, cfg: AppConfig) -> Result<ConfigView, AppError> {
    set_config_value(&state, cfg)
}

/// Kaydetmeden derin doğrulama (Ayarlar ekranı "Doğrula").
#[tauri::command]
pub async fn validate_repo(
    state: tauri::State<'_, AppState>,
    path: String,
    python_path: Option<String>,
) -> Result<RepoCheck, AppError> {
    let data_dir = state.data_dir().ok();
    Ok(validate_repo_value(&path, python_path.as_deref(), &state.embedded_index_sha(), data_dir.as_deref(), true))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// K-WIN-1: repo içindeki `.venv` yorumlayıcısı işletim sistemine göre.
    #[test]
    fn default_python_per_os() {
        let p = default_python(Path::new("repo"));
        if cfg!(windows) {
            assert_eq!(p, Path::new("repo").join(".venv").join("Scripts").join("python.exe"));
        } else {
            assert_eq!(p, Path::new("repo/.venv/bin/python"));
        }
    }

    /// K-WIN-3: verbatim önek soyma metin düzeyinde (her sistemde koşar); Windows dışında `plain_path` yolu aynen döndürür.
    #[test]
    fn strip_verbatim_prefix_forms() {
        assert_eq!(strip_verbatim_prefix(r"\\?\C:\a\b").as_deref(), Some(r"C:\a\b"));
        assert_eq!(strip_verbatim_prefix(r"\\?\c:").as_deref(), Some("c:"));
        assert_eq!(strip_verbatim_prefix(r"\\?\UNC\srv\pay\a").as_deref(), Some(r"\\srv\pay\a"));
        for s in [r"C:\a", r"\\srv\pay\a", r"\\?\Volume{x}\a", r"\\?\C:a", r"\\?\1:\a", "/tmp/a", ""] {
            assert_eq!(strip_verbatim_prefix(s), None, "{s}");
        }
        if !cfg!(windows) {
            assert_eq!(plain_path(PathBuf::from(r"\\?\C:\a")), PathBuf::from(r"\\?\C:\a"));
            assert_eq!(plain_path(PathBuf::from("/tmp/a")), PathBuf::from("/tmp/a"));
        }
    }

    /// K-WIN-3 (yalnız Windows): `\\?\C:\a\b` ile `C:\a` aynı ağaçta sayılır; sürücü öneki korunur (`D:` ≠ `C:`);
    /// gerçek `canonicalize` verbatim döndürür, `canonical` ve `is_within` yine tutar.
    #[cfg(windows)]
    #[test]
    fn is_within_verbatim_prefix_windows() {
        assert!(is_within(Path::new(r"\\?\C:\a\b"), Path::new(r"C:\a")));
        assert!(is_within(Path::new(r"C:\a\b"), Path::new(r"\\?\C:\a")));
        assert!(is_within(Path::new(r"\\?\C:\a"), Path::new(r"c:\a")));
        assert!(!is_within(Path::new(r"\\?\C:\ab"), Path::new(r"C:\a")));
        assert!(!is_within(Path::new(r"D:\a\b"), Path::new(r"C:\a")));
        assert_eq!(plain_path(PathBuf::from(r"\\?\C:\a\b")), PathBuf::from(r"C:\a\b"));
        let tmp = std::env::temp_dir();
        let verbatim = tmp.canonicalize().unwrap();
        assert!(verbatim.to_string_lossy().starts_with(r"\\?\"), "{}", verbatim.display());
        assert!(!canonical(&tmp).unwrap().to_string_lossy().starts_with(r"\\?\"));
        assert!(is_within(&tmp.join("borsai_win_verbatim").join("x.json"), &verbatim));
        assert!(is_within(&verbatim.join("y"), &tmp));
    }
}
