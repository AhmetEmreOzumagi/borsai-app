//! Girdi formu anında denetimleri (SPEC_APP §3a): virgül → nokta, sayı biçimi, 2 ≥ 4, 2 ≤ 3, 4 ≥ 0,
//! 2 = 4 + 5 + 6 (sarı), PB özdeşlikleri ID-A/B/C (kırmızı), aşamaya göre zorunlu alanlar, 13 + 14 ve
//! 15 + 16 önerileri. Model davranışını değiştirmez: formdaki not RET değildir; RET'i yalnız model verir.
//! Bütün aritmetik kesin ondalıkla (`borsai_predict::dec`), ön uç hesap yapmaz.
use serde::Serialize;
use serde_json::{Map, Value};
use std::cmp::Ordering;

use borsai_predict::dec::{self, Dec};
use borsai_predict::features::parse_decimal;
use borsai_predict::pb_features::parse_pb_decimal;

use super::{AppError, INVALID_ARGUMENT};
use crate::clock::is_iso_date;

pub const V15_FIELDS: [&str; 9] = [
    "ipo_price_tl",
    "shares_offered",
    "post_ipo_share_capital",
    "capital_increase_shares",
    "existing_share_sale_shares",
    "total_demand_multiple",
    "total_demand_filter_status",
    "additional_sale_shares",
    "ipo_size_tl",
];
pub const PB_FIELDS: [&str; 8] = borsai_predict::pb_features::PB_REQUIRED_FIELDS;
pub const DATE_FIELDS: [&str; 3] = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"];
pub const F6_FIELD: &str = "f6_market20";
pub const FILTER_STATUSES: [&str; 3] = ["NOT_SPECIFIED", "UNFILTERED", "FILTERED"];
pub const STAGES: [&str; 2] = ["PRE_BOOKBUILD", "POST_BOOKBUILD_PRE_LISTING"];

/// Formun 20 alanı, §3a tablosu sırasıyla.
pub const FORM_FIELDS: [&str; 20] = [
    "ipo_price_tl",
    "shares_offered",
    "post_ipo_share_capital",
    "capital_increase_shares",
    "existing_share_sale_shares",
    "additional_sale_shares",
    "total_demand_multiple",
    "total_demand_filter_status",
    "ipo_size_tl",
    "ipo_price_try",
    "planned_pre_ipo_capital",
    "planned_post_ipo_capital",
    "planned_capital_increase_shares",
    "planned_existing_share_sale",
    "planned_base_offer_shares",
    "planned_additional_sale_ceiling",
    "planned_max_offer_shares",
    "first_trading_date",
    "bookbuilding_start",
    "bookbuilding_end",
];

/// Model girdileri (`borsai.registry.model_inputs`): V1.5 + PB, 17 alan.
pub fn model_input_fields() -> impl Iterator<Item = &'static str> {
    V15_FIELDS.iter().chain(PB_FIELDS.iter()).copied()
}

