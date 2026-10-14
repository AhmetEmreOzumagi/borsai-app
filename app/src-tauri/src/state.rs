//! Uygulama durumu: açılışta doğrulanmış gömülü model kümesi (SPEC_APP §1.4) ve çalışma zamanı
//! ayarları (uygulama verisi dizini, `borsai.app_config/1`, repo modu). Kısmi çalışma yok:
//! tek uyuşmazlıkta `INTEGRITY_FAILED` ve bütün tahmin komutları hata döner. Kişisel modda salt okunur ekranların veri
//! kökü gömülü sicil anlık görüntüsüdür (FAZ9_SNAPSHOT K-SNAP-2; `read_root`).
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use crate::commands::config::{default_python, load_config, validate_repo_value, AppConfig, RepoCheck};
use crate::commands::models::{verify_embedded, IntegrityError, VerifiedModels};
use crate::commands::registry_snapshot::{self, SnapshotInfo};
use crate::commands::{AppError, IO_ERROR, REPO_MODE_REQUIRED};
use crate::embedded;

#[derive(Debug, Default)]
pub struct Runtime {
    pub data_dir: Option<PathBuf>,
    pub config: AppConfig,
    pub config_note: Option<String>,
    pub repo: Option<RepoCheck>,
    /// YALNIZ ekran görüntüsü koşusu (`--features snapshot`): doğruluk panelinin okuyacağı sentetik
    /// `scores.json` yolu. Üretim derlemesinde hiçbir yerden doldurulmaz.
    pub scores_fixture: Option<PathBuf>,
    /// Kişisel modda sicil anlık görüntüsü (K-SNAP-2): bu oturumda üretildiyse dizini ya da doğrulama hatası; `None`: henüz
    /// üretilmedi (repo modunda hiç üretilmez).
    pub snapshot: Option<Result<PathBuf, AppError>>,
}

pub struct AppState {
    pub models: Result<Arc<VerifiedModels>, IntegrityError>,
    pub runtime: Mutex<Runtime>,
}

/// Doğrulanmış repo: kök ve Python yolu.
#[derive(Debug, Clone)]
pub struct RepoCtx {
    pub root: PathBuf,
    pub python: PathBuf,
}

/// Salt okunur ekranların veri kökü: doğrulanmış repo ya da (kişisel modda) doğrulanmış anlık görüntü dizini.
#[derive(Debug, Clone)]
pub struct DataRoot {
    pub root: PathBuf,
    /// Anlık görüntüden okunuyorsa künyesi; repo'da `None`.
    pub snapshot: Option<SnapshotInfo>,
}

impl AppState {
    pub fn from_embedded() -> Self {
        AppState {
            models: verify_embedded().map(Arc::new),
            runtime: Mutex::new(Runtime::default()),
        }
    }

    /// Uygulama verisi dizinini bağlar, ayarı okur ve (varsa) repo'yu hızlı doğrular.
    pub fn attach_data_dir(&self, data_dir: &Path) {
        let (config, note) = load_config(data_dir);
        let repo = config.repo_root.as_deref().map(|r| {
            validate_repo_value(r, config.python_path.as_deref(), &self.embedded_index_sha(), Some(data_dir), false)
        });
        let mut rt = self.runtime.lock().expect("runtime kilidi");
        *rt = Runtime { data_dir: Some(data_dir.to_path_buf()), config, config_note: note, repo, scores_fixture: None, snapshot: None };
    }

    /// Açılış (K-SNAP-2): kişisel moddaysa gömülü anlık görüntüyü `<data_dir>/snapshot/<sha7>/` altına üretir ve doğrular.
    /// Repo modunda bir şey yapmaz; bu oturumda zaten üretildiyse yeniden yazmaz.
    pub fn prepare_snapshot(&self) {
        if self.repo().is_none() {
            let mut rt = self.runtime.lock().expect("runtime kilidi");
            Self::ensure_snapshot(&mut rt);
        }
    }

