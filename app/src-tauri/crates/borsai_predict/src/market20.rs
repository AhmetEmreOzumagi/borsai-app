//! `v1_5_market20_v0`: `borsai/predict_market20.py: predict` (SPEC_MARKET20_V0 §7, §10).
//! f6 burada hesaplanmaz; hazır değer (`f6_market20`) ya da neden kodu (`f6_market20_refusal`) gelir.
use serde_json::{Map, Value};

use crate::error::*;
use crate::features::parse_decimal;
use crate::linear::predict_core;
use crate::output::LinearOutput;
use crate::params::parse_linear;

pub const MARKET20_REASONS: [&str; 7] = [
    "CALENDAR_NOT_COVERING",
    "INSUFFICIENT_HISTORY",
    "XU100_CLOSE_MISSING",
    "STALE_S0",
    "PREDICTION_TOO_EARLY",
    "XU100_INTEGRITY",
    "NOT_PROVIDED",
];

fn horizon_keys(params: &Value) -> Vec<String> {
    match params.get("horizons") {
        Some(Value::Object(m)) => m.keys().cloned().collect(),
        _ => Vec::new(),
    }
}

fn refused_output(params: &Value, code: String, reason: String) -> LinearOutput {
    LinearOutput {
        model_id: params.get("model_id").and_then(Value::as_str).map(str::to_string),
        horizons: horizon_keys(params).into_iter().map(|h| (h, None)).collect(),
        warnings: Vec::new(),
        refused: Some(Refusal { code, field: Some("f6_market20".into()), reason }),
        features: None,
        f6_market20: Some(None),
        fall: None,
    }
}

/// Önce f6 (parametre denetiminden önce, Python'daki sıra), sonra V1.5 çekirdeği.
pub fn predict_market20(params: &Value, inputs: &Map<String, Value>) -> Result<LinearOutput, PredictError> {
    let reason = inputs.get("f6_market20_refusal").and_then(Value::as_str);
    let f6 = match parse_decimal(inputs.get("f6_market20"), "f6_market20", false) {
        Ok(v) => v,
        Err(e) => {
            return Ok(refused_output(params, format!("{MARKET20_PREFIX}NOT_NUMERIC"), e.reason));
        }
    };
    let Some(f6) = f6 else {
        let code = match reason {
            Some(r) if MARKET20_REASONS.contains(&r) => r,
            _ => "NOT_PROVIDED",
        };
        return Ok(refused_output(
            params,
            format!("{MARKET20_PREFIX}{code}"),
            format!("f6 (20 seanslık XU100 getirisi) yok: {code}; bu model f6'sız tahmin vermez, imputasyon yok"),
        ));
    };
    let lp = parse_linear(params)?;
    let f6f = f6.to_f64();
    let mut out = predict_core(&lp, inputs, &[("f6".to_string(), f6f)])?;
    out.f6_market20 = Some(Some(f6f));
    Ok(out)
}
