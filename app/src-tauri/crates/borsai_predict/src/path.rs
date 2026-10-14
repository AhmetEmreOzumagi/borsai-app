//! Tavan yolu modelleri (`ceiling_path_v0`, `ceiling_path_v0@INF`, `pb_ceiling_path_v0`):
//! `borsai/predict_path.py` portu, SPEC_CEILING_PATH_V0 §2–§4 ve §7 (SPEC_APP EK 2 §2).
//!
//! - Seri bileşeni S_k gömülü (dondurulmuş) seri modelinden `hazard::predict_hazard` ile gelir; ret
//!   ve uyarıları aynen geçer. Kopyanın INDEX'le eşitliği açılışta denetlenir (U41).
//! - Limit yolu C_h KESİN ondalıkla (`dec::div_exact` / `mul_ctx` / `to_integral`): fiyat adımı
//!   tablosu, üst limit aşağı adıma, D1 baz fiyatı HALF_UP. Metin alanları `dec::py_str`.
//! - Karışım binary64: atomlar Python ekleme sırasıyla, kararlı sıralama, kümülatif toplam düz `+=`,
//!   `p_up`/`mean` CPython `sum()` (Neumaier), kuantil eşiği `q − 1e-12`.
//! - Kesin bağlamın `Inexact`/`Overflow` tuzağı Python'da etiketsiz istisnadır → `DOMAIN_ERROR`.
use serde_json::{json, Map, Value};
use std::cmp::Ordering;
use std::collections::BTreeMap;

use crate::dec::{self, Dec, Inexact, Parsed, Rounding};
use crate::error::*;
use crate::features::parse_decimal;
use crate::hazard::predict_hazard;
use crate::output::{PathOutput, Warning};
use crate::params::PathParams;
use crate::pb_features::parse_pb_decimal;
use crate::sum::{py_max, py_min, py_sum};
use crate::survival::DAYS;

pub const ALGORITHM: &str = "CEILING_PATH_MIXTURE_EQ_V0";
pub const MARGIN: &str = "0.10";
/// (`below`, `tick`); son satırın `below`'u null (üst sınır yok).
pub const TICK_TABLE: [(Option<&str>, &str); 8] = [
    (Some("20"), "0.01"),
    (Some("50"), "0.02"),
    (Some("100"), "0.05"),
    (Some("250"), "0.10"),
    (Some("500"), "0.25"),
    (Some("1000"), "0.50"),
    (Some("2500"), "1.00"),
    (None, "2.50"),
];
pub const UPPER_ROUNDING: &str = "FLOOR_TO_TICK_AT_LIMIT_LEVEL";
pub const D1_BASE: &str = "HALF_UP_TO_TICK";
pub const PRICE_FIELDS: [&str; 2] = ["ipo_price_tl", "ipo_price_try"];
pub const N_MIN: usize = 10;
pub const GROUP_KEYS: [&str; 2] = ["Z", "B"];
pub const QUANTILE_EPS: f64 = 1e-12;
/// `predict_path._EXACT` / `_RATIO`: prec 60.
pub const PREC: u64 = 60;

pub const STATUS_OK: &str = "OK";
pub const STATUS_POST_BREAK_INSUFFICIENT: &str = "POST_BREAK_INSUFFICIENT";
pub const STATUS_REALIZED: &str = "REALIZED";
pub const STATE_STREAK_ONGOING: &str = "STREAK_ONGOING";
pub const STATE_AFTER_BREAK: &str = "AFTER_BREAK";

// ---------------------------------------------------------------- hücre anahtarı

/// Kırılma sonrası hücre grubu: Z = seri hiç başlamadı (t = 0), B = t. günde bozuldu (1 ≤ t ≤ 9).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Group {
    Z,
    B,
}

impl Group {
    pub fn as_str(&self) -> &'static str {
        match self {
            Group::Z => "Z",
            Group::B => "B",
        }
    }
    pub fn m_max(&self) -> i32 {
        match self {
            Group::Z => DAYS as i32,
            Group::B => DAYS as i32 - 1,
        }
    }
    pub fn parse(s: &str) -> Option<Group> {
        match s {
            "Z" => Some(Group::Z),
            "B" => Some(Group::B),
            _ => None,
        }
    }
}

/// `GROUPS` sırası (Python `("Z", "B")`).
pub const GROUPS: [Group; 2] = [Group::Z, Group::B];

pub fn group_of(t: usize) -> Group {
    if t == 0 {
        Group::Z
    } else {
        Group::B
    }
}

