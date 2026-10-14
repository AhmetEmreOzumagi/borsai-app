//! `scores/scores_oot.json` okuyucu (SPEC_APP EK 3 §7.1; P1: K-P1-3, P3: K-P3-1/K-P3-2). Tavan serisi ve düşüş kartlarının
//! "zaman-dışı (kasa)" sütunu, öne çıkarma kuralları (`scores::featured_ceiling`, `featured_fall`) ve Doğruluk sekmesindeki
//! "Zaman-dışı test (eski kohort)" paneli (`scores_oot_view`, `scores_oot_model`) bu okuyucudan beslenir.
//!
//! Kod görünürlüğü (K-P3-1): repo modunda satırlardan YALNIZ açık küme bloğunun (`oot_pre_h99`) `open == true` satırları
//! okunur ve özetlenerek tutulur; kasa, toplam ve D1 sonrası bloklarının satırları ayrıştırmadan sonra hiç tutulmaz (yalnız
//! hücreler, kırılımlar ve sayaçlar). Üst düzey `retro_info` yalnız açık satırlarda geçen kodlarla tutulur; geçmeyenler
//! yalnız sayı olarak (EK 3 §7.1). Kasa kodları panelde, fikstürlerde ve hata metinlerinde hiç görünmez.
//!
//! Kaynak seçimi `scores.json` ile aynı (§7.1): ayar REPO ve repo modu → `<repo>/scores/scores_oot.json`; değilse derlemeye
//! gömülü SÜZÜLMÜŞ kopya (`build_embed.rs: filter_scores_oot`; satırlar ve retro listeleri gömülmez, hücreler ve sayaçlar
//! birebir). Repo dosyası (≈ 41 MB) bir kez okunup önbelleğe alınır: yol, boyut ya da değişme zamanı değişmedikçe yeniden
//! ayrıştırılmaz. Uygulama hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz.
//!
//! Fail-closed bütünlük (§7.1, K-P1-3 değişikliğiyle): sürüm `borsai.scores_oot/1` değilse okunmaz; model bloğunda
//! `n_scored < 10` iken hücre (`OOT_CELLS_BELOW_MIN_N`); hüküm ve aralık kuralları (`VERDICT_WITHOUT_INTERVAL`,
//! `UNDECIDED_WITH_INTERVAL`; `cells`, `by_year`, `by_regime`); `n_live + n_late ≠ 0` (`OOT_LIVE_COUNTS_NONZERO`);
//! `OOT_ROW_NOT_OPEN` YALNIZ açık küme bloğunun (`oot_pre_h99`) satırlarına uygulanır — kasa açıldığı için
//! `oot_pre_h99_sealed` ve `oot_pre_h99_all` bloklarında `vault == "SEALED"` olan kapalı satırlar meşrudur (başka kapalı
//! satır yine ihlaldir). İhlal metni arz kodu basmaz, yalnız sayı.
use serde::Serialize;
use serde_json::{Map, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::time::SystemTime;

use super::models::sha256_hex;
use super::scores::{check_cell, IntegrityProblem, MIN_N_METRIC};
use crate::embedded;
use crate::state::AppState;

pub const SCORES_OOT_SCHEMA: &str = "borsai.scores_oot/1";
/// Alt küme blokları (sıra dosyadaki gibi); kasa blokları kasa açılınca yazılır.
pub const BLOCKS: [&str; 6] = ["oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"];
pub const OPEN_BLOCK: &str = "oot_pre_h99";
pub const SEALED_BLOCK: &str = "oot_pre_h99_sealed";
/// Kasa satırının `vault` değeri (veri değeri; arayüz metni değil).
pub const VAULT_SEALED: &str = "SEALED";

pub mod rules {
    pub const OOT_CELLS_BELOW_MIN_N: &str = "OOT_CELLS_BELOW_MIN_N";
    pub const OOT_LIVE_COUNTS_NONZERO: &str = "OOT_LIVE_COUNTS_NONZERO";
    pub const OOT_ROW_NOT_OPEN: &str = "OOT_ROW_NOT_OPEN";
}

/// Okunmuş dosya: başlık alanları, bütünlük sonucu ve satırları atılmış belge (kart yalnız hücreleri okur).
#[derive(Debug, Clone, Serialize)]
pub struct ScoresOotDoc {
    /// REPO | EMBEDDED
    pub source: &'static str,
    pub path: Option<String>,
    /// Kaynak dosyanın sha256'sı (gömülü kopyada `embedded_copy.source_sha256`).
    pub source_sha256: Option<String>,
    pub generated_at_utc: Option<String>,
    /// Desteklenmeyen sürüm (okunmaz; kart sütunu "—").
    pub unsupported_version: Option<String>,
    pub integrity: Option<IntegrityProblem>,
    /// Satırlar bu kopyada var mı (repo dosyası: evet, denetlendi; gömülü: hayır).
    pub rows_present: bool,
    /// Kasa bloğu (`oot_pre_h99_sealed`) var mı: kasa açıldı.
    pub vault_open: bool,
    #[serde(skip)]
    pub doc: Arc<Value>,
    /// K-P3-1: yalnız açık küme bloğunun `open == true` satırları (model başına, dosya sırasıyla), özet hâlinde.
    #[serde(skip)]
    pub open_rows: Arc<BTreeMap<String, Vec<OotRowView>>>,
    /// Üst düzey `retro_info`: yalnız açık satırlarda geçen kodlar (model başına) ve çizilmeyen sayısı.
    #[serde(skip)]
    pub retro: Arc<RetroView>,
}

impl ScoresOotDoc {
    /// Hücreleri okunabilir mi (sürüm destekli ve bütünlük temiz).
    pub fn usable(&self) -> Option<&Value> {
        (self.unsupported_version.is_none() && self.integrity.is_none()).then_some(self.doc.as_ref())
    }
}

fn u(v: &Value, key: &str) -> u64 {
    v.get(key).and_then(Value::as_u64).unwrap_or(0)
}

fn arr<'a>(v: &'a Value, key: &str) -> &'a [Value] {
    v.get(key).and_then(Value::as_array).map(Vec::as_slice).unwrap_or(&[])
}

