//! V1.5 ailesi, kurallar ve PB: `borsai/predict.py: predict`, `emit_horizons`, `z_vector`,
//! `head_values` ve `borsai/predict_pb.py: predict`.
use serde_json::{Map, Value};

use crate::error::*;
use crate::features::{compute_features, parse_decimal};
use crate::horizons::physical_return_bounds;
use crate::output::{HorizonCell, LinearOutput, PbFeatureValues, Warning};
use crate::params::{Head, Heads, LinearParams, Prep, Range};
use crate::pb_features::{compute_pb_features, parse_pb_decimal};
use crate::sum::{py_max, py_min, py_sum};
use crate::survival::sigmoid;

const EXPLICIT_FILTER_STATUSES: [&str; 2] = ["FILTERED", "UNFILTERED"];

/// Özellik değerleri (binary64), ekleme sırasıyla; `None` = verilmedi (f3 yok).
pub type Values = Vec<(String, Option<f64>)>;

fn get(values: &Values, k: &str) -> Option<f64> {
    values.iter().find(|(n, _)| n == k).and_then(|(_, v)| *v)
}

fn set(values: &mut Values, k: &str, v: Option<f64>) {
    match values.iter_mut().find(|(n, _)| n == k) {
        Some(slot) => slot.1 = v,
        None => values.push((k.to_string(), v)),
    }
}

fn fmt(x: f64) -> String {
    format!("{x:?}")
}

pub fn range_warning(r: &Range, v: f64) -> Warning {
    Warning {
        code: WARN_OUT_OF_TRAINING_RANGE.into(),
        message: format!("{} = {} eğitim aralığı [{}, {}] dışında; tahmin dışdeğerlemedir", r.feature, fmt(v), fmt(r.min), fmt(r.max)),
        feature: Some(r.feature.clone()),
        value: Some(v),
        train_min: Some(r.min),
        train_max: Some(r.max),
        ..Default::default()
    }
}

/// `for fid, rng in feature_ranges: v = values.get(fid); if v is not None and not (min <= v <= max)`.
pub fn range_warnings(ranges: &[Range], values: &Values, out: &mut Vec<Warning>) {
    for r in ranges {
        if let Some(v) = get(values, &r.feature) {
            if !(r.min <= v && v <= r.max) {
                out.push(range_warning(r, v));
            }
        }
    }
}

/// `z_vector`: winsor → log → (x − μ)/σ. `math.log(x ≤ 0)` ve σ = 0 Python'da istisnadır.
pub fn z_vector(prep: &Prep, values: &Values) -> Result<Vec<f64>, PredictError> {
    let f3_missing = get(values, "f3").is_none();
    let mut z = Vec::with_capacity(prep.columns.len());
    for col in &prep.columns {
        let x = if col == "f5" {
            if f3_missing {
                1.0
            } else {
                0.0
            }
        } else {
            let mut x = match get(values, col) {
                Some(x) => x,
                None => prep.median(col).ok_or_else(|| PredictError::params(format!("{col} için medyan yok")))?,
            };
            if let Some(w) = prep.winsor_of(col) {
                x = py_min(py_max(x, w.p05), w.p95);
            }
            if prep.log_transform.iter().any(|c| c == col) {
                if x <= 0.0 {
                    return Err(PredictError::domain(format!("{col} = {} için log tanımsız (Python math domain error)", fmt(x))));
                }
                x = x.ln();
            }
            x
        };
        let mean = prep.mean_of(col).ok_or_else(|| PredictError::params(format!("{col} için mean yok")))?;
        let std = prep.std_of(col).ok_or_else(|| PredictError::params(format!("{col} için std yok")))?;
        if std == 0.0 {
            return Err(PredictError::domain(format!("{col}: std = 0 (Python ZeroDivisionError)")));
        }
        z.push((x - mean) / std);
    }
    Ok(z)
}

pub(crate) fn linear_term(coef: &[f64], z: &[f64], intercept: f64) -> f64 {
    py_sum(coef.iter().zip(z.iter()).map(|(c, v)| c * v)) + intercept
}

