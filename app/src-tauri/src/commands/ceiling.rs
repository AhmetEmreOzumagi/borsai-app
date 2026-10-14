//! Tavan serisi görüntüleme türevleri ve koşullu güncelleme (SPEC_APP §3b grup B, §3g, EK 1).
//!
//! - Koşullu değerler yalnız `borsai_predict::survival::conditional`'dan (S_k / S_j, tek bölme).
//! - Beklenen L = Σ l·P_L[l] ve medyan L = en küçük l ile Σ_{i≤l} P_L[i] ≥ 0.5: görüntüleme türevi,
//!   kayıtlara yazılmaz. Koşullu hâlde aynı formüller koşullu P_L'ye uygulanır.
//! - Gözlenen seri j YALNIZ `<repo>/data/outcomes/<T>.csv`'den gelir (resmi j), SALT OKUMA.
//!   Kullanıcı beyanı ("seri sürüyor") yalnız bir ETİKETTİR: bu modülün hiçbir imzasında ve hiçbir
//!   hesap yolunda geçmez (SPEC_APP §3g, §5.6 U52; proje sahibi kararı 2026-09-23). Beyan yalnız
//!   ön uçtaki şerit etiketi render'ında ve kişisel kayıt modülünde (`commands/scenario.rs`) durur.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;

use borsai_predict::features::parse_decimal;
use borsai_predict::survival::{conditional, p_streak, DAYS};
use borsai_predict::ModelRef;

use super::inputs_doc::valid_ticker;
use super::{io_error, AppError, INVALID_ARGUMENT};
use crate::state::AppState;

/// "Her zaman tavan" sabit satırı (S_k ≡ 1; SPEC_DEVIATIONS C4): model çıktısı değil.
pub const ALWAYS_CEILING_ID: &str = "ALWAYS_CEILING";
pub const OUTCOMES_INVALID: &str = "OUTCOMES_INVALID";
pub const DAY_STATES: [&str; 4] = ["CEILING", "NOT_CEILING", "PENDING", "NO_LABEL"];
/// Kabul edilen tek beyan türü: "seri sürüyor" (o gün tavan kapandı). NOT_CEILING ve PENDING
/// beyanları kalktı; şema sürümü değişmez, kabul edilen değerler daralır (U52-2).
pub const USER_DAY_STATES: [&str; 1] = ["CEILING"];

