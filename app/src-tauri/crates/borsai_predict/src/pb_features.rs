//! pb1–pb4: talep toplama öncesi özellikler (`borsai/features.py: compute_pb_features`, SPEC_PB_V0 §2).
use serde_json::{Map, Value};

use crate::dec::{self, Dec, Parsed};
use crate::error::*;
use crate::features::number_text;

pub const PB_REQUIRED_FIELDS: [&str; 8] = [
    "ipo_price_try",
    "planned_pre_ipo_capital",
    "planned_post_ipo_capital",
    "planned_capital_increase_shares",
    "planned_existing_share_sale",
    "planned_base_offer_shares",
    "planned_additional_sale_ceiling",
    "planned_max_offer_shares",
];

const RANGE_SEPARATORS: [char; 3] = ['-', '–', '—'];
const EXACT_PREC: u64 = 200;

#[derive(Debug, Clone, PartialEq)]
pub struct PbFeatures {
    pub pb1: f64,
    pub pb2: f64,
    pub pb3: f64,
    pub pb4: f64,
}

fn missing(field: &str, why: &str) -> FeatureFail {
    FeatureFail::refuse(PB_FIELD_MISSING, field, format!("{field}: {why}"))
}

/// `parse_pb_decimal`.
pub fn parse_pb_decimal(v: Option<&Value>, field: &str) -> Result<Dec, FeatureFail> {
    let text = match v {
        None | Some(Value::Null) | Some(Value::Bool(_)) => return Err(missing(field, "değer yok")),
        Some(Value::String(s)) => {
            let t = dec::py_strip(s);
            if t.is_empty() || t == "DATA_NOT_FOUND" {
                return Err(missing(field, "değer yok"));
            }
            t.to_string()
        }
        Some(Value::Number(n)) => number_text(n),
        // str(list)/str(dict) '[' ya da '{' ile başlar: aralık denetimi ve Decimal() tutmaz
        Some(Value::Array(_)) | Some(Value::Object(_)) => return Err(missing(field, "ayrıştırılamıyor")),
    };
    if field == "ipo_price_try" {
        let mut chars = text.chars();
        let first = chars.next().expect("boş olmayan metin");
        let rest: &str = chars.as_str();
        for sep in RANGE_SEPARATORS {
            if let Some(pos) = rest.find(sep) {
                let lo = format!("{first}{}", &rest[..pos]);
                let hi = &rest[pos + sep.len_utf8()..];
                if dec::parse(dec::py_strip(&lo)).is_some() && dec::parse(dec::py_strip(hi)).is_some() {
                    return Err(FeatureFail::refuse(
                        PB_PRICE_RANGE,
                        field,
                        "fiyat tek değer değil (aralık); PB modeli aralıkla tahmin vermez",
                    ));
                }
            }
        }
    }
    match dec::parse(&text) {
        Some(Parsed::Finite(d)) => Ok(d),
        Some(Parsed::NonFinite) => Err(missing(field, "sonlu değil")),
        None => Err(missing(field, "ayrıştırılamıyor")),
    }
}

/// numerator / denominator × 100 kesin rasyonel (payda > 0).
fn pct_ratio(numerator: &Dec, denominator: &Dec) -> (num_bigint::BigInt, num_bigint::BigInt) {
    use num_traits::Signed;
    let (n1, d1) = numerator.as_ratio();
    let (n2, d2) = denominator.as_ratio();
    let num = n1 * &d2 * 100u32;
    let den = d1 * n2;
    if den.is_positive() {
        (num, den)
    } else {
        (-num, -den)
    }
}

fn identity(name: &str) -> FeatureFail {
    FeatureFail::refuse(PB_IDENTITY, name, format!("planlanan yapı özdeşliği ya da aralığı tutmuyor: {name}"))
}

/// `compute_pb_features`: yalnız PB_REQUIRED_FIELDS okunur.
pub fn compute_pb_features(inputs: &Map<String, Value>) -> Result<PbFeatures, FeatureFail> {
    use num_traits::{Signed, Zero};
    let mut v = Vec::with_capacity(PB_REQUIRED_FIELDS.len());
    for f in PB_REQUIRED_FIELDS {
        v.push(parse_pb_decimal(inputs.get(f), f)?);
    }
    let [price, pre, post, cap_inc, existing, base, addl, max] = <[Dec; 8]>::try_from(v).expect("8 alan");
    // _EXACT_CONTEXT (prec 200, Inexact tuzağı): herhangi biri kesin değilse "precision" reddi
    let sums = (
        dec::add_exact(&pre, &cap_inc, EXACT_PREC),
        dec::add_exact(&cap_inc, &existing, EXACT_PREC),
        dec::add_exact(&base, &addl, EXACT_PREC),
        dec::mul_exact(&price, &base, EXACT_PREC),
    );
    let (Ok(sum_a), Ok(sum_b), Ok(sum_c), Ok(value)) = sums else {
        return Err(FeatureFail::refuse(PB_FIELD_MISSING, "precision", "kesin hesaplanamıyor"));
    };
    let checks = [
        (dec::eq(&post, &sum_a), "ID-A"),
        (dec::eq(&base, &sum_b), "ID-B"),
        (dec::eq(&max, &sum_c), "ID-C"),
        (base.signum() > 0, "BASE_POSITIVE"),
        (post.signum() > 0, "POST_POSITIVE"),
        (value.signum() > 0, "VALUE_POSITIVE"),
    ];
    for (ok, name) in checks {
        if !ok {
            return Err(identity(name));
        }
    }
    let r2 = pct_ratio(&base, &post);
    let r3 = pct_ratio(&cap_inc, &base);
    let r4 = pct_ratio(&addl, &base);
    for ((num, den), name) in [(&r2, "PB2_RANGE"), (&r3, "PB3_RANGE")] {
        let hundred_den = den * 100u32;
        if !(num.is_positive() && *num <= hundred_den) {
            return Err(identity(name));
        }
    }
    if r4.0.is_negative() {
        return Err(identity("PB4_RANGE"));
    }
    let pb1 = dec::ln_to_f64(&value);
    let conv = |(n, d): &(num_bigint::BigInt, num_bigint::BigInt)| {
        debug_assert!(!d.is_zero());
        dec::ratio_to_f64(n, d)
            .map_err(|_| FeatureFail::Domain("oran binary64'e sığmıyor (Python OverflowError)".into()))
    };
    Ok(PbFeatures { pb1, pb2: conv(&r2)?, pb3: conv(&r3)?, pb4: conv(&r4)? })
}