/// `head_values`: (ham getiri, p_up).
fn head_values(heads: &Heads, z: Option<&[f64]>) -> Result<(Option<f64>, Option<f64>), PredictError> {
    let eval = |h: &Head| -> Result<f64, PredictError> {
        match h {
            Head::Constant(v) => Ok(*v),
            Head::Linear { coef, intercept } => match z {
                Some(z) => Ok(linear_term(coef, z, *intercept)),
                None => Err(PredictError::domain("özelliksiz modelde doğrusal başlık (Python TypeError)")),
            },
        }
    };
    let ret = heads.ret.as_ref().map(eval).transpose()?;
    let p = match &heads.p_up {
        Some(Head::Constant(v)) => Some(*v),
        Some(h) => Some(sigmoid(eval(h)?)),
        None => None,
    };
    Ok((ret, p))
}

/// `emit_horizons`: fiziksel sınıra kırpma, fiyat, yön.
pub fn emit_horizons(p: &LinearParams, z: Option<&[f64]>, price_f: f64, out: &mut LinearOutput) -> Result<(), PredictError> {
    let mut cells = Vec::with_capacity(p.horizons.len());
    for (h, heads) in &p.horizons {
        let (raw_ret, pu) = head_values(heads, z)?;
        let mut cell = HorizonCell { ret: None, return_unclipped: raw_ret, return_clipped: None, price: None, p_up: pu, direction: None };
        if let Some(raw) = raw_ret {
            let (lo, hi) = physical_return_bounds(h).ok_or_else(|| PredictError::params(format!("{h}: bilinmeyen ufuk")))?;
            let ret = py_min(py_max(raw, lo), hi);
            // Python `ret != raw_ret` (NaN kendine eşit değil)
            if ret != raw || raw.is_nan() {
                let side = if raw > hi { "UPPER" } else { "LOWER" };
                cell.return_clipped = Some(side.into());
                out.warnings.push(Warning {
                    code: WARN_RETURN_CLIPPED.into(),
                    message: format!("{h} getirisi {} fiziksel sınıra kırpıldı: {}", fmt(raw), fmt(ret)),
                    horizon: Some(h.clone()),
                    value: Some(raw),
                    used: Some(ret),
                    ..Default::default()
                });
            }
            cell.ret = Some(ret);
            cell.price = Some(price_f * (1.0 + ret));
        }
        if let Some(pv) = pu {
            cell.direction = Some(if pv > 0.5 { "UP" } else { "DOWN" }.into());
        }
        cells.push((h.clone(), Some(cell)));
    }
    out.horizons = cells;
    Ok(())
}

fn empty_output(p: &LinearParams) -> LinearOutput {
    LinearOutput {
        model_id: p.model_id.clone(),
        horizons: p.horizons.iter().map(|(h, _)| (h.clone(), None)).collect(),
        warnings: Vec::new(),
        refused: None,
        features: None,
        f6_market20: None,
        fall: None,
    }
}