pub fn valid_cell(g: Group, m: i32) -> bool {
    1 <= m && m <= g.m_max()
}

/// Hücre gözlemleri: (değer, ticker), dosya sırasıyla.
pub type Cells = BTreeMap<(Group, i32), Vec<(f64, String)>>;

// ---------------------------------------------------------------- §2 limit yolu

fn dec_of(text: &str) -> Dec {
    match dec::parse(text) {
        Some(Parsed::Finite(d)) => d,
        other => panic!("şartname sabiti ayrıştırılamadı: {text:?} -> {other:?}"),
    }
}

fn ticks() -> Vec<(Option<Dec>, Dec)> {
    TICK_TABLE.iter().map(|(lim, t)| (lim.map(dec_of), dec_of(t))).collect()
}

/// x'in düştüğü fiyat seviyesinin adımı (tablo sırasıyla ilk `lim is None || x < lim`).
pub fn tick(x: &Dec) -> Dec {
    for (lim, t) in ticks() {
        match &lim {
            None => return t,
            Some(l) if dec::cmp(x, l) == Ordering::Less => return t,
            _ => {}
        }
    }
    unreachable!("adım tablosu sonu")
}

/// Adımın JSON'daki metni (uyarı ve çıktı alanı; `str(Decimal)` ile aynı).
pub fn tick_text(x: &Dec) -> String {
    dec::py_str(&tick(x))
}

fn one_plus_margin() -> Dec {
    dec_of("1.10")
}

/// U(b) = floor(b·1.10 / adım(b·1.10)) · adım(b·1.10).
pub fn upper_limit(base: &Dec) -> Result<Dec, Inexact> {
    let y = dec::mul_ctx(base, &one_plus_margin(), PREC)?;
    let s = tick(&y);
    let q = dec::to_integral(&dec::div_exact(&y, &s, PREC)?, Rounding::Floor);
    dec::mul_ctx(&q, &s, PREC)
}

/// D1 baz fiyatı: arz fiyatı kendi seviyesinin adımına HALF_UP ile oturtulur.
pub fn snap(price: &Dec) -> Result<Dec, Inexact> {
    let s = tick(price);
    let q = dec::to_integral(&dec::div_exact(price, &s, PREC)?, Rounding::HalfUp);
    dec::mul_ctx(&q, &s, PREC)
}

/// `float(a / b)`: 60 haneye yuvarlanır, sonra bir kez binary64 (Python `_RATIO`; çift yuvarlama
/// aynen — kesin rasyonelden doğrudan binary64'e kısayol PARİTE KANITI DEĞİLDİR).
pub fn ratio(a: &Dec, b: &Dec) -> Result<f64, PredictError> {
    if b.is_zero() {
        return Err(PredictError::domain("oran: payda sıfır (Python decimal.DivisionByZero)"));
    }
    Ok(dec::div_round(a, b, PREC).to_f64())
}

/// `float(a / b − 1)` (aynı bağlam).
pub fn ratio_minus_one(a: &Dec, b: &Dec) -> Result<f64, PredictError> {
    if b.is_zero() {
        return Err(PredictError::domain("oran: payda sıfır (Python decimal.DivisionByZero)"));
    }
    let q = dec::div_round(a, b, PREC);
    dec::add_exact(&q, &Dec::from_i64(-1), PREC)
        .map(|d| d.to_f64())
        .map_err(|_| PredictError::domain("oran − 1 60 hanede kesin değil"))
}

/// (0.9^m − 1, 1.1^m − 1): kesin Decimal'den bir kez binary64 (metin sabitleri, SPEC_APP EK 2 §2.2).
pub fn physical_bounds(m: i32) -> (f64, f64) {
    const B: [(&str, &str); 10] = [
        ("-0.1", "0.1"),
        ("-0.19", "0.21"),
        ("-0.271", "0.331"),
        ("-0.3439", "0.4641"),
        ("-0.40951", "0.61051"),
        ("-0.468559", "0.771561"),
        ("-0.5217031", "0.9487171"),
        ("-0.56953279", "1.14358881"),
        ("-0.612579511", "1.357947691"),
        ("-0.6513215599", "1.5937424601"),
    ];
    let (lo, hi) = B[(m - 1) as usize];
    (lo.parse().expect("alt sınır"), hi.parse().expect("üst sınır"))
}

#[derive(Debug, Clone, PartialEq)]
pub struct LimitPath {
    pub price: Dec,
    pub snapped: Dec,
    pub tick: Dec,
    pub c: Vec<Dec>,
    pub rho: Vec<f64>,
    pub scale: Vec<f64>,
}

