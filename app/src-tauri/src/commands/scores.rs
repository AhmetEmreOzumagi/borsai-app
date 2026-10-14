//! `scores.json` okuyucu (SPEC_APP §2.3). İki tüketici: sonuç ekranının ipuçları (§3b model kartı ve
//! "backtest tipik hata" satırı) ve doğruluk paneli (§3d). Dosyadaki sayılar OLDUĞU GİBİ aktarılır;
//! uygulama hiçbir hücreyi hesaplamaz, düzeltmez, doldurmaz. §2.3 bütünlük denetimi fail-closed'dır:
//! kural ihlalinde panel yerine ihlal gösterilir.
use serde::Serialize;
use serde_json::{Map, Value};
use std::path::Path;

use super::models::sha256_hex;
use super::AppError;
use crate::embedded;
use crate::state::AppState;

pub const SCORES_SCHEMA: &str = "borsai.scores/1";

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ModelHint {
    /// `card` bloğu aynen.
    pub card: Value,
    pub primary_cell: Value,
    /// Ufuk → `{model_value, n}`: `output = return`, `metric = MAE` backtest hücresinin model değeri.
    pub mae: Map<String, Value>,
    pub live_n_scored: Option<u64>,
    /// Canlı birincil hücrenin `verdict`'i (yalnız dosyada varsa; n < 10'da hücre yoktur).
    pub live_primary_verdict: Option<Value>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScoreHints {
    /// REPO | EMBEDDED
    pub source: &'static str,
    /// Desteklenmeyen sürüm (ipuçları boş).
    pub unsupported_version: Option<String>,
    pub generated_at_utc: Option<String>,
    pub as_of_session: Option<String>,
    pub sha12: String,
    pub index_mismatch: bool,
    pub models: Map<String, Value>,
}

fn primary_matches(cell: &Value, primary: &Value) -> bool {
    let eq = |k: &str| cell.get(k) == primary.get(k);
    let rule_ok = primary
        .get("rule_ids")
        .and_then(Value::as_array)
        .map_or(true, |ids| ids.iter().any(|r| Some(r) == cell.get("rule_id")));
    eq("output") && eq("horizon_or_k") && eq("metric") && rule_ok
}

pub fn score_hints_from(text: &str, source: &'static str, embedded_index_sha: &str) -> Result<ScoreHints, AppError> {
    let doc: Value = serde_json::from_str(text).map_err(|e| super::io_error("scores.json", e))?;
    let sha12 = sha256_hex(text.as_bytes())[..12].to_string();
    let s = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    let version = s("schema_version").unwrap_or_default();
    let mut hints = ScoreHints {
        source,
        unsupported_version: None,
        generated_at_utc: s("generated_at_utc"),
        as_of_session: s("as_of_session"),
        sha12,
        index_mismatch: doc.pointer("/inputs/models_index_sha256").and_then(Value::as_str) != Some(embedded_index_sha),
        models: Map::new(),
    };
    if version != SCORES_SCHEMA {
        hints.unsupported_version = Some(version);
        return Ok(hints);
    }
    for m in doc.get("models").and_then(Value::as_array).into_iter().flatten() {
        let Some(id) = m.get("model_id").and_then(Value::as_str) else { continue };
        let mut mae = Map::new();
        for c in m.pointer("/backtest/cells").and_then(Value::as_array).into_iter().flatten() {
            let is_mae = c.get("output") == Some(&Value::from("return")) && c.get("metric") == Some(&Value::from("MAE"));
            if let (true, Some(h)) = (is_mae, c.get("horizon_or_k").and_then(Value::as_str)) {
                mae.entry(h.to_string())
                    .or_insert_with(|| serde_json::json!({"model_value": c.get("model_value"), "n": c.get("n")}));
            }
        }
        let primary = m.get("primary_cell").cloned().unwrap_or(Value::Null);
        let live_primary_verdict = m
            .pointer("/live/cells")
            .and_then(Value::as_array)
            .and_then(|cells| cells.iter().find(|c| primary_matches(c, &primary)))
            .map(|c| c.get("verdict").cloned().unwrap_or(Value::Null));
        let hint = ModelHint {
            card: m.get("card").cloned().unwrap_or(Value::Null),
            primary_cell: primary,
            mae,
            live_n_scored: m.pointer("/live/n_scored").and_then(Value::as_u64),
            live_primary_verdict,
        };
        hints.models.insert(id.into(), serde_json::to_value(hint).expect("serde"));
    }
    Ok(hints)
}

/// Kaynak: repo modunda ve ayar REPO ise `<repo>/scores/scores.json`, değilse gömülü anlık kopya.
/// İkisi de yoksa `None` (sonuç ekranında satır/kart alanı "—").
pub fn score_hints_value(state: &AppState) -> Result<Option<ScoreHints>, AppError> {
    let wants_repo = state.runtime.lock().expect("runtime kilidi").config.scores_source == "REPO";
    if let (true, Some(repo)) = (wants_repo, state.repo()) {
        let p = repo.root.join("scores").join("scores.json");
        if let Ok(text) = std::fs::read_to_string(&p) {
            return score_hints_from(&text, "REPO", &state.embedded_index_sha()).map(Some);
        }
    }
    match embedded::SCORES_JSON {
        Some(text) => score_hints_from(text, "EMBEDDED", &state.embedded_index_sha()).map(Some),
        None => Ok(None),
    }
}

#[tauri::command]
pub fn score_hints(state: tauri::State<'_, AppState>) -> Result<Option<ScoreHints>, AppError> {
    score_hints_value(&state)
}

// ==================================================================== aşama 4: doğruluk paneli

/// Koşullu skor bloğunun sözleşmesi (SPEC_APP EK 2 §5).
pub const CONDITIONAL_SCHEMA: &str = "borsai.scores_conditional/1";

/// §8 eşikleri: hücre ancak n ≥ 10 ile üretilir, hüküm ancak n ≥ 30 ile verilir.
pub const MIN_N_METRIC: u64 = 10;
pub const MIN_N_VERDICT: u64 = 30;

// Bu üç dize ARAYÜZ METNİ DEĞİLDİR: `scores.json`'daki `verdict` alanının §2.3 bütünlük denetiminde
// geçen değerleridir (SPEC_SCORING §8, SPEC_DEVIATIONS E11). Panelde gösterilen metin dosyadaki
// `verdict` alanının kendisidir; arayüz eşlemesi yalnız `app/src/i18n/tr.ts`'tedir (U19).
pub const VERDICT_PASS: &str = "geçiyor";
pub const VERDICT_FAIL: &str = "geçemiyor";
pub const VERDICT_UNDECIDED: &str = "ayırt edilemiyor";

/// Bütünlük denetimi kural kimlikleri (§2.3 ve görev kararı olarak eklenen iki kural).
pub mod rules {
    pub const LIVE_CELLS_BELOW_MIN_N: &str = "LIVE_CELLS_BELOW_MIN_N";
    pub const LIVE_DESCRIPTIVE_BELOW_MIN_N: &str = "LIVE_DESCRIPTIVE_BELOW_MIN_N";
    pub const SELF_REPORTED_CELLS_BELOW_MIN_N: &str = "SELF_REPORTED_CELLS_BELOW_MIN_N";
    pub const LIVE_N_SPLIT: &str = "LIVE_N_SPLIT";
    pub const VERDICT_WITHOUT_INTERVAL: &str = "VERDICT_WITHOUT_INTERVAL";
    pub const UNDECIDED_WITH_INTERVAL: &str = "UNDECIDED_WITH_INTERVAL";
    pub const CONDITIONAL_CELLS_BELOW_MIN_N: &str = "CONDITIONAL_CELLS_BELOW_MIN_N";
    pub const CONDITIONAL_N_SPLIT: &str = "CONDITIONAL_N_SPLIT";
}

/// §2.3 fail-closed: panel yerine gösterilen kural ihlali.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct IntegrityProblem {
    pub rule: String,
    pub model_id: Option<String>,
    /// Kuralın hangi sayılarla çiğnendiği (ham; uygulama düzeltmez).
    pub detail: String,
}

