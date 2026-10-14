//! Sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-1..5). Kişisel modda (repo doğrulanmamışken) Monitör, Analiz, Sicil ve
//! Performans ekranları resmi sicilin derlemeye gömülü SALT OKUNUR kopyasından okur; görünüm fonksiyonları aynıdır, yalnız
//! `repo` parametresine anlık görüntü dizini verilir.
//!
//! - Gömülü kopya manifestle doğrulanır: her dosyanın yolu, sha256'sı ve bayt sayısı manifest satırıyla, manifestin sha'sı
//!   derleme bilgisiyle. Tek uyuşmazlıkta `SNAPSHOT_INTEGRITY_FAILED`; ekranlar boş kalır (kısmi gösterim yok).
//! - Üretim: `<app_data_dir>/snapshot/<derleme sha7>/` altına repo içi göreli yollarla (`Path::join`). Dizin varsa ağaç
//!   manifestle birebir mi diye bakılır (eksik ya da fazla dosya/dizin, bağ, sha); tutmazsa silinir, geçici dizine yeniden
//!   yazılır, doğrulanır ve yerine taşınır. Yazılan ağaç da tutmazsa `SNAPSHOT_INTEGRITY_FAILED`. Hedef korunan bir kökün
//!   (repo) altına düşüyorsa hiçbir şey yazılmaz.
//! - Okuma: her okuma komutu dizini yeniden doğrular, yazmaz (`verify_tree`).
//! - Yazma komutları (dondur, D1 sonrası, girdi belgesi, kaynak belgeler) anlık görüntüyü görmez: `require_repo` onlarda aynen.
//!   Kişisel kayıtlar anlık görüntü dizinine yazılamaz (`scenario`); anlık görüntü repo kökü sayılmaz.
//! - Anlık görüntüde git çağrılmaz: tahmin kaydını ekleyen commit ve `git status` derleme anında dondurulmuştur (`frozen_git`).
use serde::Serialize;
use std::collections::BTreeSet;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use super::config::is_within;
use super::models::sha256_hex;
use super::AppError;
use crate::embedded::{self, SnapshotFile};

pub const SNAPSHOT_INTEGRITY_FAILED: &str = "SNAPSHOT_INTEGRITY_FAILED";
/// `<app_data_dir>` altındaki anlık görüntü kökü (ayrılmış ad).
pub const SNAPSHOT_DIR: &str = "snapshot";
/// Anlık görüntü dizininin kökündeki manifest kopyası (derleme bilgisindeki metinle bayt bayt aynı).
pub const MANIFEST_FILE: &str = "SNAPSHOT_MANIFEST.tsv";

/// READY: yazıldı ve doğrulandı · PENDING: bu oturumda henüz yazılmadı (ilk okumada yazılır) · FAILED: doğrulanamadı ·
/// NONE: derlemede anlık görüntü dosyası yok.
pub const STATUS_READY: &str = "READY";
pub const STATUS_PENDING: &str = "PENDING";
pub const STATUS_FAILED: &str = "FAILED";
pub const STATUS_NONE: &str = "NONE";

/// Ekranların gösterdiği künye (K-SNAP-3): kaynak, derleme ve son sonuç tarihi.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SnapshotInfo {
    pub status: &'static str,
    /// FAILED iken `SNAPSHOT_INTEGRITY_FAILED`.
    pub code: Option<&'static str>,
    pub detail: Option<String>,
    /// Derleme HEAD'inin ilk 7 hanesi (dizin adı).
    pub build_sha7: String,
    /// Derleme anında anlık görüntü yollarında commit bekleyen değişiklik vardı (`git status` boş değil; git yoksa bilinmez → false).
    pub build_dirty: bool,
    pub manifest_sha256: &'static str,
    pub n_files: usize,
    pub bytes: u64,
    /// `data/outcomes/*.csv` içindeki en geç seans (`session_date`).
    pub last_session: Option<String>,
}

fn fail(msg: impl Into<String>) -> AppError {
    AppError::new(SNAPSHOT_INTEGRITY_FAILED, msg)
}

