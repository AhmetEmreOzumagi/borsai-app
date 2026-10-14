//! Tavan serisi: `borsai/predict_hazard.py: predict` (ceiling_hazard_v0, pb_ceiling_v0, @INF, KM) ve Faz 7
//! `ceiling_hazard_v1_*` (clip, real, pooled, pooled@INF; SPEC_APP EK 3 §2).
//!
//! Doğrusal öngörücü tek fonksiyondur (`linear`; Python `_linear` / `_linear_v1`): η_d = γ_{g(d)} (+ δ·r) + β·z,
//! h_d = sigmoid(η_d). v0/PB yolu bugünkü `predict_hazard` gövdesinin aynısıdır (bit-eşit; U46).
use serde_json::{Map, Value};

use crate::dec::{self, Dec, Parsed};
use crate::error::*;
use crate::features::{compute_features, number_text};
use crate::linear::{pb4_warning, range_warnings, z_vector, Values};
use crate::output::{HazardOutput, V1Out, Warning};
use crate::params::{HazardParams, V1Params, CEILING_FEATURES, PB_CEILING_FEATURES};
use crate::pb_features::compute_pb_features;
use crate::sum::{py_max, py_min, py_sum};
use crate::survival::{group_of_day, p_close, p_streak, sigmoid, survival, DAYS};

/// `predict_hazard.REGIME_R`: tahsis rejimi etiketi → r (SPEC_HAZARD_V1 §3.3; r = 1[etiket ≠ EQUAL_DIST_20230330]).
pub const REGIME_R: [(&str, u8); 3] = [("PRE_20211111", 1), ("THRESH100_20211111", 1), ("EQUAL_DIST_20230330", 0)];
pub const REGIME_SOURCE_LIVE: &str = "LIVE_VALUE";
pub const REGIME_SOURCE_INPUT: &str = "ALLOC_REGIME_INPUT";
/// `_REAL_CTX = Context(prec=60, rounding=ROUND_HALF_EVEN)`.
pub const REAL_PREC: u64 = 60;

const F3_MISSING_TEXT: &str =
    "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tavan tahmini pb_ceiling_v0'dan gelir.";

/// Doğrusal öngörücü ve yan çıktıları (Python `_linear` / `_linear_v1` sözlüğü). Ret anında o ana kadar dolan
/// alanlar korunur (`eta` o zaman anlamsızdır).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct LinOut {
    pub refused: Option<Refusal>,
    pub warnings: Vec<Warning>,
    pub clipped: Option<bool>,
    /// Yalnız v1 ailesinde `Some`.
    pub v1: Option<V1Out>,
    /// (kolon, z) `prep.columns` sırasıyla.
    pub z: Vec<(String, f64)>,
    pub lin: f64,
    pub eta: [f64; DAYS],
}

fn curves(hazards: Vec<f64>, p: &HazardParams, out: &mut HazardOutput) {
    let s = survival(&hazards);
    out.p_l = Some(p_streak(&s));
    out.p_close_ceiling = Some(p_close(&s, p.r_a, p.r_b));
    out.s = Some(s);
    out.hazard = Some(hazards);
}

pub fn predict_hazard(p: &HazardParams, inputs: &Map<String, Value>) -> Result<HazardOutput, PredictError> {
    let mut out = HazardOutput {
        model_id: p.model_id.clone(),
        hazard: None,
        s: None,
        p_l: None,
        p_close_ceiling: None,
        clipped: None,
        warnings: Vec::new(),
        refused: None,
        v1: None,
    };
    if p.km {
        curves(p.km_hazard.clone(), p, &mut out);
        return Ok(out);
    }
    let lp = linear(p, inputs)?;
    out.clipped = lp.clipped;
    out.warnings = lp.warnings;
    out.refused = lp.refused;
    out.v1 = lp.v1;
    if out.refused.is_some() {
        return Ok(out);
    }
    let hazards = lp.eta.iter().map(|&e| sigmoid(e)).collect();
    curves(hazards, p, &mut out);
    Ok(out)
}