/// Bütünlük denetimi (ilk ihlalde durur).
pub fn check_integrity_oot(doc: &Value) -> Option<IntegrityProblem> {
    for b in BLOCKS {
        let Some(block) = doc.get(b) else { continue };
        let mut not_open = 0usize;
        for m in arr(block, "models") {
            let id = m.get("model_id").and_then(Value::as_str).unwrap_or("?");
            let n_scored = u(m, "n_scored");
            if n_scored < MIN_N_METRIC && !arr(m, "cells").is_empty() {
                return Some(IntegrityProblem::new(
                    rules::OOT_CELLS_BELOW_MIN_N,
                    Some(id),
                    format!("{b}: n_scored = {n_scored} < {MIN_N_METRIC}, cells = {}", arr(m, "cells").len()),
                ));
            }
            for key in ["cells", "by_year", "by_regime"] {
                for c in arr(m, key) {
                    if u(c, "n_live") + u(c, "n_late") != 0 {
                        return Some(IntegrityProblem::new(
                            rules::OOT_LIVE_COUNTS_NONZERO,
                            Some(id),
                            format!("{b}.{key}: n_live = {}, n_late = {}", u(c, "n_live"), u(c, "n_late")),
                        ));
                    }
                    if let Some(p) = check_cell(c, id, &format!("{b}.{key}")) {
                        return Some(p);
                    }
                }
            }
            for r in arr(m, "rows") {
                if r.get("open") == Some(&Value::Bool(true)) {
                    continue;
                }
                let sealed = r.get("vault").and_then(Value::as_str) == Some(VAULT_SEALED);
                match b {
                    // açık küme bloğunda kapalı satır olamaz
                    OPEN_BLOCK => not_open += 1,
                    // kasa ve birleşik blokta yalnız kasa (SEALED) satırı kapalı olabilir (kasa açıldı)
                    SEALED_BLOCK | "oot_pre_h99_all" if !sealed => not_open += 1,
                    // D1 sonrası satırlarında `open` alanı yoktur: kural uygulanmaz
                    _ => {}
                }
            }
        }
        if not_open > 0 {
            return Some(IntegrityProblem::new(rules::OOT_ROW_NOT_OPEN, None, format!("{b}: {not_open} satır açık küme değil")));
        }
    }
    None
}