/// C_0 = snap(P); C_k = U(C_{k−1}); ρ_k = C_k/P − 1; scale_k = C_k/P.
pub fn limit_path(price: &Dec) -> Result<LimitPath, PredictError> {
    let inexact = |_| PredictError::domain("limit yolu kesin ondalıkta hesaplanamadı (decimal.Inexact)");
    let snapped = snap(price).map_err(inexact)?;
    let mut c = Vec::with_capacity(DAYS);
    let mut b = snapped.clone();
    for _ in 0..DAYS {
        b = upper_limit(&b).map_err(inexact)?;
        c.push(b.clone());
    }
    let mut rho = Vec::with_capacity(DAYS);
    let mut scale = Vec::with_capacity(DAYS);
    for x in &c {
        rho.push(ratio_minus_one(x, price)?);
        scale.push(ratio(x, price)?);
    }
    Ok(LimitPath { price: price.clone(), snapped, tick: tick(price), c, rho, scale })
}

// ---------------------------------------------------------------- §3 havuzlama

/// §3 merdiveni: [kendi], [diğer grup aynı m], sonra d = 1..9 için m−d ve m+d (her adımda Z sonra B).
/// Geçersiz hücreler adımdan atılır; adım boş kalabilir (Python `ladder` ile aynı).
pub fn ladder(group: Group, m: i32) -> Vec<Vec<(Group, i32)>> {
    let other = if group == Group::Z { Group::B } else { Group::Z };
    let mut steps: Vec<Vec<(Group, i32)>> = vec![vec![(group, m)], vec![(other, m)]];
    for d in 1..DAYS as i32 {
        for mm in [m - d, m + d] {
            steps.push(GROUPS.iter().map(|&g| (g, mm)).collect());
        }
    }
    steps
        .into_iter()
        .map(|step| step.into_iter().filter(|(g, mm)| valid_cell(*g, *mm)).collect())
        .collect()
}

#[derive(Debug, Clone, PartialEq)]
pub struct PooledCell {
    pub group: Group,
    pub m: i32,
    /// Hedef m'nin fiziksel sınırına kırpılmış değerler, toplama sırasıyla.
    pub values: Vec<f64>,
    /// Merdivende BAKILAN bütün geçerli hücreler (boşlar dahil), sırayla.
    pub sources: Vec<(Group, i32)>,
    pub n_clipped: usize,
    pub sufficient: bool,
}

impl PooledCell {
    pub fn n(&self) -> usize {
        self.values.len()
    }
    pub fn pooled(&self) -> bool {
        self.sources.len() > 1
    }
    pub fn to_json(&self) -> Value {
        json!({
            "group": self.group.as_str(),
            "m": self.m,
            "n": self.n(),
            "pooled": self.pooled(),
            "sources": self.sources.iter().map(|(g, m)| json!([g.as_str(), m])).collect::<Vec<_>>(),
        })
    }
}

/// Deterministik havuzlama: her adım bir hücre grubu, ADIM SONUNDA n ≥ N_MIN ise durulur.
pub fn pool(cells: &Cells, group: Group, m: i32, n_min: usize) -> PooledCell {
    debug_assert!(valid_cell(group, m), "geçersiz hücre ({}, {m})", group.as_str());
    let mut gathered: Vec<f64> = Vec::new();
    let mut sources: Vec<(Group, i32)> = Vec::new();
    for step in ladder(group, m) {
        for key in step {
            sources.push(key);
            if let Some(list) = cells.get(&key) {
                gathered.extend(list.iter().map(|(v, _)| *v));
            }
        }
        if gathered.len() >= n_min {
            break;
        }
    }
    let (lo, hi) = physical_bounds(m);
    let values: Vec<f64> = gathered.iter().map(|&v| py_min(py_max(v, lo), hi)).collect();
    let n_clipped = gathered.iter().zip(&values).filter(|(a, b)| *a != *b).count();
    PooledCell { group, m, sufficient: gathered.len() >= n_min, values, sources, n_clipped }
}

// ---------------------------------------------------------------- §4 karışım

