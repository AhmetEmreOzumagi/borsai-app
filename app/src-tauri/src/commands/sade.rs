//! Sade görünüm (UI v2; FAZ9_APP_UI K-UI-3, K-UI-4) için salt okuma komutları: `monitor_view`, `arz_view`, `perf_view`,
//! `headline_gate` (kırılma kartı `sade_break.rs`'te).
//!
//! - Hiçbiri skor ya da metrik hesaplamaz (U25): dosyaları okur, eşler, sayar, sıralar. Tavan serisinin görüntüleme
//!   türevleri (beklenen / medyan L) yalnız var olan `ceiling_display_value` yolundan gelir; gözlenen seri `streak_view_in`'in
//!   kuralıdır (resmi j yalnız `data/outcomes/<T>.csv`'den).
//! - Hüküm metni dosyadaki `verdict` alanıdır. "Öne çıkan" kararı yalnız `headline_gate`'te ve yalnız dosyada önceden ilan
//!   edilmiş birincil hücrenin verdict'inden verilir (`VERDICT_PASS` sabiti; başka bir yerde karşılaştırılmaz).
//! - Bülten dosya adları ve eğitim arz listeleri hiçbir görünümde dönmez (hijyen).
//! - Uygulama repo'ya yazmaz; git yalnız `git_readonly` beyaz listesiyle (`status`).
//! - Veri kökü `AppState::read_root`: repo modunda repo; kişisel modda gömülü sicil anlık görüntüsü (FAZ9_SNAPSHOT
//!   K-SNAP-2). Görünüm fonksiyonları (`*_in`) aynıdır; anlık görüntüde git çağrılmaz (`registry_snapshot::frozen_git`).
use serde::Serialize;
use serde_json::Value;
use std::path::Path;

use borsai_predict::features::parse_decimal;

use super::ceiling::{ceiling_display_value, streak_view_in, StreakView, SVector};
use super::freeze::read_record;
use super::git::git_readonly;
use super::inputs_doc::valid_ticker;
use super::registry::{registry_view_in, RecordRow, RegistryView, RECORD_PREDICTION};
use super::scores::{
    check_integrity, scores_doc, scores_post_d1_value, IntegrityProblem, MIN_N_METRIC, MIN_N_VERDICT, VERDICT_FAIL, VERDICT_PASS,
    VERDICT_UNDECIDED,
};
use super::scores_oot::{model_block, primary_cell, scores_oot_doc};
use super::registry_snapshot::{frozen_git, SnapshotInfo};
use super::{AppError, INVALID_ARGUMENT};
use crate::state::{AppState, DataRoot};

pub const CEILING_MODEL: &str = "ceiling_hazard_v0";
pub const RETURN_MODEL: &str = "v1_5_h99";
pub const POST_D1_MODEL: &str = "post_d1_hazard_v0";
pub const BREAK_MODEL: &str = "break_floor_v0";
pub const BREAK_ZERO: &str = "break_floor_v0@ZERO";
pub const SCORES_BREAK_SCHEMA: &str = "borsai.scores_break/1";
pub const PRIMARY_LABEL: &str = "birincil";
pub const HORIZONS: [(&str, usize); 4] = [("D1", 1), ("D3", 3), ("D5", 5), ("D10", 10)];
/// Olay akışı ve günlükte gösterilen en çok satır (Monitör).
pub const MAX_EVENTS: usize = 12;

/// Ana ekranların gösterdiği çıktılar (gösterim tanımı: hangi çıktı nerede durur). Hüküm dosyadan gelir.
/// (model, çıktı, ufuk/k, dosya, soru)
pub const HEADLINE_OUTPUTS: [(&str, &str, Option<&str>, &str, &str); 12] = [
    (CEILING_MODEL, "S", None, "scores.json", "CEILING_DAYS"),
    (RETURN_MODEL, "return", Some("D1"), "scores.json", "RETURN"),
    (RETURN_MODEL, "return", Some("D3"), "scores.json", "RETURN"),
    (RETURN_MODEL, "return", Some("D5"), "scores.json", "RETURN"),
    (RETURN_MODEL, "return", Some("D10"), "scores.json", "RETURN"),
    (RETURN_MODEL, "p_up", Some("D1"), "scores.json", "ABOVE_IPO"),
    (RETURN_MODEL, "p_up", Some("D3"), "scores.json", "ABOVE_IPO"),
    (RETURN_MODEL, "p_up", Some("D5"), "scores.json", "ABOVE_IPO"),
    (RETURN_MODEL, "p_up", Some("D10"), "scores.json", "ABOVE_IPO"),
    (POST_D1_MODEL, "S_cond", None, "scores_post_d1.json", "POST_D1_BREAK"),
    (BREAK_MODEL, "p_floor", Some("F1"), "scores_break.json", "BREAK_FLOOR"),
    (BREAK_MODEL, "p_floor", Some("F2"), "scores_break.json", "BREAK_FLOOR"),
];

/// Model performansında birincil hücrelerin yanında gösterilen birincil OLMAYAN karşılaştırma: V1.5'in D10 arz üstü
/// olasılığı taban orana karşı (dosyada `label = keşif`). (model, çıktı, ufuk, ölçü, kural, soru)
pub const PERF_EXTRA_CELLS: [(&str, &str, &str, &str, &str, &str); 1] = [(RETURN_MODEL, "p_up", "D10", "Brier", "base_rate", "ABOVE_IPO")];

/// Üretimdeki modeller (sıra ekranda aynen): (model, soru, zaman-dışı blok).
pub const PRODUCTION_MODELS: [(&str, &str, Option<&str>); 4] = [
    (CEILING_MODEL, "CEILING_DAYS", Some("oot_pre_h99_all")),
    (RETURN_MODEL, "RETURN", Some("oot_pre_h99_all")),
    (POST_D1_MODEL, "POST_D1_BREAK", Some("post_d1_all")),
    (BREAK_MODEL, "BREAK_FLOOR", None),
];

// ---------------------------------------------------------------- küçük yardımcılar

fn st(v: &Value, ptr: &str) -> Option<String> {
    v.pointer(ptr).and_then(Value::as_str).map(str::to_string)
}

fn num(v: &Value, ptr: &str) -> Option<f64> {
    v.pointer(ptr).and_then(Value::as_f64)
}

fn uint(v: &Value, ptr: &str) -> Option<u64> {
    v.pointer(ptr).and_then(Value::as_u64)
}

fn models_of(doc: &Value) -> &[Value] {
    doc.get("models").and_then(Value::as_array).map_or(&[], Vec::as_slice)
}

fn model_of<'a>(doc: &'a Value, model_id: &str) -> Option<&'a Value> {
    models_of(doc).iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id))
}

/// Ondalık metnin işareti (`R_h` tam Decimal metnidir): negatif mi? Aritmetik yok, yalnız işaret.
fn is_negative(text: &str) -> Option<bool> {
    parse_decimal(Some(&Value::String(text.to_string())), "R_h", false).ok().flatten().map(|d| d.signum() < 0)
}

/// Kayıttaki model hücresi.
fn record_cell<'a>(rec: &'a Value, model_id: &str) -> Option<&'a Value> {
    models_of(rec).iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id))
}

fn refusal_code(cell: &Value) -> Option<String> {
    st(cell, "/refusal/code").or_else(|| st(cell, "/output/refused/code"))
}

// ---------------------------------------------------------------- data/outcomes/<T>.csv (salt okuma)

#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct DayRow {
    pub h: usize,
    pub session_date: Option<String>,
    pub close_raw: Option<String>,
    pub upper_limit_raw: Option<String>,
    pub reference_raw: Option<String>,
    /// 1 tavan, 0 tavan değil (yalnız `status = OK`); başka hâlde null.
    pub ceiling_close: Option<u8>,
    pub status: Option<String>,
    /// `R_h` metni aynen (dosyada yalnız h = 1, 3, 5, 10 satırlarında dolu).
    pub r_h: Option<String>,
    /// `trade_count_raw` metni aynen (bültendeki TOPLAM SOZLESME SAYISI; yalnız `status = OK`; FAZ9_UI_FIX K-FIX-4).
    pub trade_count_raw: Option<String>,
    /// Günün sayısı / arzın on günündeki en büyük sayı (0–1; en büyük gün 1). Sayı yoksa ya da tam sayı değilse null.
    pub trade_count_rel: Option<f64>,
}

