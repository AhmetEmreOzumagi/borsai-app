//! `ceiling_hazard_v1` portunun anlam birim testleri (SPEC_APP EK 3 §2.2–§2.6). Parite (Python çıktısıyla alan
//! alan eşitlik) altın vektörlerdedir (`--test golden`); burada kuralların kendisi dondurulmuş dört JSON'la sınanır:
//! TÜFE girdisi kuralları, rejim anahtarı (var/yok/null), parametre denetiminin v1 dalı, çıktı anahtar kümesi.
//!   cargo test -p borsai_predict --test v1_semantics
mod common;

use borsai_predict::error::*;
use borsai_predict::{predict, Output};
use common::*;
use serde_json::{json, Map, Value};

const CLIP: &str = "ceiling_hazard_v1_clip";
const REAL: &str = "ceiling_hazard_v1_real";
const POOLED: &str = "ceiling_hazard_v1_pooled";
const POOLED_INF: &str = "ceiling_hazard_v1_pooled@INF";

fn params(model_id: &str) -> Value {
    let idx = read_json(&repo_dir().join("models").join("INDEX.json"));
    let e = idx["models"].as_array().unwrap().iter().find(|e| e["model_id"] == json!(model_id)).expect("INDEX'te");
    let bytes = std::fs::read(repo_dir().join("models").join(e["file"].as_str().unwrap())).unwrap();
    assert_eq!(sha256_hex(&bytes), e["sha256"].as_str().unwrap(), "{model_id}: sha INDEX ile aynı değil");
    serde_json::from_slice(&bytes).unwrap()
}

/// NETGL girdi belgesinin değerleri (registry/inputs/NETGL.json).
fn netgl() -> Map<String, Value> {
    json!({
        "ipo_price_tl": "25.52", "shares_offered": "87500000", "post_ipo_share_capital": "312500000",
        "capital_increase_shares": "62500000", "existing_share_sale_shares": "25000000", "total_demand_multiple": "2.84",
        "total_demand_filter_status": "NOT_SPECIFIED", "additional_sale_shares": "0", "ipo_size_tl": "2233000000"
    })
    .as_object()
    .unwrap()
    .clone()
}

fn with(mut m: Map<String, Value>, kv: &[(&str, Value)]) -> Map<String, Value> {
    for (k, v) in kv {
        m.insert((*k).into(), v.clone());
    }
    m
}

fn run(model_id: &str, inputs: &Map<String, Value>) -> Value {
    match predict(&params(model_id), inputs).unwrap_or_else(|e| panic!("{model_id}: {e}")) {
        Output::Hazard(o) => Output::Hazard(o).to_json(),
        other => panic!("{model_id}: tavan çıktısı değil: {other:?}"),
    }
}

fn refused(v: &Value) -> Option<(String, String)> {
    v["refused"].as_object().map(|r| (r["code"].as_str().unwrap().into(), r["field"].as_str().unwrap_or("").into()))
}

fn keys(v: &Value) -> Vec<String> {
    let mut k: Vec<String> = v.as_object().unwrap().keys().cloned().collect();
    k.sort();
    k
}