/// Satırları ve retro listelerini atar (kart yalnız hücre ve sayaç okur; gömülü kopyayla aynı biçim).
pub fn strip_rows(mut doc: Value) -> Value {
    if let Some(o) = doc.as_object_mut() {
        o.remove("retro_info");
        for b in BLOCKS {
            if let Some(models) = o.get_mut(b).and_then(|x| x.get_mut("models")).and_then(Value::as_array_mut) {
                for m in models.iter_mut().filter_map(Value::as_object_mut) {
                    m.remove("rows");
                    m.remove("retro_info");
                }
            }
        }
    }
    doc
}

// ---------------------------------------------------------------- P3: panel görünümü (EK 3 §7.2; K-P3-1)

/// Açık küme satır tablosunun bir satırı (EK 3 §7.2-3; SPEC_APP §3d `rowTable` kalıbı). Tahmin ve gerçekleşen değerler
/// dosyadan seçilir (hesap yok): tavan modelinde S_1, S_5, S_10; getiri modelinde D5 getirisi ve p_up; retli satırda kod.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotRowView {
    pub ticker: String,
    pub d1: Option<String>,
    pub year: Option<Value>,
    pub alloc_regime: Option<String>,
    pub class: Option<String>,
    pub class_evidence: Value,
    pub status: Option<String>,
    pub cell_status: Option<String>,
    pub record_id: Option<String>,
    /// S | RETURN | REFUSED | NONE
    pub pred_kind: &'static str,
    /// S_1, S_5, S_10 (`prediction.S[0]`, `[4]`, `[9]`).
    pub pred_s: Option<[Option<f64>; 3]>,
    pub pred_d5_return: Option<f64>,
    pub pred_d5_p_up: Option<f64>,
    pub refused_code: Option<String>,
    pub realized_l: Option<Value>,
    /// `realized.R.D5` (Decimal metni aynen).
    pub realized_d5_r: Option<String>,
}

/// Satır tooltip'inde gösterilen sınıf kanıtı alanları (zaman kanıtları ve iki karar bayrağı; dosyadaki değerler aynen).
pub const CLASS_EVIDENCE_SHOWN: [&str; 5] = [
    "model_push_proof_created_at",
    "record_push_proof_created_at",
    "oot_ingest_push_proof_created_at",
    "model_frozen_before_ingest",
    "record_before_ingest",
];

fn row_view(r: &Value) -> OotRowView {
    let s = |v: &Value, k: &str| v.get(k).and_then(Value::as_str).map(str::to_string);
    let p = r.get("prediction").unwrap_or(&Value::Null);
    let refused_code = p.get("refused").and_then(|x| x.get("code")).and_then(Value::as_str).map(str::to_string);
    let sv = p.get("S").and_then(Value::as_array);
    let d5 = p.get("D5");
    let pred_kind = if refused_code.is_some() {
        "REFUSED"
    } else if sv.is_some() {
        "S"
    } else if d5.is_some_and(Value::is_object) {
        "RETURN"
    } else {
        "NONE"
    };
    let realized = r.get("realized").unwrap_or(&Value::Null);
    OotRowView {
        ticker: s(r, "ticker").unwrap_or_default(),
        d1: s(r, "d1"),
        year: r.get("year").cloned(),
        alloc_regime: r.get("regime_tags").and_then(|t| t.get("ALLOC_REGIME")).and_then(Value::as_str).map(str::to_string),
        class: s(r, "class"),
        class_evidence: r
            .get("class_evidence")
            .and_then(Value::as_object)
            .map(|o| Value::Object(o.iter().filter(|(k, _)| CLASS_EVIDENCE_SHOWN.contains(&k.as_str())).map(|(k, v)| (k.clone(), v.clone())).collect()))
            .unwrap_or(Value::Null),
        status: s(r, "status"),
        cell_status: s(r, "cell_status"),
        record_id: s(r, "record_id"),
        pred_kind,
        pred_s: sv.map(|a| [0usize, 4, 9].map(|i| a.get(i).and_then(Value::as_f64))),
        pred_d5_return: d5.and_then(|c| c.get("return")).and_then(Value::as_f64),
        pred_d5_p_up: d5.and_then(|c| c.get("p_up")).and_then(Value::as_f64),
        refused_code,
        realized_l: realized.get("L").filter(|x| !x.is_null()).cloned(),
        realized_d5_r: realized.get("R").and_then(|x| x.get("D5")).and_then(Value::as_str).map(str::to_string),
    }
}