/// h = 1..10 (satır yoksa boş gün). Dosya yoksa `None`. Bülten sha sütunları okunmaz.
pub fn read_days(repo: &Path, ticker: &str) -> Result<Option<(Vec<DayRow>, Option<String>)>, AppError> {
    let p = repo.join("data").join("outcomes").join(format!("{ticker}.csv"));
    let Ok(text) = std::fs::read_to_string(&p) else { return Ok(None) };
    let invalid = |m: String| AppError::new(super::ceiling::OUTCOMES_INVALID, m);
    let mut lines = text.lines();
    let header: Vec<&str> = lines.next().unwrap_or_default().trim_start_matches('\u{feff}').split(',').collect();
    let col = |name: &str| header.iter().position(|h| *h == name);
    let need = |name: &str| col(name).ok_or_else(|| invalid(format!("sütun yok: {name}")));
    let (ch, cd, cc, cu, cr, ccl, crh, cs) = (
        need("h")?,
        need("session_date")?,
        need("close_raw")?,
        need("upper_limit_raw")?,
        need("reference_raw")?,
        need("ceiling_close")?,
        need("R_h")?,
        need("status")?,
    );
    let cip = col("ipo_price");
    let ctc = col("trade_count_raw");
    let mut days: Vec<DayRow> = (1..=10).map(|h| DayRow { h, ..DayRow::default() }).collect();
    let mut ipo_price = None;
    for line in lines.filter(|l| !l.trim().is_empty()) {
        let cells: Vec<&str> = line.split(',').collect();
        if cells.len() != header.len() || line.contains('"') {
            return Err(invalid(format!("satır biçimi: {ticker}")));
        }
        let h: usize = cells[ch].parse().map_err(|_| invalid(format!("h: {}", cells[ch])))?;
        if !(1..=10).contains(&h) {
            return Err(invalid(format!("h aralık dışı: {h}")));
        }
        let opt = |i: usize| Some(cells[i].to_string()).filter(|s| !s.is_empty());
        let status = opt(cs);
        let ok = status.as_deref() == Some("OK");
        days[h - 1] = DayRow {
            h,
            session_date: opt(cd),
            close_raw: opt(cc).filter(|_| ok),
            upper_limit_raw: opt(cu).filter(|_| ok),
            reference_raw: opt(cr).filter(|_| ok),
            ceiling_close: match (ok, cells[ccl]) {
                (true, "1") => Some(1),
                (true, "0") => Some(0),
                _ => None,
            },
            status,
            r_h: opt(crh),
            trade_count_raw: ctc.and_then(opt).filter(|_| ok),
            trade_count_rel: None,
        };
        if ipo_price.is_none() {
            ipo_price = cip.and_then(opt);
        }
    }
    // göreli yükseklik: günün sayısı / on günün en büyüğü (K-FIX-4); ön uç yalnız piksele çevirir
    let counts: Vec<Option<u64>> = days.iter().map(|d| d.trade_count_raw.as_deref().and_then(|t| t.parse::<u64>().ok())).collect();
    if let Some(max) = counts.iter().flatten().max().copied().filter(|m| *m > 0) {
        for (d, c) in days.iter_mut().zip(counts) {
            d.trade_count_rel = c.map(|c| c as f64 / max as f64);
        }
    }
    Ok(Some((days, ipo_price)))
}

// ---------------------------------------------------------------- satır parçaları

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct StreakInfo {
    /// FOUND | MISSING
    pub file_status: &'static str,
    pub as_of: Option<String>,
    pub j_observed: Option<usize>,
    pub broken: bool,
    pub unlabeled: bool,
    /// Seri sürüyor: dosya var, bozulmadı, etiketsiz gün yok, j < 10.
    pub in_streak: bool,
    /// Gerçekleşen L: seri bozulduysa j, on gün tavansa 10; değilse null.
    pub realized_l: Option<usize>,
}

fn streak_info(repo: &Path, ticker: &str) -> Result<StreakInfo, AppError> {
    let dir = repo.join("data").join("outcomes");
    let s = streak_view_in(Some(&dir), Some(ticker))?;
    let j = s.j_observed;
    let complete = j == Some(10);
    Ok(StreakInfo {
        file_status: s.file_status,
        as_of: s.as_of,
        j_observed: j,
        broken: s.broken,
        unlabeled: s.unlabeled,
        in_streak: j.is_some() && !s.broken && !s.unlabeled && !complete,
        realized_l: if s.broken || complete { j } else { None },
    })
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CeilingInfo {
    pub model_id: String,
    pub record_file: String,
    pub status: Option<String>,
    pub refusal_code: Option<String>,
    pub params_sha256: Option<String>,
    /// Kayıttaki S'ten `ceiling_display_value` (görüntüleme türevi; kayda yazılmaz).
    pub expected_l: Option<f64>,
    pub median_l: Option<usize>,
    pub mode_l: Option<usize>,
    /// P(L ≥ 5) = S[4], P(L = 10) = S[9] (kayıttan aynen).
    pub p_ge5: Option<f64>,
    pub p_10: Option<f64>,
}

fn ceiling_info(rec: &Value, file: &str) -> Option<CeilingInfo> {
    let cell = record_cell(rec, CEILING_MODEL)?;
    let status = st(cell, "/status");
    let s: Option<Vec<f64>> = cell
        .pointer("/output/S")
        .and_then(|v| serde_json::from_value::<Vec<f64>>(v.clone()).ok())
        .filter(|s| s.len() == 10 && s.iter().all(|x| x.is_finite()));
    let row = s.as_ref().and_then(|s| {
        ceiling_display_value(&[SVector { model_id: CEILING_MODEL.into(), s: s.clone() }], 0, None).ok().map(|d| d.rows[0].clone())
    });
    Some(CeilingInfo {
        model_id: CEILING_MODEL.into(),
        record_file: file.to_string(),
        status,
        refusal_code: refusal_code(cell),
        params_sha256: st(cell, "/params_sha256"),
        expected_l: row.as_ref().map(|r| r.expected_l),
        median_l: row.as_ref().map(|r| r.median_l),
        mode_l: row.as_ref().map(|r| r.mode_l),
        p_ge5: s.as_ref().map(|s| s[4]),
        p_10: s.as_ref().map(|s| s[9]),
    })
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ReturnRow {
    pub horizon: &'static str,
    pub h: usize,
    /// Kayıttaki V1.5 hücresi (aynen).
    pub ret: Option<f64>,
    pub p_up: Option<f64>,
    pub price: Option<f64>,
    pub return_clipped: Option<Value>,
    /// Gerçekleşen `R_h` metni (outcomes; aynen).
    pub realized: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ReturnInfo {
    pub model_id: String,
    pub record_file: String,
    pub status: Option<String>,
    pub refusal_code: Option<String>,
    pub rows: Vec<ReturnRow>,
}

fn return_info(rec: &Value, file: &str, days: Option<&[DayRow]>) -> Option<ReturnInfo> {
    let cell = record_cell(rec, RETURN_MODEL)?;
    let rows = HORIZONS
        .iter()
        .map(|&(hz, h)| {
            let p = format!("/output/{hz}");
            ReturnRow {
                horizon: hz,
                h,
                ret: num(cell, &format!("{p}/return")),
                p_up: num(cell, &format!("{p}/p_up")),
                price: num(cell, &format!("{p}/price")),
                return_clipped: cell.pointer(&format!("{p}/return_clipped")).cloned().filter(|v| !v.is_null()),
                realized: days.and_then(|d| d.get(h - 1)).and_then(|d| d.r_h.clone()),
            }
        })
        .collect();
    Some(ReturnInfo {
        model_id: RETURN_MODEL.into(),
        record_file: file.to_string(),
        status: st(cell, "/status"),
        refusal_code: refusal_code(cell),
        rows,
    })
}

/// Model başına sınıf (dosyalardan; burada hesaplanmaz).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ClassRow {
    pub model_id: String,
    /// scores.json `class` (LIVE | LATE_RECORD | …); D1 sonrası ve kırılma: `stage_status` / `class`.
    pub class: Option<String>,
    pub status: Option<String>,
    pub record_source: Option<String>,
    pub record_push_proof_created_at: Option<String>,
}

fn live_row<'a>(doc: &'a Value, model_id: &str, ticker: &str) -> Option<&'a Value> {
    model_of(doc, model_id)?
        .pointer("/live/rows")?
        .as_array()?
        .iter()
        .find(|r| r.get("ticker").and_then(Value::as_str) == Some(ticker))
}