/// Atom listesi (Python ekleme sırası): limit atomu, sonra her parça (t, toplam ağırlık, ölçek) için
/// hücre(g(t), h − t) atomları; ölçek None ise atom v (t = 0), değilse `scale·(1 + v) − 1`.
pub fn mixture_atoms(
    limit_atom: Option<(f64, f64)>,
    parts: &[(usize, f64, Option<f64>)],
    cells: &Cells,
    h: usize,
) -> (Vec<(f64, f64)>, Vec<PooledCell>, bool) {
    let mut atoms: Vec<(f64, f64)> = limit_atom.map(|a| vec![a]).unwrap_or_default();
    let mut used: Vec<PooledCell> = Vec::new();
    for &(t, weight, scale) in parts {
        let pc = pool(cells, group_of(t), h as i32 - t as i32, N_MIN);
        let sufficient = pc.sufficient;
        let n = pc.n();
        let values = pc.values.clone();
        used.push(pc);
        if !sufficient {
            return (atoms, used, false);
        }
        let w = weight / n as f64;
        for v in values {
            atoms.push((if let Some(s) = scale { s * (1.0 + v) - 1.0 } else { v }, w));
        }
    }
    (atoms, used, true)
}

#[derive(Debug, Clone, PartialEq)]
pub struct Summary {
    pub ret: f64,
    pub p_up: f64,
    pub mean: f64,
    pub q10: f64,
    pub q50: f64,
    pub q90: f64,
}

/// Kuantil kuralı (§4): (r, ekleme sırası) artan (KARARLI sıralama); F ≥ q − 1e-12 sağlayan ilk r.
/// Kümülatif toplam düz `+=`; `p_up`/`mean` CPython `sum()` (Neumaier).
pub fn summarize(atoms: &[(f64, f64)]) -> Summary {
    let mut ordered = atoms.to_vec();
    ordered.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
    // Boş atom listesi ulaşılamaz (yeterli havuz ≥ 10 değer, ya da limit atomu vardır);
    // Python'da bu durumda `ordered[-1]` IndexError verirdi.
    let last = ordered.last().map(|a| a.0).unwrap_or(f64::NAN);
    let q = |p: f64| -> f64 {
        let mut cum = 0.0f64;
        for &(r, w) in &ordered {
            cum += w;
            if cum >= p - QUANTILE_EPS {
                return r;
            }
        }
        last
    };
    Summary {
        ret: q(0.5),
        p_up: py_sum(ordered.iter().filter(|(r, _)| *r > 0.0).map(|(_, w)| *w)),
        mean: py_sum(ordered.iter().map(|(r, w)| r * w)),
        q10: q(0.1),
        q50: q(0.5),
        q90: q(0.9),
    }
}

/// Bir ufkun çıktısı (koşulsuz ve koşullu OK hücreleri).
#[derive(Debug, Clone, PartialEq)]
pub struct Horizon {
    /// `POST_BREAK_INSUFFICIENT`'ta None (bütün özet alanları null).
    pub summary: Option<Summary>,
    pub limit_path_return: Option<f64>,
    pub s_h: Option<f64>,
    pub n_atoms: usize,
    pub cells: Vec<PooledCell>,
    pub status: &'static str,
}

fn horizon(
    atoms: Vec<(f64, f64)>,
    used: Vec<PooledCell>,
    ok: bool,
    limit_return: Option<f64>,
    s_h: Option<f64>,
) -> Horizon {
    Horizon {
        summary: ok.then(|| summarize(&atoms)),
        limit_path_return: limit_return,
        s_h,
        n_atoms: if ok { atoms.len() } else { 0 },
        cells: used,
        status: if ok { STATUS_OK } else { STATUS_POST_BREAK_INSUFFICIENT },
    }
}

impl Horizon {
    /// Python `_horizon` sözlüğünün anahtar sırası.
    pub fn to_map(&self) -> Map<String, Value> {
        let mut m = Map::new();
        let f = |x: Option<f64>| x.map(crate::output::jnum).unwrap_or(Value::Null);
        let s = self.summary.as_ref();
        m.insert("return".into(), f(s.map(|x| x.ret)));
        m.insert("p_up".into(), f(s.map(|x| x.p_up)));
        m.insert("mean".into(), f(s.map(|x| x.mean)));
        m.insert("q10".into(), f(s.map(|x| x.q10)));
        m.insert("q50".into(), f(s.map(|x| x.q50)));
        m.insert("q90".into(), f(s.map(|x| x.q90)));
        m.insert("limit_path_return".into(), f(self.limit_path_return));
        m.insert("S_h".into(), f(self.s_h));
        m.insert("p_limit_path".into(), f(self.s_h));
        m.insert("n_atoms".into(), json!(self.n_atoms));
        m.insert(
            "post_break".into(),
            json!({"cells": self.cells.iter().map(PooledCell::to_json).collect::<Vec<_>>(), "status": self.status}),
        );
        m
    }
}