impl IntegrityProblem {
    pub(crate) fn new(rule: &str, model_id: Option<&str>, detail: impl Into<String>) -> Self {
        IntegrityProblem { rule: rule.into(), model_id: model_id.map(str::to_string), detail: detail.into() }
    }
}

/// Doğruluk panelinin tek veri kaynağı (§2.3). `doc` dosyanın kendisidir: uygulama hiçbir hücreyi
/// hesaplamaz, düzeltmez, doldurmaz; yalnız başlık alanlarını ayıklar ve kural ihlalini bildirir.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScoresView {
    /// REPO | EMBEDDED | FIXTURE (yalnız ekran görüntüsü koşusu)
    pub source: &'static str,
    /// §2.5: desteklenmeyen sürümde panel kapalı, `doc` yok (kısmi gösterim yok).
    pub unsupported_version: Option<String>,
    pub generated_at_utc: Option<String>,
    pub as_of_session: Option<String>,
    pub sha12: String,
    pub index_mismatch: bool,
    /// Dosya kendini kurgusal ilan ediyor (`synthetic: true`).
    pub synthetic: bool,
    pub integrity: Option<IntegrityProblem>,
    pub doc: Option<Value>,
}

fn u(v: &Value, key: &str) -> u64 {
    v.get(key).and_then(Value::as_u64).unwrap_or(0)
}

fn arr_len(v: &Value, key: &str) -> usize {
    v.get(key).and_then(Value::as_array).map_or(0, Vec::len)
}

/// `ci95` 0'ı içeriyor mu? Yok (`null`) ya da iki uç 0'ı kapsıyorsa `true`.
fn ci_contains_zero(cell: &Value) -> bool {
    match cell.get("ci95").and_then(Value::as_array) {
        Some(ci) if ci.len() == 2 => {
            let lo = ci[0].as_f64();
            let hi = ci[1].as_f64();
            match (lo, hi) {
                (Some(lo), Some(hi)) => lo <= 0.0 && hi >= 0.0,
                _ => true,
            }
        }
        _ => true,
    }
}

fn ci_is_null(cell: &Value) -> bool {
    !matches!(cell.get("ci95").and_then(Value::as_array), Some(ci) if ci.len() == 2)
}

