// build.rs ile testlerin ortak kodu (SPEC_APP §1.4). build.rs bunu `include!` ile, testler
// `#[path]` ile alır. Yalnız std + serde_json + sha2.
//
// - Model kümesi açıkça sabittir: models/INDEX.json'un 27 kaydı. 17.–19. kayıtlar Faz 4 tavan-yolu modelleridir
//   (SPEC_APP EK 2 §3.5), 20.–23. Faz 7 `ceiling_hazard_v1` ailesi (EK 3 §4.1, Aşama P1), son dördü Faz 7C düşen arz
//   `fall_d10_v0` ailesi (EK 3 §4.1, Aşama P4); sıra kuralı INDEX sırası, ek her zaman sona. INDEX'te olup gömülmeyen
//   kayıtlar `ignored_model_ids`'e düşer (bugün boş). Sabit liste INDEX'in ilk 27 kaydıyla sırasıyla aynı değilse ya da
//   INDEX'te olup diskte olmayan dosya varsa derleme kırılır.
// - İkinci dizin (EK 3 §4.1, Aşama P2): models/INDEX_POST_D1.json ve kayıtları (`PINNED_POST_D1_MODEL_IDS`; bugün
//   tek giriş `post_d1_hazard_v0`). Sabit liste dizinle sırasıyla aynı değilse ya da dosya diskte yoksa derleme kırılır;
//   ebeveyn/tavan yolu zinciri açılışta `models::verify_post_d1` ile denetlenir.
// - Gömülü modellerde deflatörlü (f1r) model varsa TÜFE tablosu (`data/raw/tuik/tufe_genel_2025_100.csv`)
//   da gömülür (bağımsız modun tek kaynağı; EK 3 §3.1, §3.5); dosya yoksa derleme kırılır.
// - Sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-1): kişisel modda Monitör, Analiz, Sicil ve Performans ekranlarının okuduğu
//   resmi dosyalar (`SNAPSHOT_SPEC`) repo içi göreli yollarıyla aynen gömülür; manifesti (yol → sha256 → bayt), anlık
//   görüntü yollarının `git status`'u ve tahmin kayıtlarını ekleyen commit'ler derleme bilgisine girer.
// - git yalnız okuma alt komutlarıyla (`rev-parse`, `status`, `ls-files`, `log`) ve GIT_OPTIONAL_LOCKS=0 ile çağrılır:
//   paralel commit sırasında index.lock bırakılmaz.

#[allow(dead_code)]
pub mod build_embed_impl {
    use sha2::{Digest, Sha256};
    use std::fmt::Write as _;
    use std::path::{Path, PathBuf};
    use std::process::Command;

    pub const PINNED_MODEL_IDS: [&str; 27] = [
        "v1_5_h99",
        "base_always_ceiling",
        "base_train_median",
        "base_train_mean",
        "base_zero",
        "base_rate",
        "base_last10_rate",
        "v1_6_h99",
        "v1_5_market20_v0",
        "pb_v0",
        "ceiling_hazard_v0",
        "ceiling_hazard_v0@INF",
        "pb_ceiling_v0",
        "pb_ceiling_v0@INF",
        "base_km_expanding",
        "base_km_last10",
        "ceiling_path_v0",
        "ceiling_path_v0@INF",
        "pb_ceiling_path_v0",
        "ceiling_hazard_v1_clip",
        "ceiling_hazard_v1_real",
        "ceiling_hazard_v1_pooled",
        "ceiling_hazard_v1_pooled@INF",
        "fall_d10_v0_h99",
        "fall_d10_v0_pooled",
        "fall_d10_v0_addsale",
        "fall_d10_v0_pooled@ZERO",
    ];

    pub const INDEX_SCHEMA: &str = "borsai.model_index/1";
    /// İkinci dizin (D1 sonrası; EK 3 §4.1 P2): `models/INDEX_POST_D1.json`, aynı şema.
    pub const INDEX_POST_D1_SCHEMA: &str = "borsai.model_index/1";
    pub const INDEX_POST_D1_FILE: &str = "INDEX_POST_D1.json";
    pub const PINNED_POST_D1_MODEL_IDS: [&str; 1] = ["post_d1_hazard_v0"];
    /// TÜFE tablosunun repo içi yolu (bileşenler; `Path::join` ile kurulur).
    pub const TUFE_REL: [&str; 4] = ["data", "raw", "tuik", "tufe_genel_2025_100.csv"];