/// Koşulsuz D_h: limit atomu (ρ_h, S_h) + t = 0..h−1 parçaları, ağırlık P_L[t].
pub fn horizon_prediction(s: &[f64], p_l: &[f64], scale: &[f64], rho: &[f64], cells: &Cells, h: usize) -> Horizon {
    let parts: Vec<(usize, f64, Option<f64>)> =
        (0..h).map(|t| (t, p_l[t], if t == 0 { None } else { Some(scale[t - 1]) })).collect();
    let (atoms, used, ok) = mixture_atoms(Some((rho[h - 1], s[h - 1])), &parts, cells, h);
    horizon(atoms, used, ok, Some(rho[h - 1]), Some(s[h - 1]))
}

// ---------------------------------------------------------------- predict

/// Arz fiyatı (limit yolu için). `ipo_price_try` PB alanı, ötekiler V1.5 alanı.
fn price_of(field: &str, value: Option<&Value>) -> Result<Dec, Refusal> {
    if field == "ipo_price_try" {
        let p = parse_pb_decimal(value, field).map_err(|e| match e {
            FeatureFail::Refuse(r) => r,
            FeatureFail::Domain(m) => Refusal::new(PB_FIELD_MISSING, Some(field), m),
        })?;
        if p.signum() <= 0 {
            return Err(Refusal::new(PB_IDENTITY, Some("VALUE_POSITIVE"), "arz fiyatı pozitif değil"));
        }
        return Ok(p);
    }
    let p = parse_decimal(value, field, true)?.expect("required");
    if p.signum() <= 0 {
        return Err(Refusal::new(INPUT_NOT_POSITIVE, Some(field), format!("{field}: pozitif olmalı")));
    }
    Ok(p)
}

pub fn predict_path(p: &PathParams, inputs: &Map<String, Value>) -> Result<PathOutput, PredictError> {
    let surv = predict_hazard(&p.survival, inputs)?;
    let mut out = PathOutput {
        model_id: p.model_id.clone(),
        refused: None,
        warnings: surv.warnings.clone(),
        clipped: surv.clipped,
        hazard: surv.hazard.clone(),
        s: surv.s.clone(),
        p_l: surv.p_l.clone(),
        p_close_ceiling: surv.p_close_ceiling.clone(),
        limit_path: None,
        horizons: vec![None; DAYS],
    };
    if let Some(r) = surv.refused {
        out.refused = Some(r);
        return Ok(out);
    }
    let field = p.price_field.as_str();
    let price = match price_of(field, inputs.get(field)) {
        Ok(p) => p,
        Err(r) => {
            // Python `out.update(...)`: ret yazılır, seri alanları None'a çekilir, uyarılar kalır.
            out.refused = Some(r);
            out.hazard = None;
            out.s = None;
            out.p_l = None;
            out.p_close_ceiling = None;
            out.clipped = None;
            return Ok(out);
        }
    };
    let lp = limit_path(&price)?;
    if !dec::eq(&lp.snapped, &price) {
        let (value, snapped, tick_t) = (dec::py_str(&price), dec::py_str(&lp.snapped), dec::py_str(&lp.tick));
        out.warnings.push(Warning {
            code: WARN_IPO_PRICE_NOT_ON_TICK_GRID.into(),
            message: format!(
                "arz fiyatı {value} fiyat adımı ızgarasında değil (adım {tick_t}); D1 baz fiyatı {snapped} alındı"
            ),
            text_fields: vec![
                ("field".into(), field.to_string()),
                ("value".into(), value),
                ("snapped".into(), snapped),
                ("tick".into(), tick_t),
            ],
            ..Default::default()
        });
    }
    out.limit_path = Some(crate::output::LimitPathOut {
        ipo_price: dec::py_str(&lp.price),
        snapped_ipo_price: dec::py_str(&lp.snapped),
        tick: dec::py_str(&lp.tick),
        c: lp.c.iter().map(dec::py_str).collect(),
        rho: lp.rho.clone(),
    });
    let (s, p_l) = (out.s.clone().expect("S"), out.p_l.clone().expect("P_L"));
    for h in 1..=DAYS {
        out.horizons[h - 1] = Some(horizon_prediction(&s, &p_l, &lp.scale, &lp.rho, &p.cells, h));
    }
    Ok(out)
}

// ---------------------------------------------------------------- §7 koşullu güncelleme

pub const CONDITIONAL_INVALID: &str = "CONDITIONAL_INVALID";

fn invalid(msg: impl Into<String>) -> PredictError {
    PredictError::new(CONDITIONAL_INVALID, msg)
}