/// §2.3: hüküm ancak n ≥ 30 ve 0'ı dışlayan aralıkla verilebilir; "ayırt edilemiyor" ise aralık 0'ı
/// içermek zorundadır. Hücrenin hangi terazide olduğu fark etmez (backtest ve canlı aynı kural).
pub(crate) fn check_cell(cell: &Value, model_id: &str, where_: &str) -> Option<IntegrityProblem> {
    let verdict = cell.get("verdict").and_then(Value::as_str)?;
    let n = cell.get("n").and_then(Value::as_u64).unwrap_or(0);
    let ci = cell.get("ci95").cloned().unwrap_or(Value::Null);
    let cell_id = format!(
        "{where_} · {} {} {} vs {}",
        cell.get("output").and_then(Value::as_str).unwrap_or("?"),
        cell.get("horizon_or_k").map(ToString::to_string).unwrap_or_default(),
        cell.get("metric").and_then(Value::as_str).unwrap_or("?"),
        cell.get("rule_id").and_then(Value::as_str).unwrap_or("?"),
    );
    if (verdict == VERDICT_PASS || verdict == VERDICT_FAIL)
        && (n < MIN_N_VERDICT || ci_is_null(cell) || ci_contains_zero(cell))
    {
        return Some(IntegrityProblem::new(
            rules::VERDICT_WITHOUT_INTERVAL,
            Some(model_id),
            format!("{cell_id}: verdict = {verdict:?}, n = {n}, ci95 = {ci}"),
        ));
    }
    if verdict == VERDICT_UNDECIDED && !ci_is_null(cell) && !ci_contains_zero(cell) {
        return Some(IntegrityProblem::new(
            rules::UNDECIDED_WITH_INTERVAL,
            Some(model_id),
            format!("{cell_id}: verdict = {verdict:?}, ci95 = {ci}"),
        ));
    }
    None
}

fn check_cells(block: &Value, key: &str, model_id: &str, where_: &str) -> Option<IntegrityProblem> {
    block
        .get(key)
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .find_map(|c| check_cell(c, model_id, where_))
}

/// EK 2 §5: her `by_j` öğesi kendi n'iyle aynı küçük-n ve bütünlük kurallarına girer.
fn check_conditional(cond: &Value, model_id: &str) -> Option<IntegrityProblem> {
    if cond.get("schema_version").and_then(Value::as_str) != Some(CONDITIONAL_SCHEMA) {
        return None; // sürüm uyumsuz: blok gösterilmez (panel kapanmaz)
    }
    for by in cond.get("by_j").and_then(Value::as_array).into_iter().flatten() {
        let j = by.get("j").map(ToString::to_string).unwrap_or_default();
        let n = u(by, "n_scored");
        if n < MIN_N_METRIC && arr_len(by, "cells") > 0 {
            return Some(IntegrityProblem::new(
                rules::CONDITIONAL_CELLS_BELOW_MIN_N,
                Some(model_id),
                format!("j = {j}: n_scored = {n} < {MIN_N_METRIC}, cells = {}", arr_len(by, "cells")),
            ));
        }
        if u(by, "n_live") + u(by, "n_late") != n {
            return Some(IntegrityProblem::new(
                rules::CONDITIONAL_N_SPLIT,
                Some(model_id),
                format!("j = {j}: n_live = {} + n_late = {} ≠ n_scored = {n}", u(by, "n_live"), u(by, "n_late")),
            ));
        }
        if let Some(p) = check_cells(by, "cells", model_id, &format!("koşullu j = {j}")) {
            return Some(p);
        }
    }
    None
}

/// §2.3 bütünlük denetimi. İlk ihlalde durur: panel yerine hata gösterilir (fail-closed).
pub fn check_integrity(doc: &Value) -> Option<IntegrityProblem> {
    for m in doc.get("models").and_then(Value::as_array).into_iter().flatten() {
        let id = m.get("model_id").and_then(Value::as_str).unwrap_or("?");
        if let Some(p) = check_cells(m.get("backtest").unwrap_or(&Value::Null), "cells", id, "backtest") {
            return Some(p);
        }
        let Some(live) = m.get("live") else { continue };
        let n_scored = u(live, "n_scored");
        if n_scored < MIN_N_METRIC && arr_len(live, "cells") > 0 {
            return Some(IntegrityProblem::new(
                rules::LIVE_CELLS_BELOW_MIN_N,
                Some(id),
                format!("n_scored = {n_scored} < {MIN_N_METRIC}, live.cells = {}", arr_len(live, "cells")),
            ));
        }
        // Görev kararı (SPEC_DEVIATIONS satır 83 alanları): betimleyici ölçüler de §8'in n eşiğine girer.
        if n_scored < MIN_N_METRIC && arr_len(live, "descriptive") > 0 {
            return Some(IntegrityProblem::new(
                rules::LIVE_DESCRIPTIVE_BELOW_MIN_N,
                Some(id),
                format!("n_scored = {n_scored} < {MIN_N_METRIC}, live.descriptive = {}", arr_len(live, "descriptive")),
            ));
        }
        let n_self = u(live, "n_self_reported_scored");
        if n_self < MIN_N_METRIC && arr_len(live, "self_reported_cells") > 0 {
            return Some(IntegrityProblem::new(
                rules::SELF_REPORTED_CELLS_BELOW_MIN_N,
                Some(id),
                format!(
                    "n_self_reported_scored = {n_self} < {MIN_N_METRIC}, self_reported_cells = {}",
                    arr_len(live, "self_reported_cells")
                ),
            ));
        }
        if u(live, "n_live") + u(live, "n_late") != n_scored {
            return Some(IntegrityProblem::new(
                rules::LIVE_N_SPLIT,
                Some(id),
                format!("n_live = {} + n_late = {} ≠ n_scored = {n_scored}", u(live, "n_live"), u(live, "n_late")),
            ));
        }
        if let Some(p) = check_cells(live, "cells", id, "canlı") {
            return Some(p);
        }
        if let Some(p) = check_cells(live, "self_reported_cells", id, "self-reported") {
            return Some(p);
        }
        if let Some(cond) = m.get("conditional") {
            if let Some(p) = check_conditional(cond, id) {
                return Some(p);
            }
        }
    }
    None
}