#[derive(Debug, Clone, Deserialize)]
pub struct SVector {
    pub model_id: String,
    #[serde(rename = "S")]
    pub s: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CondView {
    /// k = 1..10; k ≤ j → null.
    #[serde(rename = "S_cond")]
    pub s_cond: Vec<Option<f64>>,
    /// l = 0..10; l < j → null.
    #[serde(rename = "P_L_cond")]
    pub p_l_cond: Vec<Option<f64>>,
    pub p_break_next: f64,
    pub expected_l: f64,
    /// E[L | L ≥ j] − j
    pub expected_remaining: f64,
    pub median_l: usize,
    /// En olası l (koşullu P_L üzerinde, l ≥ j; eşitlikte en küçük l). Görüntüleme türevi, kayda yazılmaz.
    pub mode_l: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CeilingRow {
    pub model_id: String,
    pub constant: bool,
    #[serde(rename = "S")]
    pub s: Vec<f64>,
    #[serde(rename = "P_L")]
    pub p_l: Vec<f64>,
    pub expected_l: f64,
    pub median_l: usize,
    /// En olası l = argmax_l P(L = l), l = 0..10; eşitlikte en küçük l (EK 3 §5.2). Görüntüleme türevi.
    pub mode_l: usize,
    /// Seçilen j'de; tanımsızsa (j ≥ 10 ya da S_j = 0) null.
    pub cond: Option<CondView>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PriceHint {
    pub k: u32,
    pub price: f64,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CeilingDisplay {
    pub j: usize,
    pub rows: Vec<CeilingRow>,
    /// "seri k gün sürerse kapanış ≈ arz fiyatı × 1.1^k" (SPEC_CEILING_V0 §8), k = 1, 3, 5, 10.
    pub price_hint: Option<Vec<PriceHint>>,
    /// Hesaplayıcı eki (FAZ9_UI_FIX K-FIX-3): kuralın koşullu değeri ve model gün grupları. Yalnız komut katmanı doldurur
    /// (`attach_calc`); saf `ceiling_display_value` çıktısında yoktur ve serileştirilmez (eski sözleşme aynen).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub calc: Option<CalcView>,
}

/// Hesaplayıcının karşılaştırma kuralı (K-FIX-3): eğitimdeki tüm arzların tablosu.
pub const CALC_RULE_ID: &str = "base_km_expanding";
/// S × n'nin tam sayı sayılma toleransı (K-FIX-3: tutmuyorsa yalnız oran gösterilir, sayım null).
pub const CALC_COUNT_TOL: f64 = 1e-9;

/// "Geçmiş arzlarda": kuralın seçilen j'deki koşullu değeri; kaynak aynı display satırı (`conditional`, S_0 = 1).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CalcHistory {
    pub rule_id: String,
    /// Kural satırı display'de var (kayıt ya da koşu kuralı içeriyor); yoksa öbür alanlar null.
    pub in_rows: bool,
    /// P(L ≥ j+1 | L ≥ j) = S_{j+1} / S_j: kural satırının `cond.S_cond[j]` değeri aynen; tanımsızsa null.
    pub p_next: Option<f64>,
    /// Kuralın seçilen j'ye koşullu eğrisi (`cond.S_cond` aynen; k ≤ j null); eğride ince gri kesikli çizgi.
    pub s_cond: Vec<Option<f64>>,
    /// Model dosyasındaki eğitim arz sayısı (`training.n`).
    pub n_train: Option<u64>,
    /// S_j × n ve S_{j+1} × n: ikisi de CALC_COUNT_TOL içinde tam sayıysa sayımlar ("j gün tavan yapan n_at_j arzdan
    /// n_next tanesi"); değilse null.
    pub n_at_j: Option<u64>,
    pub n_next: Option<u64>,
}

/// Model dosyasındaki `day_groups` (anahtar sırasıyla g1, g2, …): her grup gün listesi. Ekran metni bundan kurulur,
/// sabit "4–10" yazılmaz.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct DayGroups {
    pub model_id: String,
    pub groups: Vec<Vec<usize>>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CalcView {
    pub j: usize,
    pub history: CalcHistory,
    /// Display satırlarından dosyasında `day_groups` taşıyan modeller (ön uç öne çıkan modeli kimliğiyle seçer).
    pub day_groups: Vec<DayGroups>,
}

fn integer_count(x: f64) -> Option<u64> {
    let r = x.round();
    ((x - r).abs() <= CALC_COUNT_TOL && r >= 0.0).then_some(r as u64)
}

/// Hesaplayıcı eki: değerler display satırlarından (aynı yol), n ve gün grupları gömülü model dosyalarından (`ModelRef.params`).
pub fn calc_view_value(rows: &[CeilingRow], j: usize, models: &[ModelRef]) -> CalcView {
    let params = |id: &str| models.iter().find(|m| m.model_id == id).map(|m| &m.params);
    let rule = rows.iter().find(|r| r.model_id == CALC_RULE_ID);
    let cond = rule.and_then(|r| r.cond.as_ref());
    let n_train = params(CALC_RULE_ID).and_then(|p| p.pointer("/training/n")).and_then(Value::as_u64);
    let s_j = rule.and_then(|r| if j == 0 { Some(1.0) } else { r.s.get(j - 1).copied() });
    let s_next = rule.and_then(|r| r.s.get(j).copied());
    let counts = match (n_train, s_j, s_next, cond) {
        (Some(n), Some(a), Some(b), Some(_)) => integer_count(a * n as f64).zip(integer_count(b * n as f64)),
        _ => None,
    };
    let history = CalcHistory {
        rule_id: CALC_RULE_ID.into(),
        in_rows: rule.is_some(),
        p_next: cond.and_then(|c| c.s_cond.get(j).copied().flatten()),
        s_cond: cond.map(|c| c.s_cond.clone()).unwrap_or_default(),
        n_train,
        n_at_j: counts.map(|(a, _)| a),
        n_next: counts.map(|(_, b)| b),
    };
    let day_groups = rows
        .iter()
        .filter_map(|r| {
            let g = params(&r.model_id)?.get("day_groups")?.as_object()?;
            let mut keys: Vec<&String> = g.keys().collect();
            keys.sort_by_key(|k| (k.len(), k.as_str()));
            let groups = keys
                .iter()
                .map(|k| g[*k].as_array().into_iter().flatten().filter_map(|d| d.as_u64().map(|d| d as usize)).collect())
                .collect();
            Some(DayGroups { model_id: r.model_id.clone(), groups })
        })
        .collect();
    CalcView { j, history, day_groups }
}

/// Komut katmanı: display'e hesaplayıcı ekini takar (senaryo `ceiling_display`, resmi görünüm `record_ceiling`).
pub fn attach_calc(d: &mut CeilingDisplay, models: &[ModelRef]) {
    d.calc = Some(calc_view_value(&d.rows, d.j, models));
}

/// Σ l·P_L[l] (tanımsız hücreler 0 sayılır).
pub fn expected_l(p_l: &[Option<f64>]) -> f64 {
    let mut acc = 0.0;
    for (l, p) in p_l.iter().enumerate() {
        acc += l as f64 * p.unwrap_or(0.0);
    }
    acc
}

/// En olası l: tanımlı hücreler içinde en büyük P_L[l]; eşitlikte en küçük l (yalnız karşılaştırma, aritmetik yok).
pub fn mode_l(p_l: &[Option<f64>]) -> usize {
    let mut best: Option<(usize, f64)> = None;
    for (l, p) in p_l.iter().enumerate() {
        if let Some(p) = *p {
            if best.map_or(true, |(_, b)| p > b) {
                best = Some((l, p));
            }
        }
    }
    best.map_or(0, |(l, _)| l)
}

/// En küçük l ile Σ_{i≤l} P_L[i] ≥ 0.5.
pub fn median_l(p_l: &[Option<f64>]) -> usize {
    let mut cum = 0.0;
    for (l, p) in p_l.iter().enumerate() {
        cum += p.unwrap_or(0.0);
        if cum >= 0.5 {
            return l;
        }
    }
    p_l.len().saturating_sub(1)
}

fn row(model_id: &str, constant: bool, s: &[f64], j: usize) -> CeilingRow {
    let p_l = p_streak(s);
    let p_l_opt: Vec<Option<f64>> = p_l.iter().copied().map(Some).collect();
    let cond = conditional(s, j).map(|c| {
        let e = expected_l(&c.p_l_cond);
        CondView {
            expected_l: e,
            expected_remaining: e - j as f64,
            median_l: median_l(&c.p_l_cond),
            mode_l: mode_l(&c.p_l_cond),
            s_cond: c.s_cond,
            p_l_cond: c.p_l_cond,
            p_break_next: c.p_break_next,
        }
    });
    CeilingRow {
        model_id: model_id.into(),
        constant,
        s: s.to_vec(),
        expected_l: expected_l(&p_l_opt),
        median_l: median_l(&p_l_opt),
        mode_l: mode_l(&p_l_opt),
        p_l,
        cond,
    }
}

pub fn ceiling_display_value(models: &[SVector], j: usize, ipo_price_tl: Option<&str>) -> Result<CeilingDisplay, AppError> {
    let mut rows = Vec::with_capacity(models.len() + 1);
    for m in models {
        if m.s.len() != DAYS || m.s.iter().any(|x| !x.is_finite()) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("{}: S 10 sonlu sayı olmalı", m.model_id)));
        }
        rows.push(row(&m.model_id, false, &m.s, j));
    }
    rows.push(row(ALWAYS_CEILING_ID, true, &[1.0; DAYS], j));
    let price = ipo_price_tl
        .and_then(|p| parse_decimal(Some(&Value::String(p.to_string())), "ipo_price_tl", false).ok().flatten())
        .filter(|d| d.signum() > 0)
        .map(|d| d.to_f64());
    let price_hint = price.map(|p| [1u32, 3, 5, 10].iter().map(|&k| PriceHint { k, price: p * 1.1f64.powi(k as i32) }).collect());
    Ok(CeilingDisplay { j, rows, price_hint, calc: None })
}