/// §3a tablosu: (PB aşaması, talep sonrası aşama). REQUIRED | OPTIONAL | EMPTY | REQUIRED_IF_F3.
pub fn requirement(field: &str, stage: &str) -> &'static str {
    let pb = stage == "PRE_BOOKBUILD";
    match field {
        "ipo_price_tl" | "post_ipo_share_capital" | "capital_increase_shares" => if pb { "OPTIONAL" } else { "REQUIRED" },
        "shares_offered" | "existing_share_sale_shares" | "additional_sale_shares" => if pb { "EMPTY" } else { "REQUIRED" },
        "total_demand_multiple" | "ipo_size_tl" => if pb { "EMPTY" } else { "OPTIONAL" },
        "total_demand_filter_status" => if pb { "EMPTY" } else { "REQUIRED_IF_F3" },
        "first_trading_date" => if pb { "OPTIONAL" } else { "REQUIRED" },
        "bookbuilding_end" => if pb { "OPTIONAL" } else { "REQUIRED" },
        _ => "REQUIRED", // ipo_price_try, planned_*, bookbuilding_start
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct FormNote {
    pub field: String,
    pub code: String,
    /// error (kırmızı: model RET edecek) | warn (sarı) | info (gri)
    pub level: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct FormCheck {
    pub stage: Option<String>,
    /// Her form alanı: normalize metin ya da null (boş).
    pub normalized: Map<String, Value>,
    pub notes: Vec<FormNote>,
    /// Alan → önerilen değer (kullanıcı onaylarsa uygulanır).
    pub suggestions: Map<String, Value>,
    pub requirements: Map<String, Value>,
    /// `predict_all`'a gidecek 17 alan (normalize; boş = null).
    pub model_inputs: Map<String, Value>,
}

fn note(field: &str, code: &str, level: &'static str) -> FormNote {
    FormNote { field: field.into(), code: code.into(), level, name: None, value: None }
}

/// Kesin ondalığın düz metni (bilimsel gösterim yok). Üs çok büyükse `None`.
pub fn dec_plain(d: &Dec) -> Option<String> {
    let s = d.stripped();
    if s.is_zero() {
        return Some("0".into());
    }
    if s.exp.abs() > 40 {
        return None;
    }
    let digits = s.coeff.to_str_radix(10);
    let sign = if s.neg { "-" } else { "" };
    let body = if s.exp >= 0 {
        format!("{digits}{}", "0".repeat(s.exp as usize))
    } else {
        let places = (-s.exp) as usize;
        if digits.len() > places {
            format!("{}.{}", &digits[..digits.len() - places], &digits[digits.len() - places..])
        } else {
            format!("0.{}{digits}", "0".repeat(places - digits.len()))
        }
    };
    Some(format!("{sign}{body}"))
}

/// Tek virgül ve nokta yoksa virgül → nokta (binlik ayırıcı kullanılmaz; §3a).
fn normalize_text(raw: &str) -> (String, bool) {
    let t = raw.trim();
    if t.matches(',').count() == 1 && !t.contains('.') {
        (t.replace(',', "."), true)
    } else {
        (t.to_string(), false)
    }
}

pub fn check_form_value(stage: Option<&str>, fields: &Map<String, Value>) -> Result<FormCheck, AppError> {
    if let Some(s) = stage {
        if !STAGES.contains(&s) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("aşama {s:?}")));
        }
    }
    let mut notes = Vec::new();
    let mut normalized = Map::new();
    let mut nums: std::collections::HashMap<&str, Dec> = std::collections::HashMap::new();
    for field in FORM_FIELDS.iter().copied().chain(std::iter::once(F6_FIELD)) {
        let raw = match fields.get(field) {
            None | Some(Value::Null) => String::new(),
            Some(Value::String(s)) => s.clone(),
            Some(other) => other.to_string(),
        };
        let is_text_field = field == "total_demand_filter_status" || DATE_FIELDS.contains(&field);
        let (text, comma) = if is_text_field { (raw.trim().to_string(), false) } else { normalize_text(&raw) };
        if text.is_empty() {
            normalized.insert(field.into(), Value::Null);
            continue;
        }
        if comma {
            let mut n = note(field, "COMMA_CONVERTED", "info");
            n.value = Some(text.clone());
            notes.push(n);
        }
        normalized.insert(field.into(), Value::String(text.clone()));
        if DATE_FIELDS.contains(&field) {
            if !is_iso_date(&text) {
                notes.push(note(field, "DATE_NOT_ISO", "error"));
            }
            continue;
        }
        if field == "total_demand_filter_status" {
            if !FILTER_STATUSES.contains(&text.as_str()) {
                notes.push(note(field, "FILTER_STATUS_INVALID", "error"));
            }
            continue;
        }
        if field == "ipo_price_try" {
            if let Err(borsai_predict::error::FeatureFail::Refuse(r)) = parse_pb_decimal(Some(&Value::String(text.clone())), field) {
                if r.code == "PB_PRICE_RANGE" {
                    notes.push(note(field, "PB_PRICE_RANGE", "error"));
                    continue;
                }
            }
        }
        match parse_decimal(Some(&Value::String(text)), field, false) {
            Ok(Some(d)) => {
                nums.insert(field, d);
            }
            Ok(None) => {}
            Err(_) => notes.push(note(field, "INPUT_NOT_NUMERIC", "error")),
        }
    }

    for f in ["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "total_demand_multiple", "ipo_size_tl"] {
        if nums.get(f).is_some_and(|d| d.signum() <= 0) {
            notes.push(note(f, "INPUT_NOT_POSITIVE", "error"));
        }
    }
    let get = |f: &str| nums.get(f);
    if let Some(ci) = get("capital_increase_shares") {
        if ci.signum() < 0 {
            notes.push(note("capital_increase_shares", "INPUT_NEGATIVE", "error"));
        }
        if let Some(sh) = get("shares_offered") {
            if dec::cmp(ci, sh) == Ordering::Greater {
                notes.push(note("capital_increase_shares", "INPUT_INCONSISTENT", "error"));
            }
        }
    }
    if let (Some(sh), Some(post)) = (get("shares_offered"), get("post_ipo_share_capital")) {
        if dec::cmp(sh, post) == Ordering::Greater {
            notes.push(note("shares_offered", "INPUT_INCONSISTENT", "error"));
        }
    }
    let sum = |a: &Dec, b: &Dec| dec::add_exact(a, b, 200).ok();
    if let (Some(sh), Some(ci), Some(ex), Some(ad)) = (
        get("shares_offered"),
        get("capital_increase_shares"),
        get("existing_share_sale_shares"),
        get("additional_sale_shares"),
    ) {
        if let Some(total) = sum(ci, ex).and_then(|x| sum(&x, ad)) {
            if !dec::eq(sh, &total) {
                let mut n = note("shares_offered", "SHARES_SUM_MISMATCH", "warn");
                n.value = dec_plain(&total);
                notes.push(n);
            }
        }
    }
    if nums.contains_key("total_demand_multiple") && !normalized.get("total_demand_filter_status").is_some_and(Value::is_string) {
        notes.push(note("total_demand_filter_status", "FILTER_STATUS_REQUIRED", "warn"));
    }

    // PB özdeşlikleri (SPEC_PB_V0; features.compute_pb_features ile aynı denklemler)
    let identities = [
        ("ID-A", "planned_post_ipo_capital", "planned_pre_ipo_capital", "planned_capital_increase_shares"),
        ("ID-B", "planned_base_offer_shares", "planned_capital_increase_shares", "planned_existing_share_sale"),
        ("ID-C", "planned_max_offer_shares", "planned_base_offer_shares", "planned_additional_sale_ceiling"),
    ];
    let mut suggestions = Map::new();
    for (name, total_f, a_f, b_f) in identities {
        let (Some(a), Some(b)) = (get(a_f), get(b_f)) else { continue };
        let Some(expected) = sum(a, b) else { continue };
        match get(total_f) {
            Some(total) if dec::eq(total, &expected) => {}
            Some(_) => {
                let mut n = note(total_f, "PB_IDENTITY", "error");
                n.name = Some(name.into());
                n.value = dec_plain(&expected);
                notes.push(n);
            }
            None => {}
        }
        // ID-B ve ID-C toplamları formda önerilir (§3a #15, #17); ID-A yalnız denetim
        if name != "ID-A" && !get(total_f).is_some_and(|t| dec::eq(t, &expected)) {
            if let Some(v) = dec_plain(&expected) {
                suggestions.insert(total_f.into(), Value::String(v));
            }
        }
    }

    let mut requirements = Map::new();
    if let Some(s) = stage {
        for f in FORM_FIELDS {
            let r = requirement(f, s);
            requirements.insert(f.into(), Value::String(r.into()));
            let empty = !normalized.get(f).is_some_and(Value::is_string);
            if empty && r == "REQUIRED" {
                notes.push(note(f, "REQUIRED_EMPTY", "info"));
            }
        }
    }
    let model_inputs = model_input_fields().map(|f| (f.to_string(), normalized.get(f).cloned().unwrap_or(Value::Null))).collect();
    Ok(FormCheck { stage: stage.map(str::to_string), normalized, notes, suggestions, requirements, model_inputs })
}