    /// build.rs'nin çalıştırabileceği git alt komutları (salt okuma; `ls-files` ve `log` anlık görüntünün kayıt bilgisi için).
    pub const GIT_READONLY_SUBCOMMANDS: [&str; 4] = ["rev-parse", "status", "ls-files", "log"];

    /// Anlık görüntü girdisinin kapsamı: tek dosya; dizinin altındaki bütün dosyalar (alt dizinler dahil); `registry/records/`
    /// altında kayıt dizini olan her arz için dizindeki `<T>.<uzantı>` (varsa; dizindeki başka dosya girmez).
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    pub enum SnapshotScope {
        File,
        Tree,
        PerRecord(&'static str),
    }

    /// Sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-1): repo içi yol bileşenleri (`Path::join` ile kurulur) ve kapsam. Ham
    /// bülten, PDF, `registry/source_docs/`, `registry/oot/` girmez. `data/outcomes/`'tan yalnız kayıtlı arzların `<T>.csv`'si
    /// girer (orkestratör kararı, B2: tamlık listesi `COMPLETENESS.csv` hiçbir ekranca okunmaz). `models/break_floor_v0.json`
    /// kırılma kartının sha denetimi içindir (`sade_break::break_view_in`). Yoksa gömülmez (derleme kırılmaz; manifest neyin
    /// gömüldüğünü söyler).
    pub const SNAPSHOT_SPEC: [(&[&str], SnapshotScope); 9] = [
        (&["registry", "ipos.csv"], SnapshotScope::File),
        (&["registry", "records"], SnapshotScope::Tree),
        (&["registry", "inputs"], SnapshotScope::Tree),
        (&["registry", "post_break"], SnapshotScope::Tree),
        (&["registry", "push_proofs"], SnapshotScope::Tree),
        (&["data", "outcomes"], SnapshotScope::PerRecord("csv")),
        (&["scores", "scores_break.json"], SnapshotScope::File),
        (&["scores", "scores_post_d1.json"], SnapshotScope::File),
        (&["models", "break_floor_v0.json"], SnapshotScope::File),
    ];
    /// Tahmin kayıtlarının kökü (göreli yol, `/` ayırıcılı): kaydı ekleyen commit derleme anında buradan okunur.
    pub const SNAPSHOT_RECORDS_REL: &str = "registry/records";

    #[derive(Debug, Clone)]
    pub struct EmbedEntry {
        pub model_id: String,
        pub file: String,
        pub path: PathBuf,
    }

    #[derive(Debug, Clone)]
    pub struct EmbedPlan {
        pub index_path: PathBuf,
        pub index_sha256: String,
        pub models: Vec<EmbedEntry>,
        /// INDEX'te olup bu görevde gömülmeyen kayıtlar (sabit listenin dışı).
        pub ignored_model_ids: Vec<String>,
        pub scores_path: Option<PathBuf>,
        /// Gömülü kümede deflatörlü model varsa TÜFE tablosu (yoksa `None`).
        pub tufe_path: Option<PathBuf>,
        /// `scores/scores_oot.json` (varsa): satırsız süzülmüş kopyası gömülür (`filter_scores_oot`).
        pub scores_oot_path: Option<PathBuf>,
    }

    /// Bağımsız mod için `scores_oot.json` süzgeci (K-P1-3 eki, orkestratör kararı 2026-09-30). HESAP DEĞİL SÜZMEDİR:
    /// üst düzeyde yalnız `schema_version`, `generated_at_utc`, `code`, `cohort_sha256`, `definitions`; her alt küme
    /// bloğunda (`SCORES_OOT_BLOCKS`) `models` dışındaki alanlar (başlık, ölçek, sayaçlar) ve `models[]` öğelerinin
    /// `rows` ve `retro_info` dışındaki bütün alanları olduğu gibi. Üst düzey `retro_info` gömülmez (satırlar ve retro
    /// listeleri arz kodu taşır; boyut). Eklenen `embedded_copy`: kaynak dosyanın sha256'sı ve not.
    pub const SCORES_OOT_BLOCKS: [&str; 6] =
        ["oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"];
    pub const SCORES_OOT_TOP_KEYS: [&str; 5] = ["schema_version", "generated_at_utc", "code", "cohort_sha256", "definitions"];
    pub const SCORES_OOT_EMBED_NOTE: &str =
        "satırlar gömülmedi: rows ve retro_info yok; hücreler ve sayaçlar kaynak dosyadakilerle birebir (süzme, hesap değil)";

    pub fn filter_scores_oot(raw: &[u8]) -> Result<serde_json::Value, String> {
        use serde_json::{Map, Value};
        let doc: Value = serde_json::from_slice(raw).map_err(|e| format!("scores_oot.json ayrıştırılamadı: {e}"))?;
        let mut out = Map::new();
        for k in SCORES_OOT_TOP_KEYS {
            if let Some(v) = doc.get(k) {
                out.insert(k.to_string(), v.clone());
            }
        }
        for b in SCORES_OOT_BLOCKS {
            let Some(Value::Object(block)) = doc.get(b) else { continue };
            let mut nb = Map::new();
            for (k, v) in block {
                if k != "models" {
                    nb.insert(k.clone(), v.clone());
                    continue;
                }
                let models: Vec<Value> = v
                    .as_array()
                    .map(|a| {
                        a.iter()
                            .map(|m| match m {
                                Value::Object(mm) => Value::Object(
                                    mm.iter().filter(|(k, _)| *k != "rows" && *k != "retro_info").map(|(k, v)| (k.clone(), v.clone())).collect(),
                                ),
                                other => other.clone(),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                nb.insert(k.clone(), Value::Array(models));
            }
            out.insert(b.to_string(), Value::Object(nb));
        }
        out.insert(
            "embedded_copy".into(),
            serde_json::json!({"source_sha256": sha256_hex(raw), "rows_embedded": false, "note": SCORES_OOT_EMBED_NOTE}),
        );
        Ok(Value::Object(out))
    }

    /// Model JSON'u deflatörlü mü (`features` içinde `f1r` ve `deflator` bloğu; Python `freeze.deflator_pins`).
    pub fn has_deflator(model_json: &serde_json::Value) -> bool {
        let f1r = model_json
            .get("features")
            .and_then(|v| v.as_array())
            .is_some_and(|a| a.iter().any(|x| x.as_str() == Some("f1r")));
        f1r && model_json.get("deflator").is_some_and(|d| d.is_object())
    }

    pub fn tufe_path(repo: &Path) -> PathBuf {
        TUFE_REL.iter().fold(repo.to_path_buf(), |p, c| p.join(c))
    }

    pub fn sha256_hex(bytes: &[u8]) -> String {
        let digest = Sha256::digest(bytes);
        let mut s = String::with_capacity(64);
        for b in digest {
            let _ = write!(s, "{b:02x}");
        }
        s
    }

    /// İkinci dizinin gömme planı (EK 3 §4.1 P2).
    #[derive(Debug, Clone)]
    pub struct PostD1Plan {
        pub index_path: PathBuf,
        pub index_sha256: String,
        pub models: Vec<EmbedEntry>,
    }

    /// `repo/models/INDEX_POST_D1.json`: kayıtlar sabit listeyle sırasıyla AYNI olmalı (fazlası da eksiği de derlemeyi
    /// kırar: ikinci dizin tek bir modelle dondurulmuştur), dosyalar diskte olmalı.
    pub fn plan_post_d1(repo: &Path, pinned: &[&str]) -> Result<PostD1Plan, String> {
        let index_path = repo.join("models").join(INDEX_POST_D1_FILE);
        let bytes = std::fs::read(&index_path).map_err(|e| format!("{} okunamadı: {e}", index_path.display()))?;
        let index: serde_json::Value =
            serde_json::from_slice(&bytes).map_err(|e| format!("{INDEX_POST_D1_FILE} ayrıştırılamadı: {e}"))?;
        if index.get("schema_version").and_then(|v| v.as_str()) != Some(INDEX_POST_D1_SCHEMA) {
            return Err(format!("{INDEX_POST_D1_FILE} schema_version {INDEX_POST_D1_SCHEMA} değil"));
        }
        let entries = index
            .get("models")
            .and_then(|v| v.as_array())
            .ok_or_else(|| format!("{INDEX_POST_D1_FILE}: models listesi yok"))?;
        let ids: Vec<&str> = entries.iter().map(|e| e.get("model_id").and_then(|v| v.as_str()).unwrap_or("")).collect();
        if ids != pinned {
            return Err(format!("{INDEX_POST_D1_FILE} kayıtları {ids:?}, sabit listede {pinned:?} (sıra ya da küme değişmiş)"));
        }
        let mut models = Vec::with_capacity(pinned.len());
        for (e, id) in entries.iter().zip(pinned) {
            let file = e.get("file").and_then(|v| v.as_str()).ok_or_else(|| format!("{id}: dizin kaydında file yok"))?;
            if file.contains('/') || file.contains('\\') || file.starts_with('.') {
                return Err(format!("{id}: file adı geçersiz: {file:?}"));
            }
            let path = repo.join("models").join(file);
            if !path.is_file() {
                return Err(format!("{id}: {INDEX_POST_D1_FILE}'de var, diskte yok: {}", path.display()));
            }
            models.push(EmbedEntry { model_id: id.to_string(), file: file.to_string(), path });
        }
        Ok(PostD1Plan { index_path, index_sha256: sha256_hex(&bytes), models })
    }

    /// `repo/models/INDEX.json`'dan gömme planı. Hata metni derleme hatası olarak basılır.
    pub fn plan_embedding(repo: &Path, pinned: &[&str]) -> Result<EmbedPlan, String> {
        let index_path = repo.join("models").join("INDEX.json");
        let bytes = std::fs::read(&index_path).map_err(|e| format!("{} okunamadı: {e}", index_path.display()))?;
        let index: serde_json::Value =
            serde_json::from_slice(&bytes).map_err(|e| format!("INDEX.json ayrıştırılamadı: {e}"))?;
        if index.get("schema_version").and_then(|v| v.as_str()) != Some(INDEX_SCHEMA) {
            return Err(format!("INDEX.json schema_version {INDEX_SCHEMA} değil"));
        }
        let entries = index
            .get("models")
            .and_then(|v| v.as_array())
            .ok_or_else(|| "INDEX.json: models listesi yok".to_string())?;
        if entries.len() < pinned.len() {
            return Err(format!("INDEX.json {} kayıt; sabit küme {} kayıt ister", entries.len(), pinned.len()));
        }
        let mut models = Vec::with_capacity(pinned.len());
        for (i, id) in pinned.iter().enumerate() {
            let e = &entries[i];
            let got = e.get("model_id").and_then(|v| v.as_str()).unwrap_or("");
            if got != *id {
                return Err(format!("INDEX.json kayıt {i}: model_id {got:?}, sabit listede {id:?} (sıra ya da küme değişmiş)"));
            }
            let file = e
                .get("file")
                .and_then(|v| v.as_str())
                .ok_or_else(|| format!("{id}: INDEX kaydında file yok"))?;
            if file.contains('/') || file.contains('\\') || file.starts_with('.') {
                return Err(format!("{id}: file adı geçersiz: {file:?}"));
            }
            let path = repo.join("models").join(file);
            if !path.is_file() {
                return Err(format!("{id}: INDEX'te var, diskte yok: {}", path.display()));
            }
            models.push(EmbedEntry { model_id: id.to_string(), file: file.to_string(), path });
        }
        let ignored_model_ids = entries[pinned.len()..]
            .iter()
            .map(|e| e.get("model_id").and_then(|v| v.as_str()).unwrap_or("?").to_string())
            .collect();
        let mut deflated = false;
        for m in &models {
            let raw = std::fs::read(&m.path).map_err(|e| format!("{} okunamadı: {e}", m.path.display()))?;
            if let Ok(v) = serde_json::from_slice::<serde_json::Value>(&raw) {
                deflated |= has_deflator(&v);
            }
        }
        let tufe = tufe_path(repo);
        if deflated && !tufe.is_file() {
            return Err(format!("deflatörlü model gömülüyor ama TÜFE tablosu yok: {}", tufe.display()));
        }
        let scores = repo.join("scores").join("scores.json");
        let scores_oot = repo.join("scores").join("scores_oot.json");
        Ok(EmbedPlan {
            index_path,
            index_sha256: sha256_hex(&bytes),
            models,
            ignored_model_ids,
            scores_path: scores.is_file().then_some(scores),
            tufe_path: deflated.then_some(tufe),
            scores_oot_path: scores_oot.is_file().then_some(scores_oot),
        })
    }

    /// Anlık görüntünün bir dosyası: repo içi göreli yol (`/` ayırıcılı), diskteki yol, sha256 ve bayt sayısı.
    #[derive(Debug, Clone, PartialEq)]
    pub struct SnapshotEntry {
        pub rel: String,
        pub path: PathBuf,
        pub sha256: String,
        pub bytes: u64,
    }

    /// Anlık görüntünün gömme planı (FAZ9_SNAPSHOT K-SNAP-1).
    #[derive(Debug, Clone)]
    pub struct SnapshotPlan {
        /// Göreli yol sırasıyla (bayt sırası).
        pub files: Vec<SnapshotEntry>,
        /// Satır başına `yol\tsha256\tbayt` (dosya sırasıyla); uygulamanın açılışta doğruladığı metin.
        pub manifest: String,
        pub manifest_sha256: String,
    }

    /// Spec yolunun göreli yazımı (`/` ayırıcılı; manifest ve git yol belirteci).
    pub fn spec_rel(parts: &[&str]) -> String {
        parts.join("/")
    }

    pub fn snapshot_manifest(files: &[SnapshotEntry]) -> String {
        files.iter().map(|f| format!("{}\t{}\t{}\n", f.rel, f.sha256, f.bytes)).collect()
    }

    /// Taşınabilir dosya adı (Windows dahil; manifest satırını bozmaz): `[A-Za-z0-9._-]+`.
    pub fn portable_name(name: &str) -> bool {
        !name.is_empty() && name.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
    }

    /// `SNAPSHOT_SPEC`'ten gömme planı. Gizli adlar (`.` ile başlayan; ör. `.DS_Store`) atlanır. Sembolik bağ ve taşınabilir
    /// olmayan ad derlemeyi kırar (anlık görüntü repo dışını göstermez; kişisel modda aynı göreli yolla yazılabilir olmalı).
    pub fn plan_snapshot(repo: &Path) -> Result<SnapshotPlan, String> {
        let tickers = record_tickers(repo)?;
        let mut files = Vec::new();
        for (parts, scope) in SNAPSHOT_SPEC.iter() {
            let path = parts.iter().fold(repo.to_path_buf(), |p, c| p.join(c));
            let rel = spec_rel(parts);
            match scope {
                SnapshotScope::File => files.extend(snapshot_entry(&path, rel)?),
                SnapshotScope::Tree => collect_tree(&path, &rel, &mut files)?,
                SnapshotScope::PerRecord(ext) => {
                    for t in &tickers {
                        let name = format!("{t}.{ext}");
                        files.extend(snapshot_entry(&path.join(&name), format!("{rel}/{name}"))?);
                    }
                }
            }
        }
        files.sort_by(|a, b| a.rel.cmp(&b.rel));
        let manifest = snapshot_manifest(&files);
        Ok(SnapshotPlan { manifest_sha256: sha256_hex(manifest.as_bytes()), manifest, files })
    }

    fn snapshot_entry(path: &Path, rel: String) -> Result<Option<SnapshotEntry>, String> {
        let Ok(meta) = std::fs::symlink_metadata(path) else { return Ok(None) };
        if meta.file_type().is_symlink() {
            return Err(format!("anlık görüntüde sembolik bağ: {rel}"));
        }
        if !meta.is_file() {
            return Err(format!("anlık görüntü girdisi dosya değil: {rel}"));
        }
        let bytes = std::fs::read(path).map_err(|e| format!("{rel} okunamadı: {e}"))?;
        Ok(Some(SnapshotEntry { sha256: sha256_hex(&bytes), bytes: bytes.len() as u64, path: path.to_path_buf(), rel }))
    }

    /// Kayıtlı arzlar: `registry/records/` altındaki dizin adları (gizli adlar atlanır; yoksa boş).
    pub fn record_tickers(repo: &Path) -> Result<Vec<String>, String> {
        let dir = SNAPSHOT_RECORDS_REL.split('/').fold(repo.to_path_buf(), |p, c| p.join(c));
        let Ok(entries) = std::fs::read_dir(&dir) else { return Ok(Vec::new()) };
        let mut out = Vec::new();
        for e in entries {
            let e = e.map_err(|e| format!("{SNAPSHOT_RECORDS_REL} okunamadı: {e}"))?;
            let name = e.file_name().into_string().map_err(|n| format!("{SNAPSHOT_RECORDS_REL}: UTF-8 olmayan ad {n:?}"))?;
            if !name.starts_with('.') && e.file_type().map_err(|e| format!("{name}: {e}"))?.is_dir() {
                if !portable_name(&name) {
                    return Err(format!("anlık görüntüde taşınabilir olmayan ad: {SNAPSHOT_RECORDS_REL}/{name:?}"));
                }
                out.push(name);
            }
        }
        out.sort();
        Ok(out)
    }

    /// Dizinin altındaki bütün dosyalar, alt dizinler dahil (`Tree`).
    fn collect_tree(dir: &Path, rel: &str, out: &mut Vec<SnapshotEntry>) -> Result<(), String> {
        let Ok(meta) = std::fs::symlink_metadata(dir) else { return Ok(()) };
        if meta.file_type().is_symlink() {
            return Err(format!("anlık görüntüde sembolik bağ: {rel}"));
        }
        if !meta.is_dir() {
            return Err(format!("anlık görüntü girdisi dizin değil: {rel}"));
        }
        for e in std::fs::read_dir(dir).map_err(|e| format!("{rel} okunamadı: {e}"))? {
            let e = e.map_err(|e| format!("{rel} okunamadı: {e}"))?;
            let name = e.file_name().into_string().map_err(|n| format!("{rel}: UTF-8 olmayan ad {n:?}"))?;
            if name.starts_with('.') {
                continue;
            }
            let child = format!("{rel}/{name}");
            if !portable_name(&name) {
                return Err(format!("anlık görüntüde taşınabilir olmayan ad: {child:?}"));
            }
            let ft = e.file_type().map_err(|e| format!("{child}: {e}"))?;
            if ft.is_symlink() {
                return Err(format!("anlık görüntüde sembolik bağ: {child}"));
            }
            if ft.is_dir() {
                collect_tree(&e.path(), &child, out)?;
            } else {
                out.extend(snapshot_entry(&e.path(), child)?);
            }
        }
        Ok(())
    }

    /// Derleme anının git bilgisi: anlık görüntüde uygulama git çağırmaz, sicil görünümü bunu okur.
    #[derive(Debug, Clone, Default, PartialEq)]
    pub struct SnapshotGit {
        /// Anlık görüntüdeki izlenen tahmin kayıtları ve kaydı ekleyen commit (bulunamadıysa boş): (göreli yol, commit).
        pub records: Vec<(String, String)>,
        /// `git status --porcelain -- <SNAPSHOT_SPEC yolları>` (git yoksa `UNKNOWN`).
        pub status: String,
    }

    pub fn snapshot_git(repo: &Path, plan: &SnapshotPlan) -> SnapshotGit {
        let tracked: Vec<String> =
            git_readonly(repo, &["ls-files", "--", SNAPSHOT_RECORDS_REL]).unwrap_or_default().lines().map(str::to_string).collect();
        let prefix = format!("{SNAPSHOT_RECORDS_REL}/");
        let records = plan
            .files
            .iter()
            .filter(|f| f.rel.starts_with(&prefix) && tracked.contains(&f.rel))
            .map(|f| {
                let c = git_readonly(repo, &["log", "--diff-filter=A", "--format=%H", "-1", "--", &f.rel]).unwrap_or_default();
                (f.rel.clone(), c.trim().to_string())
            })
            .collect();
        let paths: Vec<String> = SNAPSHOT_SPEC.iter().map(|(p, _)| spec_rel(p)).collect();
        let mut args = vec!["status", "--porcelain", "--"];
        args.extend(paths.iter().map(String::as_str));
        SnapshotGit { records, status: git_readonly(repo, &args).unwrap_or_else(|| "UNKNOWN".into()) }
    }

    /// Salt okuma git çağrısı: alt komut beyaz listede olmalı; GIT_OPTIONAL_LOCKS=0 her zaman.
    pub fn git_command(repo: &Path, args: &[&str]) -> Command {
        let sub = args.first().copied().unwrap_or("");
        assert!(
            GIT_READONLY_SUBCOMMANDS.contains(&sub),
            "build.rs yalnız salt okuma git alt komutları çalıştırır: {sub:?}"
        );
        let mut cmd = Command::new("git");
        cmd.env("GIT_OPTIONAL_LOCKS", "0").arg("-C").arg(repo).args(args);
        cmd
    }

    pub fn git_readonly(repo: &Path, args: &[&str]) -> Option<String> {
        let out = git_command(repo, args).output().ok()?;
        if !out.status.success() {
            return None;
        }
        Some(String::from_utf8_lossy(&out.stdout).to_string())
    }

    fn lit(s: &str) -> String {
        format!("{s:?}")
    }

    fn path_lit(p: &Path) -> String {
        lit(&p.to_string_lossy())
    }

    /// OUT_DIR/embedded.rs içeriği (tipler src/embedded.rs'de). `scores_oot_filtered`: build.rs'nin OUT_DIR'e yazdığı
    /// süzülmüş `scores_oot.json` kopyası (yoksa `None`). `snap`, `snap_git`: sicil anlık görüntüsü ve derleme anının git
    /// bilgisi (FAZ9_SNAPSHOT K-SNAP-1).
    pub fn render_embedded_rs(
        plan: &EmbedPlan,
        post: &PostD1Plan,
        git_head: &str,
        git_status: &str,
        scores_oot_filtered: Option<&Path>,
        snap: &SnapshotPlan,
        snap_git: &SnapshotGit,
    ) -> String {
        let mut s = String::new();
        s.push_str("// build.rs üretir; elle düzenlenmez.\n");
        let _ = writeln!(s, "pub const INDEX_JSON: &str = include_str!({});", path_lit(&plan.index_path));
        let models = |s: &mut String, name: &str, list: &[EmbedEntry]| {
            let _ = writeln!(s, "pub const {name}: &[EmbeddedModel] = &[");
            for m in list {
                let _ = writeln!(
                    s,
                    "    EmbeddedModel {{ model_id: {}, file: {}, json: include_str!({}) }},",
                    lit(&m.model_id),
                    lit(&m.file),
                    path_lit(&m.path)
                );
            }
            s.push_str("];\n");
        };
        models(&mut s, "EMBEDDED_MODELS", &plan.models);
        let _ = writeln!(s, "pub const INDEX_POST_D1_JSON: &str = include_str!({});", path_lit(&post.index_path));
        models(&mut s, "EMBEDDED_POST_D1_MODELS", &post.models);
        match &plan.scores_path {
            Some(p) => {
                let _ = writeln!(s, "pub const SCORES_JSON: Option<&str> = Some(include_str!({}));", path_lit(p));
            }
            None => s.push_str("pub const SCORES_JSON: Option<&str> = None;\n"),
        }
        match scores_oot_filtered {
            Some(p) => {
                let _ = writeln!(s, "pub const SCORES_OOT_JSON: Option<&str> = Some(include_str!({}));", path_lit(p));
            }
            None => s.push_str("pub const SCORES_OOT_JSON: Option<&str> = None;\n"),
        }
        match &plan.tufe_path {
            Some(p) => {
                let _ = writeln!(s, "pub const TUFE_CSV: Option<&str> = Some(include_str!({}));", path_lit(p));
            }
            None => s.push_str("pub const TUFE_CSV: Option<&str> = None;\n"),
        }
        s.push_str("pub const SNAPSHOT_FILES: &[SnapshotFile] = &[\n");
        for f in &snap.files {
            let _ = writeln!(
                s,
                "    SnapshotFile {{ rel: {}, sha256: {}, bytes: include_bytes!({}) }},",
                lit(&f.rel),
                lit(&f.sha256),
                path_lit(&f.path)
            );
        }
        s.push_str("];\n");
        let commits: Vec<String> = snap_git.records.iter().map(|(r, c)| format!("({}, {})", lit(r), lit(c))).collect();
        let _ = writeln!(s, "pub const SNAPSHOT_RECORD_COMMITS: &[(&str, &str)] = &[{}];", commits.join(", "));
        let ignored: Vec<String> = plan.ignored_model_ids.iter().map(|m| lit(m)).collect();
        let _ = writeln!(
            s,
            "pub const BUILD_INFO: BuildInfo = BuildInfo {{ git_head: {}, git_status_models_scores: {}, index_sha256: {}, index_post_d1_sha256: {}, ignored_index_models: &[{}], snapshot_manifest: {}, snapshot_manifest_sha256: {}, git_status_snapshot: {} }};",
            lit(git_head.trim()),
            lit(git_status),
            lit(&plan.index_sha256),
            lit(&post.index_sha256),
            ignored.join(", "),
            lit(&snap.manifest),
            lit(&snap.manifest_sha256),
            lit(&snap_git.status)
        );
        s
    }
}
