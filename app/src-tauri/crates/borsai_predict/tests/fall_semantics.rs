//! Faz 7C düşen arz ailesi (`fall_d10_v0`; SPEC_APP EK 3 §8) birim düzeyi: tür, parametre denetimi, Python sırası ve
//! çıktı biçimi (referans kilidi `borsai/predict_fall.py`). Sayısal parite altın vektörlerdedir (`--test golden`, U77).
//!   cargo test -p borsai_predict --test fall_semantics
mod common;

use common::*;
use serde_json::{json, Map, Value};

use borsai_predict::params::{parse_fall, FALL_HORIZONS};
use borsai_predict::{check_params, model_kind, run_model, Kind};

const FALL_IDS: [&str; 4] = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"];
/// Python `predict_fall.predict` çıktısının anahtarları (sözlük sırası).
const OUTPUT_KEYS: [&str; 10] =
    ["model_id", "D5", "D10", "warnings", "refused", "clipped", "clipped_features", "f1r_raw", "tufe_index_used", "add_sale_used"];

fn params(id: &str) -> Value {
    read_json(&repo_dir().join("models").join(format!("{id}.json")))
}

/// NETGL girdi belgesi + TÜFE (T = 2026-09-17 → 2026-07 = 132.31).
fn netgl() -> Map<String, Value> {
    json!({
        "ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
        "capital_increase_shares": "62500000", "existing_share_sale_shares": "25000000", "total_demand_multiple": "2.84",
        "total_demand_filter_status": "NOT_SPECIFIED", "additional_sale_shares": "0", "ipo_size_tl": "2233000000",
        "tufe_index": "132.31", "tufe_refusal": null
    })
    .as_object()
    .unwrap()
    .clone()
}

fn with(mut m: Map<String, Value>, k: &str, v: Value) -> Map<String, Value> {
    m.insert(k.into(), v);
    m
}

fn without(mut m: Map<String, Value>, k: &str) -> Map<String, Value> {
    m.remove(k);
    m
}

fn out(id: &str, inputs: &Map<String, Value>) -> Value {
    borsai_predict::predict(&params(id), inputs).expect("tahmin").to_json()
}

fn code(v: &Value) -> Option<String> {
    v["refused"]["code"].as_str().map(str::to_string)
}

#[test]
fn kind_and_params() {
    for id in FALL_IDS {
        let p = params(id);
        assert_eq!(model_kind(&p), Kind::Fall, "{id}");
        assert_eq!(check_params(&p), Ok(Kind::Fall), "{id}");
        assert_eq!(Kind::Fall.as_str(), "fall");
        let fp = parse_fall(&p).unwrap();
        assert_eq!(fp.horizons.iter().map(|(h, _)| h.as_str()).collect::<Vec<_>>(), FALL_HORIZONS, "{id}: çıktı sırası D5, D10");
        assert_eq!(fp.deflator.is_some(), fp.uses("f1r"), "{id}: deflatör yalnız f1r'li modelde");
    }
    assert_eq!(parse_fall(&params("fall_d10_v0_pooled@ZERO")).unwrap().features, Vec::<String>::new());
    assert_eq!(parse_fall(&params("fall_d10_v0_addsale")).unwrap().features, ["add_sale"]);
    assert_eq!(parse_fall(&params("fall_d10_v0_h99")).unwrap().variant.as_deref(), Some("h99"));
    // run_model türü "fall"
    assert_eq!(run_model(&params("fall_d10_v0_h99"), &netgl()).to_json()["kind"], json!("fall"));
}

#[test]
fn output_keys_and_order() {
    for id in FALL_IDS {
        for inputs in [netgl(), Map::new()] {
            let o = out(id, &inputs);
            let keys: Vec<&str> = o.as_object().unwrap().keys().map(String::as_str).collect();
            assert_eq!(keys, OUTPUT_KEYS, "{id}");
        }
    }
    // tahmin: getiri alanları null, yön birebir, ek alanlar
    let o = out("fall_d10_v0_h99", &netgl());
    assert!(o["refused"].is_null());
    for h in ["D5", "D10"] {
        let c = &o[h];
        for k in ["return", "return_unclipped", "return_clipped", "price"] {
            assert!(c[k].is_null(), "{h}.{k}");
        }
        let p = c["p_up"].as_f64().unwrap();
        assert_eq!(c["direction"], json!(if p > 0.5 { "UP" } else { "DOWN" }));
    }
    assert_eq!(o["add_sale_used"], json!(0));
    assert_eq!(o["tufe_index_used"], json!("132.31"));
    assert_eq!(o["clipped"], json!(false));
    assert_eq!(o["clipped_features"], json!([]));
    assert!(o["f1r_raw"].as_f64().unwrap() > 1.6e9);
}

