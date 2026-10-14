//! U3: uç yolların kapsamı (SPEC_APP §5.1). Sayım altın satırların `expected` alanından yapılır
//! (etiketlerden değil). Her T-2 ret kodu ve her uyarı kodu ≥ 2 satırda; alan/ad kırılımları;
//! RETURN_CLIPPED her (model, ufuk) için UPPER ve LOWER. Muafiyetler golden/MANIFEST.json'da gerekçeli.
//!   cargo test -p borsai_predict --test coverage
mod common;

use common::*;
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const REFUSAL_CODES: [&str; 25] = [
    "INPUT_MISSING",
    "INPUT_NOT_NUMERIC",
    "INPUT_NOT_POSITIVE",
    "INPUT_NEGATIVE",
    "DIVISION_BY_ZERO",
    "INPUT_INCONSISTENT",
    "F3_MISSING",
    "F3_FILTER_STATUS_CONFLICT",
    "FEATURE_NOT_PROVIDED",
    "MARKET20_NOT_PROVIDED",
    "MARKET20_NOT_NUMERIC",
    "MARKET20_CALENDAR_NOT_COVERING",
    "MARKET20_INSUFFICIENT_HISTORY",
    "MARKET20_XU100_CLOSE_MISSING",
    "MARKET20_STALE_S0",
    "MARKET20_PREDICTION_TOO_EARLY",
    "MARKET20_XU100_INTEGRITY",
    "PB_FIELD_MISSING",
    "PB_IDENTITY",
    "PB_PRICE_RANGE",
    // Faz 7 v1 (SPEC_APP EK 3 §2.5)
    "TUFE_MISSING",
    "TUFE_NOT_PIT",
    "TUFE_FILE_MISMATCH",
    "REGIME_UNKNOWN",
    // Faz 7C düşen arz (SPEC_APP EK 3 §8.2)
    "ADDITIONAL_SALE_MISSING",
];

const WARNING_CODES: [&str; 7] = [
    "FEATURE_CLIPPED_TO_TRAINING_P05_P95",
    "OUT_OF_TRAINING_RANGE",
    "F4_ZERO_NO_TRAINING_EXAMPLE",
    "F3_WINSORIZED",
    "F3_CLIPPED_TO_TRAINING_P05_P95",
    "RETURN_CLIPPED_TO_PHYSICAL_BOUND",
    "PB4_ADDITIONAL_SALE_CEILING",
];

const REQUIRED_FIELD_BREAKDOWN: [(&str, &[&str]); 5] = [
    ("INPUT_MISSING", &["ipo_price_tl", "shares_offered", "post_ipo_share_capital", "capital_increase_shares"]),
    ("DIVISION_BY_ZERO", &["shares_offered", "post_ipo_share_capital"]),
    ("INPUT_INCONSISTENT", &["capital_increase_shares", "shares_offered"]),
    (
        "PB_FIELD_MISSING",
        &[
            "ipo_price_try",
            "planned_pre_ipo_capital",
            "planned_post_ipo_capital",
            "planned_capital_increase_shares",
            "planned_existing_share_sale",
            "planned_base_offer_shares",
            "planned_additional_sale_ceiling",
            "planned_max_offer_shares",
            "precision",
        ],
    ),
    (
        "PB_IDENTITY",
        &["ID-A", "ID-B", "ID-C", "BASE_POSITIVE", "POST_POSITIVE", "VALUE_POSITIVE", "PB2_RANGE", "PB3_RANGE", "PB4_RANGE"],
    ),
];

#[derive(Default)]
struct Counts {
    refusal: BTreeMap<String, usize>,
    refusal_field: BTreeMap<(String, String), usize>,
    warning: BTreeMap<String, usize>,
    range_side: BTreeMap<(String, String), usize>,
    clipped: BTreeMap<(String, String, String), usize>,
}

fn count_row(model_id: &str, row: &Value, c: &mut Counts) {
    let Some(out) = row["expected"].get("output") else { return };
    if let Some(r) = out.get("refused").filter(|r| r.is_object()) {
        let code = r["code"].as_str().unwrap().to_string();
        *c.refusal.entry(code.clone()).or_default() += 1;
        let field = r["field"].as_str().unwrap_or("").to_string();
        *c.refusal_field.entry((code, field)).or_default() += 1;
    }
    for w in out["warnings"].as_array().into_iter().flatten() {
        let code = w["code"].as_str().unwrap().to_string();
        *c.warning.entry(code.clone()).or_default() += 1;
        if code == "OUT_OF_TRAINING_RANGE" {
            let v = &w["value"];
            let lo = w["train_min"].as_f64().unwrap();
            let side = match v {
                Value::Number(n) if n.as_f64().unwrap() < lo => "low",
                Value::String(s) if s == "-Infinity" => "low",
                _ => "high",
            };
            *c.range_side.entry((w["feature"].as_str().unwrap().to_string(), side.to_string())).or_default() += 1;
        }
    }
    for h in ["D1", "D3", "D5", "D10"] {
        if let Some(side) = out.get(h).and_then(|cell| cell.get("return_clipped")).and_then(Value::as_str) {
            *c.clipped.entry((model_id.to_string(), h.to_string(), side.to_string())).or_default() += 1;
        }
    }
}

