//! Derlemeye gömülü dosyalar (SPEC_APP §1.4; EK 3 §3.5 TÜFE tablosu, §4.1 P2 ikinci dizin; FAZ9_SNAPSHOT sicil anlık
//! görüntüsü). İçerik `build.rs` tarafından `OUT_DIR/embedded.rs` olarak üretilir; burada yalnız tipler tanımlıdır.

#[derive(Debug, Clone, Copy)]
pub struct EmbeddedModel {
    pub model_id: &'static str,
    pub file: &'static str,
    pub json: &'static str,
}

/// Sicil anlık görüntüsünün bir dosyası (FAZ9_SNAPSHOT K-SNAP-1): repo içi göreli yol (`/` ayırıcılı), sha256, baytlar.
#[derive(Debug, Clone, Copy)]
pub struct SnapshotFile {
    pub rel: &'static str,
    pub sha256: &'static str,
    pub bytes: &'static [u8],
}

#[derive(Debug, Clone, Copy)]
pub struct BuildInfo {
    /// Derleme anındaki `git rev-parse HEAD` (GIT_OPTIONAL_LOCKS=0).
    pub git_head: &'static str,
    /// Derleme anındaki `git status --porcelain -- models scores`.
    pub git_status_models_scores: &'static str,
    /// Gömülü INDEX.json baytlarının sha256'sı (build.rs'nin okuduğu).
    pub index_sha256: &'static str,
    /// Gömülü ikinci dizinin (models/INDEX_POST_D1.json; EK 3 §4.1 P2) sha256'sı.
    pub index_post_d1_sha256: &'static str,
    /// INDEX'te olup bu sürümde gömülmeyen kayıtlar (sabit 27 modelin dışı; bugün boş).
    pub ignored_index_models: &'static [&'static str],
    /// Gömülü sicil anlık görüntüsünün manifesti: satır başına `yol\tsha256\tbayt`, yol sırasıyla (K-SNAP-1).
    pub snapshot_manifest: &'static str,
    /// Manifest metninin sha256'sı.
    pub snapshot_manifest_sha256: &'static str,
    /// Derleme anındaki `git status --porcelain -- <anlık görüntü yolları>` (boşsa commit'li içerik; git yoksa `UNKNOWN`).
    pub git_status_snapshot: &'static str,
}

include!(concat!(env!("OUT_DIR"), "/embedded.rs"));