/// Senaryo yolu; hesaplayıcı eki gömülü model dosyalarından (bütünlük hatasında ek yok, display yine döner).
#[tauri::command]
pub fn ceiling_display(
    state: tauri::State<'_, AppState>,
    models: Vec<SVector>,
    j: usize,
    ipo_price_tl: Option<String>,
) -> Result<CeilingDisplay, AppError> {
    let mut d = ceiling_display_value(&models, j, ipo_price_tl.as_deref())?;
    if let Ok(m) = state.models.as_ref() {
        attach_calc(&mut d, &m.models);
    }
    Ok(d)
}

// ---------------------------------------------------------------- gözlenen seri (şerit)

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct StreakDay {
    pub h: usize,
    pub session_date: Option<String>,
    /// Dosyadan (tek kaynak): CEILING | NOT_CEILING | PENDING | NO_LABEL | null (satır ya da dosya yok).
    pub file: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct StreakView {
    pub ticker: Option<String>,
    /// FOUND | MISSING | NO_REPO | NO_TICKER
    pub file_status: &'static str,
    pub file_rel_path: Option<String>,
    /// Dosyadaki son dolu `session_date`.
    pub as_of: Option<String>,
    pub days: Vec<StreakDay>,
    /// Resmi j: yalnız dosyadan; dosya yoksa null. Kullanıcı beyanı bu değeri DEĞİŞTİRMEZ (U52).
    pub j_observed: Option<usize>,
    /// Seri bozuldu: gerçekleşen L = j_observed.
    pub broken: bool,
    /// Etiketsiz gün (NA_LIMIT / TARGET_UNAVAILABLE) serinin sayımını durdurdu.
    pub unlabeled: bool,
}

struct FileDay {
    session_date: Option<String>,
    /// `status` sütunu aynen (OK | NA_LIMIT | TARGET_UNAVAILABLE | PENDING).
    status_raw: String,
    state: &'static str,
    /// `close_raw` (metin, aynen): yalnız `status = OK` satırlarında dolu.
    close_raw: Option<String>,
}

/// `data/outcomes/<T>.csv` (Faz 2B, `borsai/outcomes.py`): h = 1..10 satırları.
fn read_outcomes(path: &Path) -> Result<Vec<Option<FileDay>>, AppError> {
    let text = std::fs::read_to_string(path).map_err(|e| io_error("outcomes", e))?;
    let invalid = |m: String| AppError::new(OUTCOMES_INVALID, m);
    let mut lines = text.lines();
    let header: Vec<&str> = lines.next().ok_or_else(|| invalid("boş dosya".into()))?.trim_start_matches('\u{feff}').split(',').collect();
    let col = |name: &str| header.iter().position(|h| *h == name).ok_or_else(|| invalid(format!("sütun yok: {name}")));
    let (ch, cd, cc, cs, cr) = (col("h")?, col("session_date")?, col("ceiling_close")?, col("status")?, col("close_raw")?);
    let mut days: Vec<Option<FileDay>> = (0..DAYS).map(|_| None).collect();
    for line in lines.filter(|l| !l.trim().is_empty()) {
        if line.contains('"') {
            return Err(invalid("tırnaklı alan beklenmiyor".into()));
        }
        let cells: Vec<&str> = line.split(',').collect();
        if cells.len() != header.len() {
            return Err(invalid(format!("sütun sayısı: {line}")));
        }
        let h: usize = cells[ch].parse().map_err(|_| invalid(format!("h: {}", cells[ch])))?;
        if !(1..=DAYS).contains(&h) {
            return Err(invalid(format!("h aralık dışı: {h}")));
        }
        let state = match (cells[cs], cells[cc]) {
            ("OK", "1") => "CEILING",
            ("OK", "0") => "NOT_CEILING",
            ("OK", _) | ("NA_LIMIT", _) | ("TARGET_UNAVAILABLE", _) => "NO_LABEL",
            ("PENDING", _) => "PENDING",
            (other, _) => return Err(invalid(format!("status {other:?}"))),
        };
        let date = Some(cells[cd].to_string()).filter(|s| !s.is_empty());
        let close_raw = Some(cells[cr].to_string()).filter(|s| !s.is_empty() && cells[cs] == "OK");
        days[h - 1] = Some(FileDay { session_date: date, status_raw: cells[cs].to_string(), state, close_raw });
    }
    Ok(days)
}

/// Resmi kapanışlar (`close_raw`, metin aynen) ve seans tarihleri; h = 1..10, yoksa `None`.
/// SALT OKUMA; kullanıcı beyanı bu yola hiç girmez (U52).
pub fn read_closes_in(outcomes_dir: &Path, ticker: &str) -> Result<Vec<Option<(String, Option<String>)>>, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let p = outcomes_dir.join(format!("{ticker}.csv"));
    if !p.is_file() {
        return Ok((0..DAYS).map(|_| None).collect());
    }
    Ok(read_outcomes(&p)?
        .into_iter()
        .map(|d| d.and_then(|x| x.close_raw.map(|c| (c, x.session_date))))
        .collect())
}