/// `linear_predictor`: hazard modelinin doğrusal öngörücüsü (KM kurallarında yoktur: PARAMS_INVALID).
pub fn linear(p: &HazardParams, inputs: &Map<String, Value>) -> Result<LinOut, PredictError> {
    if p.km {
        return Err(PredictError::params("doğrusal öngörücü yalnız hazard modelinde"));
    }
    match &p.v1 {
        Some(v1) => linear_v1(p, v1, inputs),
        None => linear_v0(p, inputs),
    }
}

/// z ve β·z (`prep.columns` sırasıyla; Python `sum(β[c]·z[c] for c in z)`).
fn z_terms(p: &HazardParams, values: &Values) -> Result<(Vec<(String, f64)>, f64), PredictError> {
    let mut z_out = Vec::new();
    let mut terms = Vec::new();
    if !p.features.is_empty() {
        let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
        let z = z_vector(prep, values)?;
        for (c, zc) in prep.columns.iter().zip(z) {
            let b = p.beta_of(c).ok_or_else(|| PredictError::params(format!("beta[{c}] yok")))?;
            terms.push(b * zc);
            z_out.push((c.clone(), zc));
        }
    }
    Ok((z_out, py_sum(terms)))
}

fn linear_v0(p: &HazardParams, inputs: &Map<String, Value>) -> Result<LinOut, PredictError> {
    let mut out = LinOut::default();
    let mut values: Values = Vec::new();
    if p.features == CEILING_FEATURES {
        let feats = match compute_features(inputs) {
            Ok(f) => f,
            Err(FeatureFail::Refuse(r)) => {
                out.refused = Some(r);
                return Ok(out);
            }
            Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
        };
        let Some(f3) = feats.f3.as_ref().map(|d| d.to_f64()) else {
            out.refused = Some(Refusal::new(F3_MISSING, Some("total_demand_multiple"), F3_MISSING_TEXT));
            return Ok(out);
        };
        values = vec![
            ("f1".into(), Some(feats.f1.to_f64())),
            ("f2".into(), Some(feats.f2.to_f64())),
            ("f3".into(), Some(f3)),
        ];
        range_warnings(&p.feature_ranges, &values, &mut out.warnings);
        let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
        let w = prep.winsor_of("f3");
        let clipped = w.is_some_and(|w| !(w.p05 <= f3 && f3 <= w.p95));
        out.clipped = Some(clipped);
        if let (true, Some(w)) = (clipped, w) {
            let used = py_min(py_max(f3, w.p05), w.p95);
            out.warnings.push(Warning {
                code: WARN_F3_CLIPPED.into(),
                message: format!("f3 = {f3:?} eğitim p05/p95 sınırına kırpıldı: {used:?}"),
                feature: Some("f3".into()),
                value: Some(f3),
                used: Some(used),
                ..Default::default()
            });
        }
    } else if p.features == PB_CEILING_FEATURES {
        let pb = match compute_pb_features(inputs) {
            Ok(f) => f,
            Err(FeatureFail::Refuse(r)) => {
                out.refused = Some(r);
                return Ok(out);
            }
            Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
        };
        values = vec![("pb1".into(), Some(pb.pb1)), ("pb2".into(), Some(pb.pb2))];
        range_warnings(&p.feature_ranges, &values, &mut out.warnings);
        if pb.pb4 > 0.0 {
            out.warnings.push(pb4_warning(pb.pb4));
        }
    }
    let (z, lin) = z_terms(p, &values)?;
    out.z = z;
    out.lin = lin;
    for d in 1..=DAYS {
        out.eta[d - 1] = p.gamma[group_of_day(d)] + lin;
    }
    Ok(out)
}