/// `retro_info` model başına: açık satırlarda geçen kodlar ve çizilmeyen (açık satırda geçmeyen) sayısı.
#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct RetroGroup {
    pub model_id: String,
    pub n: usize,
    pub tickers: Vec<String>,
    pub n_not_drawn: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct RetroView {
    pub groups: Vec<RetroGroup>,
    pub n: usize,
    pub n_not_drawn: usize,
}

/// K-P3-1: açık küme bloğunun `open == true` satırları (başka blok ve kapalı satır okunmaz) ve süzülmüş RETRO listesi.
fn open_rows_and_retro(doc: &Value) -> (BTreeMap<String, Vec<OotRowView>>, RetroView) {
    let mut rows: BTreeMap<String, Vec<OotRowView>> = BTreeMap::new();
    let mut open_tickers: BTreeSet<String> = BTreeSet::new();
    for m in doc.get(OPEN_BLOCK).map(|b| arr(b, "models")).unwrap_or(&[]) {
        let id = m.get("model_id").and_then(Value::as_str).unwrap_or("?").to_string();
        let kept: Vec<OotRowView> =
            arr(m, "rows").iter().filter(|r| r.get("open") == Some(&Value::Bool(true))).map(row_view).collect();
        open_tickers.extend(kept.iter().map(|r| r.ticker.clone()));
        rows.insert(id, kept);
    }
    let mut retro = RetroView::default();
    for item in arr(doc, "retro_info") {
        let id = item.get("model_id").and_then(Value::as_str).unwrap_or("?").to_string();
        let t = item.get("ticker").and_then(Value::as_str).unwrap_or("");
        let g = match retro.groups.iter().position(|g| g.model_id == id) {
            Some(i) => &mut retro.groups[i],
            None => {
                retro.groups.push(RetroGroup { model_id: id, ..Default::default() });
                retro.groups.last_mut().expect("eklendi")
            }
        };
        g.n += 1;
        retro.n += 1;
        if open_tickers.contains(t) {
            g.tickers.push(t.to_string());
        } else {
            g.n_not_drawn += 1;
            retro.n_not_drawn += 1;
        }
    }
    (rows, retro)
}

/// Metinden okuma (repo dosyası ya da gömülü kopya).
pub fn scores_oot_from(bytes: &[u8], source: &'static str, path: Option<&Path>) -> Result<ScoresOotDoc, String> {
    let doc: Value = serde_json::from_slice(bytes).map_err(|e| format!("scores_oot.json ayrıştırılamadı: {e}"))?;
    let s = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    let version = s("schema_version").unwrap_or_default();
    let embedded_sha = doc.pointer("/embedded_copy/source_sha256").and_then(Value::as_str).map(str::to_string);
    let mut out = ScoresOotDoc {
        source,
        path: path.map(|p| p.display().to_string()),
        source_sha256: embedded_sha.or_else(|| Some(sha256_hex(bytes))),
        generated_at_utc: s("generated_at_utc"),
        unsupported_version: None,
        integrity: None,
        rows_present: doc.pointer("/embedded_copy/rows_embedded") != Some(&Value::Bool(false)),
        vault_open: doc.get(SEALED_BLOCK).is_some(),
        doc: Arc::new(Value::Null),
        open_rows: Arc::new(BTreeMap::new()),
        retro: Arc::new(RetroView::default()),
    };
    if version != SCORES_OOT_SCHEMA {
        out.unsupported_version = Some(version);
        return Ok(out);
    }
    out.integrity = check_integrity_oot(&doc);
    if out.rows_present {
        let (rows, retro) = open_rows_and_retro(&doc);
        out.open_rows = Arc::new(rows);
        out.retro = Arc::new(retro);
    }
    out.doc = Arc::new(strip_rows(doc));
    Ok(out)
}

type CacheEntry = (PathBuf, u64, Option<SystemTime>, Arc<ScoresOotDoc>);

