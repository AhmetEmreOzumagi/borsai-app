//! U65 (SPEC_APP EK 3 §10.2): `post_d1_hazard_v0` Rust içi anlam testleri.
//!   cargo test -p borsai_predict post_d1_inf_and_lock
//! (a) δ = {0, 0} yamasıyla S ve `conditional_j1` `ceiling_hazard_v0`'ın `survival::conditional(S, 1)` çıktısına BİT-EŞİT
//! (H2: δ = 0'da özel dal yok, `+ 0.0`); (b) `hazard[0]` ana modelle bit-eşit (dondurulmuş δ ile de); (c) `evaluate_d1`
//! kilit eşitliği Decimal değer eşitliğidir: "10.12"/"10.120" → 1, "10.12"/"10.1200000000000000001" → 0 (K3 çifti).
mod common;

use common::*;
use serde_json::{json, Map, Value};

use borsai_predict::output::Output;
use borsai_predict::post_d1::{self, evaluate_d1};
use borsai_predict::survival;

fn model(file: &str) -> Value {
    read_json(&repo_dir().join("models").join(file))
}

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

fn d1_at(upper: &str, low: &str, volume: &str) -> Value {
    json!({"fields_raw": {"open": upper, "high": upper, "low": low, "close": upper, "volume": volume, "trade_count": "4000",
                          "upper_limit": upper, "special_trade_volume": "0"}, "half_day": 0, "halt_flag": 0})
}

fn bits(v: &[f64]) -> Vec<u64> {
    v.iter().map(|x| x.to_bits()).collect()
}

#[test]
fn post_d1_inf_and_lock() {
    let parent = model("ceiling_hazard_v0.json");
    let mut post = model("post_d1_hazard_v0.json");
    let path = model("ceiling_path_v0.json");
    let inputs = netgl();
    let Output::Hazard(base) = borsai_predict::predict(&parent, &inputs).unwrap() else { panic!("tavan çıktısı") };
    let base_s = base.s.clone().unwrap();
    let base_h = base.hazard.clone().unwrap();
    let d1 = d1_at("28.06", "28.06", "8750000");

    // (b) dondurulmuş δ ile h_1 ana modelle bit-eşit; d ≥ 2 farklı
    let out = post_d1::predict(&post, &parent, &inputs, &d1, Some(&path)).unwrap();
    let h = out.hazard.clone().unwrap();
    assert_eq!(h[0].to_bits(), base_h[0].to_bits(), "h_1 ana modelden aynen");
    assert!(h[1..].iter().zip(&base_h[1..]).all(|(a, b)| a != b), "δ ≠ 0: d ≥ 2 güncellenir");
    assert!(out.path_conditional.is_some(), "path verilince path_conditional dolu");

    // (a) δ = {0, 0}: S ve koşullu görünüm ana modelin S'iyle ve survival::conditional(S, 1) ile bit-eşit
    post["delta"] = json!({"d1_lock": 0.0, "d1_turnover": 0.0});
    for (lock_low, vol) in [("28.06", "8750000"), ("28.04", "100"), ("28.06", "87500000000")] {
        let d1 = d1_at("28.06", lock_low, vol);
        let out = post_d1::predict(&post, &parent, &inputs, &d1, None).unwrap();
        assert_eq!(bits(out.s.as_ref().unwrap()), bits(&base_s), "δ = 0: S ana modelle bit-eşit ({lock_low}, {vol})");
        assert_eq!(bits(out.hazard.as_ref().unwrap()), bits(&base_h));
        let c = survival::conditional(&base_s, 1).unwrap();
        let cj = out.conditional_j1.as_ref().unwrap();
        let want_s: Vec<f64> = c.s_cond[1..].iter().map(|x| x.unwrap()).collect();
        let want_pl: Vec<f64> = c.p_l_cond[1..].iter().map(|x| x.unwrap()).collect();
        assert_eq!(bits(&cj.s_cond), bits(&want_s), "S_cond k = 2..10");
        assert_eq!(bits(&cj.p_l_cond), bits(&want_pl), "P_L_cond l = 1..10");
        assert_eq!(cj.p_break_next.to_bits(), c.p_break_next.to_bits(), "p_break_next");
        assert!(out.path_conditional.is_none(), "path verilmedi");
    }

    // (c) kilit eşitliği Decimal değeriyle
    let shares = json!("87500000");
    let lock = |upper: &str, low: &str| evaluate_d1(&d1_at(upper, low, "8750000"), Some(&shares)).unwrap().lock;
    assert_eq!(lock("10.12", "10.120"), 1);
    assert_eq!(lock("10.12", "10.1200000000000000001"), 0);
    assert_eq!(lock("10.120", "10.12"), 1);
    // kapanış = limit değerce (metin farklı) → tavan; kapanış limitten 1e-19 farklı → kapsam dışı
    let close_vs = |close: &str| {
        let mut d = d1_at("10.12", "10.12", "8750000");
        d["fields_raw"]["close"] = json!(close);
        evaluate_d1(&d, Some(&shares))
    };
    assert!(close_vs("10.1200").is_ok());
    assert!(matches!(close_vs("10.1200000000000000001"), Err(post_d1::D1Fail::NotApplicable(_))));
}