/// `borsai/predict.py: predict`. `extra`: f1–f4 dışındaki hazır özellikler (market20 için f6).
pub fn predict_core(p: &LinearParams, inputs: &Map<String, Value>, extra: &[(String, f64)]) -> Result<LinearOutput, PredictError> {
    let mut out = empty_output(p);
    let uses_features = !p.features.is_empty();
    let price = match parse_decimal(inputs.get("ipo_price_tl"), "ipo_price_tl", true) {
        Ok(d) => d.expect("required"),
        Err(r) => {
            out.refused = Some(r);
            return Ok(out);
        }
    };
    if price.signum() <= 0 {
        out.refused = Some(Refusal::new(INPUT_NOT_POSITIVE, Some("ipo_price_tl"), "ipo_price_tl: pozitif olmalı"));
        return Ok(out);
    }
    let mut z = None;
    if uses_features {
        let feats = match compute_features(inputs) {
            Ok(f) => f,
            Err(FeatureFail::Refuse(r)) => {
                out.refused = Some(r);
                return Ok(out);
            }
            Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
        };
        let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
        if feats.f3.is_none() && p.f3_missing.as_deref() == Some("REFUSE") {
            out.refused = Some(Refusal::new(
                F3_MISSING,
                Some("total_demand_multiple"),
                "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz tahmin PB sütunlarındadır.",
            ));
            return Ok(out);
        }
        let status = inputs.get("total_demand_filter_status").and_then(Value::as_str);
        let mode = prep.f3_filter_mode.as_deref();
        if let (Some(_), Some(st), Some(md)) = (&feats.f3, status, mode) {
            if EXPLICIT_FILTER_STATUSES.contains(&st) && EXPLICIT_FILTER_STATUSES.contains(&md) && st != md
                && p.f3_filter_status_conflict.as_deref() == Some("REFUSE")
            {
                out.refused = Some(Refusal::new(
                    F3_FILTER_STATUS_CONFLICT,
                    Some("total_demand_filter_status"),
                    format!("f3 filtre durumu {st}, eğitimdeki mod {md}: talep katları karşılaştırılamaz"),
                ));
                return Ok(out);
            }
        }
        let mut values: Values = vec![
            ("f1".into(), Some(feats.f1.to_f64())),
            ("f2".into(), Some(feats.f2.to_f64())),
            ("f3".into(), feats.f3.as_ref().map(|d| d.to_f64())),
            ("f4".into(), Some(feats.f4.to_f64())),
        ];
        for (k, v) in extra {
            set(&mut values, k, Some(*v));
        }
        for col in &prep.columns {
            if col != "f5" && get(&values, col).is_none() && !prep.medians.contains_key(col) {
                out.refused = Some(Refusal::new(
                    FEATURE_NOT_PROVIDED,
                    Some(col),
                    format!("{col} modelin girdisidir ve verilmedi; impute edilmez"),
                ));
                return Ok(out);
            }
        }
        range_warnings(&p.feature_ranges, &values, &mut out.warnings);
        let f4 = get(&values, "f4").expect("f4");
        if f4 == 0.0 && p.range_min("f4").unwrap_or(0.0) > 0.0 {
            out.warnings.push(Warning {
                code: WARN_F4_ZERO.into(),
                message: "f4 = 0 (sermaye artırımı yok): eğitimde f4 = 0 olan arz yok; tahmin dışdeğerlemedir".into(),
                feature: Some("f4".into()),
                value: Some(0.0),
                ..Default::default()
            });
        }
        if let (Some(w), Some(f3)) = (prep.winsor_of("f3"), get(&values, "f3")) {
            if !(w.p05 <= f3 && f3 <= w.p95) {
                let clamped = py_min(py_max(f3, w.p05), w.p95);
                out.warnings.push(Warning {
                    code: WARN_F3_WINSORIZED.into(),
                    message: format!("f3 = {} eğitim p05/p95 sınırına kırpıldı: {}", fmt(f3), fmt(clamped)),
                    feature: Some("f3".into()),
                    value: Some(f3),
                    used: Some(clamped),
                    ..Default::default()
                });
            }
        }
        z = Some(z_vector(prep, &values)?);
    }
    emit_horizons(p, z.as_deref(), price.to_f64(), &mut out)?;
    Ok(out)
}

/// `borsai/predict_pb.py: predict`.
pub fn predict_pb(p: &LinearParams, inputs: &Map<String, Value>) -> Result<LinearOutput, PredictError> {
    let mut out = empty_output(p);
    out.features = Some(None);
    let f = match compute_pb_features(inputs) {
        Ok(f) => f,
        Err(FeatureFail::Refuse(r)) => {
            out.refused = Some(r);
            return Ok(out);
        }
        Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
    };
    let values: Values = vec![("pb1".into(), Some(f.pb1)), ("pb2".into(), Some(f.pb2)), ("pb3".into(), Some(f.pb3))];
    out.features = Some(Some(PbFeatureValues { pb1: f.pb1, pb2: f.pb2, pb3: f.pb3, pb4: f.pb4 }));
    range_warnings(&p.feature_ranges, &values, &mut out.warnings);
    if f.pb4 > 0.0 {
        out.warnings.push(pb4_warning(f.pb4));
    }
    let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
    let z = z_vector(prep, &values)?;
    let price = match parse_pb_decimal(inputs.get("ipo_price_try"), "ipo_price_try") {
        Ok(d) => d.to_f64(),
        Err(_) => return Err(PredictError::domain("ipo_price_try ikinci kez ayrıştırılamadı")),
    };
    emit_horizons(p, Some(&z), price, &mut out)?;
    Ok(out)
}

pub fn pb4_warning(pb4: f64) -> Warning {
    Warning {
        code: WARN_PB4_POSITIVE.into(),
        message: format!("ek satış tavanı var (pb4 = {}); eğitimde 7 örnek", fmt(pb4)),
        feature: Some("pb4".into()),
        value: Some(pb4),
        ..Default::default()
    }
}