/// `_tufe_input`: (endeks, ret kodu). Dondurma/kayıt `tufe_index` (metin) ya da `tufe_refusal` (TUFE_* kodu) verir.
/// Her okunamayan değer TUFE_MISSING'dir (INPUT_NOT_NUMERIC değil); imputasyon yok.
pub fn tufe_input(inputs: &Map<String, Value>) -> Result<Dec, Refusal> {
    let refuse = |code: &str, reason: String| Err(Refusal::new(code, Some("tufe_index"), reason));
    match inputs.get("tufe_refusal") {
        None | Some(Value::Null) => {}
        Some(v) => {
            let code = v.as_str().filter(|c| TUFE_REFUSALS.contains(c)).unwrap_or(TUFE_MISSING);
            return refuse(code, format!("TÜFE (T'nin ayı − 2) kullanılamıyor: {code}. Bu model deflatörsüz tahmin vermez; imputasyon yok."));
        }
    }
    let text = match inputs.get("tufe_index") {
        None | Some(Value::Null) | Some(Value::Bool(_)) => None,
        Some(Value::String(s)) if dec::py_strip(s).is_empty() => None,
        Some(Value::String(s)) => Some(s.clone()),
        Some(Value::Number(n)) => Some(number_text(n)),
        // Python `Decimal(str(list/dict))`: sözdizimi hatası
        Some(other) => Some(other.to_string()),
    };
    let Some(text) = text else {
        return refuse(TUFE_MISSING, "TÜFE endeksi (T'nin ayı − 2) verilmedi. Bu model deflatörsüz tahmin vermez; imputasyon yok.".into());
    };
    match dec::parse(&text) {
        Some(Parsed::Finite(d)) if d.signum() > 0 => Ok(d),
        Some(_) => refuse(TUFE_MISSING, format!("TÜFE endeksi pozitif sonlu değil: {text:?}")),
        None => refuse(TUFE_MISSING, format!("TÜFE endeksi sayı değil: {text:?}")),
    }
}