/// Metinden panel görünümü. Sürüm uyumsuzsa `doc` verilmez (§2.5), bütünlük ihlalinde `integrity`
/// dolar ve ön uç panel yerine hatayı basar (§2.3).
pub fn scores_view_from(text: &str, source: &'static str, embedded_index_sha: &str) -> Result<ScoresView, AppError> {
    let doc: Value = serde_json::from_str(text).map_err(|e| super::io_error("scores.json", e))?;
    let s = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    let mut view = ScoresView {
        source,
        unsupported_version: None,
        generated_at_utc: s("generated_at_utc"),
        as_of_session: s("as_of_session"),
        sha12: sha256_hex(text.as_bytes())[..12].to_string(),
        index_mismatch: doc.pointer("/inputs/models_index_sha256").and_then(Value::as_str) != Some(embedded_index_sha),
        synthetic: doc.get("synthetic").and_then(Value::as_bool).unwrap_or(false),
        integrity: None,
        doc: None,
    };
    let version = s("schema_version").unwrap_or_default();
    if version != SCORES_SCHEMA {
        view.unsupported_version = Some(version);
        return Ok(view);
    }
    view.integrity = check_integrity(&doc);
    if view.integrity.is_none() {
        view.doc = Some(doc);
    }
    Ok(view)
}

/// Kaynak seçimi §2.3: repo modunda ayar REPO ise repo kopyası, değilse gömülü anlık kopya.
/// Ekran görüntüsü koşusunda (yalnız `--features snapshot`) sentetik fixture geçici olarak öne geçer.
#[tauri::command]
pub fn scores_view(state: tauri::State<'_, AppState>) -> Result<Option<ScoresView>, AppError> {
    if let Some(p) = state.scores_fixture() {
        let text = std::fs::read_to_string(&p).map_err(|e| super::io_error(&p.display().to_string(), e))?;
        return scores_view_from(&text, "FIXTURE", &state.embedded_index_sha()).map(Some);
    }
    let wants_repo = state.runtime.lock().expect("runtime kilidi").config.scores_source == "REPO";
    if let (true, Some(repo)) = (wants_repo, state.repo()) {
        let p = repo.root.join("scores").join("scores.json");
        if let Ok(text) = std::fs::read_to_string(&p) {
            return scores_view_from(&text, "REPO", &state.embedded_index_sha()).map(Some);
        }
    }
    match embedded::SCORES_JSON {
        Some(text) => scores_view_from(text, "EMBEDDED", &state.embedded_index_sha()).map(Some),
        None => Ok(None),
    }
}

// ==================================================================== EK 3 §5: yakın dönem, canlı satır, öne çıkarma

/// `models[].backtest.near_era` sözleşmesi (EK 3 §5.5, Ö1).
pub const NEAR_ERA_SCHEMA: &str = "borsai.near_era/1";
/// Etiket değer kümesi: VERİ değerleridir (dosyadaki metin aynen gösterilir; arayüz metni değil). Bu üçü dışı fail-closed.
pub const NEAR_ERA_LABELS: [&str; 3] = ["tolerans içinde", "bozuyor", "belirsiz"];
pub const NEAR_ERA_BREAKS: &str = "bozuyor";
pub const NEAR_ERA_LABEL_INVALID: &str = "NEAR_ERA_LABEL_INVALID";

/// Kart sütunu için yakın dönem bloğu (dosyadaki alanlar aynen).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct NearEraView {
    /// `schema_version` destekleniyor mu (değilse etiket gösterilmez, k3 = false).
    pub supported: bool,
    pub schema_version: Option<String>,
    pub label: Option<String>,
    pub comparator: Option<String>,
    pub metric: Option<String>,
    pub subset: Option<String>,
    pub diff: Option<Value>,
    pub ci95: Option<Value>,
    pub n: Option<u64>,
    pub n_blocks: Option<u64>,
}

fn model_of<'a>(doc: &'a Value, model_id: &str) -> Option<&'a Value> {
    doc.get("models")?.as_array()?.iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id))
}

/// Blok yoksa `Ok(None)` ("—"); sürüm farklıysa `supported = false`; etiket üç değer dışındaysa bütünlük hatası.
pub fn near_era_of(doc: &Value, model_id: &str) -> Result<Option<NearEraView>, IntegrityProblem> {
    let Some(b) = model_of(doc, model_id).and_then(|m| m.pointer("/backtest/near_era")).filter(|b| b.is_object()) else {
        return Ok(None);
    };
    let s = |k: &str| b.get(k).and_then(Value::as_str).map(str::to_string);
    let version = s("schema_version");
    let supported = version.as_deref() == Some(NEAR_ERA_SCHEMA);
    let label = s("label");
    if supported && !label.as_deref().is_some_and(|l| NEAR_ERA_LABELS.contains(&l)) {
        return Err(IntegrityProblem::new(NEAR_ERA_LABEL_INVALID, Some(model_id), format!("near_era.label = {:?}", b.get("label"))));
    }
    Ok(Some(NearEraView {
        supported,
        schema_version: version,
        label: if supported { label } else { None },
        comparator: s("comparator"),
        metric: s("metric"),
        subset: s("subset"),
        diff: b.get("diff").cloned(),
        ci95: b.get("ci95").cloned(),
        n: b.get("n").and_then(Value::as_u64),
        n_blocks: b.get("n_blocks").and_then(Value::as_u64),
    }))
}

/// Canlı sicil sütunu: `live.n_scored` ve birincil canlı hücrenin `verdict`'i (yalnız dosyada varsa).
#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct LiveView {
    pub n_scored: Option<u64>,
    pub verdict: Option<Value>,
}