#[test]
fn tufe_input_rules() {
    let base = netgl();
    for model in [REAL, POOLED] {
        // anahtar yok / null / boş / bool / sayı değil / ≤ 0 / sonlu değil → TUFE_MISSING (INPUT_NOT_NUMERIC değil)
        let bad: [Option<Value>; 11] = [
            None,
            Some(Value::Null),
            Some(json!("")),
            Some(json!("   ")),
            Some(json!(true)),
            Some(json!("abc")),
            Some(json!("134,75")),
            Some(json!("0")),
            Some(json!("-1")),
            Some(json!("inf")),
            Some(json!("nan")),
        ];
        for b in bad {
            let inputs = match &b {
                None => base.clone(),
                Some(v) => with(base.clone(), &[("tufe_index", v.clone())]),
            };
            let out = run(model, &inputs);
            assert_eq!(refused(&out), Some((TUFE_MISSING.into(), "tufe_index".into())), "{model} {b:?}");
            // TÜFE reddinde clipped/clipped_features null, f1r_raw/tufe_index_used/regime_* yok
            assert_eq!((&out["clipped"], &out["clipped_features"]), (&Value::Null, &Value::Null));
            for k in ["f1r_raw", "tufe_index_used", "regime_value_used", "regime_source"] {
                assert!(out.get(k).is_none(), "{model} {b:?}: {k} yazılmamalı");
            }
        }
        // tufe_refusal dolu → o kod (bilinmeyen → TUFE_MISSING), tufe_index dolu olsa bile
        for (code, want) in [
            ("TUFE_NOT_PIT", TUFE_NOT_PIT),
            ("TUFE_FILE_MISMATCH", TUFE_FILE_MISMATCH),
            ("TUFE_MISSING", TUFE_MISSING),
            ("BOGUS", TUFE_MISSING),
        ] {
            let inputs = with(base.clone(), &[("tufe_index", json!("132.31")), ("tufe_refusal", json!(code))]);
            assert_eq!(refused(&run(model, &inputs)), Some((want.into(), "tufe_index".into())), "{model} {code}");
        }
        // biçimler: metin Decimal olarak okunur ve str(Decimal) yazılır; JSON sayı repr yolu
        for (raw, used) in [(json!("134.75"), "134.75"), (json!("134.750"), "134.750"), (json!("1.3475E2"), "134.75"), (json!(" 134.75 "), "134.75"), (json!(134.75), "134.75")] {
            let out = run(model, &with(base.clone(), &[("tufe_index", raw.clone()), ("tufe_refusal", Value::Null)]));
            assert!(out["refused"].is_null(), "{model} {raw}: {out}");
            assert_eq!(out["tufe_index_used"], json!(used), "{model} {raw}");
        }
    }
    // clip ve @INF TÜFE istemez
    for model in [CLIP, POOLED_INF] {
        let out = run(model, &base);
        assert!(out["refused"].is_null(), "{model}: {out}");
        assert!(out.get("f1r_raw").is_none() && out.get("tufe_index_used").is_none());
    }
}

#[test]
fn f3_missing_before_tufe() {
    let inputs = with(netgl(), &[("total_demand_multiple", Value::Null)]);
    for model in [CLIP, REAL, POOLED] {
        assert_eq!(refused(&run(model, &inputs)), Some((F3_MISSING.into(), "total_demand_multiple".into())), "{model}");
    }
    assert!(run(POOLED_INF, &inputs)["refused"].is_null(), "@INF girdi kullanmaz");
}

#[test]
fn regime_key_rules() {
    let base = with(netgl(), &[("tufe_index", json!("132.31")), ("tufe_refusal", Value::Null)]);
    for model in [POOLED, POOLED_INF] {
        // anahtar yok → r = live_value = 0, LIVE_VALUE
        let live = run(model, &base);
        assert_eq!((&live["regime_value_used"], &live["regime_source"]), (&json!(0), &json!("LIVE_VALUE")), "{model}");
        // etiket → r; EQUAL_DIST'te η canlıyla aynı
        for (label, r) in [("PRE_20211111", 1), ("THRESH100_20211111", 1), ("EQUAL_DIST_20230330", 0)] {
            let out = run(model, &with(base.clone(), &[("alloc_regime", json!(label))]));
            assert_eq!((&out["regime_value_used"], &out["regime_source"]), (&json!(r), &json!("ALLOC_REGIME_INPUT")), "{model} {label}");
            if r == 0 {
                assert_eq!(out["S"], live["S"], "{model}: r = 0 canlıyla bit-eşit");
            } else {
                assert_ne!(out["S"], live["S"], "{model}: r = 1'de δ eklenir");
            }
        }
        // anahtar VAR ama geçersiz (null dahil) → REGIME_UNKNOWN
        for bad in [Value::Null, json!(""), json!("UNKNOWN"), json!(1)] {
            let out = run(model, &with(base.clone(), &[("alloc_regime", bad.clone())]));
            assert_eq!(refused(&out), Some((REGIME_UNKNOWN.into(), "alloc_regime".into())), "{model} {bad}");
            assert!(out.get("regime_value_used").is_none() && out.get("regime_source").is_none());
            if model == POOLED {
                // rejim reddinde TÜFE ve kırpma alanları dolu
                assert!(out.get("f1r_raw").is_some() && out["clipped_features"].is_array() && out["clipped"] == json!(false));
            } else {
                assert!(out["clipped"].is_null() && out["clipped_features"].is_null());
            }
        }
    }
    // rejimsiz modeller anahtarı yok sayar
    for model in [CLIP, REAL] {
        let out = run(model, &with(base.clone(), &[("alloc_regime", Value::Null)]));
        assert!(out["refused"].is_null() && out.get("regime_value_used").is_none(), "{model}");
    }
}