/// h = 1 satırı: (`status` aynen, `session_date`); dosya ya da satır yoksa `None`. D1 sonrası sihirbazın ön koşulu
/// (EK 3 §6.6 adım 1; Python `freeze.d1_session`: OK ya da NA_LIMIT ve tarih dolu ise D_1 oluşmuştur). SALT OKUMA.
pub fn outcome_day1_in(outcomes_dir: &Path, ticker: &str) -> Result<Option<(String, Option<String>)>, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let p = outcomes_dir.join(format!("{ticker}.csv"));
    if !p.is_file() {
        return Ok(None);
    }
    Ok(read_outcomes(&p)?.into_iter().next().flatten().map(|d| (d.status_raw, d.session_date)))
}

/// Şerit ve resmi j. İmzada beyan parametresi YOKTUR (U52-5): beyan bir etikettir, ön uçta kalır.
pub fn streak_view_in(outcomes_dir: Option<&Path>, ticker: Option<&str>) -> Result<StreakView, AppError> {
    let ticker = ticker.map(str::trim).filter(|t| !t.is_empty());
    if let Some(t) = ticker {
        if !valid_ticker(t) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {t:?}")));
        }
    }
    let (file_status, rel, file_days) = match (outcomes_dir, ticker) {
        (None, _) => ("NO_REPO", None, None),
        (Some(_), None) => ("NO_TICKER", None, None),
        (Some(dir), Some(t)) => {
            let rel = format!("data/outcomes/{t}.csv");
            let p = dir.join(format!("{t}.csv"));
            if p.is_file() {
                ("FOUND", Some(rel), Some(read_outcomes(&p)?))
            } else {
                ("MISSING", Some(rel), None)
            }
        }
    };
    let as_of = file_days
        .as_ref()
        .and_then(|d| d.iter().flatten().filter_map(|x| x.session_date.clone()).max());
    let mut days = Vec::with_capacity(DAYS);
    for i in 0..DAYS {
        let fd = file_days.as_ref().and_then(|d| d[i].as_ref());
        days.push(StreakDay {
            h: i + 1,
            session_date: fd.and_then(|x| x.session_date.clone()),
            file: fd.map(|x| x.state.to_string()),
        });
    }
    let mut j = 0;
    let (mut broken, mut unlabeled) = (false, false);
    for d in &days {
        match d.file.as_deref() {
            Some("CEILING") => j += 1,
            Some("NOT_CEILING") => {
                broken = true;
                break;
            }
            Some("NO_LABEL") => {
                unlabeled = true;
                break;
            }
            _ => break,
        }
    }
    let observed = file_days.is_some();
    Ok(StreakView {
        ticker: ticker.map(str::to_string),
        file_status,
        file_rel_path: rel,
        as_of,
        days,
        j_observed: observed.then_some(j),
        broken: observed && broken,
        unlabeled: observed && unlabeled,
    })
}

#[tauri::command]
pub fn streak_view(state: tauri::State<'_, AppState>, ticker: Option<String>) -> Result<StreakView, AppError> {
    let dir = state.repo().map(|r| r.root.join("data").join("outcomes"));
    streak_view_in(dir.as_deref(), ticker.as_deref())
}

// ---------------------------------------------------------------- "Tavan serisi — kaç gün tavan?" kartı (EK 3 §5)
//
// Kart hiçbir sayı ÜRETMEZ: satır değerleri `row` (ceiling_display) çıktısından, terazi sütunları `scores.json`
// (yakın dönem, canlı) ve `scores_oot.json` (kasa) okuyucularından, öne çıkan `scores::featured_ceiling`'den gelir.
// Beyan (U52) bu komutlara girmez: imzada beyan parametresi yok; beyan resmi verinin önündeyse koşullu satırı ön uç
// "resmi kapanış bekleniyor" ile değiştirir.

use super::predict::{tufe_info_value, TufeInfo};
use super::scores::{featured_ceiling, live_of, near_era_of, scores_doc, Featured, IntegrityProblem, LiveView, NearEraView};
use super::scores_oot::{info_of, model_block, primary_cell, scores_oot_doc, ScoresOotDoc, ScoresOotInfo, SEALED_BLOCK};

/// Kart satır sırası (EK 3 §5.2-6): öne çıkan → v1 adayları (INDEX sırası) → v0 (öne çıkan değilse) → kurallar →
/// PB aynası → her zaman tavan.
pub const SUMMARY_CANDIDATES: [&str; 4] =
    ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v0"];