pub fn live_of(doc: &Value, model_id: &str) -> LiveView {
    let Some(m) = model_of(doc, model_id) else { return LiveView::default() };
    let primary = m.get("primary_cell").cloned().unwrap_or(Value::Null);
    LiveView {
        n_scored: m.pointer("/live/n_scored").and_then(Value::as_u64),
        verdict: m
            .pointer("/live/cells")
            .and_then(Value::as_array)
            .and_then(|cells| cells.iter().find(|c| primary_matches(c, &primary)))
            .and_then(|c| c.get("verdict").cloned()),
    }
}

/// Kaynak seçimi (§2.3; `score_hints_value` ile aynı): ayar REPO ve repo modu → repo kopyası; değilse gömülü.
pub fn scores_doc(state: &AppState) -> Option<(Value, &'static str, String)> {
    let wants_repo = state.runtime.lock().expect("runtime kilidi").config.scores_source == "REPO";
    let (text, source) = match (wants_repo, state.repo()) {
        (true, Some(repo)) => match std::fs::read_to_string(repo.root.join("scores").join("scores.json")) {
            Ok(t) => (t, "REPO"),
            Err(_) => (embedded::SCORES_JSON?.to_string(), "EMBEDDED"),
        },
        _ => (embedded::SCORES_JSON?.to_string(), "EMBEDDED"),
    };
    let sha12 = sha256_hex(text.as_bytes())[..12].to_string();
    let doc: Value = serde_json::from_str(&text).ok()?;
    (doc.get("schema_version").and_then(Value::as_str) == Some(SCORES_SCHEMA)).then_some((doc, source, sha12))
}

/// Öne çıkarma kuralının sabitleri (SPEC_HAZARD_V1 §5.5, KARARLAR K4; EK 3 §5.3).
pub const FEATURED_DEFAULT: &str = "ceiling_hazard_v0";
pub const FEATURED_CANDIDATES: [&str; 3] = ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"];
/// k1: kasa birincil hücresi (S · RPS, basit kural `base_km_expanding`); k2: v0'a karşı S · RPS aralığının üst ucu < 0.
pub const K1_RULE: &str = "base_km_expanding";
pub const K2_RULE: &str = "ceiling_hazard_v0";
pub const REASON_VAULT_CLOSED: &str = "VAULT_CLOSED_V0_DEFAULT";
pub const REASON_RULE: &str = "RULE_5_5";
pub const REASON_NONE_ELIGIBLE: &str = "RULE_5_5_NONE_ELIGIBLE_V0";

/// Adayın k1–k3 durumu: yalnız dosyadaki alanların karşılaştırması (skor hesaplanmaz).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CandidateCheck {
    pub model_id: String,
    pub in_index: bool,
    /// Kasa birincil hücresinin `verdict`'i (dosyadaki metin).
    pub primary_verdict: Option<String>,
    pub model_value: Option<f64>,
    /// v0'a karşı hücrenin `ci95[1]`'i.
    pub v0_ci95_hi: Option<f64>,
    pub near_era_label: Option<String>,
    pub k1: bool,
    pub k2: bool,
    pub k3: bool,
    pub eligible: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Featured {
    pub model_id: String,
    /// VAULT_CLOSED_V0_DEFAULT | RULE_5_5 | RULE_5_5_NONE_ELIGIBLE_V0
    pub reason: &'static str,
    pub candidates: Vec<CandidateCheck>,
}

/// `round(x, 3)` (Python ile aynı: kesin ikili değerin doğru yuvarlanmış 3 ondalığı).
fn round3(x: f64) -> f64 {
    format!("{x:.3}").parse().unwrap_or(x)
}

/// Öne çıkarma kuralı (EK 3 §5.3): kasa bloğu yoksa v0 (`VAULT_CLOSED_V0_DEFAULT`); varsa her aday için
/// k1 = kasa birincil hücresi "geçiyor", k2 = v0'a karşı aralığın üst ucu < 0, k3 = yakın dönem etiketi "bozuyor" değil
/// (blok yoksa ya da sürüm desteklenmiyorsa k3 = false). Uygun adaylardan (round(model_value, 3), clip < real < pooled)
/// en küçüğü; uygun yoksa v0 (`RULE_5_5_NONE_ELIGIBLE_V0`). Hiçbir model listeden kalkmaz (K4): öne çıkan yalnız ilk satır.
pub fn featured_ceiling(scores: Option<&Value>, oot: Option<&Value>, embedded_ids: &[String]) -> Featured {
    use super::scores_oot::{model_block, primary_cell, rps_cell, SEALED_BLOCK};
    let sealed = oot.filter(|d| d.get(SEALED_BLOCK).is_some());
    let mut candidates = Vec::new();
    for c in FEATURED_CANDIDATES {
        let in_index = embedded_ids.iter().any(|x| x == c);
        let block = sealed.and_then(|d| model_block(d, SEALED_BLOCK, c));
        let prim = block.and_then(primary_cell).filter(|p| {
            p.get("rule_id").and_then(Value::as_str) == Some(K1_RULE)
                && p.get("output").and_then(Value::as_str) == Some("S")
                && p.get("metric").and_then(Value::as_str) == Some("RPS")
        });
        let primary_verdict = prim.and_then(|p| p.get("verdict")).and_then(Value::as_str).map(str::to_string);
        let model_value = prim.and_then(|p| p.get("model_value")).and_then(Value::as_f64);
        let v0_ci95_hi = block
            .and_then(|b| rps_cell(b, K2_RULE))
            .and_then(|x| x.get("ci95"))
            .and_then(Value::as_array)
            .filter(|a| a.len() == 2)
            .and_then(|a| a[1].as_f64());
        let near = scores.and_then(|d| near_era_of(d, c).ok().flatten());
        let near_era_label = near.as_ref().and_then(|n| n.label.clone());
        let k1 = primary_verdict.as_deref() == Some(VERDICT_PASS);
        let k2 = v0_ci95_hi.is_some_and(|hi| hi < 0.0);
        let k3 = near_era_label.as_deref().is_some_and(|l| l != NEAR_ERA_BREAKS);
        candidates.push(CandidateCheck {
            model_id: c.to_string(),
            in_index,
            primary_verdict,
            model_value,
            v0_ci95_hi,
            near_era_label,
            k1,
            k2,
            k3,
            eligible: in_index && sealed.is_some() && k1 && k2 && k3 && model_value.is_some(),
        });
    }
    if sealed.is_none() {
        return Featured { model_id: FEATURED_DEFAULT.into(), reason: REASON_VAULT_CLOSED, candidates };
    }
    let best = candidates
        .iter()
        .enumerate()
        .filter(|(_, c)| c.eligible)
        .min_by(|(ia, a), (ib, b)| {
            let (ka, kb) = (round3(a.model_value.unwrap_or(f64::MAX)), round3(b.model_value.unwrap_or(f64::MAX)));
            ka.partial_cmp(&kb).unwrap_or(std::cmp::Ordering::Equal).then(ia.cmp(ib))
        })
        .map(|(_, c)| c.model_id.clone());
    match best {
        Some(m) => Featured { model_id: m, reason: REASON_RULE, candidates },
        None => Featured { model_id: FEATURED_DEFAULT.into(), reason: REASON_NONE_ELIGIBLE, candidates },
    }
}