    fn ensure_snapshot(rt: &mut Runtime) {
        if rt.snapshot.is_some() || embedded::SNAPSHOT_FILES.is_empty() {
            return;
        }
        let Some(data_dir) = rt.data_dir.clone() else { return };
        let mut protected: Vec<PathBuf> = rt.config.repo_root.iter().map(PathBuf::from).collect();
        protected.extend(crate::commands::config::build_repo_root());
        rt.snapshot = Some(registry_snapshot::prepare(&data_dir, &protected));
    }

    /// Salt okunur ekranların veri kökü (K-SNAP-2): doğrulanmış repo; değilse gömülü anlık görüntü dizini (bu oturumda ilk
    /// kez gerekiyorsa üretilir; her okumada yeniden doğrulanır, yazılmaz). Uygulama verisi yoksa ya da derlemede anlık
    /// görüntü yoksa `REPO_MODE_REQUIRED`; doğrulanamıyorsa `SNAPSHOT_INTEGRITY_FAILED`.
    pub fn read_root(&self) -> Result<DataRoot, AppError> {
        if let Some(r) = self.repo() {
            return Ok(DataRoot { root: r.root, snapshot: None });
        }
        let dir = {
            let mut rt = self.runtime.lock().expect("runtime kilidi");
            Self::ensure_snapshot(&mut rt);
            match &rt.snapshot {
                None => return Err(AppError::new(REPO_MODE_REQUIRED, "bu ekran repo modu ya da gömülü anlık görüntü ister")),
                Some(Err(e)) => return Err(e.clone()),
                Some(Ok(d)) => d.clone(),
            }
        };
        registry_snapshot::verify_dir(&dir)?;
        Ok(DataRoot { snapshot: Some(registry_snapshot::info(Some(&Ok(dir.clone())))), root: dir })
    }

    /// Ekran görüntüsü koşusunun sentetik skor dosyası (yoksa `None`).
    pub fn scores_fixture(&self) -> Option<PathBuf> {
        self.runtime.lock().expect("runtime kilidi").scores_fixture.clone()
    }

    pub fn set_scores_fixture(&self, path: Option<PathBuf>) {
        self.runtime.lock().expect("runtime kilidi").scores_fixture = path;
    }

    pub fn embedded_index_sha(&self) -> String {
        embedded::BUILD_INFO.index_sha256.to_string()
    }

    pub fn data_dir(&self) -> Result<PathBuf, AppError> {
        self.runtime
            .lock()
            .expect("runtime kilidi")
            .data_dir
            .clone()
            .ok_or_else(|| AppError::new(IO_ERROR, "uygulama verisi dizini çözülemedi"))
    }

    /// Doğrulanmış repo modu; değilse `None`.
    pub fn repo(&self) -> Option<RepoCtx> {
        let rt = self.runtime.lock().expect("runtime kilidi");
        let r = rt.repo.as_ref().filter(|r| r.ok)?;
        let root = PathBuf::from(&r.repo_root);
        Some(RepoCtx { python: PathBuf::from(&r.python_path), root })
    }

    pub fn require_repo(&self) -> Result<RepoCtx, AppError> {
        self.repo().ok_or_else(|| AppError::new(REPO_MODE_REQUIRED, "bu işlem repo modu ister (Ayarlar)"))
    }

    /// Kişisel kayıt yol koruması için repo kökleri: ayardaki (doğrulanmamış olsa bile) ve derleme anındaki.
    pub fn protected_roots(&self) -> Vec<PathBuf> {
        let rt = self.runtime.lock().expect("runtime kilidi");
        let mut roots: Vec<PathBuf> = rt.config.repo_root.iter().map(PathBuf::from).collect();
        roots.extend(crate::commands::config::build_repo_root());
        roots
    }

    /// Test ve e2e için: repo doğrulaması yerine hazır bağlam.
    pub fn with_repo_for_tests(self, data_dir: &Path, repo: &Path) -> Self {
        {
            let mut rt = self.runtime.lock().expect("runtime kilidi");
            rt.data_dir = Some(data_dir.to_path_buf());
            rt.config.repo_root = Some(repo.display().to_string());
            rt.repo = Some(RepoCheck {
                repo_root: repo.display().to_string(),
                python_path: default_python(repo).display().to_string(),
                ok: true,
                checks: Vec::new(),
                git_head: None,
                market20_sources: None,
            });
        }
        self
    }
}