/// JSON'dan binary64: sayı ya da sonlu olmayanların metni ("NaN", "Infinity", "-Infinity").
fn jf64(v: &Value) -> Option<f64> {
    match v {
        Value::Number(n) => n.as_f64(),
        Value::String(s) => match s.as_str() {
            "NaN" => Some(f64::NAN),
            "Infinity" => Some(f64::INFINITY),
            "-Infinity" => Some(f64::NEG_INFINITY),
            _ => None,
        },
        _ => None,
    }
}

fn jvec(v: Option<&Value>) -> Option<Vec<f64>> {
    v?.as_array()?.iter().map(jf64).collect()
}

fn parse_close(text: &str) -> Result<Dec, PredictError> {
    match dec::parse(text) {
        Some(Parsed::Finite(d)) => Ok(d),
        _ => Err(PredictError::domain(format!("kapanış ayrıştırılamadı: {text:?}"))),
    }
}

/// Dondurulmuş kayıttaki çıktıdan limit yolu (YENİDEN HESAPLANMAZ; SPEC_APP §3g, U38).
fn record_path(output: &Value) -> Result<(Dec, Vec<Dec>, Vec<f64>), PredictError> {
    let refused = output.get("refused").is_some_and(|r| !r.is_null());
    let lp = output.get("limit_path").filter(|v| !v.is_null());
    let s_ok = output.get("S").is_some_and(|v| !v.is_null());
    let Some(lp) = lp.filter(|_| !refused && s_ok) else {
        return Err(invalid("koşullu güncelleme reddedilmiş ya da limit yolu olmayan kayıttan yapılamaz"));
    };
    let price = lp
        .get("ipo_price")
        .and_then(Value::as_str)
        .ok_or_else(|| invalid("kayıtta limit_path.ipo_price yok"))?;
    let c_text = lp.get("C").and_then(Value::as_array).ok_or_else(|| invalid("kayıtta limit_path.C yok"))?;
    if c_text.len() != DAYS {
        return Err(invalid("kayıtta limit_path.C 10 değer değil"));
    }
    let mut c = Vec::with_capacity(DAYS);
    for v in c_text {
        c.push(parse_close(v.as_str().ok_or_else(|| invalid("limit_path.C metin değil"))?)?);
    }
    let rho = jvec(lp.get("rho")).filter(|r| r.len() == DAYS).ok_or_else(|| invalid("kayıtta limit_path.rho yok"))?;
    Ok((parse_close(price)?, c, rho))
}

/// (S_k/S_j, k = j+1..10; P(L = t | L ≥ j), t = j..10). S_0 = 1 (j = 0 koşulsuzdur).
pub fn conditional_weights(s: &[f64], j: usize) -> Result<(Vec<f64>, Vec<f64>), PredictError> {
    if j > DAYS {
        return Err(invalid(format!("j = {j} 0..10 dışında")));
    }
    let mut s0 = Vec::with_capacity(DAYS + 1);
    s0.push(1.0);
    s0.extend_from_slice(s);
    let sj = s0[j];
    if sj <= 0.0 {
        return Err(invalid(format!("S_{j} = {sj:?}: koşul tanımsız")));
    }
    // s_cond[k − (j+1)] = S0[k]/Sj, k = j+1..10
    let s_cond: Vec<f64> = ((j + 1)..=DAYS).map(|k| s0[k] / sj).collect();
    // pl_cond[t − j] = (S0[t] − S0[t+1])/Sj, t = j..9; son öğe t = 10 için S0[10]/Sj
    let mut pl_cond: Vec<f64> = (j..DAYS).map(|t| (s0[t] - s0[t + 1]) / sj).collect();
    pl_cond.push(s0[DAYS] / sj);
    Ok((s_cond, pl_cond))
}

fn realized(close: &Dec, price: &Dec) -> Result<Value, PredictError> {
    Ok(json!({"status": STATUS_REALIZED, "realized_return": crate::output::jnum(ratio_minus_one(close, price)?)}))
}

fn mismatch_flag(obs: &[Dec], c: &[Dec], upto: usize) -> i64 {
    i64::from((1..=upto).any(|t| !dec::eq(&obs[t - 1], &c[t - 1])))
}

fn horizon_value(status: &'static str, h: &Horizon) -> Value {
    let mut m = Map::new();
    m.insert("status".into(), json!(status));
    for (k, v) in h.to_map() {
        m.insert(k, v);
    }
    Value::Object(m)
}