// ==================================================================== EK 3 §8.4: düşüş kartında öne çıkarma (SPEC_C_V0 §5.5)

/// (C) adayları, SPEC_C_V0 §5.5 basitlik sırasıyla (eşitlikte basit olan: addsale < h99 < pooled).
pub const FALL_CANDIDATES: [&str; 3] = ["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled"];
/// Yakın dönem etiketi "bozuyor" ile okunan aday (near_era bloğunun karşılaştırıcısı `fall_d10_v0_h99`); öteki iki aday
/// için near_era bloğu taban orana karşıdır ve k3 "aralık tamamen 0'ın üstünde değil" diye okunur.
pub const FALL_POOLED: &str = "fall_d10_v0_pooled";
/// k1: kasa birincil hücresi (`p_up` · D10 · Brier · `base_rate`); k2: aynı hücrenin `v1_5_h99`'a karşı karşılığı.
pub const FALL_K1_RULE: &str = "base_rate";
pub const FALL_K2_RULE: &str = "v1_5_h99";
pub const FALL_REASON_VAULT_CLOSED: &str = "VAULT_CLOSED";
pub const FALL_REASON_RULE: &str = "RULE_5_5";
pub const FALL_REASON_NONE_ELIGIBLE: &str = "RULE_5_5_NONE_ELIGIBLE";

/// (C) adayının k1–k3 durumu: yalnız dosyadaki `verdict`, `ci95` ve `near_era` alanlarının karşılaştırması (skor
/// hesaplanmaz). `first_failed`: sağlanmayan ilk koşul (`k1` | `k2` | `k3`; kart satırında düz metinle gösterilir).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FallCandidateCheck {
    pub model_id: String,
    pub in_index: bool,
    /// Kasa birincil hücresinin `verdict`'i ve modelin D10 Brier'i (dosyadaki değerler).
    pub primary_verdict: Option<String>,
    pub model_value: Option<f64>,
    /// `v1_5_h99`'a karşı hücrenin `ci95[1]`'i.
    pub v15_ci95_hi: Option<f64>,
    pub near_era_label: Option<String>,
    pub near_era_comparator: Option<String>,
    pub near_era_ci95_lo: Option<f64>,
    pub k1: bool,
    pub k2: bool,
    pub k3: bool,
    pub eligible: bool,
    pub first_failed: Option<&'static str>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FeaturedFall {
    /// Öne çıkan aday; kasa kapalıysa ya da uygun aday yoksa `None` (K-P4-1; V1.5 p_up sütunu olduğu gibi kalır).
    pub model_id: Option<String>,
    /// VAULT_CLOSED | RULE_5_5 | RULE_5_5_NONE_ELIGIBLE
    pub reason: &'static str,
    pub candidates: Vec<FallCandidateCheck>,
}

fn ci_at(cell: Option<&Value>, i: usize) -> Option<f64> {
    cell?.get("ci95")?.as_array().filter(|a| a.len() == 2)?[i].as_f64()
}

/// Kasa bloğunda modelin `p_up` · `D10` · `Brier` · `rule_id` hücresi.
fn fall_cell<'a>(block: &'a Value, rule_id: &str) -> Option<&'a Value> {
    block.get("cells")?.as_array()?.iter().find(|c| {
        c.get("output").and_then(Value::as_str) == Some("p_up")
            && c.get("horizon_or_k").and_then(Value::as_str) == Some("D10")
            && c.get("metric").and_then(Value::as_str) == Some("Brier")
            && c.get("rule_id").and_then(Value::as_str) == Some(rule_id)
    })
}