#[test]
fn zero_rule_reads_no_input() {
    let p = params("fall_d10_v0_pooled@ZERO");
    let want = |h: &str| p["horizons"][h]["p_up"]["value"].as_f64().unwrap();
    for inputs in [netgl(), Map::new(), with(netgl(), "additional_sale_shares", Value::Null), with(netgl(), "tufe_refusal", json!("TUFE_MISSING"))] {
        let o = out("fall_d10_v0_pooled@ZERO", &inputs);
        assert!(o["refused"].is_null());
        assert_eq!(o["warnings"], json!([]));
        for k in ["clipped", "clipped_features", "f1r_raw", "tufe_index_used", "add_sale_used"] {
            assert!(o[k].is_null(), "{k}");
        }
        for h in ["D5", "D10"] {
            assert_eq!(o[h]["p_up"].as_f64().unwrap().to_bits(), want(h).to_bits(), "{h}: sabit başlık bit-eşit");
        }
    }
}

#[test]
fn addsale_reads_only_its_field() {
    let only = |v: Value| json!({"additional_sale_shares": v}).as_object().unwrap().clone();
    let o = out("fall_d10_v0_addsale", &only(json!("35000000")));
    assert!(o["refused"].is_null());
    assert_eq!((o["add_sale_used"].clone(), o["f1r_raw"].clone(), o["clipped_features"].clone()), (json!(1), Value::Null, json!([])));
    assert_eq!(code(&out("fall_d10_v0_addsale", &Map::new())).as_deref(), Some("ADDITIONAL_SALE_MISSING"));
    assert_eq!(code(&out("fall_d10_v0_addsale", &only(json!("-5")))).as_deref(), Some("INPUT_NEGATIVE"));
    assert_eq!(out("fall_d10_v0_addsale", &only(json!("-5")))["refused"]["field"], json!("additional_sale_shares"));
    // h99/pooled girdileri (fiyat, f3, TÜFE) okunmaz
    let o = out("fall_d10_v0_addsale", &without(without(netgl(), "ipo_price_tl"), "tufe_index"));
    assert!(o["refused"].is_null());
}

#[test]
fn python_refusal_order() {
    for id in ["fall_d10_v0_h99", "fall_d10_v0_pooled"] {
        // f3 boş + TÜFE yok + ek satış boş → F3_MISSING (önce)
        let i = with(with(without(netgl(), "tufe_index"), "total_demand_multiple", Value::Null), "additional_sale_shares", Value::Null);
        assert_eq!(code(&out(id, &i)).as_deref(), Some("F3_MISSING"), "{id}");
        // TÜFE yok + ek satış boş → TUFE_MISSING (Python: TÜFE ek satıştan önce; EK 3 §8.2 önerisi değil)
        let i = with(without(netgl(), "tufe_index"), "additional_sale_shares", Value::Null);
        let o = out(id, &i);
        assert_eq!((code(&o).as_deref(), o["refused"]["field"].as_str()), (Some("TUFE_MISSING"), Some("tufe_index")), "{id}");
        assert!(o["f1r_raw"].is_null());
        // ek satış boş (TÜFE var) → ADDITIONAL_SALE_MISSING; f1r_raw ve tufe_index_used o ana kadar dolu kalır
        let o = out(id, &with(netgl(), "additional_sale_shares", json!("DATA_NOT_FOUND")));
        assert_eq!(code(&o).as_deref(), Some("ADDITIONAL_SALE_MISSING"), "{id}");
        assert!(o["f1r_raw"].is_number() && o["tufe_index_used"] == json!("132.31") && o["add_sale_used"].is_null());
        assert!(o["clipped"].is_null() && o["clipped_features"].is_null() && o["warnings"] == json!([]));
        // girdi hatası (compute_features) en önce
        let o = out(id, &with(netgl(), "ipo_price_tl", json!("abc")));
        assert_eq!(code(&o).as_deref(), Some("INPUT_NOT_NUMERIC"));
        // TÜFE ret kodu aynen
        let o = out(id, &with(netgl(), "tufe_refusal", json!("TUFE_NOT_PIT")));
        assert_eq!(code(&o).as_deref(), Some("TUFE_NOT_PIT"));
    }
}