/// §7 durum 1: seri j gün sürüyor. `output` dondurulmuş kayıttaki bu modelin çıktısıdır.
pub fn conditional(
    p: &PathParams,
    output: &Value,
    j: usize,
    observed_closes: &[String],
) -> Result<Value, PredictError> {
    let (price, c, rho) = record_path(output)?;
    if j >= DAYS {
        return Err(invalid("j 0..9 olmalı (j = 10: bütün ufuklar gerçekleşmiştir)"));
    }
    if observed_closes.len() < j {
        return Err(invalid(format!("j = {j} için {j} gözlenen kapanış gerekir")));
    }
    let obs: Vec<Dec> = observed_closes.iter().map(|x| parse_close(x)).collect::<Result<_, _>>()?;
    let s = jvec(output.get("S")).filter(|v| v.len() == DAYS).ok_or_else(|| invalid("kayıtta S 10 değer değil"))?;
    let (s_cond, pl_cond) = conditional_weights(&s, j)?;
    let mut scale = Vec::with_capacity(DAYS);
    for t in 1..=DAYS {
        let base = if t <= j { &obs[t - 1] } else { &c[t - 1] };
        scale.push(ratio(base, &price)?);
    }
    let mut out = Map::new();
    out.insert("state".into(), json!(STATE_STREAK_ONGOING));
    out.insert("j".into(), json!(j));
    out.insert("S_j".into(), crate::output::jnum(if j == 0 { 1.0 } else { s[j - 1] }));
    out.insert(
        "S_cond".into(),
        Value::Object(((j + 1)..=DAYS).map(|k| (k.to_string(), crate::output::jnum(s_cond[k - j - 1]))).collect()),
    );
    out.insert(
        "P_L_cond".into(),
        Value::Object((j..=DAYS).map(|t| (t.to_string(), crate::output::jnum(pl_cond[t - j]))).collect()),
    );
    out.insert("limit_path_mismatch".into(), json!(mismatch_flag(&obs, &c, j)));
    for h in 1..=DAYS {
        let key = format!("D{h}");
        if h <= j {
            out.insert(key, realized(&obs[h - 1], &price)?);
            continue;
        }
        let parts: Vec<(usize, f64, Option<f64>)> = (j..h)
            .map(|t| (t, pl_cond[t - j], if t == 0 { None } else { Some(scale[t - 1]) }))
            .collect();
        let (atoms, used, ok) = mixture_atoms(Some((rho[h - 1], s_cond[h - j - 1])), &parts, &p.cells, h);
        let hz = horizon(atoms, used, ok, Some(rho[h - 1]), Some(s_cond[h - j - 1]));
        out.insert(key, horizon_value(hz.status, &hz));
    }
    Ok(Value::Object(out))
}