/// Düşüş kartının öne çıkarma kuralı (SPEC_C_V0 §5.5; EK 3 §8.4; K-P4-1): kasa bloğu (`oot_pre_h99_sealed`) yoksa öne çıkan
/// yok (`VAULT_CLOSED`, "kasa: bekliyor"); varsa her aday için k1 = kasa birincil hücresi (D10 Brier − `base_rate`)
/// "geçiyor"; k2 = `v1_5_h99`'a karşı aynı hücrenin aralık üst ucu < 0; k3 = `pooled` için yakın dönem etiketi "bozuyor"
/// değil, `h99`/`addsale` için yakın dönem (taban orana karşı) aralığı tamamen 0'ın üstünde değil (blok yoksa, sürüm
/// desteklenmiyorsa ya da karşılaştırıcı beklenen değilse k3 = false). Uygun adaylardan (round(model_value, 3), addsale <
/// h99 < pooled) en küçüğü; uygun yoksa öne çıkan yok (`RULE_5_5_NONE_ELIGIBLE`). Hiçbir model listeden kalkmaz (K4).
pub fn featured_fall(scores: Option<&Value>, oot: Option<&Value>, embedded_ids: &[String]) -> FeaturedFall {
    use super::scores_oot::{model_block, primary_cell, SEALED_BLOCK};
    let sealed = oot.filter(|d| d.get(SEALED_BLOCK).is_some());
    let mut candidates = Vec::new();
    for c in FALL_CANDIDATES {
        let in_index = embedded_ids.iter().any(|x| x == c);
        let block = sealed.and_then(|d| model_block(d, SEALED_BLOCK, c));
        let prim = block.and_then(primary_cell).filter(|p| {
            p.get("rule_id").and_then(Value::as_str) == Some(FALL_K1_RULE)
                && p.get("output").and_then(Value::as_str) == Some("p_up")
                && p.get("horizon_or_k").and_then(Value::as_str) == Some("D10")
                && p.get("metric").and_then(Value::as_str) == Some("Brier")
        });
        let primary_verdict = prim.and_then(|p| p.get("verdict")).and_then(Value::as_str).map(str::to_string);
        let model_value = prim.and_then(|p| p.get("model_value")).and_then(Value::as_f64);
        let v15_ci95_hi = ci_at(block.and_then(|b| fall_cell(b, FALL_K2_RULE)), 1);
        let near = scores.and_then(|d| near_era_of(d, c).ok().flatten()).filter(|n| n.supported);
        let near_era_label = near.as_ref().and_then(|n| n.label.clone());
        let near_era_comparator = near.as_ref().and_then(|n| n.comparator.clone());
        let near_era_ci95_lo = near.as_ref().and_then(|n| n.ci95.as_ref()).and_then(Value::as_array).filter(|a| a.len() == 2).and_then(|a| a[0].as_f64());
        let k1 = primary_verdict.as_deref() == Some(VERDICT_PASS);
        let k2 = v15_ci95_hi.is_some_and(|hi| hi < 0.0);
        let k3 = if c == FALL_POOLED {
            near_era_label.as_deref().is_some_and(|l| l != NEAR_ERA_BREAKS)
        } else {
            near_era_comparator.as_deref() == Some(FALL_K1_RULE) && near_era_ci95_lo.is_some_and(|lo| !(lo > 0.0))
        };
        let first_failed = if !k1 {
            Some("k1")
        } else if !k2 {
            Some("k2")
        } else if !k3 {
            Some("k3")
        } else {
            None
        };
        candidates.push(FallCandidateCheck {
            model_id: c.to_string(),
            in_index,
            primary_verdict,
            model_value,
            v15_ci95_hi,
            near_era_label,
            near_era_comparator,
            near_era_ci95_lo,
            k1,
            k2,
            k3,
            eligible: in_index && sealed.is_some() && k1 && k2 && k3 && model_value.is_some(),
            first_failed: sealed.and(first_failed),
        });
    }
    if sealed.is_none() {
        return FeaturedFall { model_id: None, reason: FALL_REASON_VAULT_CLOSED, candidates };
    }
    let best = candidates
        .iter()
        .enumerate()
        .filter(|(_, c)| c.eligible)
        .min_by(|(ia, a), (ib, b)| {
            let (ka, kb) = (round3(a.model_value.unwrap_or(f64::MAX)), round3(b.model_value.unwrap_or(f64::MAX)));
            ka.partial_cmp(&kb).unwrap_or(std::cmp::Ordering::Equal).then(ia.cmp(ib))
        })
        .map(|(_, c)| c.model_id.clone());
    match best {
        Some(m) => FeaturedFall { model_id: Some(m), reason: FALL_REASON_RULE, candidates },
        None => FeaturedFall { model_id: None, reason: FALL_REASON_NONE_ELIGIBLE, candidates },
    }
}

// ==================================================================== EK 3 §6.5: D1 sonrası skorlar (scores_post_d1.json)

/// `scores/scores_post_d1.json` (SPEC_DEVIATIONS H28; L1). Gömülmez: yalnız repo modunda okunur ("dosya yok" / "repo modu
/// ister" durumları ayrı). Ölçek `live_post_d1`: hiçbir ölçekle birleşmez; panelde ayrı bölüm.
pub const SCORES_POST_D1_SCHEMA: &str = "borsai.scores_post_d1/1";
pub const POST_D1_PRIMARY_RULE: &str = "ceiling_hazard_v0";

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScoresPostD1View {
    /// REPO (okundu) | NO_REPO (repo modu değil) | NO_FILE (dosya yok)
    pub status: &'static str,
    pub path: Option<String>,
    pub sha12: Option<String>,
    pub generated_at_utc: Option<String>,
    pub as_of_session: Option<String>,
    pub unsupported_version: Option<String>,
    pub integrity: Option<IntegrityProblem>,
    pub doc: Option<Value>,
}

