//! Düşen arz modeli v0 ailesi (`fall_d10_v0_h99`, `_pooled`, `_addsale`, kural satırı `_pooled@ZERO`):
//! `borsai/predict_fall.py: predict` portu (SPEC_APP EK 3 §8; referans kilidi P4 adım 0, `app/parity/README.md`).
//!
//! Çıktı V1.5 ufuk hücresi biçimindedir (`LinearOutput`; getiri alanları null): ufuk başına (D5, D10)
//! p_up = P(kapanış > arz); "düşme olasılığı" 1 − p_up olarak yalnız gösterimde yazılır. Ek anahtarlar `FallOut`.
//!
//! Sıra Python'daki gibidir (EK 3 §8.2'nin önerisinden farklı; Python kazanır): `@ZERO` (özelliksiz) hiçbir girdi
//! okumadan sabit başlıkları verir. f3'lü modellerde `compute_features` retleri → F3_MISSING → f3 filtre çelişkisi →
//! TÜFE (`tufe_index` / `tufe_refusal`; f1r = büyüklük / (TÜFE / 100), 60 hane) → ek satış bayrağı
//! (ADDITIONAL_SALE_MISSING / INPUT_NEGATIVE / INPUT_NOT_NUMERIC) → ham değerle aralık uyarıları → f1r ve f3 eğitim
//! p05/p95'ine kırpma (FEATURE_CLIPPED_TO_TRAINING_P05_P95) → winsor → ln → z. `addsale` yalnız ek satış alanını okur.
use serde_json::{Map, Value};

use crate::dec;
use crate::error::*;
use crate::features::{compute_features, parse_decimal};
use crate::hazard::{real_size, tufe_input};
use crate::linear::{linear_term, range_warnings, z_vector, Values};
use crate::output::{FallOut, HorizonCell, LinearOutput, Warning};
use crate::params::{FallParams, Head};
use crate::sum::{py_max, py_min};
use crate::survival::sigmoid;

pub const ADDITIONAL_SALE_FIELD: &str = "additional_sale_shares";
const EXPLICIT_FILTER_STATUSES: [&str; 2] = ["FILTERED", "UNFILTERED"];
const F3_MISSING_TEXT: &str =
    "Toplam talep katı (f3) yok; bu model f3'süz tahmin vermez. f3'süz düşüş tahmini fall_d10_v0_addsale'den gelir.";

/// `additional_sale_flag`: 1[Decimal(additional_sale_shares) > 0]. Boş, null, boşluk ve DATA_NOT_FOUND →
/// ADDITIONAL_SALE_MISSING (0 varsayılmaz; KARARLAR_C C4); negatif → INPUT_NEGATIVE; sayı değil / sonlu değil / bool →
/// INPUT_NOT_NUMERIC (`features.parse_decimal(required=False)`).
pub fn additional_sale_flag(v: Option<&Value>) -> Result<u8, Refusal> {
    let Some(d) = parse_decimal(v, ADDITIONAL_SALE_FIELD, false)? else {
        return Err(Refusal::new(
            ADDITIONAL_SALE_MISSING,
            Some(ADDITIONAL_SALE_FIELD),
            "ek satış alanı boş; 'yok' ile 'bulunamadı' karışmaz, 0 varsayılmaz (KARARLAR_C C4)",
        ));
    };
    match d.signum() {
        s if s < 0 => Err(Refusal::new(INPUT_NEGATIVE, Some(ADDITIONAL_SALE_FIELD), format!("negatif olamaz: {}", dec::py_str(&d)))),
        s if s > 0 => Ok(1),
        _ => Ok(0),
    }
}

/// `_emit`: `FALL_HORIZONS` sırasıyla p_up ve yön (UP ancak p > 0.5); getiri alanları null.
fn emit(p: &FallParams, z: Option<&[f64]>, out: &mut LinearOutput) -> Result<(), PredictError> {
    let mut cells = Vec::with_capacity(p.horizons.len());
    for (h, head) in &p.horizons {
        let pv = match head {
            Head::Constant(v) => *v,
            Head::Linear { coef, intercept } => match z {
                Some(z) => sigmoid(linear_term(coef, z, *intercept)),
                None => return Err(PredictError::domain("özelliksiz modelde logit başlığı (Python TypeError)")),
            },
        };
        let direction = if pv > 0.5 { "UP" } else { "DOWN" };
        let cell = HorizonCell { ret: None, return_unclipped: None, return_clipped: None, price: None, p_up: Some(pv), direction: Some(direction.into()) };
        cells.push((h.clone(), Some(cell)));
    }
    out.horizons = cells;
    Ok(())
}