fn cache() -> &'static Mutex<Option<CacheEntry>> {
    static CACHE: OnceLock<Mutex<Option<CacheEntry>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(None))
}

/// Repo dosyası; önbellek: (yol, boyut, değişme zamanı) aynıysa yeniden okunmaz ve ayrıştırılmaz. Dosya yoksa `None`.
pub fn scores_oot_repo(path: &Path) -> Option<Result<Arc<ScoresOotDoc>, String>> {
    let meta = std::fs::metadata(path).ok()?;
    let key = (path.to_path_buf(), meta.len(), meta.modified().ok());
    let mut guard = cache().lock().expect("scores_oot önbellek kilidi");
    if let Some((p, len, mtime, doc)) = guard.as_ref() {
        if (p, *len, *mtime) == (&key.0, key.1, key.2) {
            return Some(Ok(Arc::clone(doc)));
        }
    }
    REPO_PARSES.fetch_add(1, Ordering::SeqCst);
    let loaded = std::fs::read(path)
        .map_err(|e| format!("{} okunamadı: {e}", path.display()))
        .and_then(|b| scores_oot_from(&b, "REPO", Some(path)))
        .map(Arc::new);
    if let Ok(doc) = &loaded {
        *guard = Some((key.0, key.1, key.2, Arc::clone(doc)));
    }
    Some(loaded)
}

static REPO_PARSES: AtomicUsize = AtomicUsize::new(0);

/// Repo dosyası bu süreçte kaç kez okunup ayrıştırıldı (test: her tahminde yeniden ayrıştırılmadığını sınar).
pub fn repo_parse_count() -> usize {
    REPO_PARSES.load(Ordering::SeqCst)
}

/// Gömülü süzülmüş kopya (derlemede yoksa `None`).
pub fn scores_oot_embedded() -> Option<Arc<ScoresOotDoc>> {
    static DOC: OnceLock<Option<Arc<ScoresOotDoc>>> = OnceLock::new();
    DOC.get_or_init(|| embedded::SCORES_OOT_JSON.and_then(|t| scores_oot_from(t.as_bytes(), "EMBEDDED", None).ok()).map(Arc::new))
        .clone()
}

pub fn scores_oot_path_in(repo: &Path) -> PathBuf {
    repo.join("scores").join("scores_oot.json")
}

/// Kaynak seçimi (§7.1): ayar REPO ve repo modu → repo dosyası (yoksa gömülü); değilse gömülü.
pub fn scores_oot_doc(state: &AppState) -> Option<Arc<ScoresOotDoc>> {
    let wants_repo = state.runtime.lock().expect("runtime kilidi").config.scores_source == "REPO";
    if let (true, Some(repo)) = (wants_repo, state.repo()) {
        if let Some(Ok(doc)) = scores_oot_repo(&scores_oot_path_in(&repo.root)) {
            return Some(doc);
        }
    }
    scores_oot_embedded()
}

/// Alt küme bloğundaki modelin bloğu.
pub fn model_block<'a>(doc: &'a Value, block: &str, model_id: &str) -> Option<&'a Value> {
    doc.get(block)?.get("models")?.as_array()?.iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id))
}

/// Model bloğunun önceden ilan edilmiş birincil hücresi (`label == "birincil"`).
pub fn primary_cell(block: &Value) -> Option<&Value> {
    arr(block, "cells").iter().find(|c| c.get("label").and_then(Value::as_str) == Some("birincil"))
}

/// Model bloğunda S · RPS · `rule_id` hücresi (ufuksuz).
pub fn rps_cell<'a>(block: &'a Value, rule_id: &str) -> Option<&'a Value> {
    arr(block, "cells").iter().find(|c| {
        c.get("output").and_then(Value::as_str) == Some("S")
            && c.get("metric").and_then(Value::as_str) == Some("RPS")
            && c.get("rule_id").and_then(Value::as_str) == Some(rule_id)
            && c.get("horizon_or_k").map_or(true, Value::is_null)
    })
}

/// Başlık bilgisi (kart kaynağı satırı).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScoresOotInfo {
    pub source: &'static str,
    pub generated_at_utc: Option<String>,
    pub sha12: Option<String>,
    pub vault_open: bool,
    pub rows_present: bool,
    pub unsupported_version: Option<String>,
    pub integrity: Option<IntegrityProblem>,
}