fn denominator_row<'a>(doc: &'a Value, model_id: &str, block: &str, ticker: &str) -> Option<&'a Value> {
    model_of(doc, model_id)?
        .get(block)?
        .get("denominator")?
        .as_array()?
        .iter()
        .find(|r| r.get("ticker").and_then(Value::as_str) == Some(ticker))
}

fn classes_of(docs: &Docs, ticker: &str) -> Vec<ClassRow> {
    let mut out = Vec::new();
    for mid in [CEILING_MODEL, RETURN_MODEL] {
        let r = docs.scores.and_then(|d| live_row(d, mid, ticker));
        out.push(ClassRow {
            model_id: mid.into(),
            class: r.and_then(|r| st(r, "/class")),
            status: r.and_then(|r| st(r, "/status")),
            record_source: r.and_then(|r| st(r, "/record_source")),
            record_push_proof_created_at: r.and_then(|r| st(r, "/class_evidence/record_push_proof_created_at")),
        });
    }
    let p = docs.post_d1.and_then(|d| denominator_row(d, POST_D1_MODEL, "conditional_j1", ticker));
    out.push(ClassRow {
        model_id: POST_D1_MODEL.into(),
        class: p.and_then(|r| st(r, "/class").or_else(|| st(r, "/stage_status"))),
        status: p.and_then(|r| st(r, "/stage_status")),
        record_source: None,
        record_push_proof_created_at: None,
    });
    let b = docs.brk.and_then(|d| denominator_row(d, BREAK_MODEL, "live_break", ticker));
    out.push(ClassRow {
        model_id: BREAK_MODEL.into(),
        class: b.and_then(|r| st(r, "/class")),
        status: b.and_then(|r| st(r, "/stage_status")),
        record_source: None,
        record_push_proof_created_at: None,
    });
    out
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BreakInfo {
    pub record_file: String,
    pub produced_at_utc: Option<String>,
    pub b: Option<u64>,
    pub l: Option<u64>,
    pub break_date: Option<String>,
    /// 1: kırılma günü kapanış alt limitte (taban); 0: taban üstü.
    pub b_floor: Option<u64>,
    pub close_raw: Option<String>,
    pub status: Option<String>,
    pub p_floor_f1: Option<f64>,
    pub p_floor_f2: Option<f64>,
    /// `structural_zero_D10.impossible`: D10'da arz fiyatının altına inemez.
    pub impossible_d10: Option<bool>,
    pub warnings: Vec<String>,
    pub t_open: Option<String>,
}

/// Arzın makine kayıtları (`registry/post_break/<T>/machine_*.json`), dosya adı sırasıyla (en erken = birincil gösterim).
pub fn machine_files(repo: &Path, ticker: &str) -> Vec<String> {
    let dir = repo.join("registry").join("post_break").join(ticker);
    let mut files: Vec<String> = std::fs::read_dir(dir)
        .map(|d| {
            d.flatten()
                .filter_map(|e| e.file_name().to_str().filter(|n| n.starts_with("machine_") && n.ends_with(".json")).map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    files.sort();
    files
}

pub fn read_machine(repo: &Path, ticker: &str, file: &str) -> Result<Value, AppError> {
    let p = repo.join("registry").join("post_break").join(ticker).join(file);
    let bytes = std::fs::read(&p).map_err(|e| super::io_error("registry/post_break", e))?;
    serde_json::from_slice(&bytes).map_err(|e| super::io_error("makine kaydı", e))
}

fn break_info(repo: &Path, ticker: &str) -> Result<Option<BreakInfo>, AppError> {
    let Some(file) = machine_files(repo, ticker).into_iter().next() else { return Ok(None) };
    let m = read_machine(repo, ticker, &file)?;
    let cell = record_cell(&m, BREAK_MODEL);
    let mut warnings: Vec<String> = cell
        .and_then(|c| c.pointer("/output/warnings"))
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|w| w.get("code").and_then(Value::as_str).map(str::to_string))
        .collect();
    warnings.extend(m.pointer("/break_day/warnings").and_then(Value::as_array).into_iter().flatten().filter_map(|w| {
        w.as_str().map(str::to_string).or_else(|| w.get("code").and_then(Value::as_str).map(str::to_string))
    }));
    Ok(Some(BreakInfo {
        record_file: file,
        produced_at_utc: st(&m, "/produced_at_utc"),
        b: uint(&m, "/streak/b"),
        l: uint(&m, "/streak/L"),
        break_date: st(&m, "/streak/break_date"),
        b_floor: uint(&m, "/break_day/b_floor"),
        close_raw: st(&m, "/break_day/fields_raw/close"),
        status: cell.and_then(|c| st(c, "/status")),
        p_floor_f1: cell.and_then(|c| num(c, "/output/F1/p_floor")),
        p_floor_f2: cell.and_then(|c| num(c, "/output/F2/p_floor")),
        impossible_d10: m.pointer("/structural_zero_D10/impossible").and_then(Value::as_bool),
        warnings,
        t_open: st(&m, "/t_open"),
    }))
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct RegimeInfo {
    pub tag: String,
    pub start_d1: Option<String>,
    pub end_d1: Option<String>,
}

/// Rejim tanımı `scores_break.json` kartından (C4: FON_KRIZI_2026, D_1 ≥ 2026-09-16, bitiş yok).
fn regime_of(docs: &Docs) -> Option<RegimeInfo> {
    let w = docs.brk.and_then(|d| model_of(d, BREAK_MODEL)).and_then(|m| m.pointer("/card/regime_warning"))?;
    Some(RegimeInfo { tag: st(w, "/tag")?, start_d1: st(w, "/start_d1"), end_d1: st(w, "/end_d1") })
}

/// D_1 rejim penceresinde mi (ISO tarih metinleri; sözlük sırası = tarih sırası).
fn regime_tags(regime: Option<&RegimeInfo>, d1: Option<&str>) -> Vec<String> {
    match (regime, d1) {
        (Some(r), Some(d)) => {
            let after = r.start_d1.as_deref().is_some_and(|s| d >= s);
            let before = r.end_d1.as_deref().map_or(true, |e| d <= e);
            if after && before {
                vec![r.tag.clone()]
            } else {
                Vec::new()
            }
        }
        _ => Vec::new(),
    }
}

// ---------------------------------------------------------------- dosya kümeleri

/// Sade görünümün okuduğu skor dosyaları (her biri yoksa `None`).
pub struct Docs<'a> {
    pub scores: Option<&'a Value>,
    pub scores_source: Option<&'static str>,
    pub post_d1: Option<&'a Value>,
    pub brk: Option<&'a Value>,
    pub oot: Option<&'a Value>,
}

/// `scores_break.json` (repo modu): şema ve küçük-n bütünlüğü (n_scored < 10 iken hücre → kullanılmaz).
pub fn scores_break_in(repo: &Path) -> Option<Value> {
    let text = std::fs::read_to_string(repo.join("scores").join("scores_break.json")).ok()?;
    let doc: Value = serde_json::from_str(&text).ok()?;
    if doc.get("schema_version").and_then(Value::as_str) != Some(SCORES_BREAK_SCHEMA) {
        return None;
    }
    for m in models_of(&doc) {
        let n = uint(m, "/live_break/n_scored").unwrap_or(0);
        let cells = m.pointer("/live_break/cells").and_then(Value::as_array).map_or(0, Vec::len);
        if n < MIN_N_METRIC && cells > 0 {
            return None;
        }
    }
    Some(doc)
}

/// Komutların ortak dosya yüklemesi. scores.json fail-closed (§2.3): bütünlük ihlalinde kullanılmaz ve ihlal döner.
pub struct Loaded {
    pub scores: Option<(Value, &'static str)>,
    pub scores_integrity: Option<IntegrityProblem>,
    pub post_d1: Option<Value>,
    pub brk: Option<Value>,
    pub oot: Option<Value>,
}

impl Loaded {
    pub fn docs(&self) -> Docs<'_> {
        Docs {
            scores: self.scores.as_ref().map(|(d, _)| d),
            scores_source: self.scores.as_ref().map(|(_, s)| *s),
            post_d1: self.post_d1.as_ref(),
            brk: self.brk.as_ref(),
            oot: self.oot.as_ref(),
        }
    }
}

pub fn load(state: &AppState) -> Loaded {
    load_with(state, state.read_root().ok().as_ref())
}

/// `root`: veri kökü (repo ya da anlık görüntü; yoksa D1 sonrası ve kırılma skorları yok). D1 sonrası skorları repo modunda
/// eskisi gibi `scores_post_d1_value`'dan, anlık görüntüde onun içindeki kopyadan (aynı okuyucu, aynı bütünlük denetimi).
pub fn load_with(state: &AppState, root: Option<&DataRoot>) -> Loaded {
    let (scores, scores_integrity) = match scores_doc(state) {
        Some((d, src, _)) => match check_integrity(&d) {
            None => (Some((d, src)), None),
            Some(p) => (None, Some(p)),
        },
        None => (None, None),
    };
    let post_d1 = match root {
        Some(r) if r.snapshot.is_some() => super::scores::scores_post_d1_in(&r.root).ok().and_then(|v| v.doc),
        _ => scores_post_d1_value(state).ok().and_then(|v| v.doc),
    };
    let brk = root.and_then(|r| scores_break_in(&r.root));
    let oot = scores_oot_doc(state).and_then(|d| d.usable().cloned());
    Loaded { scores, scores_integrity, post_d1, brk, oot }
}

/// Dosyaları doğrudan repo'dan yükler (testler ve repo modu; scores.json repo kopyası).
pub fn load_repo(repo: &Path) -> Loaded {
    let read = |name: &str| -> Option<Value> {
        serde_json::from_str(&std::fs::read_to_string(repo.join("scores").join(name)).ok()?).ok()
    };
    let (scores, scores_integrity) = match read("scores.json") {
        Some(d) => match check_integrity(&d) {
            None => (Some((d, "REPO")), None),
            Some(p) => (None, Some(p)),
        },
        None => (None, None),
    };
    let post_d1 = std::fs::read_to_string(repo.join("scores").join("scores_post_d1.json"))
        .ok()
        .and_then(|t| super::scores::scores_post_d1_from(&t, &repo.join("scores").join("scores_post_d1.json")).ok())
        .and_then(|v| v.doc);
    let oot = read("scores_oot.json").filter(|d| super::scores_oot::check_integrity_oot(d).is_none());
    Loaded { scores, scores_integrity, post_d1, brk: scores_break_in(repo), oot }
}

// ---------------------------------------------------------------- monitor_view

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct MonitorRow {
    pub ticker: String,
    pub company: Option<String>,
    pub first_trading_date: Option<String>,
    pub ipo_status: Option<String>,
    /// Girdi belgesindeki `ipo_price_tl` (yoksa outcomes `ipo_price`), metin aynen.
    pub ipo_price: Option<String>,
    pub shares_offered: Option<String>,
    pub days: Vec<DayRow>,
    pub d10_close: Option<String>,
    pub d10_date: Option<String>,
    /// `R_10` metni aynen ve işareti (negatif: D10'da arz fiyatının altında).
    pub r10: Option<String>,
    pub r10_below: Option<bool>,
    pub streak: StreakInfo,
    pub record_file: Option<String>,
    pub recorded_at_istanbul: Option<String>,
    pub ceiling: Option<CeilingInfo>,
    pub returns: Option<ReturnInfo>,
    pub break_info: Option<BreakInfo>,
    pub classes: Vec<ClassRow>,
    pub regime_tags: Vec<String>,
    pub n_pre_listing_records: usize,
    pub n_post_d1_records: usize,
    pub n_machine_records: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct MonitorCounts {
    pub n_ipos: usize,
    pub first_d1: Option<String>,
    pub last_d1: Option<String>,
    pub n_in_streak: usize,
    pub n_d10_known: usize,
    pub n_d10_below: usize,
    pub n_break_known: usize,
    pub n_break_floor: usize,
    pub n_impossible_d10: usize,
    /// Payda (`registry/ipos.csv`): satır sayısı ve durumlara göre.
    pub n_payda: usize,
    pub n_frozen: usize,
    pub n_out_of_scope: usize,
    pub n_skipped: usize,
    pub n_pre_listing_records: usize,
    pub n_post_d1_records: usize,
    pub n_machine_records: usize,
    pub n_push_proofs: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct EventItem {
    /// ISO tarih ya da tarih-saat (dosyadaki gibi).
    pub at: String,
    /// RECORD | LEGACY_RECORD | STREAK | BREAK | D10 | MACHINE | MODEL_FROZEN | REGIME | POST_D1
    pub kind: &'static str,
    pub ticker: Option<String>,
    /// Birleştirilmiş olayın arzları (aynı gün aynı tür kayıt olayları tek satır; tek arzda `[ticker]`).
    pub tickers: Vec<String>,
    pub model_id: Option<String>,
    pub h_from: Option<usize>,
    pub h_to: Option<usize>,
    pub b: Option<u64>,
    pub b_floor: Option<u64>,
    pub close_raw: Option<String>,
    pub closes: Vec<String>,
    pub r: Option<String>,
    pub class: Option<String>,
    pub proof_at: Option<String>,
    pub file: Option<String>,
}

impl EventItem {
    fn new(at: String, kind: &'static str, ticker: Option<&str>) -> Self {
        EventItem {
            at,
            kind,
            ticker: ticker.map(str::to_string),
            tickers: ticker.map(|t| vec![t.to_string()]).unwrap_or_default(),
            model_id: None,
            h_from: None,
            h_to: None,
            b: None,
            b_floor: None,
            close_raw: None,
            closes: Vec::new(),
            r: None,
            class: None,
            proof_at: None,
            file: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct MonitorView {
    /// Gerçekleşen seri dosyalarındaki en geç `session_date`.
    pub data_date: Option<String>,
    pub rows: Vec<MonitorRow>,
    pub counts: MonitorCounts,
    pub regime: Option<RegimeInfo>,
    pub events: Vec<EventItem>,
    /// `git status --porcelain -- registry data` (boşsa temiz; anlık görüntüde derleme anınınki).
    pub git_status: String,
    pub scores_source: Option<&'static str>,
    pub scores_integrity: Option<IntegrityProblem>,
    /// Kişisel modda gömülü anlık görüntünün künyesi (K-SNAP-3 veri şeridi); repo modunda alan yok.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snapshot: Option<SnapshotInfo>,
}

fn active_records(rows: &[RecordRow]) -> Vec<&RecordRow> {
    let mut v: Vec<&RecordRow> = rows
        .iter()
        .filter(|r| r.status == "OK" && r.record_type.as_deref() == Some(RECORD_PREDICTION) && r.cancelled_by.is_none())
        .collect();
    v.sort_by(|a, b| a.file.cmp(&b.file));
    v
}

fn inputs_field(repo: &Path, ticker: &str, field: &str) -> Option<String> {
    let bytes = std::fs::read(repo.join("registry").join("inputs").join(format!("{ticker}.json"))).ok()?;
    let doc: Value = serde_json::from_slice(&bytes).ok()?;
    st(&doc, &format!("/fields/{field}/value"))
}

fn monitor_row(repo: &Path, reg: &RegistryView, ticker: &str, docs: &Docs, regime: Option<&RegimeInfo>) -> Result<MonitorRow, AppError> {
    let t = reg.tickers.iter().find(|t| t.ticker == ticker);
    let meta = reg.ipos.iter().find(|m| m.get("ticker").and_then(Value::as_str) == Some(ticker));
    let mget = |k: &str| meta.and_then(|m| m.get(k)).and_then(Value::as_str).filter(|s| !s.is_empty()).map(str::to_string);
    let days_ipo = read_days(repo, ticker)?;
    let (days, csv_price) = match days_ipo {
        Some((d, p)) => (d, p),
        None => ((1..=10).map(|h| DayRow { h, ..DayRow::default() }).collect(), None),
    };
    let active = t.map(|t| active_records(&t.records)).unwrap_or_default();
    let first = active.first().copied();
    let rec = match first {
        Some(r) => Some(read_record(repo, &r.rel_path)?),
        None => None,
    };
    let d10 = &days[9];
    let r10 = d10.r_h.clone();
    let first_trading_date = t.and_then(|t| t.first_trading_date.clone()).or_else(|| mget("first_trading_date"));
    Ok(MonitorRow {
        ticker: ticker.to_string(),
        company: t.and_then(|t| t.company.clone()).or_else(|| mget("company")),
        regime_tags: regime_tags(regime, first_trading_date.as_deref()),
        first_trading_date,
        ipo_status: t.and_then(|t| t.ipo_status.clone()).or_else(|| mget("status")),
        ipo_price: inputs_field(repo, ticker, "ipo_price_tl").or(csv_price),
        shares_offered: inputs_field(repo, ticker, "shares_offered"),
        d10_close: d10.close_raw.clone(),
        d10_date: d10.session_date.clone(),
        r10_below: r10.as_deref().and_then(is_negative),
        r10,
        streak: streak_info(repo, ticker)?,
        record_file: first.map(|r| r.file.clone()),
        recorded_at_istanbul: first.and_then(|r| r.recorded_at_istanbul.clone()),
        ceiling: rec.as_ref().zip(first).and_then(|(rec, r)| ceiling_info(rec, &r.file)),
        returns: rec.as_ref().zip(first).and_then(|(rec, r)| return_info(rec, &r.file, Some(days.as_slice()))),
        break_info: break_info(repo, ticker)?,
        classes: classes_of(docs, ticker),
        n_pre_listing_records: active.len(),
        n_post_d1_records: t.map_or(0, |t| t.n_post_d1_active),
        n_machine_records: machine_files(repo, ticker).len(),
        days,
    })
}

/// Monitörün arzları: payda satırlarından durumu FROZEN olanlar (kayıtlı arzlar), D1 azalan.
fn monitor_tickers(reg: &RegistryView) -> Vec<String> {
    let mut v: Vec<(String, String)> = reg
        .ipos
        .iter()
        .filter(|m| m.get("status").and_then(Value::as_str) == Some("FROZEN"))
        .filter_map(|m| {
            let t = m.get("ticker").and_then(Value::as_str)?.to_string();
            let d = m.get("first_trading_date").and_then(Value::as_str).unwrap_or_default().to_string();
            valid_ticker(&t).then_some((d, t))
        })
        .collect();
    for t in &reg.tickers {
        if !v.iter().any(|(_, x)| *x == t.ticker) && t.n_active > 0 {
            v.push((t.first_trading_date.clone().unwrap_or_default(), t.ticker.clone()));
        }
    }
    v.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    v.into_iter().map(|(_, t)| t).collect()
}

/// Arz başına olaylar (dosyalardan): kayıt, canlı (eski repo) kaydı, tavan serisi, kırılma, D10, makine kaydı.
fn ticker_events(row: &MonitorRow) -> Vec<EventItem> {
    let t = Some(row.ticker.as_str());
    let mut out = Vec::new();
    if let (Some(at), Some(f)) = (&row.recorded_at_istanbul, &row.record_file) {
        let mut e = EventItem::new(at.clone(), "RECORD", t);
        e.file = Some(f.clone());
        e.class = row.classes.iter().find(|c| c.model_id == CEILING_MODEL).and_then(|c| c.class.clone());
        out.push(e);
    }
    for c in row.classes.iter().filter(|c| c.record_source.as_deref() == Some("LEGACY")) {
        if let Some(at) = &c.record_push_proof_created_at {
            let mut e = EventItem::new(at.clone(), "LEGACY_RECORD", t);
            e.model_id = Some(c.model_id.clone());
            e.class = c.class.clone();
            out.push(e);
        }
    }
    let run: Vec<&DayRow> = row.days.iter().take_while(|d| d.ceiling_close == Some(1)).collect();
    if let (Some(first), Some(last)) = (run.first(), run.last()) {
        let mut e = EventItem::new(last.session_date.clone().unwrap_or_default(), "STREAK", t);
        e.h_from = Some(first.h);
        e.h_to = Some(last.h);
        e.closes = run.iter().filter_map(|d| d.close_raw.clone()).collect();
        if first.session_date.is_some() {
            out.push(e);
        }
    }
    if let Some(b) = &row.break_info {
        if let Some(d) = &b.break_date {
            let mut e = EventItem::new(d.clone(), "BREAK", t);
            e.b = b.b;
            e.b_floor = b.b_floor;
            e.close_raw = b.close_raw.clone();
            out.push(e);
        }
        if let Some(at) = &b.produced_at_utc {
            let mut e = EventItem::new(at.clone(), "MACHINE", t);
            e.class = row.classes.iter().find(|c| c.model_id == BREAK_MODEL).and_then(|c| c.class.clone());
            e.file = Some(b.record_file.clone());
            out.push(e);
        }
    }
    if let (Some(d), Some(c)) = (&row.d10_date, &row.d10_close) {
        let mut e = EventItem::new(d.clone(), "D10", t);
        e.close_raw = Some(c.clone());
        e.r = row.r10.clone();
        e.h_to = Some(10);
        out.push(e);
    }
    out
}

/// Model düzeyi olaylar: kırılma modelinin dondurulması (kart) ve rejim başlangıcı.
fn global_events(docs: &Docs, regime: Option<&RegimeInfo>) -> Vec<EventItem> {
    let mut out = Vec::new();
    if let Some(card) = docs.brk.and_then(|d| model_of(d, BREAK_MODEL)).and_then(|m| m.get("card")) {
        if let Some(at) = st(card, "/frozen_at") {
            let mut e = EventItem::new(at, "MODEL_FROZEN", None);
            e.model_id = Some(BREAK_MODEL.into());
            e.proof_at = st(card, "/model_push_proof_created_at");
            out.push(e);
        }
    }
    if let Some(start) = regime.and_then(|r| r.start_d1.clone()) {
        let mut e = EventItem::new(start, "REGIME", None);
        e.model_id = regime.map(|r| r.tag.clone());
        out.push(e);
    }
    out
}

/// Aynı gün yazılan kayıt olaylarını (RECORD, MACHINE) tek satırda birleştirir: arz listesi, en geç zaman; sınıf ve dosya
/// yalnız hepsinde aynıysa kalır. Öbür olaylar aynen.
fn group_events(v: Vec<EventItem>) -> Vec<EventItem> {
    let mut out: Vec<EventItem> = Vec::new();
    for e in v {
        let day = |x: &EventItem| x.at.chars().take(10).collect::<String>();
        if matches!(e.kind, "RECORD" | "MACHINE") {
            if let Some(g) = out.iter_mut().find(|g| g.kind == e.kind && day(g) == day(&e)) {
                g.tickers.extend(e.tickers.iter().cloned());
                g.tickers.sort();
                g.tickers.dedup();
                if g.at < e.at {
                    g.at = e.at.clone();
                }
                if g.class != e.class {
                    g.class = None;
                }
                g.ticker = (g.tickers.len() == 1).then(|| g.tickers[0].clone());
                g.file = None;
                continue;
            }
        }
        out.push(e);
    }
    out
}

fn sort_events(v: &mut [EventItem]) {
    // ISO metinleri: aynı biçimde sözlük sırası = zaman sırası; yeni olan üstte
    v.sort_by(|a, b| b.at.cmp(&a.at).then(a.kind.cmp(b.kind)));
}

pub fn monitor_view_in(repo: &Path, docs: &Docs, supported: &[String]) -> Result<MonitorView, AppError> {
    let reg = registry_view_in(repo, supported)?;
    let regime = regime_of(docs);
    let mut rows = Vec::new();
    for t in monitor_tickers(&reg) {
        rows.push(monitor_row(repo, &reg, &t, docs, regime.as_ref())?);
    }
    let status_of = |s: &str| reg.ipos.iter().filter(|m| m.get("status").and_then(Value::as_str) == Some(s)).count();
    let d1s: Vec<&str> = rows.iter().filter_map(|r| r.first_trading_date.as_deref()).collect();
    let counts = MonitorCounts {
        n_ipos: rows.len(),
        first_d1: d1s.iter().min().map(|s| s.to_string()),
        last_d1: d1s.iter().max().map(|s| s.to_string()),
        n_in_streak: rows.iter().filter(|r| r.streak.in_streak).count(),
        n_d10_known: rows.iter().filter(|r| r.r10_below.is_some()).count(),
        n_d10_below: rows.iter().filter(|r| r.r10_below == Some(true)).count(),
        n_break_known: rows.iter().filter(|r| r.break_info.as_ref().is_some_and(|b| b.b_floor.is_some())).count(),
        n_break_floor: rows.iter().filter(|r| r.break_info.as_ref().and_then(|b| b.b_floor) == Some(1)).count(),
        n_impossible_d10: rows.iter().filter(|r| r.break_info.as_ref().and_then(|b| b.impossible_d10) == Some(true)).count(),
        n_payda: reg.ipos.len(),
        n_frozen: status_of("FROZEN"),
        n_out_of_scope: status_of("OUT_OF_SCOPE"),
        n_skipped: status_of("SKIPPED"),
        n_pre_listing_records: rows.iter().map(|r| r.n_pre_listing_records).sum(),
        n_post_d1_records: rows.iter().map(|r| r.n_post_d1_records).sum(),
        n_machine_records: rows.iter().map(|r| r.n_machine_records).sum(),
        n_push_proofs: reg.proofs.len(),
    };
    let mut events: Vec<EventItem> = rows.iter().flat_map(ticker_events).collect();
    events.extend(global_events(docs, regime.as_ref()));
    let mut events = group_events(events);
    sort_events(&mut events);
    events.truncate(MAX_EVENTS);
    let data_date = rows.iter().filter_map(|r| r.streak.as_of.clone()).max();
    Ok(MonitorView {
        data_date,
        rows,
        counts,
        regime,
        events,
        git_status: match frozen_git(repo) {
            Some(f) => f.status(&["registry", "data"]),
            None => git_readonly(repo, &["status", "--porcelain", "--", "registry", "data"]).unwrap_or_default(),
        },
        scores_source: docs.scores_source,
        scores_integrity: None,
        snapshot: None,
    })
}

fn supported_ids(state: &AppState) -> Result<Vec<String>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    Ok(models.models.iter().map(|m| m.model_id.clone()).collect())
}

/// Monitör: repo ya da kişisel modda gömülü anlık görüntü (K-SNAP-2).
pub fn monitor_view_value(state: &AppState) -> Result<MonitorView, AppError> {
    let root = state.read_root()?;
    let loaded = load_with(state, Some(&root));
    let mut v = monitor_view_in(&root.root, &loaded.docs(), &supported_ids(state)?)?;
    v.scores_integrity = loaded.scores_integrity.clone();
    v.snapshot = root.snapshot;
    Ok(v)
}

#[tauri::command]
pub fn monitor_view(state: tauri::State<'_, AppState>) -> Result<MonitorView, AppError> {
    monitor_view_value(&state)
}

// ---------------------------------------------------------------- arz_view

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ArzView {
    pub row: MonitorRow,
    /// Kayıttaki `ceiling_hazard_v0.output.P_close_ceiling` (h = 1..10, aynen).
    pub p_close_ceiling: Vec<Option<f64>>,
    pub record_rel_path: Option<String>,
    pub record_models_index_sha256: Option<String>,
    pub record_push_proof_created_at: Option<String>,
    pub record_added_commit: Option<String>,
    /// Etkin D1 sonrası kayıt dosyaları (`post_d1_records_in`).
    pub post_d1_files: Vec<String>,
    pub regime: Option<RegimeInfo>,
    pub log: Vec<EventItem>,
}

pub fn arz_view_in(repo: &Path, ticker: &str, docs: &Docs, supported: &[String]) -> Result<ArzView, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let reg = registry_view_in(repo, supported)?;
    let regime = regime_of(docs);
    let row = monitor_row(repo, &reg, ticker, docs, regime.as_ref())?;
    let rec_row = reg.tickers.iter().find(|t| t.ticker == ticker).and_then(|t| {
        active_records(&t.records).into_iter().find(|r| Some(&r.file) == row.record_file.as_ref()).cloned()
    });
    let p_close_ceiling = match &rec_row {
        Some(r) => {
            let rec = read_record(repo, &r.rel_path)?;
            (0..10)
                .map(|i| record_cell(&rec, CEILING_MODEL).and_then(|c| num(c, &format!("/output/P_close_ceiling/{i}"))))
                .collect()
        }
        None => vec![None; 10],
    };
    let post = super::post_d1::post_d1_records_in(repo, ticker).unwrap_or_default();
    let mut log = ticker_events(&row);
    log.extend(global_events(docs, None));
    sort_events(&mut log);
    log.reverse(); // günlük eskiden yeniye
    Ok(ArzView {
        p_close_ceiling,
        record_rel_path: rec_row.as_ref().map(|r| r.rel_path.clone()),
        record_models_index_sha256: rec_row.as_ref().and_then(|r| r.models_index_sha256.clone()),
        record_push_proof_created_at: rec_row.as_ref().and_then(|r| r.push_proof.as_ref()).and_then(|p| p.created_at.clone()),
        record_added_commit: rec_row.as_ref().and_then(|r| r.added_commit.clone()),
        post_d1_files: super::post_d1::active_files(&post),
        regime,
        log,
        row,
    })
}

pub fn arz_view_value(state: &AppState, ticker: &str) -> Result<ArzView, AppError> {
    let root = state.read_root()?;
    let loaded = load_with(state, Some(&root));
    arz_view_in(&root.root, ticker, &loaded.docs(), &supported_ids(state)?)
}

#[tauri::command]
pub fn arz_view(state: tauri::State<'_, AppState>, ticker: String) -> Result<ArzView, AppError> {
    arz_view_value(&state, &ticker)
}

/// Analiz ekranının gözlenen tavan serisi (`streak_view_in`; resmi j yalnız `data/outcomes/<T>.csv`'den) veri kökünden.
/// Kişisel tahmin sonucu ekranının `streak_view` komutu aynen kalır: orada anlık görüntü okunmaz.
pub fn arz_streak_value(state: &AppState, ticker: &str) -> Result<StreakView, AppError> {
    let root = state.read_root()?;
    streak_view_in(Some(&root.root.join("data").join("outcomes")), Some(ticker))
}

#[tauri::command]
pub fn arz_streak(state: tauri::State<'_, AppState>, ticker: String) -> Result<StreakView, AppError> {
    arz_streak_value(&state, &ticker)
}

// ---------------------------------------------------------------- headline_gate (K-UI-4)

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct GateEntry {
    pub model_id: String,
    pub output: String,
    pub horizon_or_k: Option<String>,
    pub question: &'static str,
    pub source: &'static str,
    /// OK | NO_FILE (dosya yok, repo modu değil ya da bütünlük ihlali) | NO_MODEL (dosyada model yok)
    pub status: &'static str,
    /// Bu çıktı modelin önceden ilan edilmiş birincil hücresi mi.
    pub is_primary: bool,
    pub featured: bool,
    pub primary_metric: Option<String>,
    pub primary_rules: Vec<String>,
    /// Birincil hücrelerin dosyadaki verdict'leri (birincil satır başına, aynen).
    pub verdicts: Vec<String>,
    /// Kırılma: `card.promotion.label` (aynen).
    pub label: Option<String>,
    pub live_n: Option<u64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct HeadlineGate {
    pub entries: Vec<GateEntry>,
    pub scores_source: Option<&'static str>,
}

fn horizon_eq(cell_h: Option<&Value>, h: Option<&str>) -> bool {
    match (cell_h, h) {
        (None, None) | (Some(Value::Null), None) => true,
        (Some(Value::String(a)), Some(b)) => a == b,
        _ => false,
    }
}

/// Birincil hücrenin satırları: dosyadaki `primary_cell` (çıktı, ufuk, ölçü, kurallar) + `label = birincil`.
fn primary_rows<'a>(cells: &'a [Value], pc: &Value) -> Vec<&'a Value> {
    let rules: Vec<&str> = pc.get("rule_ids").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).collect();
    cells
        .iter()
        .filter(|c| {
            c.get("output") == pc.get("output")
                && c.get("metric") == pc.get("metric")
                && horizon_eq(c.get("horizon_or_k"), pc.get("horizon_or_k").and_then(Value::as_str))
                && c.get("label").and_then(Value::as_str) == Some(PRIMARY_LABEL)
                && c.get("rule_id").and_then(Value::as_str).is_some_and(|r| rules.contains(&r))
        })
        .collect()
}

fn gate_entry(docs: &Docs, model_id: &str, output: &str, h: Option<&str>, source: &'static str, question: &'static str) -> GateEntry {
    let mut e = GateEntry {
        model_id: model_id.into(),
        output: output.into(),
        horizon_or_k: h.map(str::to_string),
        question,
        source,
        status: "OK",
        is_primary: false,
        featured: false,
        primary_metric: None,
        primary_rules: Vec::new(),
        verdicts: Vec::new(),
        label: None,
        live_n: None,
    };
    let doc = match source {
        "scores.json" => docs.scores,
        "scores_post_d1.json" => docs.post_d1,
        _ => docs.brk,
    };
    let Some(doc) = doc else {
        e.status = "NO_FILE";
        return e;
    };
    let Some(m) = model_of(doc, model_id) else {
        e.status = "NO_MODEL";
        return e;
    };
    let pc = m.get("primary_cell").cloned().unwrap_or(Value::Null);
    e.primary_metric = st(&pc, "/metric");
    e.primary_rules = pc.get("rule_ids").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(str::to_string).collect();
    e.is_primary = pc.get("output").and_then(Value::as_str) == Some(output) && horizon_eq(pc.get("horizon_or_k"), h);
    match source {
        "scores_break.json" => {
            e.label = st(m, "/card/promotion/label");
            e.live_n = uint(m, "/live_break/n_scored");
            e.featured = e.is_primary && m.pointer("/card/promotion/promoted").and_then(Value::as_bool) == Some(true);
        }
        _ => {
            let cells_ptr = if source == "scores.json" { "/backtest/cells" } else { "/conditional_j1/cells" };
            let cells = m.pointer(cells_ptr).and_then(Value::as_array).map_or(&[][..], Vec::as_slice);
            let rows = if e.is_primary { primary_rows(cells, &pc) } else { Vec::new() };
            e.verdicts = rows.iter().filter_map(|c| st(c, "/verdict")).collect();
            e.live_n = if source == "scores.json" { uint(m, "/live/n_live") } else { uint(m, "/conditional_j1/n_live") };
            e.featured = e.is_primary
                && !rows.is_empty()
                && rows.len() == e.primary_rules.len()
                && rows.iter().all(|c| c.get("verdict").and_then(Value::as_str) == Some(VERDICT_PASS));
        }
    }
    e
}

pub fn headline_gate_value(docs: &Docs) -> HeadlineGate {
    HeadlineGate {
        entries: HEADLINE_OUTPUTS.iter().map(|&(m, o, h, src, q)| gate_entry(docs, m, o, h, src, q)).collect(),
        scores_source: docs.scores_source,
    }
}

#[tauri::command]
pub fn headline_gate(state: tauri::State<'_, AppState>) -> Result<HeadlineGate, AppError> {
    Ok(headline_gate_value(&load(&state).docs()))
}

// ---------------------------------------------------------------- perf_view

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PerfRow {
    pub model_id: String,
    pub question: &'static str,
    pub source: &'static str,
    /// Dosyadaki ölçek (`backtest`, `backtest_break`).
    pub scale: Option<String>,
    pub output: Option<String>,
    pub horizon_or_k: Option<String>,
    pub metric: Option<String>,
    pub rule_id: Option<String>,
    /// `birincil` | `keşif` (dosyadan); kırılma satırları null.
    pub label: Option<String>,
    pub model_value: Option<Value>,
    pub rule_value: Option<Value>,
    pub diff: Option<Value>,
    pub ci95: Option<Value>,
    pub n: Option<u64>,
    pub n_months: Option<u64>,
    pub wins: Option<u64>,
    pub losses: Option<u64>,
    pub ties: Option<u64>,
    /// Dosyadaki hüküm alanı (aynen); kırılma `backtest_info`'da hüküm alanı yok → null.
    pub verdict: Option<String>,
    /// Kırılma: `backtest_info.label` (aynen).
    pub file_label: Option<String>,
    pub featured: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OotSummary {
    /// OK | NO_FILE | NO_BLOCK | NO_TEST
    pub status: &'static str,
    pub block: Option<String>,
    pub verdict: Option<String>,
    pub n: Option<u64>,
    pub rule_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct LiveSummary {
    pub n_scored: Option<u64>,
    pub n_live: Option<u64>,
    pub n_late: Option<u64>,
    pub n_refused: Option<u64>,
    pub n_retro: Option<u64>,
    pub n_machine: Option<u64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ScaleSummary {
    pub model_id: String,
    pub question: &'static str,
    /// Geçmiş test: birincil hücre verdict'leri (scores.json / scores_post_d1.json) ya da kırılma `backtest_info.label`.
    pub backtest_verdicts: Vec<String>,
    pub backtest_label: Option<String>,
    pub backtest_status: &'static str,
    pub featured: bool,
    pub oot: OotSummary,
    pub live: LiveSummary,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct LiveCell {
    pub class: Option<String>,
    pub status: Option<String>,
    /// Tavan: tahmin S'inden beklenen L (`ceiling_display_value`); getiri: `prediction.D5.return`.
    pub predicted: Option<f64>,
    /// Tavan: `realized.L`; getiri: `realized.R.D5` metni.
    pub realized: Option<Value>,
    pub record_source: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PerfLiveRow {
    pub ticker: String,
    pub d1: Option<String>,
    pub ceiling: Option<LiveCell>,
    pub d5: Option<LiveCell>,
    pub post_d1_status: Option<String>,
    pub break_class: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Default)]
pub struct PerfCounts {
    pub n_rows: usize,
    /// Dosyadaki verdict'e göre ayrı sayımlar (FAZ9_UI_FIX K-FIX-5): geçiyor / ayırt edilemiyor / geçemiyor / başka verdict
    /// (ör. yetersiz örnek); hüküm alanı olmayan satırlar ayrı. Toplanmaz, birbirine karışmaz.
    pub n_pass: usize,
    pub n_undecided: usize,
    pub n_fail: usize,
    pub n_other: usize,
    pub n_no_verdict: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PerfView {
    pub rows: Vec<PerfRow>,
    pub scales: Vec<ScaleSummary>,
    pub live_rows: Vec<PerfLiveRow>,
    pub counts: PerfCounts,
    pub min_n_metric: u64,
    pub min_n_verdict: u64,
    pub n_production: usize,
    pub scores_source: Option<&'static str>,
    pub scores_integrity: Option<IntegrityProblem>,
    pub has_post_d1: bool,
    pub has_break: bool,
    pub has_oot: bool,
}

fn cell_row(m_id: &str, question: &'static str, c: &Value, featured: bool) -> PerfRow {
    PerfRow {
        model_id: m_id.into(),
        question,
        source: "scores.json",
        scale: st(c, "/scale"),
        output: st(c, "/output"),
        horizon_or_k: c.get("horizon_or_k").and_then(|h| h.as_str().map(str::to_string).or_else(|| h.as_u64().map(|x| x.to_string()))),
        metric: st(c, "/metric"),
        rule_id: st(c, "/rule_id"),
        label: st(c, "/label"),
        model_value: c.get("model_value").cloned(),
        rule_value: c.get("rule_value").cloned(),
        diff: c.get("diff").cloned(),
        ci95: c.get("ci95").cloned().filter(|v| !v.is_null()),
        n: uint(c, "/n"),
        n_months: uint(c, "/n_blocks"),
        wins: uint(c, "/wins"),
        losses: uint(c, "/losses"),
        ties: uint(c, "/ties"),
        verdict: st(c, "/verdict"),
        file_label: None,
        featured,
    }
}

fn break_row(info: &Value, key: &str, rule: &str, featured: bool) -> Option<PerfRow> {
    let b = info.get(key)?;
    Some(PerfRow {
        model_id: BREAK_MODEL.into(),
        question: "BREAK_FLOOR",
        source: "scores_break.json",
        scale: st(info, "/scale"),
        output: Some("p_floor".into()),
        horizon_or_k: Some("F1".into()),
        metric: Some("Brier".into()),
        rule_id: Some(rule.into()),
        label: None,
        model_value: None,
        rule_value: None,
        diff: b.get("diff").cloned(),
        ci95: b.get("ci95").cloned().filter(|v| !v.is_null()),
        n: uint(b, "/n"),
        n_months: uint(b, "/n_months"),
        wins: None,
        losses: None,
        ties: None,
        verdict: None,
        file_label: st(info, "/label"),
        featured,
    })
}

fn oot_summary(docs: &Docs, model_id: &str, block: Option<&str>) -> OotSummary {
    let none = |status| OotSummary { status, block: block.map(str::to_string), verdict: None, n: None, rule_id: None };
    let Some(block) = block else { return none("NO_TEST") };
    let Some(doc) = docs.oot else { return none("NO_FILE") };
    let Some(c) = model_block(doc, block, model_id).and_then(primary_cell) else { return none("NO_BLOCK") };
    OotSummary {
        status: "OK",
        block: Some(block.into()),
        verdict: st(c, "/verdict"),
        n: uint(c, "/n"),
        rule_id: st(c, "/rule_id"),
    }
}

fn live_summary(docs: &Docs, model_id: &str) -> LiveSummary {
    let (doc, ptr) = match model_id {
        POST_D1_MODEL => (docs.post_d1, "/conditional_j1"),
        BREAK_MODEL => (docs.brk, "/live_break"),
        _ => (docs.scores, "/live"),
    };
    let Some(b) = doc.and_then(|d| model_of(d, model_id)).and_then(|m| m.pointer(ptr)) else { return LiveSummary::default() };
    LiveSummary {
        n_scored: uint(b, "/n_scored"),
        n_live: uint(b, "/n_live"),
        n_late: uint(b, "/n_late"),
        n_refused: uint(b, "/n_refused"),
        n_retro: uint(b, "/n_retro"),
        n_machine: uint(b, "/n_machine"),
    }
}

fn expected_from_prediction(pred: &Value) -> Option<f64> {
    let s: Vec<f64> = serde_json::from_value(pred.get("S")?.clone()).ok()?;
    if s.len() != 10 || !s.iter().all(|x| x.is_finite()) {
        return None;
    }
    ceiling_display_value(&[SVector { model_id: CEILING_MODEL.into(), s }], 0, None).ok().map(|d| d.rows[0].expected_l)
}

fn live_rows(docs: &Docs) -> Vec<PerfLiveRow> {
    let Some(doc) = docs.scores else { return Vec::new() };
    let rows_of = |mid: &str| -> Vec<Value> {
        model_of(doc, mid).and_then(|m| m.pointer("/live/rows")).and_then(Value::as_array).cloned().unwrap_or_default()
    };
    let ceil = rows_of(CEILING_MODEL);
    let ret = rows_of(RETURN_MODEL);
    let mut tickers: Vec<(String, String)> = ceil
        .iter()
        .chain(ret.iter())
        .filter_map(|r| Some((st(r, "/d1").unwrap_or_default(), st(r, "/ticker")?)))
        .collect();
    tickers.sort();
    tickers.dedup();
    let find = |rows: &[Value], t: &str| rows.iter().find(|r| r.get("ticker").and_then(Value::as_str) == Some(t)).cloned();
    tickers
        .into_iter()
        .map(|(d1, t)| {
            let c = find(&ceil, &t);
            let r = find(&ret, &t);
            PerfLiveRow {
                ceiling: c.as_ref().map(|c| LiveCell {
                    class: st(c, "/class"),
                    status: st(c, "/status"),
                    predicted: c.get("prediction").and_then(expected_from_prediction),
                    realized: c.pointer("/realized/L").cloned(),
                    record_source: st(c, "/record_source"),
                }),
                d5: r.as_ref().map(|r| LiveCell {
                    class: st(r, "/class"),
                    status: st(r, "/status"),
                    predicted: num(r, "/prediction/D5/return"),
                    realized: r.pointer("/realized/R/D5").cloned(),
                    record_source: st(r, "/record_source"),
                }),
                post_d1_status: docs
                    .post_d1
                    .and_then(|d| denominator_row(d, POST_D1_MODEL, "conditional_j1", &t))
                    .and_then(|r| st(r, "/stage_status")),
                break_class: docs.brk.and_then(|d| denominator_row(d, BREAK_MODEL, "live_break", &t)).and_then(|r| st(r, "/class")),
                d1: Some(d1).filter(|d| !d.is_empty()),
                ticker: t,
            }
        })
        .collect()
}

pub fn perf_view_value(docs: &Docs) -> PerfView {
    let gate = headline_gate_value(docs);
    let featured = |m: &str, o: &str, h: Option<&str>| {
        gate.entries.iter().any(|e| e.model_id == m && e.output == o && e.horizon_or_k.as_deref() == h && e.featured)
    };
    let mut rows = Vec::new();
    if let Some(doc) = docs.scores {
        for (mid, q) in [(CEILING_MODEL, "CEILING_DAYS"), (RETURN_MODEL, "RETURN")] {
            let Some(m) = model_of(doc, mid) else { continue };
            let pc = m.get("primary_cell").cloned().unwrap_or(Value::Null);
            let cells = m.pointer("/backtest/cells").and_then(Value::as_array).map_or(&[][..], Vec::as_slice);
            let f = featured(mid, st(&pc, "/output").as_deref().unwrap_or_default(), pc.get("horizon_or_k").and_then(Value::as_str));
            let mut prim = primary_rows(cells, &pc);
            // kural sırası dosyadaki `rule_ids` sırasıyla
            let order: Vec<String> = pc.get("rule_ids").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(str::to_string).collect();
            prim.sort_by_key(|c| order.iter().position(|r| Some(r.as_str()) == c.get("rule_id").and_then(Value::as_str)));
            rows.extend(prim.into_iter().map(|c| cell_row(mid, q, c, f)));
        }
        for (mid, out, h, metric, rule, q) in PERF_EXTRA_CELLS {
            let Some(m) = model_of(doc, mid) else { continue };
            let cells = m.pointer("/backtest/cells").and_then(Value::as_array).map_or(&[][..], Vec::as_slice);
            if let Some(c) = cells.iter().find(|c| {
                st(c, "/output").as_deref() == Some(out)
                    && c.get("horizon_or_k").and_then(Value::as_str) == Some(h)
                    && st(c, "/metric").as_deref() == Some(metric)
                    && st(c, "/rule_id").as_deref() == Some(rule)
            }) {
                rows.push(cell_row(mid, q, c, featured(mid, out, Some(h))));
            }
        }
    }
    if let Some(info) = docs.brk.and_then(|d| model_of(d, BREAK_MODEL)).and_then(|m| m.pointer("/card/backtest_info")) {
        let f = featured(BREAK_MODEL, "p_floor", Some("F1"));
        rows.extend(break_row(info, "F1_product", "PRODUCT_BREAK_FLOOR", f));
        rows.extend(break_row(info, "F1_zero", BREAK_ZERO, f));
    }
    let counts = PerfCounts {
        n_rows: rows.len(),
        n_pass: rows.iter().filter(|r| r.verdict.as_deref() == Some(VERDICT_PASS)).count(),
        n_undecided: rows.iter().filter(|r| r.verdict.as_deref() == Some(VERDICT_UNDECIDED)).count(),
        n_fail: rows.iter().filter(|r| r.verdict.as_deref() == Some(VERDICT_FAIL)).count(),
        n_other: rows
            .iter()
            .filter(|r| r.verdict.as_deref().is_some_and(|v| v != VERDICT_PASS && v != VERDICT_UNDECIDED && v != VERDICT_FAIL))
            .count(),
        n_no_verdict: rows.iter().filter(|r| r.verdict.is_none()).count(),
    };
    let scales = PRODUCTION_MODELS
        .iter()
        .map(|&(mid, q, block)| {
            let entry = gate.entries.iter().find(|e| e.model_id == mid && e.is_primary);
            let (verdicts, label, status) = if mid == BREAK_MODEL {
                let info = docs.brk.and_then(|d| model_of(d, BREAK_MODEL)).and_then(|m| m.pointer("/card/backtest_info"));
                (Vec::new(), info.and_then(|i| st(i, "/label")), if info.is_some() { "OK" } else { "NO_FILE" })
            } else {
                (entry.map(|e| e.verdicts.clone()).unwrap_or_default(), None, entry.map_or("NO_FILE", |e| e.status))
            };
            ScaleSummary {
                model_id: mid.into(),
                question: q,
                backtest_verdicts: verdicts,
                backtest_label: label,
                backtest_status: status,
                featured: entry.is_some_and(|e| e.featured),
                oot: oot_summary(docs, mid, block),
                live: live_summary(docs, mid),
            }
        })
        .collect();
    PerfView {
        rows,
        scales,
        live_rows: live_rows(docs),
        counts,
        min_n_metric: MIN_N_METRIC,
        min_n_verdict: MIN_N_VERDICT,
        n_production: PRODUCTION_MODELS.len(),
        scores_source: docs.scores_source,
        scores_integrity: None,
        has_post_d1: docs.post_d1.is_some(),
        has_break: docs.brk.is_some(),
        has_oot: docs.oot.is_some(),
    }
}

#[tauri::command]
pub fn perf_view(state: tauri::State<'_, AppState>) -> Result<PerfView, AppError> {
    let loaded = load(&state);
    let mut v = perf_view_value(&loaded.docs());
    v.scores_integrity = loaded.scores_integrity.clone();
    Ok(v)
}