#[tauri::command]
pub fn check_form(stage: Option<String>, fields: Map<String, Value>) -> Result<FormCheck, AppError> {
    check_form_value(stage.as_deref(), &fields)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn f(v: Value) -> Map<String, Value> {
        v.as_object().unwrap().clone()
    }

    fn codes(c: &FormCheck) -> Vec<(String, String)> {
        c.notes.iter().map(|n| (n.field.clone(), n.code.clone())).collect()
    }

    #[test]
    fn comma_and_consistency() {
        let c = check_form_value(
            Some("POST_BOOKBUILD_PRE_LISTING"),
            &f(json!({"ipo_price_tl": "25,52", "shares_offered": "100", "post_ipo_share_capital": "90",
                      "capital_increase_shares": "120", "existing_share_sale_shares": "0", "additional_sale_shares": "0",
                      "total_demand_multiple": "2.84"})),
        )
        .unwrap();
        assert_eq!(c.normalized["ipo_price_tl"], json!("25.52"));
        assert_eq!(c.model_inputs["ipo_price_tl"], json!("25.52"));
        let cs = codes(&c);
        assert!(cs.contains(&("ipo_price_tl".into(), "COMMA_CONVERTED".into())));
        assert!(cs.contains(&("capital_increase_shares".into(), "INPUT_INCONSISTENT".into())));
        assert!(cs.contains(&("shares_offered".into(), "INPUT_INCONSISTENT".into())));
        assert!(cs.contains(&("shares_offered".into(), "SHARES_SUM_MISMATCH".into())));
        assert!(cs.contains(&("total_demand_filter_status".into(), "FILTER_STATUS_REQUIRED".into())));
        assert_eq!(c.model_inputs.len(), 17);
    }

    #[test]
    fn pb_identities_and_suggestions() {
        let c = check_form_value(
            Some("PRE_BOOKBUILD"),
            &f(json!({"ipo_price_try": "10-12", "planned_pre_ipo_capital": "100", "planned_post_ipo_capital": "130",
                      "planned_capital_increase_shares": "25", "planned_existing_share_sale": "5.5",
                      "planned_additional_sale_ceiling": "3"})),
        )
        .unwrap();
        let cs = codes(&c);
        assert!(cs.contains(&("ipo_price_try".into(), "PB_PRICE_RANGE".into())));
        let id_a = c.notes.iter().find(|n| n.code == "PB_IDENTITY").unwrap();
        assert_eq!((id_a.name.as_deref(), id_a.value.as_deref()), (Some("ID-A"), Some("125")));
        assert_eq!(c.suggestions["planned_base_offer_shares"], json!("30.5"));
        assert!(c.suggestions.get("planned_max_offer_shares").is_none(), "taban boşken azami önerilmez");
        assert_eq!(c.requirements["shares_offered"], json!("EMPTY"));
        assert!(cs.contains(&("planned_base_offer_shares".into(), "REQUIRED_EMPTY".into())));
    }

    #[test]
    fn plain_decimal() {
        let p = |s: &str| match dec::parse(s) {
            Some(dec::Parsed::Finite(d)) => dec_plain(&d).unwrap(),
            _ => panic!(),
        };
        assert_eq!(p("6.5E7"), "65000000");
        assert_eq!(p("0.0012"), "0.0012");
        assert_eq!(p("-12.500"), "-12.5");
    }
}