/// Kayıt yolu: `run_post_d1` durumları (PREDICTED / REFUSED / NOT_APPLICABLE / ERROR) ve `predict` dağıtımının bu türü
/// çalıştırmaması (Python `run_model` ERROR, PARAMS_INVALID).
#[test]
fn post_d1_run_statuses() {
    let parent = model("ceiling_hazard_v0.json");
    let post = model("post_d1_hazard_v0.json");
    let inputs = netgl();
    assert_eq!(borsai_predict::model_kind(&post), borsai_predict::Kind::PostD1);
    let r = borsai_predict::run_model(&post, &inputs);
    assert_eq!((r.status, r.refusal.unwrap().code.as_str()), ("ERROR", "PARAMS_INVALID"));
    assert!(borsai_predict::check_params(&post).is_err(), "ebeveynsiz denetlenemez");
    let run = |d1: &Value, inputs: &Map<String, Value>| post_d1::run_post_d1(&post, &parent, inputs, d1, None);
    assert_eq!(run(&d1_at("28.06", "28.06", "8750000"), &inputs).status, "PREDICTED");
    let mut nc = d1_at("28.06", "28.06", "8750000");
    nc["fields_raw"]["close"] = json!("27.50");
    let r = run(&nc, &inputs);
    assert_eq!((r.status, r.refusal.as_ref().unwrap().code.as_str()), (post_d1::STATUS_NOT_APPLICABLE, "D1_NOT_CEILING"));
    assert_eq!(r.to_json()["kind"], json!("post_d1"));
    let out = r.to_json()["output"].clone();
    assert_eq!(out["not_applicable"].as_object().unwrap().keys().collect::<Vec<_>>(), ["code", "reason"]);
    let mut no_f3 = inputs.clone();
    no_f3.insert("total_demand_multiple".into(), Value::Null);
    let r = run(&d1_at("28.06", "28.06", "8750000"), &no_f3);
    assert_eq!((r.status, r.refusal.unwrap().code.as_str()), ("REFUSED", "F3_MISSING"));
    let mut nt = d1_at("28.06", "28.06", "8750000");
    nt["fields_raw"]["trade_count"] = json!("");
    let r = run(&nt, &inputs);
    assert_eq!((r.status, r.refusal.unwrap().code.as_str(), r.output.is_none()), ("ERROR", "D1_NOT_TRADED", true));
    // çıktı anahtar sırası (Python sözlüğü)
    let out = post_d1::predict(&post, &parent, &inputs, &d1_at("28.06", "28.06", "8750000"), None).unwrap().to_json();
    let keys: Vec<&String> = out.as_object().unwrap().keys().collect();
    assert_eq!(
        keys,
        [
            "model_id", "stage", "refused", "not_applicable", "warnings", "clipped", "hazard", "S", "P_L", "P_close_ceiling",
            "conditional_j1", "path_conditional", "d1_features"
        ]
    );
    let f: Vec<&String> = out["d1_features"].as_object().unwrap().keys().collect();
    assert_eq!(
        f,
        ["d1_lock", "d1_turnover_ratio", "d1_turnover_ln", "clipped", "d1_turnover_used", "z", "ceiling_close_D1", "lock_consistency"]
    );
}