#[test]
fn clipping_and_output_keys() {
    let base = with(netgl(), &[("tufe_index", json!("132.31")), ("tufe_refusal", Value::Null)]);
    let v0 = ["P_L", "P_close_ceiling", "S", "clipped", "hazard", "model_id", "refused", "warnings"];
    let with_keys = |extra: &[&str]| {
        let mut k: Vec<String> = v0.iter().chain(extra).map(|s| s.to_string()).collect();
        k.sort();
        k
    };
    assert_eq!(keys(&run(CLIP, &base)), with_keys(&["clipped_features"]));
    assert_eq!(keys(&run(REAL, &base)), with_keys(&["clipped_features", "f1r_raw", "tufe_index_used"]));
    assert_eq!(
        keys(&run(POOLED, &base)),
        with_keys(&["clipped_features", "f1r_raw", "tufe_index_used", "regime_value_used", "regime_source"])
    );
    assert_eq!(keys(&run(POOLED_INF, &base)), with_keys(&["clipped_features", "regime_value_used", "regime_source"]));
    assert!(run(POOLED_INF, &base)["clipped_features"].is_null());
    // v0 çıktısının anahtarları değişmez
    let v0p = read_json(&repo_dir().join("models").join("ceiling_hazard_v0.json"));
    let Output::Hazard(o) = predict(&v0p, &base).unwrap() else { panic!() };
    assert_eq!(keys(&Output::Hazard(o).to_json()), with_keys(&[]));
    // NETGL: kırpma yok
    for model in [CLIP, REAL, POOLED] {
        let out = run(model, &base);
        assert_eq!((&out["clipped"], &out["clipped_features"]), (&json!(false), &json!([])), "{model}");
    }
    // f1r kırpılır (üst), f1 kırpılmaz: büyüklük × 10, iki sütun birden (f3 alt)
    let big = with(base.clone(), &[("ipo_size_tl", json!("22330000000")), ("total_demand_multiple", json!("0.3"))]);
    for model in [REAL, POOLED] {
        let out = run(model, &big);
        assert_eq!(out["clipped_features"], json!(["f1r", "f3"]), "{model}: {out}");
        let codes: Vec<(&str, &str)> = out["warnings"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|w| w["code"] == json!(WARN_FEATURE_CLIPPED))
            .map(|w| (w["code"].as_str().unwrap(), w["feature"].as_str().unwrap()))
            .collect();
        assert_eq!(codes, [(WARN_FEATURE_CLIPPED, "f1r"), (WARN_FEATURE_CLIPPED, "f3")], "{model}");
    }
    let out = run(CLIP, &big);
    assert_eq!(out["clipped_features"], json!(["f1", "f3"]), "clip: f1 ham TL ile kırpılır");
}

#[test]
fn v1_params_check() {
    let check = |p: &Value| borsai_predict::check_params(p).map(|_| ()).map_err(|e| e.code);
    for m in [CLIP, REAL, POOLED, POOLED_INF] {
        assert_eq!(check(&params(m)), Ok(()), "{m}");
    }
    let edit = |m: &str, f: &dyn Fn(&mut Value)| {
        let mut p = params(m);
        f(&mut p);
        check(&p)
    };
    let invalid = Err(PARAMS_INVALID.to_string());
    assert_eq!(edit(CLIP, &|p| p["preprocessing"]["winsor"].as_object_mut().unwrap().remove("f2").map(|_| ()).unwrap()), invalid);
    assert_eq!(edit(REAL, &|p| p.as_object_mut().unwrap().remove("deflator").map(|_| ()).unwrap()), invalid);
    assert_eq!(edit(POOLED, &|p| p["regime"]["penalized"] = json!(true)), invalid);
    assert_eq!(edit(POOLED, &|p| p["regime"]["delta"] = json!(true)), invalid);
    assert_eq!(edit(POOLED_INF, &|p| p["regime"]["live_value"] = json!(2)), invalid);
    assert_eq!(edit(POOLED_INF, &|p| p["regime"]["live_value"] = json!(1)), Ok(()));
    // aile adı yoksa [f1r, f2, f3] yasak (v1 olmayan dal)
    assert_eq!(edit(REAL, &|p| p.as_object_mut().unwrap().remove("family").map(|_| ()).unwrap()), invalid);
    // v1'de PB listesi yasak
    assert_eq!(
        edit(CLIP, &|p| {
            p["features"] = json!(["pb1", "pb2"]);
            p["beta"] = json!({"pb1": 0.1, "pb2": 0.2});
        }),
        invalid
    );
    assert_eq!(edit(POOLED, &|p| p["schema_version"] = json!("borsai.model/2")), Err(SCHEMA_UNSUPPORTED.to_string()));
}