#[test]
fn golden_coverage() {
    let manifest = manifest();
    let params = load_params();
    let exemptions = manifest["coverage_exemptions"].as_array().unwrap().clone();
    let mut c = Counts::default();
    for mid in manifest["model_ids"].as_array().unwrap() {
        let mid = mid.as_str().unwrap();
        for row in read_jsonl(&golden_dir().join(format!("{mid}.jsonl"))) {
            count_row(mid, &row, &mut c);
        }
    }
    let mut patched = Counts::default();
    for row in read_jsonl(&golden_dir().join("_patched_params.jsonl")) {
        count_row(row["model_id"].as_str().unwrap(), &row, &mut patched);
    }

    let mut missing = Vec::new();
    let mut table = Vec::new();
    for code in REFUSAL_CODES {
        let n = c.refusal.get(code).copied().unwrap_or(0);
        let np = patched.refusal.get(code).copied().unwrap_or(0);
        let exempt = exemptions.iter().any(|e| e["code"] == json!(code));
        table.push(json!({"code": code, "rows": n, "patched_rows": np}));
        if n < 2 && !(exempt && np >= 2) {
            missing.push(format!("ret {code}: {n} satır (yamalı {np})"));
        }
    }
    for code in WARNING_CODES {
        let n = c.warning.get(code).copied().unwrap_or(0);
        table.push(json!({"code": code, "rows": n}));
        if n < 2 {
            missing.push(format!("uyarı {code}: {n} satır"));
        }
    }
    for (code, fields) in REQUIRED_FIELD_BREAKDOWN {
        for f in fields {
            let n = c.refusal_field.get(&(code.to_string(), f.to_string())).copied().unwrap_or(0);
            if n < 2 {
                missing.push(format!("ret {code}/{f}: {n} satır"));
            }
        }
    }
    // OUT_OF_TRAINING_RANGE: kayıtlı modellerin feature_ranges'teki her özellik, alt ve üst
    let mut features = BTreeSet::new();
    for (p, _) in params.values() {
        if let Some(fr) = p.get("feature_ranges").and_then(Value::as_object) {
            features.extend(fr.keys().cloned());
        }
    }
    for f in &features {
        for side in ["low", "high"] {
            let n = c.range_side.get(&(f.clone(), side.to_string())).copied().unwrap_or(0);
            let exempt = exemptions.iter().any(|e| e["feature"] == json!(f) && e["side"] == json!(side));
            if n < 2 && !exempt {
                missing.push(format!("OUT_OF_TRAINING_RANGE {f}/{side}: {n} satır"));
            }
        }
    }
    // RETURN_CLIPPED: sabit olmayan getiri başlığı olan her (model, ufuk) UPPER ve LOWER
    for (mid, (p, _)) in &params {
        for (h, heads) in p["horizons"].as_object().unwrap() {
            // yalnız ridge başlıkları kırpma üretir (gen_golden `clip_cases` ile aynı kural);
            // `mixture_median` (tavan yolu) başlığında `return_clipped` alanı yoktur.
            if heads.get("return").and_then(|r| r.get("kind")).and_then(Value::as_str) != Some("ridge") {
                continue;
            }
            for side in ["UPPER", "LOWER"] {
                let n = c.clipped.get(&(mid.clone(), h.clone(), side.to_string())).copied().unwrap_or(0);
                let exempt = exemptions
                    .iter()
                    .any(|e| e["model_id"] == json!(mid) && e["horizon"] == json!(h) && e["direction"] == json!(side));
                if n < 1 && !exempt {
                    missing.push(format!("RETURN_CLIPPED {mid}/{h}/{side}: {n} satır"));
                }
            }
        }
    }
    let clip_table: Vec<Value> =
        c.clipped.iter().map(|((m, h, s), n)| json!({"model_id": m, "horizon": h, "side": s, "rows": n})).collect();
    let report = json!({"codes": table, "return_clipped": clip_table,
                        "out_of_training_range": c.range_side.iter().map(|((f, s), n)| json!({"feature": f, "side": s, "rows": n})).collect::<Vec<_>>(),
                        "missing": missing});
    std::fs::write(target_dir().join("golden_coverage.json"), serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
    assert!(missing.is_empty(), "kapsanmayan uç yollar:\n{}", missing.join("\n"));
}

// ---------------------------------------------------------------- U44: tavan yolu kapsaması (EK 2 §3.6)

fn path_ids(params: &BTreeMap<String, (Value, String)>) -> Vec<String> {
    params
        .iter()
        .filter(|(_, (p, _))| borsai_predict::model_kind(p) == borsai_predict::Kind::CeilingPath)
        .map(|(k, _)| k.clone())
        .collect()
}

#[test]
fn path_coverage() {
    let manifest = manifest();
    let params = load_params();
    let ids = path_ids(&params);
    assert_eq!(ids.len(), 3, "üç tavan yolu modeli");
    let exemptions = manifest["coverage_exemptions"].as_array().unwrap().clone();
    let mut missing = Vec::new();
    let mut table = Vec::new();
    for mid in &ids {
        let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
        let (mut tick_warn, mut price_refusal, mut exceptions, mut snap_eq, mut snap_ne) = (0, 0, 0, 0, 0);
        let mut sh: BTreeMap<(usize, &str), usize> = BTreeMap::new();
        for row in &rows {
            let e = &row["expected"];
            if e.get("exception").is_some() {
                exceptions += 1;
            }
            let Some(out) = e.get("output") else { continue };
            for w in out["warnings"].as_array().into_iter().flatten() {
                if w["code"] == json!("IPO_PRICE_NOT_ON_TICK_GRID") {
                    tick_warn += 1;
                    assert!(w.get("field").is_some() && w.get("snapped").is_some() && w.get("tick").is_some(),
                            "{mid}: uyarı metin alanları eksik: {w}");
                }
            }
            if let Some(r) = out.get("refused").filter(|r| r.is_object()) {
                let code = r["code"].as_str().unwrap_or("");
                if r["field"] == json!("ipo_price_tl")
                    && ["INPUT_MISSING", "INPUT_NOT_NUMERIC", "INPUT_NOT_POSITIVE"].contains(&code)
                {
                    price_refusal += 1;
                }
            }
            if let Some(lp) = out.get("limit_path").filter(|v| v.is_object()) {
                if lp["ipo_price"] == lp["snapped_ipo_price"] {
                    snap_eq += 1;
                } else {
                    snap_ne += 1;
                }
            }
            if let Some(s) = out.get("S").and_then(Value::as_array) {
                for h in [1usize, 3, 5, 10] {
                    let side = if s[h - 1].as_f64().unwrap_or(0.0) >= 0.5 { "ge" } else { "lt" };
                    *sh.entry((h, side)).or_default() += 1;
                }
            }
        }
        table.push(json!({"model_id": mid, "tick_grid_warnings": tick_warn, "exceptions": exceptions,
                          "price_refusals": price_refusal, "snap_equal": snap_eq, "snap_different": snap_ne,
                          "S_h": sh.iter().map(|((h, s), n)| json!({"h": h, "side": s, "rows": n})).collect::<Vec<_>>()}));
        if tick_warn < 2 {
            missing.push(format!("{mid}: IPO_PRICE_NOT_ON_TICK_GRID {tick_warn} satır (< 2)"));
        }
        if exceptions < 2 {
            missing.push(format!("{mid}: expected.exception {exceptions} satır (< 2)"));
        }
        if snap_eq < 2 || snap_ne < 2 {
            missing.push(format!("{mid}: snap = P {snap_eq}, snap ≠ P {snap_ne} (< 2)"));
        }
        if mid.ends_with("@INF") && price_refusal < 2 {
            missing.push(format!("{mid}: ipo_price_tl reddi {price_refusal} satır (< 2)"));
        }
        let exempt_sh = exemptions.iter().any(|e| e["code"] == json!("S_H_THRESHOLD") && e["model_id"] == json!(mid));
        if !exempt_sh {
            for h in [1usize, 3, 5, 10] {
                for side in ["ge", "lt"] {
                    let n = sh.get(&(h, side)).copied().unwrap_or(0);
                    if n < 5 {
                        missing.push(format!("{mid}: S_{h} {side} {n} satır (< 5)"));
                    }
                }
            }
        }
        // koşullu dosya: j = 0..9 ve t = 0..9 her biri ≥ 40
        let crows = read_jsonl(&golden_dir().join(format!("{mid}.conditional.jsonl")));
        let (mut js, mut ts): (BTreeMap<u64, usize>, BTreeMap<u64, usize>) = (BTreeMap::new(), BTreeMap::new());
        for r in &crows {
            for v in r["streak_ongoing"].as_array().unwrap() {
                *js.entry(v["j"].as_u64().unwrap()).or_default() += 1;
            }
            for v in r["after_break"].as_array().unwrap() {
                *ts.entry(v["t"].as_u64().unwrap()).or_default() += 1;
            }
        }
        for j in 0..10u64 {
            if js.get(&j).copied().unwrap_or(0) < 40 {
                missing.push(format!("{mid}: koşullu j = {j} {} vektör (< 40)", js.get(&j).copied().unwrap_or(0)));
            }
            if ts.get(&j).copied().unwrap_or(0) < 40 {
                missing.push(format!("{mid}: koşullu t = {j} {} vektör (< 40)", ts.get(&j).copied().unwrap_or(0)));
            }
        }
    }

    // yamalı satırlar: POST_BREAK_INSUFFICIENT, pooled ve kırpılmış havuz (dondurulmuş hücrelerde tetiklenmez)
    let prows = read_jsonl(&golden_dir().join("_patched_params.jsonl"));
    let (mut insufficient, mut pooled) = (0usize, 0usize);
    let mut clipped_pool = 0usize;
    for row in &prows {
        let mid = row["model_id"].as_str().unwrap();
        if !ids.iter().any(|x| x == mid) {
            continue;
        }
        let Some(out) = row["expected"].get("output") else { continue };
        for h in 1..=10 {
            let Some(pbk) = out[format!("D{h}")].get("post_break") else { continue };
            if pbk["status"] == json!("POST_BREAK_INSUFFICIENT") {
                insufficient += 1;
            }
            if pbk["cells"].as_array().into_iter().flatten().any(|c| c["pooled"] == json!(true)) {
                pooled += 1;
            }
        }
        // kırpma: yamalı hücrelerde pool(B,1) kırpılmış değer içeriyor mu (n_clipped çıktıda yoktur)
        if row["tags"].as_array().into_iter().flatten().any(|t| t == &json!("patched:path:clipped_pool")) {
            let patched = apply_patch(&params[mid].0, &row["params_patch"]);
            let p = borsai_predict::params::parse_path(&patched).expect("yamalı parse_path");
            let pc = borsai_predict::path::pool(&p.cells, borsai_predict::path::Group::B, 1, borsai_predict::path::N_MIN);
            assert_eq!((pc.n(), pc.pooled()), (10, true), "kırpılmış havuz: n ve pooled");
            clipped_pool += pc.n_clipped;
        }
    }
    if insufficient < 2 {
        missing.push(format!("yamalı POST_BREAK_INSUFFICIENT {insufficient} hücre (< 2)"));
    }
    if pooled < 2 {
        missing.push(format!("yamalı pooled {pooled} hücre (< 2)"));
    }
    if clipped_pool < 1 {
        missing.push(format!("yamalı kırpılmış havuz {clipped_pool} değer (< 1)"));
    }
    let report = json!({"models": table, "patched": {"post_break_insufficient_cells": insufficient,
                        "pooled_cells": pooled, "clipped_values": clipped_pool}, "missing": missing});
    std::fs::write(target_dir().join("golden_coverage_path.json"), serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
    assert!(missing.is_empty(), "tavan yolu kapsaması eksik:\n{}", missing.join("\n"));
}

// ---------------------------------------------------------------- U54: Faz 7 v1 kapsaması (EK 3 §10.1)

const V1_IDS: [&str; 4] =
    ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"];

/// TUFE_MISSING satırının girdi yolu (EK 3 §2.3 adım 2): ret kodu girdi sözlüğünden sınıflanır.
fn tufe_path(inputs: &serde_json::Map<String, Value>) -> &'static str {
    if inputs.get("tufe_refusal").is_some_and(|v| !v.is_null()) {
        return "tufe_refusal";
    }
    match inputs.get("tufe_index") {
        None | Some(Value::Null) => "absent_or_null",
        Some(Value::String(s)) if s.trim().is_empty() => "blank",
        Some(Value::Bool(_)) => "bool",
        Some(Value::String(s)) => match borsai_predict::dec::parse(s) {
            Some(borsai_predict::dec::Parsed::Finite(d)) if d.signum() <= 0 => "not_positive",
            Some(borsai_predict::dec::Parsed::Finite(_)) => "valid",
            _ => "not_numeric",
        },
        Some(_) => "other",
    }
}

#[test]
fn v1_coverage() {
    let mut missing = Vec::new();
    let mut by_model = Vec::new();
    let (mut tufe_paths, mut not_pit, mut mismatch) = (BTreeMap::<&str, usize>::new(), 0usize, 0usize);
    let (mut regime_unknown, mut src_live, mut src_input, mut r1) = (BTreeMap::<&str, usize>::new(), 0usize, 0usize, 0usize);
    let mut clip_side: BTreeMap<(String, String, String), usize> = BTreeMap::new();
    let mut multi_col = 0usize;
    let mut f3_missing: BTreeMap<&str, usize> = BTreeMap::new();
    for mid in V1_IDS {
        let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
        let (mut n_out, mut inf_clipped_non_null) = (0usize, 0usize);
        for row in &rows {
            let Some(out) = row["expected"].get("output") else { continue };
            n_out += 1;
            let inputs = call_inputs(row);
            if let Some(r) = out.get("refused").filter(|r| r.is_object()) {
                let code = r["code"].as_str().unwrap();
                match code {
                    "TUFE_MISSING" => *tufe_paths.entry(tufe_path(&inputs)).or_default() += 1,
                    "TUFE_NOT_PIT" => not_pit += 1,
                    "TUFE_FILE_MISMATCH" => mismatch += 1,
                    "REGIME_UNKNOWN" => *regime_unknown.entry(mid).or_default() += 1,
                    "F3_MISSING" => *f3_missing.entry(mid).or_default() += 1,
                    _ => {}
                }
                let deflated = mid.ends_with("_real") || mid.ends_with("_pooled");
                if code.starts_with("TUFE_") && !deflated {
                    missing.push(format!("{mid}: TÜFE istemeyen modelde {code}"));
                }
                if code == "REGIME_UNKNOWN" && !mid.contains("pooled") {
                    missing.push(format!("{mid}: rejimsiz modelde REGIME_UNKNOWN"));
                }
            }
            match out.get("regime_source").and_then(Value::as_str) {
                Some("LIVE_VALUE") => src_live += 1,
                Some("ALLOC_REGIME_INPUT") => src_input += 1,
                _ => {}
            }
            if out.get("regime_value_used") == Some(&json!(1)) {
                r1 += 1;
            }
            if mid.ends_with("@INF") && !(out["clipped"].is_null() && out["clipped_features"].is_null()) {
                inf_clipped_non_null += 1;
            }
            if out["clipped_features"].as_array().is_some_and(|a| a.len() >= 2) {
                multi_col += 1;
            }
            for w in out["warnings"].as_array().into_iter().flatten() {
                if w["code"] != json!("FEATURE_CLIPPED_TO_TRAINING_P05_P95") {
                    continue;
                }
                let (v, u) = (w["value"].as_f64(), w["used"].as_f64().unwrap());
                let side = match (&w["value"], v) {
                    (_, Some(v)) if v < u => "low",
                    (Value::String(s), _) if s == "-Infinity" => "low",
                    _ => "high",
                };
                *clip_side.entry((mid.to_string(), w["feature"].as_str().unwrap().to_string(), side.into())).or_default() += 1;
            }
        }
        if mid.ends_with("@INF") && inf_clipped_non_null > 0 {
            missing.push(format!("{mid}: {inf_clipped_non_null} satırda clipped/clipped_features null değil"));
        }
        by_model.push(json!({"model_id": mid, "rows": rows.len(), "rows_with_output": n_out}));
    }
    let tufe_total: usize = tufe_paths.values().sum();
    if tufe_total < 10 {
        missing.push(format!("TUFE_MISSING {tufe_total} satır (< 10)"));
    }
    for path in ["absent_or_null", "blank", "bool", "not_numeric", "not_positive", "tufe_refusal"] {
        if tufe_paths.get(path).copied().unwrap_or(0) < 2 {
            missing.push(format!("TUFE_MISSING yolu {path}: {} satır (< 2)", tufe_paths.get(path).copied().unwrap_or(0)));
        }
    }
    if not_pit < 2 || mismatch < 2 {
        missing.push(format!("TUFE_NOT_PIT {not_pit}, TUFE_FILE_MISMATCH {mismatch} (< 2)"));
    }
    let ru: usize = regime_unknown.values().sum();
    if ru < 4 || regime_unknown.len() != 2 || regime_unknown.values().any(|n| *n < 2) {
        missing.push(format!("REGIME_UNKNOWN {regime_unknown:?} (toplam ≥ 4, pooled ve @INF'te ≥ 2)"));
    }
    if src_live < 10 || src_input < 10 {
        missing.push(format!("regime_source LIVE_VALUE {src_live}, ALLOC_REGIME_INPUT {src_input} (< 10)"));
    }
    if r1 < 20 {
        missing.push(format!("regime_value_used = 1: {r1} satır (< 20)"));
    }
    let wants: [(&str, &[&str]); 3] = [
        ("ceiling_hazard_v1_clip", &["f1", "f2", "f3"]),
        ("ceiling_hazard_v1_real", &["f1r", "f2", "f3"]),
        ("ceiling_hazard_v1_pooled", &["f1r", "f2", "f3"]),
    ];
    for (mid, cols) in wants {
        for col in cols {
            for side in ["low", "high"] {
                let n = clip_side.get(&(mid.to_string(), col.to_string(), side.to_string())).copied().unwrap_or(0);
                if n < 2 {
                    missing.push(format!("FEATURE_CLIPPED {mid}/{col}/{side}: {n} satır (< 2)"));
                }
            }
        }
        if f3_missing.get(mid).copied().unwrap_or(0) < 2 {
            missing.push(format!("F3_MISSING {mid}: {} satır (< 2)", f3_missing.get(mid).copied().unwrap_or(0)));
        }
    }
    if clip_side.keys().any(|(m, c, _)| (c == "f1" && !m.ends_with("_clip")) || (c == "f1r" && m.ends_with("_clip"))) {
        missing.push("f1 yalnız clip'te, f1r yalnız real/pooled'da kırpılır".into());
    }
    if multi_col < 2 {
        missing.push(format!("clipped_features ≥ 2 sütunlu satır {multi_col} (< 2)"));
    }
    let report = json!({
        "models": by_model,
        "tufe_missing_paths": tufe_paths, "tufe_not_pit": not_pit, "tufe_file_mismatch": mismatch,
        "regime_unknown": regime_unknown, "regime_source": {"LIVE_VALUE": src_live, "ALLOC_REGIME_INPUT": src_input},
        "regime_value_used_1": r1, "clipped_features_multi_column_rows": multi_col, "f3_missing": f3_missing,
        "feature_clipped": clip_side.iter().map(|((m, c, s), n)| json!({"model_id": m, "feature": c, "side": s, "rows": n})).collect::<Vec<_>>(),
        "oot_open_rows": manifest()["oot_open_rows"],
        "missing": missing,
    });
    std::fs::write(target_dir().join("golden_coverage_v1.json"), serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
    assert!(missing.is_empty(), "v1 kapsaması eksik:\n{}", missing.join("\n"));
}

// ---------------------------------------------------------------- U66: D1 sonrası kapsaması (EK 3 §10.2)

/// `golden/post_d1_hazard_v0.jsonl`'ın `expected` alanından: her `D1_*` reddi ≥ 2 (`D1_FIELD_INVALID` üç alanın her biri),
/// `D1_NOT_CEILING` ≥ 5, `D1_NOT_TRADED` (`expected.error`) ≥ 2, her `WARN_D1_*` ≥ 2, `D1_TURNOVER_CLIPPED` alt/üst ≥ 2,
/// `OUT_OF_TRAINING_RANGE` d1_turnover ≥ 2, `path_conditional` null (path verilmemiş) ≥ 2 ve dolu ≥ 100;
/// `INPUT_SHARES_OFFERED` MANIFEST muafiyeti (ana model önce reddeder; birim testte sınanır).
#[test]
fn post_d1_coverage() {
    let manifest = manifest();
    let mut missing = Vec::new();
    let mut refusal: BTreeMap<(String, String), usize> = BTreeMap::new();
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    let mut bump = |k: String| *counts.entry(k).or_default() += 1;
    for mid in post_d1_ids() {
        for row in read_jsonl(&golden_dir().join(format!("{mid}.jsonl"))) {
            let e = &row["expected"];
            if let Some(code) = e.pointer("/error/code").and_then(Value::as_str) {
                bump(format!("error:{code}"));
                continue;
            }
            let Some(out) = e.get("output") else { continue };
            if let Some(r) = out.get("refused").filter(|r| r.is_object()) {
                let key = (r["code"].as_str().unwrap().to_string(), r["field"].as_str().unwrap_or("").to_string());
                *refusal.entry(key).or_default() += 1;
            }
            if let Some(code) = out.pointer("/not_applicable/code").and_then(Value::as_str) {
                bump(format!("not_applicable:{code}"));
            }
            for w in out["warnings"].as_array().into_iter().flatten() {
                let code = w["code"].as_str().unwrap();
                bump(format!("warning:{code}"));
                if code == "D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95" {
                    let side = if w["value"].as_f64().unwrap() < w["used"].as_f64().unwrap() { "low" } else { "high" };
                    bump(format!("clip:{side}"));
                }
                if code == "OUT_OF_TRAINING_RANGE" && w["feature"] == json!("d1_turnover") {
                    bump("oor:d1_turnover".into());
                }
            }
            let predicted = out["refused"].is_null() && out["not_applicable"].is_null();
            if predicted {
                let set = !out["path_conditional"].is_null();
                bump(format!("path_conditional:{}", if set { "set" } else { "null" }));
                if !set && row["path_params"] != json!(false) {
                    missing.push(format!("{}: path verilmiş ama path_conditional null", row["case_id"]));
                }
            }
        }
    }
    let n = |k: &str| counts.get(k).copied().unwrap_or(0);
    let need = |k: &str, min: usize, missing: &mut Vec<String>| {
        if n(k) < min {
            missing.push(format!("{k}: {} satır (< {min})", n(k)));
        }
    };
    for (code, field) in [("D1_LIMIT_NA", "upper_limit"), ("D1_VOLUME_INVALID", "volume"), ("D1_FIELD_INVALID", "low"),
                          ("D1_FIELD_INVALID", "open"), ("D1_FIELD_INVALID", "high")] {
        let got = refusal.get(&(code.to_string(), field.to_string())).copied().unwrap_or(0);
        if got < 2 {
            missing.push(format!("ret {code}/{field}: {got} satır (< 2)"));
        }
    }
    need("not_applicable:D1_NOT_CEILING", 5, &mut missing);
    need("error:D1_NOT_TRADED", 2, &mut missing);
    for w in ["WARN_D1_HALF_DAY", "WARN_D1_INTRADAY_HALT", "WARN_D1_SPECIAL_TRADES", "WARN_D1_LOCK_INCONSISTENT"] {
        need(&format!("warning:{w}"), 2, &mut missing);
    }
    need("clip:low", 2, &mut missing);
    need("clip:high", 2, &mut missing);
    need("oor:d1_turnover", 2, &mut missing);
    need("path_conditional:null", 2, &mut missing);
    need("path_conditional:set", 100, &mut missing);
    let exempt = manifest["coverage_exemptions"]
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["code"] == json!("INPUT_SHARES_OFFERED") && e["model_id"] == json!("post_d1_hazard_v0"));
    if !exempt {
        missing.push("INPUT_SHARES_OFFERED muafiyeti MANIFEST'te yok".into());
    }
    let report = json!({
        "counts": counts,
        "refusals": refusal.iter().map(|((c, f), n)| json!({"code": c, "field": f, "rows": n})).collect::<Vec<_>>(),
        "missing": missing,
    });
    std::fs::write(target_dir().join("golden_coverage_post_d1.json"), serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
    assert!(missing.is_empty(), "D1 sonrası kapsaması eksik:\n{}", missing.join("\n"));
}

// ---------------------------------------------------------------- U78: (C) kapsaması (EK 3 §10.4)

const FALL_IDS: [&str; 4] = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"];
const FALL_DEFLATED: [&str; 2] = ["fall_d10_v0_h99", "fall_d10_v0_pooled"];

/// `additional_sale_shares` girdisinin ret yolu (sayım `expected`'tan; yol çağrı girdisinden).
fn add_sale_path(inputs: &serde_json::Map<String, Value>) -> &'static str {
    match inputs.get("additional_sale_shares") {
        None => "absent",
        Some(Value::Null) => "null",
        Some(Value::String(s)) if s.trim().is_empty() => "blank",
        Some(Value::String(s)) if s.trim() == "DATA_NOT_FOUND" => "DATA_NOT_FOUND",
        Some(_) => "other",
    }
}

/// `golden/fall_d10_v0_*.jsonl`'ın `expected` alanından: `ADDITIONAL_SALE_MISSING` ≥ 6 (yok/null/boş/DATA_NOT_FOUND her biri ≥ 1),
/// `INPUT_NEGATIVE` (`additional_sale_shares`) ≥ 2, `add_sale_used = 1` ≥ 20 (h99, pooled, addsale); `F3_MISSING` ve `TUFE_*`
/// yalnız h99/pooled (her TÜFE kodu ≥ 2); f1r ve f3 kırpması (ln öncesi ham değer) alt/üst ≥ 2 yalnız h99/pooled; `@ZERO` her
/// satırda sabit başlıklarla bit-eşit (≥ 200 satır), ret ve ek alan yok.
#[test]
fn fall_coverage() {
    let params = load_params();
    let mut missing = Vec::new();
    let mut report = Vec::new();
    for mid in FALL_IDS {
        let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
        let (mut codes, mut asm_paths, mut clip) = (BTreeMap::<String, usize>::new(), BTreeMap::<&str, usize>::new(), BTreeMap::<(String, String), usize>::new());
        let (mut neg_add, mut add1, mut zero_ok) = (0usize, 0usize, 0usize);
        let p = &params[mid].0;
        for row in &rows {
            let Some(out) = row["expected"].get("output") else { continue };
            let inputs = call_inputs(row);
            if let Some(r) = out.get("refused").filter(|r| r.is_object()) {
                let code = r["code"].as_str().unwrap().to_string();
                if code == "ADDITIONAL_SALE_MISSING" {
                    *asm_paths.entry(add_sale_path(&inputs)).or_default() += 1;
                }
                if code == "INPUT_NEGATIVE" && r["field"] == json!("additional_sale_shares") {
                    neg_add += 1;
                }
                *codes.entry(code).or_default() += 1;
            }
            if out["add_sale_used"] == json!(1) {
                add1 += 1;
            }
            for w in out["warnings"].as_array().into_iter().flatten() {
                if w["code"] != json!("FEATURE_CLIPPED_TO_TRAINING_P05_P95") {
                    continue;
                }
                let (v, u) = (w["value"].as_f64(), w["used"].as_f64().unwrap());
                let side = match (&w["value"], v) {
                    (_, Some(v)) if v < u => "low",
                    (Value::String(s), _) if s == "-Infinity" => "low",
                    _ => "high",
                };
                *clip.entry((w["feature"].as_str().unwrap().to_string(), side.to_string())).or_default() += 1;
            }
            if mid.ends_with("@ZERO") {
                let same = |h: &str| out[h]["p_up"].as_f64().map(f64::to_bits) == p["horizons"][h]["p_up"]["value"].as_f64().map(f64::to_bits);
                let extras_null = ["clipped", "clipped_features", "f1r_raw", "tufe_index_used", "add_sale_used"].iter().all(|k| out[*k].is_null());
                if out["refused"].is_null() && same("D5") && same("D10") && extras_null && out["warnings"] == json!([]) {
                    zero_ok += 1;
                }
            }
        }
        let n = |c: &str| codes.get(c).copied().unwrap_or(0);
        let deflated = FALL_DEFLATED.contains(&mid);
        if mid.ends_with("@ZERO") {
            if zero_ok != rows.len() || zero_ok < 200 {
                missing.push(format!("{mid}: sabit çıktı {zero_ok}/{} satır (≥ 200, hepsi)", rows.len()));
            }
        } else {
            if n("ADDITIONAL_SALE_MISSING") < 6 || ["absent", "null", "blank", "DATA_NOT_FOUND"].iter().any(|k| asm_paths.get(k).copied().unwrap_or(0) < 1) {
                missing.push(format!("{mid}: ADDITIONAL_SALE_MISSING {} {asm_paths:?} (≥ 6; dört yol)", n("ADDITIONAL_SALE_MISSING")));
            }
            if neg_add < 2 {
                missing.push(format!("{mid}: INPUT_NEGATIVE (additional_sale_shares) {neg_add} (< 2)"));
            }
            if add1 < 20 {
                missing.push(format!("{mid}: add_sale = 1 {add1} satır (< 20)"));
            }
        }
        for c in ["F3_MISSING", "TUFE_MISSING", "TUFE_NOT_PIT", "TUFE_FILE_MISMATCH"] {
            if deflated && n(c) < 2 {
                missing.push(format!("{mid}: {c} {} (< 2)", n(c)));
            }
            if !deflated && n(c) > 0 {
                missing.push(format!("{mid}: {c} bu modelde olamaz ({})", n(c)));
            }
        }
        for col in ["f1r", "f3"] {
            for side in ["low", "high"] {
                let k = clip.get(&(col.to_string(), side.to_string())).copied().unwrap_or(0);
                if deflated && k < 2 {
                    missing.push(format!("{mid}: FEATURE_CLIPPED {col}/{side} {k} (< 2)"));
                }
            }
        }
        if !deflated && !clip.is_empty() {
            missing.push(format!("{mid}: kırpma bu modelde olamaz {clip:?}"));
        }
        report.push(json!({
            "model_id": mid, "rows": rows.len(), "refusals": codes, "additional_sale_missing_paths": asm_paths,
            "input_negative_additional_sale": neg_add, "add_sale_used_1": add1,
            "feature_clipped": clip.iter().map(|((c, s), k)| json!({"feature": c, "side": s, "rows": k})).collect::<Vec<_>>(),
            "zero_constant_rows": zero_ok,
        }));
    }
    let doc = json!({"models": report, "fall_oot_open_rows": manifest()["fall_oot_open_rows"], "missing": missing});
    std::fs::write(target_dir().join("golden_coverage_fall.json"), serde_json::to_string_pretty(&doc).unwrap() + "\n").unwrap();
    assert!(missing.is_empty(), "(C) kapsaması eksik:\n{}", missing.join("\n"));
}