pub fn info_of(d: &ScoresOotDoc) -> ScoresOotInfo {
    ScoresOotInfo {
        source: d.source,
        generated_at_utc: d.generated_at_utc.clone(),
        sha12: d.source_sha256.as_ref().map(|s| s[..12.min(s.len())].to_string()),
        vault_open: d.vault_open,
        rows_present: d.rows_present,
        unsupported_version: d.unsupported_version.clone(),
        integrity: d.integrity.clone(),
    }
}

/// Test yardımcısı: bir JSON nesnesi (arz kodu içermeyen sentetik fixture) için okuma.
pub fn scores_oot_value(doc: &Value) -> ScoresOotDoc {
    scores_oot_from(serde_json::to_string(doc).expect("serde").as_bytes(), "REPO", None).expect("sentetik scores_oot")
}

// ---------------------------------------------------------------- P3: panel komutları (EK 3 §7.2–§7.3)

/// Model bloğunun sayaçları (`n_` ile başlayan alanlar, dosyadaki gibi).
fn counters(v: &Value) -> Map<String, Value> {
    v.as_object().map(|o| o.iter().filter(|(k, _)| k.starts_with("n_")).map(|(k, x)| (k.clone(), x.clone())).collect()).unwrap_or_default()
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotModelSummary {
    pub model_id: String,
    pub kind: Option<String>,
    pub scale: Option<String>,
    pub subset: Option<String>,
    /// Önceden ilan edilmiş birincil hücre tanımı (`primary_cell`) ve hücrenin kendisi (`label == "birincil"`).
    pub primary_cell: Value,
    pub primary: Option<Value>,
    pub counters: Map<String, Value>,
    /// D1 sonrası blokları (`MACHINE_SEQUENCED` …).
    pub exposure_class: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotBlockView {
    pub key: &'static str,
    pub title: Option<String>,
    pub scale: Option<String>,
    pub subset: Option<String>,
    /// Kohort sayaçları (`n_member`, `n_open`, …; dosyadaki gibi).
    pub counters: Map<String, Value>,
    /// `oot_pre_h99_all` / `post_d1_all`: birleştirilmeyen modeller (`model_id`, `reason`, sayılar; kod yok).
    pub excluded_models: Vec<Value>,
    pub models: Vec<OotModelSummary>,
}

/// Doğruluk sekmesi zaman-dışı paneli (EK 3 §7.2): başlık, kohort sayaçları, altı blok (varsa), RETRO (yalnız açık
/// satırlarda geçen kodlar). Satırlar bu görünümde yok: `scores_oot_model` yalnız açık küme bloğunda verir.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotPanelView {
    /// OK | NO_FILE | REPO_ONLY | UNSUPPORTED | INTEGRITY
    pub status: &'static str,
    pub source: Option<&'static str>,
    pub path: Option<String>,
    pub sha12: Option<String>,
    pub generated_at_utc: Option<String>,
    pub git_head12: Option<String>,
    pub cohort_sha12: Option<String>,
    pub unsupported_version: Option<String>,
    pub integrity: Option<IntegrityProblem>,
    pub rows_present: bool,
    pub vault_open: bool,
    pub class_definition: Option<String>,
    pub blocks: Vec<OotBlockView>,
    pub retro: RetroView,
}

fn s12(s: Option<&str>) -> Option<String> {
    s.map(|x| x[..12.min(x.len())].to_string())
}

pub fn panel_view(d: Option<&ScoresOotDoc>, repo_mode: bool) -> OotPanelView {
    let mut v = OotPanelView {
        status: "OK",
        source: None,
        path: None,
        sha12: None,
        generated_at_utc: None,
        git_head12: None,
        cohort_sha12: None,
        unsupported_version: None,
        integrity: None,
        rows_present: false,
        vault_open: false,
        class_definition: None,
        blocks: Vec::new(),
        retro: RetroView::default(),
    };
    let Some(d) = d else {
        v.status = if repo_mode { "NO_FILE" } else { "REPO_ONLY" };
        return v;
    };
    v.source = Some(d.source);
    v.path = d.path.clone();
    v.sha12 = s12(d.source_sha256.as_deref());
    v.generated_at_utc = d.generated_at_utc.clone();
    v.rows_present = d.rows_present;
    v.vault_open = d.vault_open;
    if let Some(ver) = &d.unsupported_version {
        v.status = "UNSUPPORTED";
        v.unsupported_version = Some(ver.clone());
        return v;
    }
    if let Some(p) = &d.integrity {
        v.status = "INTEGRITY";
        v.integrity = Some(p.clone());
        return v;
    }
    let doc = d.doc.as_ref();
    v.git_head12 = s12(doc.pointer("/code/git_head").and_then(Value::as_str));
    v.cohort_sha12 = s12(doc.get("cohort_sha256").and_then(Value::as_str));
    v.class_definition = doc.pointer("/definitions/class").and_then(Value::as_str).map(str::to_string);
    let text = |b: &Value, k: &str| b.get(k).and_then(Value::as_str).map(str::to_string);
    for key in BLOCKS {
        let Some(b) = doc.get(key) else { continue };
        let models = arr(b, "models")
            .iter()
            .map(|m| OotModelSummary {
                model_id: text(m, "model_id").unwrap_or_default(),
                kind: text(m, "kind"),
                scale: text(m, "scale"),
                subset: text(m, "subset"),
                primary_cell: m.get("primary_cell").cloned().unwrap_or(Value::Null),
                primary: primary_cell(m).cloned(),
                counters: counters(m),
                exposure_class: text(m, "exposure_class"),
            })
            .collect();
        v.blocks.push(OotBlockView {
            key,
            title: text(b, "title"),
            scale: text(b, "scale"),
            subset: text(b, "subset"),
            counters: counters(b),
            excluded_models: arr(b, "excluded_models").to_vec(),
            models,
        });
    }
    v.retro = d.retro.as_ref().clone();
    v
}

/// Bir bloktaki modelin ayrıntısı: hücreler, kırılımlar, bilgi satırı ve YALNIZ açık küme bloğunda açık satırlar.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotModelDetail {
    pub block: String,
    pub model_id: String,
    pub kind: Option<String>,
    pub primary_cell: Value,
    pub cells: Vec<Value>,
    pub by_year: Vec<Value>,
    pub by_regime: Vec<Value>,
    pub info: Vec<Value>,
    /// Açık küme bloğu ve repo modu: satırlar burada; başka blokta hep boş (K-P3-1).
    pub rows: Vec<OotRowView>,
    /// Satır tablosu bu blokta tanımlı mı (yalnız açık küme) ve bu kopyada var mı (repo modu).
    pub rows_block: bool,
    pub rows_available: bool,
}