/// §2.3 + H40 kuralları `conditional_j1` bloğuna: n < 10 iken hücre ya da betimleyici yok; n_live + n_late = n_scored;
/// hüküm/aralık kuralı her hücrede.
pub fn check_integrity_post_d1(doc: &Value) -> Option<IntegrityProblem> {
    for m in doc.get("models").and_then(Value::as_array).into_iter().flatten() {
        let id = m.get("model_id").and_then(Value::as_str).unwrap_or("?");
        let Some(b) = m.get("conditional_j1") else { continue };
        let n = u(b, "n_scored");
        if n < MIN_N_METRIC && arr_len(b, "cells") > 0 {
            return Some(IntegrityProblem::new(
                rules::CONDITIONAL_CELLS_BELOW_MIN_N,
                Some(id),
                format!("post_d1 j = 1: n_scored = {n} < {MIN_N_METRIC}, cells = {}", arr_len(b, "cells")),
            ));
        }
        if n < MIN_N_METRIC && arr_len(b, "descriptive") > 0 {
            return Some(IntegrityProblem::new(
                rules::LIVE_DESCRIPTIVE_BELOW_MIN_N,
                Some(id),
                format!("post_d1 j = 1: n_scored = {n} < {MIN_N_METRIC}, descriptive = {}", arr_len(b, "descriptive")),
            ));
        }
        if u(b, "n_live") + u(b, "n_late") != n {
            return Some(IntegrityProblem::new(
                rules::CONDITIONAL_N_SPLIT,
                Some(id),
                format!("post_d1 j = 1: n_live = {} + n_late = {} ≠ n_scored = {n}", u(b, "n_live"), u(b, "n_late")),
            ));
        }
        if let Some(p) = check_cells(b, "cells", id, "D1 sonrası j = 1") {
            return Some(p);
        }
    }
    None
}

pub fn scores_post_d1_from(text: &str, path: &Path) -> Result<ScoresPostD1View, AppError> {
    let doc: Value = serde_json::from_str(text).map_err(|e| super::io_error("scores_post_d1.json", e))?;
    let s = |k: &str| doc.get(k).and_then(Value::as_str).map(str::to_string);
    let mut view = ScoresPostD1View {
        status: "REPO",
        path: Some(path.display().to_string()),
        sha12: Some(sha256_hex(text.as_bytes())[..12].to_string()),
        generated_at_utc: s("generated_at_utc"),
        as_of_session: s("as_of_session"),
        unsupported_version: None,
        integrity: None,
        doc: None,
    };
    let version = s("schema_version").unwrap_or_default();
    if version != SCORES_POST_D1_SCHEMA {
        view.unsupported_version = Some(version);
        return Ok(view);
    }
    view.integrity = check_integrity_post_d1(&doc);
    if view.integrity.is_none() {
        view.doc = Some(doc);
    }
    Ok(view)
}

pub fn scores_post_d1_path_in(repo: &Path) -> std::path::PathBuf {
    repo.join("scores").join("scores_post_d1.json")
}

fn scores_post_d1_none(status: &'static str) -> ScoresPostD1View {
    ScoresPostD1View {
        status,
        path: None,
        sha12: None,
        generated_at_utc: None,
        as_of_session: None,
        unsupported_version: None,
        integrity: None,
        doc: None,
    }
}

/// Kökteki `scores/scores_post_d1.json` (repo ya da kişisel modda gömülü anlık görüntü; FAZ9_SNAPSHOT); yoksa `NO_FILE`.
pub fn scores_post_d1_in(root: &Path) -> Result<ScoresPostD1View, AppError> {
    let p = scores_post_d1_path_in(root);
    match std::fs::read_to_string(&p) {
        Ok(text) => scores_post_d1_from(&text, &p),
        Err(_) => Ok(ScoresPostD1View { path: Some(p.display().to_string()), ..scores_post_d1_none("NO_FILE") }),
    }
}

/// Repo modu ister; dosya yoksa `NO_FILE`.
pub fn scores_post_d1_value(state: &AppState) -> Result<ScoresPostD1View, AppError> {
    let Some(repo) = state.repo() else { return Ok(scores_post_d1_none("NO_REPO")) };
    scores_post_d1_in(&repo.root)
}

#[tauri::command]
pub fn scores_post_d1_view(state: tauri::State<'_, AppState>) -> Result<ScoresPostD1View, AppError> {
    scores_post_d1_value(&state)
}

/// Kartın "canlı sicil" sütunu (K-P2-3): `conditional_j1.n_live` ve n ≥ 10 ise birincil hücrenin (S_cond · RPS ·
/// ceiling_hazard_v0) dosyadaki verdict'i.
pub fn post_d1_live_of(doc: &Value, model_id: &str) -> LiveView {
    let Some(b) = model_of(doc, model_id).and_then(|m| m.get("conditional_j1")) else { return LiveView::default() };
    LiveView {
        n_scored: b.get("n_live").and_then(Value::as_u64),
        verdict: b
            .get("cells")
            .and_then(Value::as_array)
            .and_then(|cells| {
                cells.iter().find(|c| {
                    c.get("output").and_then(Value::as_str) == Some("S_cond")
                        && c.get("metric").and_then(Value::as_str) == Some("RPS")
                        && c.get("rule_id").and_then(Value::as_str) == Some(POST_D1_PRIMARY_RULE)
                })
            })
            .and_then(|c| c.get("verdict").cloned()),
    }
}