/// Taşınabilir yol bileşeni (`build_embed::portable_name` ile aynı kural): `[A-Za-z0-9._-]+`, `.` ve `..` değil.
fn portable(c: &str) -> bool {
    !c.is_empty() && c != "." && c != ".." && c.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
}

/// Göreli yol (`/` ayırıcılı) → `base` altında yol; bileşenlerden biri taşınabilir değilse `None`.
pub fn rel_path(base: &Path, rel: &str) -> Option<PathBuf> {
    let parts: Vec<&str> = rel.split('/').collect();
    parts.iter().all(|c| portable(c)).then(|| parts.iter().fold(base.to_path_buf(), |p, c| p.join(c)))
}

/// Derleme HEAD'inin ilk 7 hanesi; HEAD bilinmiyorsa manifest sha'sının ilk 7 hanesi (dizin adı yine içeriğe bağlı kalır).
pub fn build_sha7() -> String {
    let head = embedded::BUILD_INFO.git_head;
    if head.len() >= 7 && head.bytes().all(|b| b.is_ascii_hexdigit()) {
        head[..7].to_string()
    } else {
        embedded::BUILD_INFO.snapshot_manifest_sha256.chars().take(7).collect()
    }
}

/// Gömülü kopyanın bütünlüğü: manifest sha'sı = derleme bilgisi; dosyalar manifest satırlarıyla aynı sırada, aynı yol,
/// sha256 ve bayt sayısında; yollar taşınabilir ve tekil.
pub fn verify_embedded(manifest: &str, manifest_sha: &str, files: &[SnapshotFile]) -> Result<(), AppError> {
    if sha256_hex(manifest.as_bytes()) != manifest_sha {
        return Err(fail("anlık görüntü manifesti derleme bilgisiyle uyuşmuyor"));
    }
    let rows: Vec<&str> = manifest.lines().collect();
    if rows.len() != files.len() {
        return Err(fail(format!("manifest {} satır, gömülü {} dosya", rows.len(), files.len())));
    }
    let mut seen = BTreeSet::new();
    for (row, f) in rows.iter().zip(files) {
        let want = format!("{}\t{}\t{}", f.rel, sha256_hex(f.bytes), f.bytes.len());
        if *row != want || f.sha256 != sha256_hex(f.bytes) {
            return Err(fail(format!("{}: gömülü dosya manifestle uyuşmuyor", f.rel)));
        }
        if rel_path(Path::new(""), f.rel).is_none() || !seen.insert(f.rel) {
            return Err(fail(format!("{}: geçersiz ya da yinelenen yol", f.rel)));
        }
    }
    Ok(())
}