pub const SUMMARY_RULES: [&str; 4] = ["ceiling_hazard_v1_pooled@INF", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10"];
pub const SUMMARY_PB: [&str; 2] = ["pb_ceiling_v0", "pb_ceiling_v0@INF"];
const F3_MISSING_CODE: &str = "F3_MISSING";

/// Kartın girdisi: bir modelin sonucu (predict_all satırı ya da dondurulmuş kayıt hücresi).
#[derive(Debug, Clone, Deserialize)]
pub struct SummaryModel {
    pub model_id: String,
    pub status: String,
    #[serde(default)]
    pub refusal: Value,
    #[serde(default)]
    pub output: Value,
}

impl SummaryModel {
    fn s(&self) -> Option<Vec<f64>> {
        (self.status == "PREDICTED").then(|| serde_json::from_value(self.output.get("S")?.clone()).ok()).flatten()
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SummaryCond {
    pub p_break_next: f64,
    pub expected_remaining: f64,
    pub median_l: usize,
    pub mode_l: usize,
    /// P(L = mode_l | L ≥ j)
    pub p_mode: Option<f64>,
    /// P(L ≥ 5 | L ≥ j), P(L = 10 | L ≥ j) = S_cond[4], S_cond[9]; k ≤ j → null
    pub s_cond_5: Option<f64>,
    pub s_cond_10: Option<f64>,
}

/// Zaman-dışı (kasa) sütunu: CLOSED = kasa bloğu yok ("kasa: bekliyor"); OPEN = birincil hücrenin dosyadaki verdict'i
/// (hücre yoksa null → "—"); UNAVAILABLE = dosya yok.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct VaultView {
    pub status: &'static str,
    pub verdict: Option<String>,
    pub diff: Option<Value>,
    pub ci95: Option<Value>,
    pub n: Option<u64>,
    pub rule_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct SummaryRow {
    pub model_id: String,
    /// FEATURED | CANDIDATE | RULE | PB | CONSTANT
    pub role: &'static str,
    /// Resmi görünüm: kayıt bu modeli içermiyor (kayıt INDEX'ten eski) → false.
    pub in_record: bool,
    pub status: Option<String>,
    /// Ret ya da hata: `{code, field}` (dosyadaki/çıktıdaki gibi).
    pub refused: Option<Value>,
    pub expected_l: Option<f64>,
    pub median_l: Option<usize>,
    pub mode_l: Option<usize>,
    /// En olası bozulma günü D{mode_l + 1} (1 ≤ mode_l ≤ 9); mode_l = 0 (D1'de tavan yok) ve 10 (sansürlü) → null.
    pub mode_break_day: Option<usize>,
    /// P(L = mode_l)
    pub p_mode: Option<f64>,
    /// P(L ≥ 3) = S[2], P(L ≥ 5) = S[4], P(L = 10) = S[9]
    pub p_ge3: Option<f64>,
    pub p_ge5: Option<f64>,
    pub p_10: Option<f64>,
    pub cond: Option<SummaryCond>,
    pub near_era: Option<NearEraView>,
    pub vault: VaultView,
    pub live: LiveView,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScoresSourceInfo {
    pub source: &'static str,
    pub sha12: String,
    pub generated_at_utc: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CeilingSummary {
    pub featured: Featured,
    pub featured_params_sha256: Option<String>,
    pub j: usize,
    /// OFFICIAL (gözlenen j) | HYPOTHETICAL | NONE (j = 0)
    pub j_source: &'static str,
    pub official: bool,
    /// Resmi görünümde kayıt dosyası.
    pub record_file: Option<String>,
    /// f3 boş (v0 F3_MISSING): PB aynası satırları açık.
    pub f3_missing: bool,
    pub rows: Vec<SummaryRow>,
    /// Fail-closed: skor dosyalarından biri sözleşmeye aykırı → kart yerine ihlal gösterilir.
    pub integrity: Option<IntegrityProblem>,
    pub scores: Option<ScoresSourceInfo>,
    pub oot: Option<ScoresOotInfo>,
    pub tufe: Option<TufeInfo>,
    /// "Düşüş (D10)" kartı (EK 3 §8.4; `commands::fall`): komut katmanı doldurur (gömülü kümede (C) yoksa null).
    pub fall: Option<super::fall::FallSummary>,
}

pub(crate) fn vault_of(oot: Option<&ScoresOotDoc>, model_id: &str) -> VaultView {
    let none = |status| VaultView { status, verdict: None, diff: None, ci95: None, n: None, rule_id: None };
    let Some(d) = oot.and_then(ScoresOotDoc::usable) else { return none("UNAVAILABLE") };
    if d.get(SEALED_BLOCK).is_none() {
        return none("CLOSED");
    }
    let Some(c) = model_block(d, SEALED_BLOCK, model_id).and_then(primary_cell) else { return none("OPEN") };
    VaultView {
        status: "OPEN",
        verdict: c.get("verdict").and_then(Value::as_str).map(str::to_string),
        diff: c.get("diff").cloned(),
        ci95: c.get("ci95").cloned(),
        n: c.get("n").and_then(Value::as_u64),
        rule_id: c.get("rule_id").and_then(Value::as_str).map(str::to_string),
    }
}

/// Kartı derler (saf; testler doğrudan çağırır). `embedded_ids`: gömülü model kümesi (INDEX sırası).
#[allow(clippy::too_many_arguments)]
pub fn ceiling_summary_value(
    models: &[SummaryModel],
    j: usize,
    j_observed: Option<usize>,
    official: bool,
    record_file: Option<String>,
    embedded: &[(String, String)],
    scores: Option<(&Value, &'static str, &str)>,
    oot: Option<&ScoresOotDoc>,
    tufe: Option<TufeInfo>,
) -> CeilingSummary {
    let ids: Vec<String> = embedded.iter().map(|(id, _)| id.clone()).collect();
    let sdoc = scores.map(|(d, ..)| d);
    let featured = featured_ceiling(sdoc, oot.and_then(ScoresOotDoc::usable), &ids);
    let mut integrity = oot.and_then(|d| d.integrity.clone());
    let by_id = |id: &str| models.iter().find(|m| m.model_id == id);
    let f3_missing = by_id("ceiling_hazard_v0")
        .and_then(|m| m.refusal.get("code"))
        .and_then(Value::as_str)
        == Some(F3_MISSING_CODE);
    let mut order: Vec<(&str, &'static str)> = vec![(featured.model_id.as_str(), "FEATURED")];
    for c in SUMMARY_CANDIDATES {
        if c != featured.model_id {
            order.push((c, "CANDIDATE"));
        }
    }
    order.extend(SUMMARY_RULES.iter().map(|r| (*r, "RULE")));
    order.extend(SUMMARY_PB.iter().map(|r| (*r, "PB")));
    let mut rows = Vec::new();
    for (id, role) in order {
        if !ids.iter().any(|x| x == id) {
            continue; // gömülü kümede yok
        }
        let m = by_id(id);
        let near_era = match sdoc.map(|d| near_era_of(d, id)) {
            Some(Ok(v)) => v,
            Some(Err(p)) => {
                integrity.get_or_insert(p);
                None
            }
            None => None,
        };
        let mut r = SummaryRow {
            model_id: id.to_string(),
            role,
            in_record: m.is_some(),
            status: m.map(|m| m.status.clone()),
            refused: m.filter(|m| m.status != "PREDICTED").map(|m| m.refusal.clone()),
            expected_l: None,
            median_l: None,
            mode_l: None,
            mode_break_day: None,
            p_mode: None,
            p_ge3: None,
            p_ge5: None,
            p_10: None,
            cond: None,
            near_era,
            vault: vault_of(oot, id),
            live: sdoc.map(|d| live_of(d, id)).unwrap_or_default(),
        };
        if let Some(s) = m.and_then(SummaryModel::s).filter(|s| s.len() == DAYS && s.iter().all(|x| x.is_finite())) {
            fill(&mut r, &row(id, false, &s, j), j);
        }
        rows.push(r);
    }
    let mut constant = SummaryRow {
        model_id: ALWAYS_CEILING_ID.into(),
        role: "CONSTANT",
        in_record: true,
        status: None,
        refused: None,
        expected_l: None,
        median_l: None,
        mode_l: None,
        mode_break_day: None,
        p_mode: None,
        p_ge3: None,
        p_ge5: None,
        p_10: None,
        cond: None,
        near_era: None,
        vault: VaultView { status: "NONE", verdict: None, diff: None, ci95: None, n: None, rule_id: None },
        live: LiveView::default(),
    };
    fill(&mut constant, &row(ALWAYS_CEILING_ID, true, &[1.0; DAYS], j), j);
    rows.push(constant);
    let j_source = match (j, j_observed) {
        (0, _) => "NONE",
        (j, Some(o)) if o == j => "OFFICIAL",
        _ => "HYPOTHETICAL",
    };
    CeilingSummary {
        featured_params_sha256: embedded.iter().find(|(id, _)| *id == featured.model_id).map(|(_, s)| s.clone()),
        featured,
        j,
        j_source,
        official,
        record_file,
        f3_missing,
        rows,
        integrity,
        scores: scores.map(|(d, source, sha)| ScoresSourceInfo {
            source,
            sha12: sha.to_string(),
            generated_at_utc: d.get("generated_at_utc").and_then(Value::as_str).map(str::to_string),
        }),
        oot: oot.map(info_of),
        tufe,
        fall: None,
    }
}

/// Satır değerleri `ceiling_display` satırından aynen (S[2], S[4], S[9] doğrudan okunur).
fn fill(r: &mut SummaryRow, c: &CeilingRow, j: usize) {
    r.expected_l = Some(c.expected_l);
    r.median_l = Some(c.median_l);
    r.mode_l = Some(c.mode_l);
    r.mode_break_day = (1..DAYS).contains(&c.mode_l).then_some(c.mode_l + 1);
    r.p_mode = c.p_l.get(c.mode_l).copied();
    r.p_ge3 = c.s.get(2).copied();
    r.p_ge5 = c.s.get(4).copied();
    r.p_10 = c.s.get(9).copied();
    r.cond = (j > 0).then_some(()).and(c.cond.as_ref()).map(|k| SummaryCond {
        p_break_next: k.p_break_next,
        expected_remaining: k.expected_remaining,
        median_l: k.median_l,
        mode_l: k.mode_l,
        p_mode: k.p_l_cond.get(k.mode_l).copied().flatten(),
        s_cond_5: k.s_cond.get(4).copied().flatten(),
        s_cond_10: k.s_cond.get(9).copied().flatten(),
    });
}

fn embedded_pairs(state: &AppState) -> Result<Vec<(String, String)>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    Ok(models.models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect())
}

/// Senaryo/sonuç ekranı: `runs` predict_all ya da kişisel kayıttaki çıktılar (yeniden hesaplanmaz).
#[tauri::command]
pub fn ceiling_summary(
    state: tauri::State<'_, AppState>,
    runs: Vec<SummaryModel>,
    j: usize,
    j_observed: Option<usize>,
    t: Option<String>,
) -> Result<CeilingSummary, AppError> {
    let embedded = embedded_pairs(&state)?;
    let scores = scores_doc(&state);
    let oot = scores_oot_doc(&state);
    let tufe = tufe_info_value(&state, t.as_deref());
    let sc = scores.as_ref().map(|(d, s, sha)| (d, *s, sha.as_str()));
    let mut s = ceiling_summary_value(&runs, j, j_observed, false, None, &embedded, sc, oot.as_deref(), tufe.clone());
    let refs = &state.models.as_ref().map_err(|e| e.to_app_error())?.models;
    s.fall = super::fall::fall_summary_value(&runs, false, None, refs, sc, oot.as_deref(), tufe);
    Ok(s)
}

/// Resmi görünüm (arz sayfası): S YALNIZ dondurulmuş kayıttan (U38, U62); model yeniden çalıştırılmaz, predict_all çağrılmaz.
/// TÜFE satırı kaydın `tufe` bloğundandır (kayıt esastır).
pub fn record_summary_in(
    repo: &Path,
    ticker: &str,
    file: &str,
    j: usize,
    j_observed: Option<usize>,
    embedded: &[(String, String)],
    scores: Option<(&Value, &'static str, &str)>,
    oot: Option<&ScoresOotDoc>,
) -> Result<CeilingSummary, AppError> {
    let ids: Vec<String> = embedded.iter().map(|(id, _)| id.clone()).collect();
    // doğrulama (tahmin kaydı, iptal edilmemiş, S var) record_ceiling ile aynı yol
    super::registry::record_ceiling_in(repo, ticker, file, j, &ids, embedded)?;
    let doc = super::freeze::read_record(repo, &format!("registry/records/{ticker}/{file}"))?;
    let models: Vec<SummaryModel> = doc["models"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|c| serde_json::from_value(c.clone()).ok())
        .collect();
    let tufe = doc.get("tufe").filter(|t| t.is_object()).map(|t| record_tufe(t));
    Ok(ceiling_summary_value(&models, j, j_observed, true, Some(file.to_string()), embedded, scores, oot, tufe))
}

/// Resmi görünümün düşüş kartı (EK 3 §8.4): değerler YALNIZ kaydın hücrelerinden (p_up), model yeniden çalıştırılmaz.
pub fn record_fall_summary_in(
    repo: &Path,
    ticker: &str,
    file: &str,
    refs: &[borsai_predict::ModelRef],
    scores: Option<(&Value, &'static str, &str)>,
    oot: Option<&ScoresOotDoc>,
) -> Result<Option<super::fall::FallSummary>, AppError> {
    let doc = super::freeze::read_record(repo, &format!("registry/records/{ticker}/{file}"))?;
    let models: Vec<SummaryModel> = doc["models"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|c| serde_json::from_value(c.clone()).ok())
        .collect();
    let tufe = doc.get("tufe").filter(|t| t.is_object()).map(|t| record_tufe(t));
    Ok(super::fall::fall_summary_value(&models, true, Some(file.to_string()), refs, scores, oot, tufe))
}

/// Kaydın `tufe` bloğu → TÜFE satırı (kayıttaki değerler aynen; dosya yeniden okunmaz).
fn record_tufe(t: &Value) -> TufeInfo {
    let s = |k: &str| t.get(k).and_then(Value::as_str).map(str::to_string);
    let refusal: Option<&'static str> = match t.get("refusal").and_then(Value::as_str) {
        Some("TUFE_MISSING") => Some("TUFE_MISSING"),
        Some("TUFE_NOT_PIT") => Some("TUFE_NOT_PIT"),
        Some("TUFE_FILE_MISMATCH") => Some("TUFE_FILE_MISMATCH"),
        _ => None,
    };
    TufeInfo {
        source: "RECORD",
        path: s("file"),
        file_sha256: s("file_sha256"),
        through_month: None,
        t: None,
        month: s("month"),
        index: s("index"),
        release_date: s("release_date"),
        bulletin_id: s("bulletin_id"),
        refusal,
        reason: match refusal {
            Some("TUFE_NOT_PIT") => Some("NOT_PIT"),
            Some("TUFE_FILE_MISMATCH") => Some("PIN_MISMATCH"),
            Some(_) => Some("T_UNKNOWN"),
            None => None,
        },
        detail: s("reason"),
        append_command: None,
        pin_ok: refusal.is_none().then_some(true),
    }
}

// ---------------------------------------------------------------- D1 sonrası satırı (EK 3 §6.5, K-P2-3)

pub const POST_D1_ROLE: &str = "POST_D1";
pub const POST_D1_SEALED_BLOCK: &str = "post_d1_sealed";

/// Kartın POST_D1 satırının zaman-dışı sütunu (K-P2-3): `post_d1_sealed` bloğunun `label == "birincil"` hücresi (verdict,
/// fark, aralık, n) ve karşılaştırıcı (`rule_id`; bu birincil hücre basit kurala değil ebeveyn modele karşıdır). Açık küme
/// ya da `_all` bloğu bu sütuna yazılmaz. Blok yoksa CLOSED ("kasa: bekliyor"), dosya yoksa UNAVAILABLE.
fn vault_post_d1(oot: Option<&ScoresOotDoc>) -> VaultView {
    let none = |status| VaultView { status, verdict: None, diff: None, ci95: None, n: None, rule_id: None };
    let Some(d) = oot.and_then(ScoresOotDoc::usable) else { return none("UNAVAILABLE") };
    if d.get(POST_D1_SEALED_BLOCK).is_none() {
        return none("CLOSED");
    }
    let Some(c) = model_block(d, POST_D1_SEALED_BLOCK, super::post_d1::POST_D1_MODEL_ID).and_then(primary_cell) else {
        return none("OPEN");
    };
    VaultView {
        status: "OPEN",
        verdict: c.get("verdict").and_then(Value::as_str).map(str::to_string),
        diff: c.get("diff").cloned(),
        ci95: c.get("ci95").cloned(),
        n: c.get("n").and_then(Value::as_u64),
        rule_id: c.get("rule_id").and_then(Value::as_str).map(str::to_string),
    }
}

/// Resmi görünümde (arz sayfası kartı) etkin POST_D1 kaydı ve j ≥ 1 varken "D1 sonrası (post_d1_hazard_v0)" satırı
/// (rol POST_D1; öne çıkan satırın hemen altına). Değerler yalnız kaydın S'inden (`post_d1_view` satırı, aynı
/// `ceiling_display`); koşulsuz sütunlar bilgi amaçlıdır (S_1 ana modelden). Terazi sütunları K-P2-3: yakın dönem "—";
/// zaman-dışı `post_d1_sealed` birincil hücresi; canlı `scores_post_d1.json` `n_live`. Değerler toplanmaz, ortalanmaz.
pub fn add_post_d1_row(
    s: &mut CeilingSummary,
    view: &super::post_d1::PostD1View,
    oot: Option<&ScoresOotDoc>,
    post_scores: Option<&Value>,
) {
    if !s.official || s.j == 0 || !matches!(view.state, "PREDICTED" | "REFUSED" | "NOT_APPLICABLE") {
        return;
    }
    let mut r = SummaryRow {
        model_id: super::post_d1::POST_D1_MODEL_ID.into(),
        role: POST_D1_ROLE,
        in_record: true,
        status: Some(view.state.to_string()),
        refused: view.refusal.clone(),
        expected_l: None,
        median_l: None,
        mode_l: None,
        mode_break_day: None,
        p_mode: None,
        p_ge3: None,
        p_ge5: None,
        p_10: None,
        cond: None,
        near_era: None,
        vault: vault_post_d1(oot),
        live: post_scores.map(|d| super::scores::post_d1_live_of(d, super::post_d1::POST_D1_MODEL_ID)).unwrap_or_default(),
    };
    if let (Some(row), "PREDICTED") = (view.row.as_ref(), view.state) {
        fill(&mut r, row, s.j);
    }
    let at = s.rows.iter().position(|x| x.role == "FEATURED").map_or(0, |i| i + 1);
    s.rows.insert(at, r);
}

/// Kayıt kartı (Analiz; salt okuma): repo ya da kişisel modda gömülü sicil anlık görüntüsü (FAZ9_SNAPSHOT K-SNAP-2).
pub fn record_summary_value(
    state: &AppState,
    ticker: &str,
    file: &str,
    j: usize,
    j_observed: Option<usize>,
) -> Result<CeilingSummary, AppError> {
    let root = state.read_root()?;
    let embedded = embedded_pairs(state)?;
    let scores = scores_doc(state);
    let oot = scores_oot_doc(state);
    let sc = scores.as_ref().map(|(d, s, sha)| (d, *s, sha.as_str()));
    let mut s = record_summary_in(&root.root, ticker, file, j, j_observed, &embedded, sc, oot.as_deref())?;
    let refs = &state.models.as_ref().map_err(|e| e.to_app_error())?.models;
    s.fall = record_fall_summary_in(&root.root, ticker, file, refs, sc, oot.as_deref())?;
    let view = super::post_d1::post_d1_view_in(&root.root, ticker, j, None)?;
    let post_scores = match root.snapshot {
        None => super::scores::scores_post_d1_value(state)?.doc,
        Some(_) => super::scores::scores_post_d1_in(&root.root)?.doc,
    };
    add_post_d1_row(&mut s, &view, oot.as_deref(), post_scores.as_ref());
    Ok(s)
}

#[tauri::command]
pub fn record_summary(
    state: tauri::State<'_, AppState>,
    ticker: String,
    file: String,
    j: usize,
    j_observed: Option<usize>,
) -> Result<CeilingSummary, AppError> {
    record_summary_value(&state, &ticker, &file, j, j_observed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_derivatives() {
        let d = ceiling_display_value(&[SVector { model_id: "m".into(), s: vec![0.5, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }], 1, Some("10"))
            .unwrap();
        let r = &d.rows[0];
        assert_eq!(r.p_l, vec![0.5, 0.25, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
        assert_eq!((r.expected_l, r.median_l), (0.75, 0));
        let c = r.cond.as_ref().unwrap();
        assert_eq!(c.s_cond[1], Some(0.5));
        assert_eq!(c.p_break_next, 0.5);
        assert_eq!((c.expected_l, c.expected_remaining, c.median_l), (1.5, 0.5, 1));
        // S_j = 0 → tanımsız
        let d3 = ceiling_display_value(&[SVector { model_id: "m".into(), s: r.s.clone() }], 3, None).unwrap();
        assert!(d3.rows[0].cond.is_none() && d3.price_hint.is_none());
        // her zaman tavan sabiti
        let a = d.rows.last().unwrap();
        assert!(a.constant && a.model_id == ALWAYS_CEILING_ID);
        assert_eq!((a.expected_l, a.median_l, a.cond.as_ref().unwrap().p_break_next), (10.0, 10, 0.0));
        assert_eq!(d.price_hint.as_ref().unwrap()[0], PriceHint { k: 1, price: 10.0 * 1.1 });
        assert!(ceiling_display_value(&[], 10, None).unwrap().rows[0].cond.is_none());
    }
}