/// §7 durum 2: seri t. günde kırıldı (L = t); S kısmı düşer.
pub fn conditional_after_break(
    p: &PathParams,
    output: &Value,
    t: usize,
    observed_closes: &[String],
) -> Result<Value, PredictError> {
    let (price, c, _) = record_path(output)?;
    if t >= DAYS {
        return Err(invalid("t 0..9 olmalı"));
    }
    if observed_closes.len() < t + 1 {
        return Err(invalid(format!("L = {t} ancak kapanış(D_{}) gözlendiyse bilinir", t + 1)));
    }
    let obs: Vec<Dec> = observed_closes.iter().map(|x| parse_close(x)).collect::<Result<_, _>>()?;
    let scale = if t == 0 { None } else { Some(ratio(&obs[t - 1], &price)?) };
    let mut out = Map::new();
    out.insert("state".into(), json!(STATE_AFTER_BREAK));
    out.insert("t".into(), json!(t));
    out.insert("note".into(), json!(format!("kırılma sonrası, D_{t}'ye koşullu")));
    out.insert("limit_path_mismatch".into(), json!(mismatch_flag(&obs, &c, t)));
    for h in 1..=DAYS {
        let key = format!("D{h}");
        if h <= obs.len() {
            out.insert(key, realized(&obs[h - 1], &price)?);
            continue;
        }
        let (atoms, used, ok) = mixture_atoms(None, &[(t, 1.0, scale)], &p.cells, h);
        let hz = horizon(atoms, used, ok, None, None);
        out.insert(key, horizon_value(hz.status, &hz));
    }
    Ok(Value::Object(out))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> Dec {
        dec_of(s)
    }

    #[test]
    fn tick_boundaries() {
        for (x, want) in [("19.999", "0.01"), ("20", "0.02"), ("49.99", "0.02"), ("50", "0.05"), ("2500", "2.50")] {
            assert_eq!(dec::py_str(&tick(&d(x))), want, "tick({x})");
        }
    }

    #[test]
    fn limit_path_measured_rows() {
        for (price, snapped, tick_t, c1, c2, c10) in [
            ("25.52", "25.52", "0.02", "28.06", "30.86", "66.05"),
            ("25.5", "25.50", "0.02", "28.04", "30.84", "66.00"),
            ("1E2", "1.0E+2", "0.10", "110.0", "121.00", "259.00"),
            ("1E3", "1.00E+3", "1.00", "1100.0", "1210.00", "2590.00"),
            ("25.29", "25.30", "0.02", "27.82", "30.60", "65.50"),
            ("18.19", "18.19", "0.01", "20.00", "22.00", "47.12"),
            ("0.014", "0.01", "0.01", "0.01", "0.01", "0.01"),
            ("1e-400", "0.00", "0.01", "0.00", "0.00", "0.00"),
            ("999999999", "1000000000.00", "2.50", "1100000000.00", "1210000000.00", "2593742457.50"),
        ] {
            let lp = limit_path(&d(price)).expect(price);
            assert_eq!(dec::py_str(&lp.snapped), snapped, "snap({price})");
            assert_eq!(dec::py_str(&lp.tick), tick_t, "tick({price})");
            assert_eq!(dec::py_str(&lp.c[0]), c1, "C1({price})");
            assert_eq!(dec::py_str(&lp.c[1]), c2, "C2({price})");
            assert_eq!(dec::py_str(&lp.c[9]), c10, "C10({price})");
        }
        // 18.2 -> 20.02, 9.09 -> 9.99, 9.10 -> 10.01 (adım, yuvarlanacak değerin KENDİ seviyesinden)
        for (price, c1) in [("18.2", "20.02"), ("9.09", "9.99"), ("9.10", "10.01")] {
            assert_eq!(dec::py_str(&limit_path(&d(price)).unwrap().c[0]), c1, "C1({price})");
        }
        // 25. + 70 hane 5 -> decimal.Inexact -> DOMAIN_ERROR
        let long = format!("25.{}", "5".repeat(70));
        assert_eq!(limit_path(&d(&long)).unwrap_err().code, DOMAIN_ERROR);
    }

    #[test]
    fn ladder_order() {
        let l = ladder(Group::B, 1);
        let text: Vec<Vec<String>> =
            l.iter().take(4).map(|s| s.iter().map(|(g, m)| format!("{}{m}", g.as_str())).collect()).collect();
        assert_eq!(text, vec![vec!["B1"], vec!["Z1"], vec![], vec!["Z2", "B2"]]);
        let z = ladder(Group::Z, 10);
        let zt: Vec<Vec<String>> =
            z.iter().take(5).map(|s| s.iter().map(|(g, m)| format!("{}{m}", g.as_str())).collect()).collect();
        assert_eq!(zt, vec![vec!["Z10"], vec![], vec!["Z9", "B9"], vec![], vec!["Z8", "B8"]]);
    }

    #[test]
    fn pool_clips_and_pools() {
        let mut cells: Cells = BTreeMap::new();
        for g in GROUPS {
            for m in 1..=g.m_max() {
                cells.insert((g, m), Vec::new());
            }
        }
        cells.insert((Group::Z, 1), (0..5).map(|i| (0.01 * f64::from(i), format!("T{i}"))).collect());
        let p = pool(&cells, Group::B, 1, N_MIN);
        assert_eq!((p.n(), p.sufficient, p.sources.len()), (5, false, 19));
        // kırpma: (B,2)'ye sınır dışı iki değer
        cells.insert((Group::B, 2), vec![(-0.25, "XX".into()), (0.30, "YY".into())]);
        cells.insert((Group::Z, 2), (0..6).map(|i| (0.5, format!("S{i}"))).collect());
        let q = pool(&cells, Group::B, 1, N_MIN);
        assert_eq!(q.n(), 13);
        assert!(q.values.iter().all(|v| (-0.1..=0.1).contains(v)), "hedef m = 1 sınırına kırpıldı");
        assert!(q.pooled());
    }

    #[test]
    fn summarize_quantiles() {
        let atoms = vec![(0.1, 0.5), (-0.2, 0.25), (0.3, 0.25)];
        let s = summarize(&atoms);
        assert_eq!(s.q10, -0.2);
        assert_eq!(s.ret, 0.1);
        assert_eq!(s.q50, 0.1);
        assert_eq!(s.q90, 0.3);
        assert_eq!(s.p_up, 0.75);
    }
}