/// Dizindeki ağaç manifestle birebir mi: beklenen dosyalar (+ kökteki manifest kopyası) ve onların üst dizinleri dışında
/// hiçbir şey yok; sembolik bağ yok; her dosyanın sha256'sı manifestteki gibi. Yazmaz.
pub fn verify_tree(dir: &Path, files: &[SnapshotFile], manifest: &str) -> Result<(), String> {
    let meta = std::fs::symlink_metadata(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    if !meta.is_dir() || meta.file_type().is_symlink() {
        return Err(format!("{} dizin değil", dir.display()));
    }
    let mut want_files: BTreeSet<String> = files.iter().map(|f| f.rel.to_string()).collect();
    want_files.insert(MANIFEST_FILE.to_string());
    let want_dirs: BTreeSet<String> = want_files
        .iter()
        .flat_map(|r| {
            let parts: Vec<&str> = r.split('/').collect();
            (1..parts.len()).map(move |i| parts[..i].join("/"))
        })
        .collect();
    let (mut got_files, mut got_dirs) = (BTreeSet::new(), BTreeSet::new());
    walk(dir, "", &mut got_files, &mut got_dirs)?;
    if got_files != want_files || got_dirs != want_dirs {
        let extra: Vec<&String> = got_files.difference(&want_files).chain(got_dirs.difference(&want_dirs)).collect();
        let missing: Vec<&String> = want_files.difference(&got_files).collect();
        return Err(format!("ağaç manifestle aynı değil: fazla {extra:?}, eksik {missing:?}"));
    }
    for f in files {
        let p = rel_path(dir, f.rel).ok_or_else(|| format!("{}: geçersiz yol", f.rel))?;
        let bytes = std::fs::read(&p).map_err(|e| format!("{}: {e}", f.rel))?;
        if bytes.len() != f.bytes.len() || sha256_hex(&bytes) != f.sha256 {
            return Err(format!("{}: sha256 manifestle uyuşmuyor", f.rel));
        }
    }
    let m = std::fs::read(dir.join(MANIFEST_FILE)).map_err(|e| format!("{MANIFEST_FILE}: {e}"))?;
    if m != manifest.as_bytes() {
        return Err(format!("{MANIFEST_FILE} gömülü manifestle aynı değil"));
    }
    Ok(())
}

fn walk(dir: &Path, rel: &str, files: &mut BTreeSet<String>, dirs: &mut BTreeSet<String>) -> Result<(), String> {
    for e in std::fs::read_dir(dir).map_err(|e| format!("{}: {e}", dir.display()))? {
        let e = e.map_err(|e| e.to_string())?;
        let name = e.file_name().to_string_lossy().to_string();
        let child = if rel.is_empty() { name } else { format!("{rel}/{name}") };
        let ft = e.file_type().map_err(|e| e.to_string())?;
        if ft.is_symlink() {
            return Err(format!("{child}: sembolik bağ"));
        } else if ft.is_dir() {
            dirs.insert(child.clone());
            walk(&e.path(), &child, files, dirs)?;
        } else if ft.is_file() {
            files.insert(child);
        } else {
            return Err(format!("{child}: dosya değil"));
        }
    }
    Ok(())
}

fn write_tree(dir: &Path, files: &[SnapshotFile], manifest: &str) -> Result<(), String> {
    std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let write_new = |p: &Path, bytes: &[u8]| -> Result<(), String> {
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        // yeni dizin: var olan dosya (ya da bağ) izlenmez, üzerine yazılmaz
        let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(p).map_err(|e| format!("{}: {e}", p.display()))?;
        f.write_all(bytes).map_err(|e| format!("{}: {e}", p.display()))
    };
    for f in files {
        write_new(&rel_path(dir, f.rel).ok_or_else(|| format!("{}: geçersiz yol", f.rel))?, f.bytes)?;
    }
    write_new(&dir.join(MANIFEST_FILE), manifest.as_bytes())
}

/// Bağı izlemeden siler (dizin: içiyle; bağ ya da dosya: yalnız kendisi). Yoksa bir şey yapmaz.
fn remove_any(p: &Path) -> Result<(), String> {
    match std::fs::symlink_metadata(p) {
        Err(_) => Ok(()),
        Ok(m) if m.is_dir() && !m.file_type().is_symlink() => std::fs::remove_dir_all(p).map_err(|e| format!("{}: {e}", p.display())),
        Ok(_) => std::fs::remove_file(p).map_err(|e| format!("{}: {e}", p.display())),
    }
}

/// Anlık görüntüyü `<data_dir>/snapshot/<sha7>/` altına üretir (K-SNAP-2): varsa doğrular; tutmazsa siler, geçici dizine
/// yazar, doğrular ve yerine taşır. `protected`: korunan kökler (repo); hedef bunlardan birinin altındaysa hiçbir şey yazılmaz.
pub fn materialize(
    data_dir: &Path,
    protected: &[PathBuf],
    sha7: &str,
    files: &[SnapshotFile],
    manifest: &str,
) -> Result<PathBuf, AppError> {
    if !portable(sha7) {
        return Err(fail(format!("dizin adı geçersiz: {sha7:?}")));
    }
    let base = data_dir.join(SNAPSHOT_DIR);
    let dir = base.join(sha7);
    if let Some(root) = protected.iter().find(|r| is_within(&dir, r)) {
        return Err(fail(format!("{} korunan kök altında: {}", dir.display(), root.display())));
    }
    // kök bağsa (uygulama verisinin ayrılmış adı) yalnız bağ kaldırılır, gerçek dizin açılır
    if std::fs::symlink_metadata(&base).is_ok_and(|m| !m.is_dir() || m.file_type().is_symlink()) {
        remove_any(&base).map_err(fail)?;
    }
    if verify_tree(&dir, files, manifest).is_ok() {
        return Ok(dir);
    }
    let tmp = base.join(format!("{sha7}.tmp{}", std::process::id()));
    remove_any(&tmp).map_err(fail)?;
    write_tree(&tmp, files, manifest).map_err(fail)?;
    verify_tree(&tmp, files, manifest).map_err(fail)?;
    remove_any(&dir).map_err(fail)?;
    if let Err(e) = std::fs::rename(&tmp, &dir) {
        // eşzamanlı ikinci açılış aynı dizini yazmış olabilir: doğrulanıyorsa kullanılır
        let _ = remove_any(&tmp);
        verify_tree(&dir, files, manifest).map_err(|v| fail(format!("{e}; {v}")))?;
    }
    verify_tree(&dir, files, manifest).map_err(fail)?;
    Ok(dir)
}

/// Gömülü kopyanın doğrulanıp üretilmesi (açılış ya da oturum içinde kişisel moda geçildikten sonraki ilk okuma).
pub fn prepare(data_dir: &Path, protected: &[PathBuf]) -> Result<PathBuf, AppError> {
    let b = embedded::BUILD_INFO;
    verify_embedded(b.snapshot_manifest, b.snapshot_manifest_sha256, embedded::SNAPSHOT_FILES)?;
    materialize(data_dir, protected, &build_sha7(), embedded::SNAPSHOT_FILES, b.snapshot_manifest)
}

/// Okuma öncesi doğrulama (yazmaz).
pub fn verify_dir(dir: &Path) -> Result<(), AppError> {
    verify_tree(dir, embedded::SNAPSHOT_FILES, embedded::BUILD_INFO.snapshot_manifest).map_err(fail)
}

/// `data/outcomes/*.csv` içindeki en geç `session_date` (sütunu olmayan dosya, ör. tamlık listesi, sayılmaz).
pub fn last_session(files: &[SnapshotFile]) -> Option<String> {
    files
        .iter()
        .filter(|f| f.rel.strip_prefix("data/outcomes/").is_some_and(|n| !n.contains('/') && n.ends_with(".csv")))
        .filter_map(|f| {
            let text = std::str::from_utf8(f.bytes).ok()?;
            let mut lines = text.lines();
            let col = lines.next()?.trim_start_matches('\u{feff}').split(',').position(|h| h == "session_date")?;
            lines.filter_map(|l| l.split(',').nth(col).filter(|s| !s.is_empty()).map(str::to_string)).max()
        })
        .max()
}

fn embedded_last_session() -> Option<String> {
    static LAST: std::sync::OnceLock<Option<String>> = std::sync::OnceLock::new();
    LAST.get_or_init(|| last_session(embedded::SNAPSHOT_FILES)).clone()
}

/// Künye: `slot` bu oturumdaki üretim sonucu (`None`: henüz üretilmedi).
pub fn info(slot: Option<&Result<PathBuf, AppError>>) -> SnapshotInfo {
    let files = embedded::SNAPSHOT_FILES;
    let b = embedded::BUILD_INFO;
    let (status, code, detail) = match slot {
        _ if files.is_empty() => (STATUS_NONE, None, None),
        None => (STATUS_PENDING, None, None),
        Some(Ok(_)) => (STATUS_READY, None, None),
        Some(Err(e)) => (STATUS_FAILED, Some(SNAPSHOT_INTEGRITY_FAILED), Some(e.message.clone())),
    };
    SnapshotInfo {
        status,
        code,
        detail,
        build_sha7: build_sha7(),
        build_dirty: !matches!(b.git_status_snapshot.trim(), "" | "UNKNOWN"),
        manifest_sha256: b.snapshot_manifest_sha256,
        n_files: files.len(),
        bytes: files.iter().map(|f| f.bytes.len() as u64).sum(),
        last_session: embedded_last_session(),
    }
}

/// Derleme anının git bilgisi (anlık görüntüde git çağrılmaz).
#[derive(Debug, Clone, Copy)]
pub struct FrozenGit {
    /// (izlenen tahmin kaydının göreli yolu, kaydı ekleyen commit; bulunamadıysa boş).
    pub records: &'static [(&'static str, &'static str)],
    /// `git status --porcelain -- <anlık görüntü yolları>`.
    pub status: &'static str,
}

impl FrozenGit {
    /// `git ls-files -- registry/records` karşılığı.
    pub fn tracked(&self) -> BTreeSet<String> {
        self.records.iter().map(|(r, _)| r.to_string()).collect()
    }

    /// `git log --diff-filter=A --format=%H -1 -- <rel>` karşılığı.
    pub fn added_commit(&self, rel: &str) -> Option<String> {
        self.records.iter().find(|(r, _)| *r == rel).map(|(_, c)| c.to_string()).filter(|c| !c.is_empty())
    }

    /// `git status --porcelain -- <kökler>` karşılığı: derleme anındaki satırlardan yolu bu köklerin altında olanlar
    /// (git derleme anında yoksa `UNKNOWN` aynen).
    pub fn status(&self, roots: &[&str]) -> String {
        if self.status.trim() == "UNKNOWN" {
            return self.status.to_string();
        }
        self.status
            .lines()
            .filter(|l| l.get(3..).is_some_and(|p| roots.iter().any(|r| p == *r || p.starts_with(&format!("{r}/")))))
            .map(|l| format!("{l}\n"))
            .collect()
    }
}

/// `root` bu derlemenin anlık görüntüsü mü: kökteki manifest kopyası gömülü manifestle bayt bayt aynıysa derleme anının
/// git bilgisi döner (sicil görünümü bu kökte git çağırmaz); repo'da `None`.
pub fn frozen_git(root: &Path) -> Option<FrozenGit> {
    let manifest = embedded::BUILD_INFO.snapshot_manifest;
    let bytes = std::fs::read(root.join(MANIFEST_FILE)).ok()?;
    (!embedded::SNAPSHOT_FILES.is_empty() && bytes == manifest.as_bytes())
        .then_some(FrozenGit { records: embedded::SNAPSHOT_RECORD_COMMITS, status: embedded::BUILD_INFO.git_status_snapshot })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rel_path_rejects_unsafe_components() {
        assert_eq!(rel_path(Path::new("b"), "registry/ipos.csv"), Some(Path::new("b").join("registry").join("ipos.csv")));
        for bad in ["", "a//b", "../x", "a/./b", "a\\b", "C:x", "/abs", "a b"] {
            assert_eq!(rel_path(Path::new("b"), bad), None, "{bad}");
        }
    }

    #[test]
    fn frozen_status_filters_by_root() {
        let f = FrozenGit { records: &[("registry/records/A/x.json", "abc"), ("registry/records/A/y.json", "")], status: " M registry/ipos.csv\n?? data/outcomes/A.csv\n M scores/scores_break.json\n" };
        assert_eq!(f.status(&["registry"]), " M registry/ipos.csv\n");
        assert_eq!(f.status(&["registry", "data"]), " M registry/ipos.csv\n?? data/outcomes/A.csv\n");
        assert_eq!(f.added_commit("registry/records/A/x.json").as_deref(), Some("abc"));
        assert_eq!(f.added_commit("registry/records/A/y.json"), None);
        assert_eq!(f.tracked().len(), 2);
        let u = FrozenGit { records: &[], status: "UNKNOWN" };
        assert_eq!(u.status(&["registry"]), "UNKNOWN");
    }
}