/// `Context(prec, ROUND_HALF_EVEN)` içinde a / b: kesinse libmpdec üs kuralıyla (`div_exact`), değilse
/// `prec` haneye doğru yuvarlanmış (`div_round`). Taşma (`decimal.Overflow`, tuzaklı) → DOMAIN_ERROR. f1r (`real_size`)
/// ve D1 el değiştirme oranı (`post_d1::evaluate_d1`) aynı yolu kullanır.
pub fn div_ctx(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, PredictError> {
    let q = dec::div_exact(a, b, prec).unwrap_or_else(|_| dec::div_round(a, b, prec));
    if !q.is_zero() && q.adjusted() > dec::CTX_EMAX as i128 {
        return Err(PredictError::domain("60 haneli bağlamda taşma (Python decimal.Overflow)"));
    }
    Ok(q)
}

/// `real_size`: f1r'nin ham değeri (2025 TL) = büyüklük_TL / (TÜFE / 100); iki Decimal işlemi 60 hanede
/// (idx / 100 kesin: üs kaydırması; ardından tek HALF_EVEN yuvarlama).
pub fn real_size(size_tl: &Dec, tufe_index: &Dec) -> Result<Dec, PredictError> {
    if tufe_index.signum() <= 0 || size_tl.signum() <= 0 {
        return Err(PredictError::domain("real_size: pozitif sonlu değil"));
    }
    let q = div_ctx(tufe_index, &Dec::from_i64(100), REAL_PREC)?;
    div_ctx(size_tl, &q, REAL_PREC)
}

/// `_linear_v1`: η_d = γ_{g(d)} (+ δ·r) + β·z (SPEC_HAZARD_V1 §12; EK 3 §2.3 sırası).
fn linear_v1(p: &HazardParams, v1: &V1Params, inputs: &Map<String, Value>) -> Result<LinOut, PredictError> {
    let mut out = LinOut { v1: Some(V1Out::default()), ..Default::default() };
    let mut values: Values = Vec::new();
    if !p.features.is_empty() {
        let feats = match compute_features(inputs) {
            Ok(f) => f,
            Err(FeatureFail::Refuse(r)) => {
                out.refused = Some(r);
                return Ok(out);
            }
            Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
        };
        let Some(f3) = feats.f3.as_ref() else {
            out.refused = Some(Refusal::new(F3_MISSING, Some("total_demand_multiple"), F3_MISSING_TEXT));
            return Ok(out);
        };
        if p.features.iter().any(|f| f == "f1r") {
            let idx = match tufe_input(inputs) {
                Ok(i) => i,
                Err(r) => {
                    out.refused = Some(r);
                    return Ok(out);
                }
            };
            let f1r = real_size(&feats.f1, &idx)?.to_f64();
            values = vec![("f1r".into(), Some(f1r)), ("f2".into(), Some(feats.f2.to_f64())), ("f3".into(), Some(f3.to_f64()))];
            let v = out.v1.as_mut().expect("v1");
            v.f1r_raw = Some(f1r);
            v.tufe_index_used = Some(dec::py_str(&idx));
        } else {
            values = vec![
                ("f1".into(), Some(feats.f1.to_f64())),
                ("f2".into(), Some(feats.f2.to_f64())),
                ("f3".into(), Some(f3.to_f64())),
            ];
        }
        range_warnings(&p.feature_ranges, &values, &mut out.warnings);
        let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
        let mut clipped: Vec<String> = Vec::new();
        for col in &prep.columns {
            let Some(w) = prep.winsor_of(col) else { continue };
            let x = values
                .iter()
                .find(|(n, _)| n == col)
                .and_then(|(_, v)| *v)
                .ok_or_else(|| PredictError::params(format!("{col}: özellik değeri yok")))?;
            if !(w.p05 <= x && x <= w.p95) {
                let used = py_min(py_max(x, w.p05), w.p95);
                clipped.push(col.clone());
                out.warnings.push(Warning {
                    code: WARN_FEATURE_CLIPPED.into(),
                    message: format!("{col} = {x:?} eğitim p05/p95 sınırına kırpıldı: {used:?}"),
                    feature: Some(col.clone()),
                    value: Some(x),
                    used: Some(used),
                    ..Default::default()
                });
            }
        }
        out.clipped = Some(!clipped.is_empty());
        out.v1.as_mut().expect("v1").clipped_features = Some(clipped);
    }
    let mut dr: Option<f64> = None;
    if let Some(regime) = &v1.regime {
        let (r, source) = if inputs.contains_key("alloc_regime") {
            let label = inputs.get("alloc_regime").and_then(Value::as_str);
            let Some(r) = label.and_then(|l| REGIME_R.iter().find(|(k, _)| *k == l)).map(|(_, r)| *r) else {
                out.refused = Some(Refusal::new(
                    REGIME_UNKNOWN,
                    Some("alloc_regime"),
                    format!(
                        "tahsis rejimi etiketi bilinmiyor ({}); eski kohort kaydı kohort satırındaki ALLOC_REGIME'i verir.",
                        inputs.get("alloc_regime").map(Value::to_string).unwrap_or_default()
                    ),
                ));
                return Ok(out);
            };
            (r, REGIME_SOURCE_INPUT)
        } else {
            (regime.live_value, REGIME_SOURCE_LIVE)
        };
        let v = out.v1.as_mut().expect("v1");
        v.regime_value_used = Some(r);
        v.regime_source = Some(source);
        dr = Some(regime.delta * f64::from(r));
    }
    let (z, lin) = z_terms(p, &values)?;
    out.z = z;
    out.lin = lin;
    for d in 1..=DAYS {
        let g = p.gamma[group_of_day(d)];
        out.eta[d - 1] = match dr {
            Some(dr) => (g + dr) + lin,
            None => g + lin,
        };
    }
    Ok(out)
}