pub fn model_detail(d: &ScoresOotDoc, block: &str, model_id: &str) -> Option<OotModelDetail> {
    let doc = d.usable()?;
    let m = model_block(doc, block, model_id)?;
    let rows_block = block == OPEN_BLOCK;
    Some(OotModelDetail {
        block: block.to_string(),
        model_id: model_id.to_string(),
        kind: m.get("kind").and_then(Value::as_str).map(str::to_string),
        primary_cell: m.get("primary_cell").cloned().unwrap_or(Value::Null),
        cells: arr(m, "cells").to_vec(),
        by_year: arr(m, "by_year").to_vec(),
        by_regime: arr(m, "by_regime").to_vec(),
        info: arr(m, "info").to_vec(),
        rows: if rows_block { d.open_rows.get(model_id).cloned().unwrap_or_default() } else { Vec::new() },
        rows_block,
        rows_available: rows_block && d.rows_present,
    })
}

#[tauri::command]
pub fn scores_oot_view(state: tauri::State<'_, AppState>) -> OotPanelView {
    let doc = scores_oot_doc(&state);
    panel_view(doc.as_deref(), state.repo().is_some())
}

#[tauri::command]
pub fn scores_oot_model(state: tauri::State<'_, AppState>, block: String, model_id: String) -> Option<OotModelDetail> {
    let doc = scores_oot_doc(&state)?;
    if !BLOCKS.contains(&block.as_str()) {
        return None;
    }
    model_detail(&doc, &block, &model_id)
}
