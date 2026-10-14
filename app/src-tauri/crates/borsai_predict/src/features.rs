//! f1–f4: V1.5 girdilerinin tek tanımı (`borsai/features.py: compute_features`). Kesin ondalık.
use serde_json::{Map, Number, Value};
use std::cmp::Ordering;

use crate::dec::{self, Dec, Parsed};
use crate::error::*;

/// Python `parse_decimal`'ın girdi sınıflandırması.
#[derive(Debug, Clone, PartialEq)]
pub enum RawInput {
    /// None, "", "DATA_NOT_FOUND" (kırpıldıktan sonra)
    Missing,
    /// bool, liste, sözlük
    NotNumeric,
    /// `Decimal()`'a gidecek metin: str için `str.strip()`, sayı için `str(int)` / `repr(float)`.
    Text(String),
}

/// JSON sayının Python metni: tamsayı `str(int)`, kayan nokta `repr(float)` (en kısa gidiş-dönüş).
pub fn number_text(n: &Number) -> String {
    if let Some(u) = n.as_u64() {
        u.to_string()
    } else if let Some(i) = n.as_i64() {
        i.to_string()
    } else {
        format!("{:?}", n.as_f64().unwrap_or(f64::NAN))
    }
}

pub fn raw_input(v: Option<&Value>) -> RawInput {
    match v {
        None | Some(Value::Null) => RawInput::Missing,
        Some(Value::String(s)) => {
            let t = dec::py_strip(s);
            if t.is_empty() || t == "DATA_NOT_FOUND" {
                RawInput::Missing
            } else {
                RawInput::Text(t.to_string())
            }
        }
        Some(Value::Number(n)) => RawInput::Text(number_text(n)),
        Some(Value::Bool(_)) | Some(Value::Array(_)) | Some(Value::Object(_)) => RawInput::NotNumeric,
    }
}

/// `parse_decimal(value, field, required=...)`.
pub fn parse_decimal(v: Option<&Value>, field: &str, required: bool) -> Result<Option<Dec>, Refusal> {
    match raw_input(v) {
        RawInput::Missing => {
            if required {
                Err(Refusal::new(INPUT_MISSING, Some(field), format!("{field}: değer yok")))
            } else {
                Ok(None)
            }
        }
        RawInput::NotNumeric => Err(Refusal::new(INPUT_NOT_NUMERIC, Some(field), format!("{field}: sayı değil"))),
        RawInput::Text(t) => match dec::parse(&t) {
            Some(Parsed::Finite(d)) => Ok(Some(d)),
            Some(Parsed::NonFinite) => {
                Err(Refusal::new(INPUT_NOT_NUMERIC, Some(field), format!("{field}: sonlu değil: {t:?}")))
            }
            None => Err(Refusal::new(INPUT_NOT_NUMERIC, Some(field), format!("{field}: sayı değil: {t:?}"))),
        },
    }
}

fn required(inputs: &Map<String, Value>, field: &str) -> Result<Dec, FeatureFail> {
    parse_decimal(inputs.get(field), field, true)
        .map(|d| d.expect("required"))
        .map_err(FeatureFail::Refuse)
}

/// `_require_positive`.
fn require_positive(value: Dec, field: &str, denominator: bool) -> Result<Dec, FeatureFail> {
    if value.is_zero() && denominator {
        return Err(FeatureFail::refuse(DIVISION_BY_ZERO, field, format!("{field}: payda sıfır")));
    }
    if value.signum() <= 0 {
        return Err(FeatureFail::refuse(INPUT_NOT_POSITIVE, field, format!("{field}: pozitif olmalı")));
    }
    Ok(value)
}

/// Ön işleme öncesi f1–f4 (kesin). f5 = f3 yoksa 1.
#[derive(Debug, Clone, PartialEq)]
pub struct RawFeatures {
    pub f1: Dec,
    pub f2: Dec,
    pub f3: Option<Dec>,
    pub f4: Dec,
}

/// `compute_features`: ret sırası Python'daki gibi.
pub fn compute_features(inputs: &Map<String, Value>) -> Result<RawFeatures, FeatureFail> {
    let price = require_positive(required(inputs, "ipo_price_tl")?, "ipo_price_tl", false)?;
    let shares = require_positive(required(inputs, "shares_offered")?, "shares_offered", true)?;
    let post = require_positive(required(inputs, "post_ipo_share_capital")?, "post_ipo_share_capital", true)?;
    let cap_inc = required(inputs, "capital_increase_shares")?;
    if cap_inc.signum() < 0 {
        return Err(FeatureFail::refuse(INPUT_NEGATIVE, "capital_increase_shares", "sermaye artırımı payı negatif olamaz"));
    }
    if dec::cmp(&cap_inc, &shares) == Ordering::Greater {
        return Err(FeatureFail::refuse(
            INPUT_INCONSISTENT,
            "capital_increase_shares",
            "sermaye artırımı payı satılan paydan büyük",
        ));
    }
    if dec::cmp(&shares, &post) == Ordering::Greater {
        return Err(FeatureFail::refuse(INPUT_INCONSISTENT, "shares_offered", "satılan pay arz sonrası sermayeden büyük"));
    }
    let f3 = parse_decimal(inputs.get("total_demand_multiple"), "total_demand_multiple", false)
        .map_err(FeatureFail::Refuse)?;
    if let Some(f3v) = &f3 {
        if f3v.signum() <= 0 {
            return Err(FeatureFail::refuse(
                INPUT_NOT_POSITIVE,
                "total_demand_multiple",
                "total_demand_multiple: pozitif olmalı",
            ));
        }
    }
    let size = parse_decimal(inputs.get("ipo_size_tl"), "ipo_size_tl", false).map_err(FeatureFail::Refuse)?;
    let f1 = match size {
        Some(s) => require_positive(s, "ipo_size_tl", false)?,
        None => dec::mul_round(&shares, &price, 28).map_err(|_| {
            FeatureFail::Domain("f1 = pay × fiyat 28 haneli bağlamda taşıyor (Python decimal.Overflow)".into())
        })?,
    };
    Ok(RawFeatures { f1, f2: dec::pct(&shares, &post), f3, f4: dec::pct(&cap_inc, &shares) })
}