#[test]
fn clipping_ln_winsor() {
    // f3 eğitim p05 altı ve p95 üstü: FEATURE_CLIPPED_TO_TRAINING_P05_P95 (f3), clipped_features = ["f3"]
    for (id, f3) in [("fall_d10_v0_h99", "1.0"), ("fall_d10_v0_pooled", "60")] {
        let o = out(id, &with(netgl(), "total_demand_multiple", json!(f3)));
        assert_eq!(o["clipped"], json!(true), "{id}");
        assert_eq!(o["clipped_features"], json!(["f3"]), "{id}");
        let w: Vec<&str> = o["warnings"].as_array().unwrap().iter().map(|w| w["code"].as_str().unwrap()).collect();
        assert!(w.contains(&"FEATURE_CLIPPED_TO_TRAINING_P05_P95"), "{id}: {w:?}");
        assert!(!w.contains(&"F3_WINSORIZED"), "{id}: V1.5 kodu değil");
    }
    // f1r alt uçta (TÜFE × 10): kırpma f1r
    let o = out("fall_d10_v0_h99", &with(netgl(), "tufe_index", json!("1323.1")));
    assert_eq!(o["clipped_features"], json!(["f1r"]));
}

#[test]
fn params_check_python_codes() {
    let bad = |id: &str, f: &dyn Fn(&mut Value)| {
        let mut p = params(id);
        f(&mut p);
        borsai_predict::predict(&p, &netgl()).map(|_| ()).map_err(|e| e.code)
    };
    // `family` silinince tür hâlâ fall (algorithm) ve PARAMS_INVALID (EK 3 §8.1 önerisi: Linear'a düşerdi)
    assert_eq!(bad("fall_d10_v0_h99", &|p| p["family"] = Value::Null), Err("PARAMS_INVALID".into()));
    let mut p = params("fall_d10_v0_h99");
    p.as_object_mut().unwrap().remove("family");
    assert_eq!(model_kind(&p), Kind::Fall);
    assert_eq!(bad("fall_d10_v0_h99", &|p| p["deflator"] = Value::Null), Err("PARAMS_INVALID".into()));
    assert_eq!(bad("fall_d10_v0_pooled", &|p| p["preprocessing"]["log_transform"] = json!(["f1r"])), Err("PARAMS_INVALID".into()));
    assert_eq!(bad("fall_d10_v0_h99", &|p| p["features"] = json!(["f1r", "f3"])), Err("PARAMS_INVALID".into()));
    assert_eq!(bad("fall_d10_v0_addsale", &|p| p["horizons"]["D1"] = p["horizons"]["D10"].clone()), Err("PARAMS_INVALID".into()));
    assert_eq!(bad("fall_d10_v0_addsale", &|p| p["horizons"]["D5"]["return"] = json!({"kind": "constant", "value": 0.0})), Err("PARAMS_INVALID".into()));
    // sabit başlıkta bool yok (V1.5 `_check_params` bool'u sayı sayar; predict_fall saymaz)
    assert_eq!(bad("fall_d10_v0_pooled@ZERO", &|p| p["horizons"]["D10"]["p_up"]["value"] = json!(true)), Err("PARAMS_INVALID".into()));
    assert_eq!(bad("fall_d10_v0_pooled@ZERO", &|p| p["schema_version"] = json!("borsai.model/2")), Err("SCHEMA_UNSUPPORTED".into()));
    // yön: UP ancak p > 0.5
    let mut p = params("fall_d10_v0_pooled@ZERO");
    p["horizons"]["D5"]["p_up"]["value"] = json!(0.5);
    let o = borsai_predict::predict(&p, &Map::new()).unwrap().to_json();
    assert_eq!(o["D5"]["direction"], json!("DOWN"));
}