pub fn predict_fall(p: &FallParams, inputs: &Map<String, Value>) -> Result<LinearOutput, PredictError> {
    let mut out = LinearOutput {
        model_id: p.model_id.clone(),
        horizons: p.horizons.iter().map(|(h, _)| (h.clone(), None)).collect(),
        warnings: Vec::new(),
        refused: None,
        features: None,
        f6_market20: None,
        fall: Some(FallOut::default()),
    };
    macro_rules! refuse {
        ($r:expr) => {{
            out.refused = Some($r);
            return Ok(out);
        }};
    }
    if p.features.is_empty() {
        emit(p, None, &mut out)?;
        return Ok(out);
    }
    let prep = p.prep.as_ref().ok_or_else(|| PredictError::params("preprocessing yok"))?;
    let mut values: Values = Vec::new();
    if p.uses("f3") {
        let feats = match compute_features(inputs) {
            Ok(f) => f,
            Err(FeatureFail::Refuse(r)) => refuse!(r),
            Err(FeatureFail::Domain(m)) => return Err(PredictError::domain(m)),
        };
        let Some(f3) = feats.f3.as_ref() else {
            refuse!(Refusal::new(F3_MISSING, Some("total_demand_multiple"), F3_MISSING_TEXT));
        };
        let status = inputs.get("total_demand_filter_status").and_then(Value::as_str);
        let mode = prep.f3_filter_mode.as_deref();
        if let (Some(st), Some(md)) = (status, mode) {
            if EXPLICIT_FILTER_STATUSES.contains(&st) && EXPLICIT_FILTER_STATUSES.contains(&md) && st != md
                && p.f3_filter_status_conflict.as_deref() == Some("REFUSE")
            {
                refuse!(Refusal::new(
                    F3_FILTER_STATUS_CONFLICT,
                    Some("total_demand_filter_status"),
                    format!("f3 filtre durumu {st}, eğitimdeki mod {md}: talep katları karşılaştırılamaz")
                ));
            }
        }
        let idx = match tufe_input(inputs) {
            Ok(i) => i,
            Err(r) => refuse!(r),
        };
        let f1r = real_size(&feats.f1, &idx)?.to_f64();
        values.push(("f1r".into(), Some(f1r)));
        values.push(("f3".into(), Some(f3.to_f64())));
        let f = out.fall.as_mut().expect("fall");
        f.f1r_raw = Some(f1r);
        f.tufe_index_used = Some(dec::py_str(&idx));
    }
    let flag = match additional_sale_flag(inputs.get(ADDITIONAL_SALE_FIELD)) {
        Ok(x) => x,
        Err(r) => refuse!(r),
    };
    values.push(("add_sale".into(), Some(f64::from(flag))));
    out.fall.as_mut().expect("fall").add_sale_used = Some(flag);
    range_warnings(&p.feature_ranges, &values, &mut out.warnings);
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
    let f = out.fall.as_mut().expect("fall");
    f.clipped = Some(!clipped.is_empty());
    f.clipped_features = Some(clipped);
    let z = z_vector(prep, &values)?;
    emit(p, Some(&z), &mut out)?;
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn flag(v: Value) -> Result<u8, String> {
        additional_sale_flag(Some(&v)).map_err(|r| format!("{}:{}", r.code, r.field.unwrap_or_default()))
    }

    #[test]
    fn additional_sale_flag_rules() {
        assert_eq!(additional_sale_flag(None).unwrap_err().code, ADDITIONAL_SALE_MISSING);
        for v in [Value::Null, json!(""), json!("   "), json!("DATA_NOT_FOUND")] {
            assert_eq!(flag(v), Err("ADDITIONAL_SALE_MISSING:additional_sale_shares".into()));
        }
        for v in [json!("abc"), json!("inf"), json!("nan"), json!(true)] {
            assert_eq!(flag(v), Err("INPUT_NOT_NUMERIC:additional_sale_shares".into()));
        }
        assert_eq!(flag(json!("-1")), Err("INPUT_NEGATIVE:additional_sale_shares".into()));
        assert_eq!(flag(json!("-0.001")), Err("INPUT_NEGATIVE:additional_sale_shares".into()));
        for v in [json!("0"), json!("0.0"), json!("-0"), json!(0), json!("0E+5")] {
            assert_eq!(flag(v), Ok(0));
        }
        for v in [json!("35000000"), json!("1e400"), json!(0.5), json!("1E-30")] {
            assert_eq!(flag(v), Ok(1));
        }
    }
}
