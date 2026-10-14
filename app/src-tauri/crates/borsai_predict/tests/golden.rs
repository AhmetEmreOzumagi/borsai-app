//! Rust ↔ Python parite (SPEC_APP §1.3, §5.1 U1–U2, §5.6 U37; EK 2 U42, U43, U45; EK 3 U53, U64).
//!   cargo test -p borsai_predict --test golden
//! Sonuç: `target/parity_report.json` (model başına satır, maks |Δ|, bit-eşit oranı, koşullu bölüm).
mod common;

use common::*;
use serde_json::{json, Value};
use std::sync::OnceLock;

use borsai_predict::survival;

#[derive(Debug, Default, Clone)]
struct ModelStat {
    model_id: String,
    rows: usize,
    passed: usize,
    bit_equal_rows: usize,
    max_abs: f64,
    refused_rows: usize,
    error_rows: usize,
    numbers: usize,
    // koşullu (hazard/km)
    cond_rows: usize,
    cond_vectors: usize,
    cond_max_abs: f64,
    cond_j0_bit_equal: bool,
    cond_undefined: usize,
    cond_failures: Vec<String>,
}

/// Tavan yolu koşullu karışım sayaçları (U43).
#[derive(Debug, Default, Clone)]
struct PathCondStat {
    model_id: String,
    base_rows: usize,
    vectors: usize,
    after_break_vectors: usize,
    invalid_vectors: usize,
    max_abs: f64,
    j0_bit_equal: bool,
    mismatch_flagged: usize,
    failures: Vec<String>,
}

struct Run {
    stats: Vec<ModelStat>,
    /// D1 sonrası (ikinci dizin; EK 3 §6.4).
    post_stats: Vec<ModelStat>,
    patched: ModelStat,
    path_cond: Vec<PathCondStat>,
    passthrough: Vec<String>,
    failures: Vec<String>,
    report: Value,
}

/// U45: `ceiling_path` modelinin S/ret alanları gömülü seri modelinin aynı girdiyle ürettiğiyle
/// BİT-EŞİT olmalı (kopya, yeniden fit değil).
fn survival_passthrough(
    mid: &str,
    params: &Value,
    surv_params: &Value,
    rows: &[Value],
    out: &mut Vec<String>,
) -> usize {
    let mut checked = 0usize;
    for row in rows {
        if row.get("params_patch").is_some() {
            continue;
        }
        let inputs = call_inputs(row);
        let (path, surv) = (borsai_predict::predict(params, &inputs), borsai_predict::predict(surv_params, &inputs));
        let (Ok(p), Ok(h)) = (&path, &surv) else { continue };
        let (borsai_predict::Output::Path(p), borsai_predict::Output::Hazard(h)) = (p, h) else {
            out.push(format!("{mid}/{}: çıktı türleri beklenen değil", row["case_id"]));
            continue;
        };
        let _ = mid;
        checked += 1;
        let case = row["case_id"].as_str().unwrap_or("?");
        let pr = p.refused.as_ref().map(|r| (r.code.as_str(), r.field.as_deref()));
        let hr = h.refused.as_ref().map(|r| (r.code.as_str(), r.field.as_deref()));
        if hr.is_some() {
            // seri modelinin reddi AYNEN geçer (F3_MISSING, PB_* dahil)
            if pr != hr {
                out.push(format!("{case}: miras ret {pr:?} != seri modeli {hr:?}"));
            }
            continue;
        }
        if let Some((code, field)) = pr {
            // seri modeli reddetmedi: bu ancak limit yolu fiyat reddi olabilir (EK 2 §2.6 adım 4)
            let price_codes = ["INPUT_MISSING", "INPUT_NOT_NUMERIC", "INPUT_NOT_POSITIVE", "PB_FIELD_MISSING",
                               "PB_PRICE_RANGE", "PB_IDENTITY"];
            if !price_codes.contains(&code) {
                out.push(format!("{case}: tavan yolunun kendi reddi fiyat reddi değil: {code} / {field:?}"));
            }
            if p.s.is_some() || p.hazard.is_some() || p.clipped.is_some() {
                out.push(format!("{case}: fiyat reddinde seri alanları None'a çekilmemiş"));
            }
            continue;
        }
        // S, hazard, P_L, P_close_ceiling bit-eşit
        for (name, a, b) in [
            ("S", &p.s, &h.s),
            ("hazard", &p.hazard, &h.hazard),
            ("P_L", &p.p_l, &h.p_l),
            ("P_close_ceiling", &p.p_close_ceiling, &h.p_close_ceiling),
        ] {
            let bits = |v: &Option<Vec<f64>>| v.as_ref().map(|x| x.iter().map(|y| y.to_bits()).collect::<Vec<_>>());
            if bits(a) != bits(b) {
                out.push(format!("{case}: {name} seri modeliyle bit-eşit değil"));
            }
        }
        if p.clipped != h.clipped {
            out.push(format!("{case}: clipped {:?} != {:?}", p.clipped, h.clipped));
        }
    }
    checked
}

/// U43: `<model>.conditional.jsonl` vektörleri (durum 1, sapma, durum 2, ön koşul ihlalleri).
fn run_conditional_path(mid: &str, params: &Value, rows: &[Value]) -> PathCondStat {
    let mut st = PathCondStat { model_id: mid.to_string(), j0_bit_equal: true, ..Default::default() };
    let p = borsai_predict::params::parse_path(params).expect("parse_path");
    let closes = |v: &Value| -> Vec<String> {
        v.as_array().unwrap().iter().map(|x| x.as_str().unwrap().to_string()).collect()
    };
    for row in rows {
        st.base_rows += 1;
        let output = &row["output"];
        let case = row["case_id"].as_str().unwrap_or("?");
        let check = |label: String, exp: &Value, act: Result<Value, borsai_predict::PredictError>, st: &mut PathCondStat| {
            let mut c = RowCmp::new();
            match (exp.get("output"), exp.get("exception"), exp.get("error"), &act) {
                (Some(e), _, _, Ok(a)) => cmp_conditional(e, a, &mut c),
                (_, Some(_), _, Err(e)) if e.code == borsai_predict::path::CONDITIONAL_INVALID => {}
                (_, _, Some(err), Err(e)) if err["code"].as_str() == Some(e.code.as_str()) => {}
                _ => c.fail(format!(
                    "sonuç türü: beklenen {exp}, Rust {}",
                    match &act {
                        Ok(v) => v.to_string(),
                        Err(e) => format!("Err({e})"),
                    }
                )),
            }
            st.max_abs = st.max_abs.max(c.max_abs);
            for f in c.failures {
                st.failures.push(format!("{case} {label}: {f}"));
            }
        };
        for v in row["streak_ongoing"].as_array().unwrap() {
            let j = v["j"].as_u64().unwrap() as usize;
            let act = borsai_predict::path::conditional(&p, output, j, &closes(&v["closes"]));
            st.vectors += 1;
            if j == 0 {
                // j = 0 koşulsuzla bit-eşit: D{h}.return/p_up/q10/q50/q90/mean/n_atoms
                if let Ok(a) = &act {
                    for h in 1..=10 {
                        let (uc, cc) = (&output[format!("D{h}")], &a[format!("D{h}")]);
                        for f in ["return", "p_up", "q10", "q50", "q90", "mean", "n_atoms"] {
                            if uc[f] != cc[f] {
                                st.j0_bit_equal = false;
                                st.failures.push(format!("{case} j=0 D{h}.{f}: {} != {}", uc[f], cc[f]));
                            }
                        }
                    }
                }
            }
            check(format!("streak j={j}"), &v["expected"], act, &mut st);
        }
        for v in row["streak_ongoing_mismatch"].as_array().unwrap() {
            let j = v["j"].as_u64().unwrap() as usize;
            let act = borsai_predict::path::conditional(&p, output, j, &closes(&v["closes"]));
            st.vectors += 1;
            if let Ok(a) = &act {
                if a["limit_path_mismatch"] == json!(1) {
                    st.mismatch_flagged += 1;
                } else {
                    st.failures.push(format!("{case} mismatch j={j}: bayrak 1 değil"));
                }
                for h in 1..=j {
                    if a[format!("D{h}")]["status"] != json!("REALIZED") {
                        st.failures.push(format!("{case} mismatch j={j}: D{h} REALIZED değil"));
                    }
                }
            }
            check(format!("mismatch j={j}"), &v["expected"], act, &mut st);
        }
        for v in row["after_break"].as_array().unwrap() {
            let t = v["t"].as_u64().unwrap() as usize;
            let act = borsai_predict::path::conditional_after_break(&p, output, t, &closes(&v["closes"]));
            st.after_break_vectors += 1;
            check(format!("after_break t={t}"), &v["expected"], act, &mut st);
        }
        for v in row.get("invalid").and_then(Value::as_array).unwrap_or(&Vec::new()) {
            let out = v.get("output").unwrap_or(output);
            let act = if v["fn"] == json!("conditional") {
                borsai_predict::path::conditional(&p, out, v["j"].as_u64().unwrap() as usize, &closes(&v["closes"]))
            } else {
                borsai_predict::path::conditional_after_break(&p, out, v["t"].as_u64().unwrap() as usize, &closes(&v["closes"]))
            };
            st.invalid_vectors += 1;
            check(format!("invalid {}", v["case"]), &v["expected"], act, &mut st);
        }
    }
    st
}

fn conditional_json(c: Option<survival::Conditional>) -> Value {
    c.map(|c| c.to_json()).unwrap_or(Value::Null)
}

fn check_conditional(row: &Value, out: &borsai_predict::Output, st: &mut ModelStat) {
    let Some(expected) = row.get("conditional").and_then(Value::as_array) else { return };
    let borsai_predict::Output::Hazard(h) = out else {
        st.cond_failures.push(format!("{}: koşullu satır ama tavan çıktısı değil", row["case_id"]));
        return;
    };
    let s = h.s.as_ref().expect("S");
    let p_l = h.p_l.as_ref().expect("P_L");
    st.cond_rows += 1;
    for (j, exp) in expected.iter().enumerate() {
        let got = survival::conditional(s, j);
        // j = 0: koşulsuz S ile bit-eşit
        if j == 0 {
            let c0 = got.as_ref().expect("j = 0 her zaman tanımlı");
            let s_ok = c0.s_cond.iter().zip(s).all(|(a, b)| a.map(f64::to_bits) == Some(b.to_bits()));
            let pl_ok = c0.p_l_cond.iter().zip(p_l).all(|(a, b)| a.map(f64::to_bits) == Some(b.to_bits()));
            let br_ok = c0.p_break_next.to_bits() == p_l[0].to_bits();
            if !(s_ok && pl_ok && br_ok) {
                st.cond_j0_bit_equal = false;
                st.cond_failures.push(format!("{}: j = 0 koşulsuz S ile bit-eşit değil", row["case_id"]));
            }
        }
        let act = conditional_json(got);
        match (exp, &act) {
            (Value::Null, Value::Null) => st.cond_undefined += 1,
            (Value::Object(_), Value::Object(_)) => {
                st.cond_vectors += 1;
                let mut c = RowCmp::new();
                for k in ["S_cond", "P_L_cond"] {
                    let (ea, aa) = (exp[k].as_array().unwrap(), act[k].as_array().unwrap());
                    if ea.len() != aa.len() {
                        c.failures.push(format!("{k} uzunluğu"));
                        continue;
                    }
                    for (i, (x, y)) in ea.iter().zip(aa).enumerate() {
                        cmp_num(&format!("{k}[{i}]"), x, y, TOL_CONDITIONAL, &mut c);
                    }
                }
                cmp_num("p_break_next", &exp["p_break_next"], &act["p_break_next"], TOL_CONDITIONAL, &mut c);
                if exp["j"] != act["j"] {
                    c.failures.push("j".into());
                }
                st.cond_max_abs = st.cond_max_abs.max(c.max_abs);
                for f in c.failures {
                    st.cond_failures.push(format!("{} j={j}: {f}", row["case_id"]));
                }
            }
            _ => st.cond_failures.push(format!("{} j={j}: beklenen {exp}, Rust {act}", row["case_id"])),
        }
    }
}

type Runner<'a> = &'a dyn Fn(&Value, &Value) -> Result<borsai_predict::Output, borsai_predict::PredictError>;

fn run_file(model_id: &str, params: &Value, sha: &str, rows: &[Value], failures: &mut Vec<String>) -> ModelStat {
    run_file_with(model_id, params, sha, rows, failures, &run_row)
}

fn run_file_with(
    model_id: &str,
    params: &Value,
    sha: &str,
    rows: &[Value],
    failures: &mut Vec<String>,
    runner: Runner<'_>,
) -> ModelStat {
    let mut st = ModelStat { model_id: model_id.to_string(), cond_j0_bit_equal: true, ..Default::default() };
    for row in rows {
        st.rows += 1;
        assert_eq!(row["model_id"].as_str(), Some(model_id));
        assert_eq!(row["params_sha256"].as_str(), Some(sha), "{}: params_sha256", row["case_id"]);
        let params = match row.get("params_patch") {
            Some(p) => apply_patch(params, p),
            None => params.clone(),
        };
        let actual = runner(&params, row);
        let mut c = RowCmp::new();
        cmp_expected(&row["expected"], &actual, &mut c);
        match &actual {
            Ok(out) => {
                if out.refused().is_some() {
                    st.refused_rows += 1;
                }
                check_conditional(row, out, &mut st);
            }
            Err(_) => st.error_rows += 1,
        }
        st.numbers += c.n_numbers;
        st.max_abs = st.max_abs.max(c.max_abs);
        if c.failures.is_empty() {
            st.passed += 1;
            if c.bit_equal {
                st.bit_equal_rows += 1;
            }
        } else {
            for f in c.failures {
                failures.push(format!("{}: {f}", row["case_id"].as_str().unwrap_or("?")));
            }
        }
    }
    st
}

fn stat_json(s: &ModelStat) -> Value {
    json!({
        "model_id": s.model_id,
        "rows": s.rows,
        "rows_passed": s.passed,
        "max_abs_delta": s.max_abs,
        "bit_equal_rows": s.bit_equal_rows,
        "bit_equal_ratio": if s.rows > 0 { s.bit_equal_rows as f64 / s.rows as f64 } else { 0.0 },
        "numbers_compared": s.numbers,
        "refused_rows": s.refused_rows,
        "error_rows": s.error_rows,
    })
}

fn run() -> &'static Run {
    static RUN: OnceLock<Run> = OnceLock::new();
    RUN.get_or_init(|| {
        let manifest = manifest();
        let params = load_params();
        let mut failures = Vec::new();
        let mut stats = Vec::new();
        let mut path_cond = Vec::new();
        let mut passthrough = Vec::new();
        for mid in manifest["model_ids"].as_array().unwrap() {
            let mid = mid.as_str().unwrap();
            let (p, sha) = &params[mid];
            let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
            stats.push(run_file(mid, p, sha, &rows, &mut failures));
            if borsai_predict::model_kind(p) != borsai_predict::Kind::CeilingPath {
                continue;
            }
            // U45: seri bileşeni gömülü modelin bit-eşit kopyası
            let sid = p["survival_model_id"].as_str().expect("survival_model_id");
            let (sp, _) = &params[sid];
            survival_passthrough(mid, p, sp, &rows, &mut passthrough);
            // U43: koşullu karışım vektörleri
            let crows = read_jsonl(&golden_dir().join(format!("{mid}.conditional.jsonl")));
            path_cond.push(run_conditional_path(mid, p, &crows));
        }
        // D1 sonrası (EK 3 §6.4, U64): ikinci dizin; ebeveyn ceiling_hazard_v0, ikincil ceiling_path_v0
        let post_params = load_post_d1_params();
        let (parent, path) = (params["ceiling_hazard_v0"].0.clone(), params["ceiling_path_v0"].0.clone());
        let post_runner = |p: &Value, row: &Value| run_post_d1_row(p, &parent, &path, row);
        let mut post_stats = Vec::new();
        for mid in post_d1_ids() {
            let (p, sha) = &post_params[&mid];
            let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
            post_stats.push(run_file_with(&mid, p, sha, &rows, &mut failures, &post_runner));
        }
        // yamalı parametreler (F3_FILTER_STATUS_CONFLICT, PARAMS_INVALID, SCHEMA_UNSUPPORTED; D1 sonrası +8)
        let prow = read_jsonl(&golden_dir().join("_patched_params.jsonl"));
        let mut patched = ModelStat { model_id: "_patched_params".into(), cond_j0_bit_equal: true, ..Default::default() };
        for row in &prow {
            let mid = row["model_id"].as_str().unwrap();
            let s = match post_params.get(mid) {
                Some((p, sha)) => run_file_with(mid, p, sha, std::slice::from_ref(row), &mut failures, &post_runner),
                None => {
                    let (p, sha) = &params[mid];
                    run_file(mid, p, sha, std::slice::from_ref(row), &mut failures)
                }
            };
            patched.rows += s.rows;
            patched.passed += s.passed;
            patched.bit_equal_rows += s.bit_equal_rows;
            patched.max_abs = patched.max_abs.max(s.max_abs);
            patched.refused_rows += s.refused_rows;
            patched.error_rows += s.error_rows;
            patched.numbers += s.numbers;
        }
        let cond: Vec<Value> = stats
            .iter()
            .filter(|s| s.cond_rows > 0)
            .map(|s| {
                json!({
                    "model_id": s.model_id,
                    "rows": s.cond_rows,
                    "vectors_j0_9": s.cond_vectors,
                    "undefined": s.cond_undefined,
                    "max_abs_delta": s.cond_max_abs,
                    "j0_bit_equal_to_unconditional": s.cond_j0_bit_equal,
                    "failures": s.cond_failures.len(),
                })
            })
            .collect();
        let total_rows: usize = stats.iter().map(|s| s.rows).sum();
        let total_bit: usize = stats.iter().map(|s| s.bit_equal_rows).sum();
        let max_abs = stats.iter().map(|s| s.max_abs).fold(0.0, f64::max);
        let report = json!({
            "schema_version": "borsai.app_parity_report/1",
            "generated_by": "cargo test -p borsai_predict --test golden",
            "tolerance_abs": TOL,
            "golden": {
                "seed": manifest["seed"],
                "models_index_sha256": manifest["models_index_sha256"],
                "predict_sources_sha256": manifest["predict_sources_sha256"],
            },
            "models": stats.iter().map(stat_json).collect::<Vec<_>>(),
            "post_d1": {
                "models_index_post_d1_sha256": manifest["models_index_post_d1_sha256"],
                "tolerance_abs": TOL,
                "tolerance_conditional_j1": TOL_CONDITIONAL,
                "models": post_stats.iter().map(stat_json).collect::<Vec<_>>(),
            },
            "patched_params": stat_json(&patched),
            "conditional": {
                "tolerance_abs": TOL_CONDITIONAL,
                "j_range": "0..10 (10 = tanımsız)",
                "models": cond,
                "ceiling_path": path_cond.iter().map(|s| json!({
                    "model_id": s.model_id,
                    "base_rows": s.base_rows,
                    "vectors": s.vectors,
                    "after_break_vectors": s.after_break_vectors,
                    "invalid_vectors": s.invalid_vectors,
                    "max_abs_delta": s.max_abs,
                    "j0_bit_equal_to_unconditional": s.j0_bit_equal,
                    "mismatch_flagged": s.mismatch_flagged,
                    "failures": s.failures.len(),
                })).collect::<Vec<_>>(),
            },
            "survival_passthrough_failures": passthrough.len(),
            "totals": {
                "models": stats.len(),
                "models_passing": stats.iter().filter(|s| s.passed == s.rows).count(),
                "rows": total_rows,
                "bit_equal_rows": total_bit,
                "bit_equal_ratio": total_bit as f64 / total_rows as f64,
                "max_abs_delta": max_abs,
                "failures": failures.len(),
            },
            "failures_first_50": failures.iter().take(50).collect::<Vec<_>>(),
        });
        let path = target_dir().join("parity_report.json");
        std::fs::write(&path, serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
        eprintln!("parite raporu: {}", path.display());
        Run { stats, post_stats, patched, path_cond, passthrough, failures, report }
    })
}

/// Sabit model kümesi (SPEC_APP EK 3 §4.1): INDEX'in 27 kaydı; 20.–23. Faz 7 v1 ailesi, son dördü Faz 7C düşen arz (P4).
const N_MODELS: usize = 27;
const V1_IDS: [&str; 4] =
    ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"];
const FALL_IDS: [&str; 4] = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"];

/// U1 + U42 + U53 + U77 (Rust tarafı): 27 model için altın dosya var (≥ 200 satır; tavan yolu ≥ 450; v1 ≥ 600;
/// (C) ≥ 560), model kümesi INDEX'in 27 kaydı, üç koşullu dosya 40 taban satır.
#[test]
fn golden_files_present() {
    let m = manifest();
    let ids: Vec<&str> = m["model_ids"].as_array().unwrap().iter().map(|v| v.as_str().unwrap()).collect();
    assert_eq!(ids.len(), N_MODELS, "sabit model kümesi 27 model");
    let idx: Vec<String> = index_entries(N_MODELS).into_iter().map(|e| e.0).collect();
    assert_eq!(ids, idx.iter().map(String::as_str).collect::<Vec<_>>(), "MANIFEST model kümesi INDEX'in 27 kaydı değil");
    assert_eq!(&ids[19..23], V1_IDS, "20.–23. kayıtlar Faz 7 v1 ailesi");
    assert_eq!(&ids[23..], FALL_IDS, "son dört kayıt Faz 7C düşen arz ailesi");
    let params = load_params();
    let mut path_files = 0usize;
    for mid in &ids {
        let rows = read_jsonl(&golden_dir().join(format!("{mid}.jsonl")));
        assert!(rows.len() >= 200, "{mid}: {} satır (< 200)", rows.len());
        if V1_IDS.contains(mid) {
            assert!(rows.len() >= 600, "{mid}: {} satır (v1 ≥ 600)", rows.len());
        }
        if FALL_IDS.contains(mid) {
            assert!(rows.len() >= 560, "{mid}: {} satır ((C) ≥ 560)", rows.len());
        }
        if borsai_predict::model_kind(&params[*mid].0) != borsai_predict::Kind::CeilingPath {
            continue;
        }
        path_files += 1;
        assert!(rows.len() >= 450, "{mid}: {} satır (tavan yolu ≥ 450)", rows.len());
        let crows = read_jsonl(&golden_dir().join(format!("{mid}.conditional.jsonl")));
        assert_eq!(crows.len(), 40, "{mid}: koşullu taban satır sayısı");
        assert_eq!(m["conditional_rows"][*mid], json!(crows.len()));
    }
    assert_eq!(path_files, 3, "üç tavan yolu modeli");
}

/// Portun tanımı değişmedi: MANIFEST'teki Python kaynak sha'ları diskteki dosyalarla aynı.
#[test]
fn predict_sources_unchanged() {
    let m = manifest();
    for (path, sha) in m["predict_sources_sha256"].as_object().unwrap() {
        let got = sha256_hex(&std::fs::read(repo_dir().join(path)).unwrap());
        assert_eq!(&got, sha.as_str().unwrap(), "{path} değişmiş: altın vektörleri yeniden üret (gen_golden.py) ve Rust'ı uyumla");
    }
}

/// U2 + U53 + U77: bütün satırlarda §1.3 karşılaştırması (sayısal |Δ| ≤ 1e-9; ret kodu+alan; uyarı çok kümesi;
/// direction/return_clipped/clipped birebir; v1 alanları EK 3 §2.7; (C) `add_sale_used` birebir, `return*` null) ve 27/27 model.
#[test]
fn golden_parity() {
    let r = run();
    for s in &r.stats {
        eprintln!(
            "{:<24} satır {:>4}  geçen {:>4}  bit-eşit {:>4} ({:.4})  maks |Δ| {:e}",
            s.model_id,
            s.rows,
            s.passed,
            s.bit_equal_rows,
            s.bit_equal_rows as f64 / s.rows as f64,
            s.max_abs
        );
    }
    assert!(r.failures.is_empty(), "{} uyuşmazlık; ilk 20:\n{}", r.failures.len(), r.failures.iter().take(20).cloned().collect::<Vec<_>>().join("\n"));
    assert_eq!(r.stats.len(), N_MODELS);
    assert!(r.stats.iter().all(|s| s.passed == s.rows && s.max_abs <= TOL));
    assert_eq!(r.patched.passed, r.patched.rows);
    assert_eq!(r.report["totals"]["models_passing"], json!(N_MODELS));

    // B10: tolerans (1e-9) içindeki sessiz sürüklenme. Model başına bit-eşit satır sayısı
    // `app/parity/bit_equal_floor.json` tabanından az olamaz; tabanı olmayan model KIRMIZIDIR (yeni
    // model eklenince taban bilerek yazılır), koşuda olmayan taban girdisi de.
    // FAZ9_WINDOWS K-WIN-5: taban macOS'ta ölçüldü; Windows libm'i exp/ln/powi'de son basamakta farklıdır. Orada taban
    // denetlenmez; model başına bit-eşit satır sayısı ve maks |Δ| yukarıda basılır (rapora yazılır), 1e-9 her sistemde.
    if !cfg!(target_os = "macos") {
        return;
    }
    let floor_doc = read_json(&app_dir().join("parity").join("bit_equal_floor.json"));
    let floor = floor_doc["bit_equal_rows"].as_object().expect("bit_equal_floor.json: bit_equal_rows");
    let mut drift = Vec::new();
    for s in r.stats.iter().chain(&r.post_stats) {
        match floor.get(&s.model_id).and_then(Value::as_u64) {
            None => drift.push(format!("{}: tabanı yok (app/parity/bit_equal_floor.json'a bilerek yazılır)", s.model_id)),
            Some(f) if (s.bit_equal_rows as u64) < f => {
                drift.push(format!("{}: bit-eşit satır {} < taban {} (tolerans içi sürüklenme)", s.model_id, s.bit_equal_rows, f))
            }
            Some(_) => {}
        }
    }
    for id in floor.keys().filter(|id| !r.stats.iter().chain(&r.post_stats).any(|s| &s.model_id == *id)) {
        drift.push(format!("{id}: tabanda var, koşuda yok"));
    }
    assert!(drift.is_empty(), "bit-eşitlik tabanı:\n{}", drift.join("\n"));
}

/// U64 (EK 3 §6.3–§6.4): `post_d1_hazard_v0` paritesi. Altın dosya ≥ 220 satır; §6.3 kuralları (`conditional_j1` ve
/// `path_conditional` koşullu değerleri |Δ| ≤ 1e-12, `d1_turnover_ratio` metni birebir, sayılar ≤ 1e-9); yamalı 8 satır
/// ilk hata koduyla; bit-eşitlik tabanı (`bit_equal_floor.json`) golden_parity'de.
#[test]
fn post_d1_parity() {
    let r = run();
    let m = manifest();
    assert_eq!(post_d1_ids(), ["post_d1_hazard_v0"], "PINNED_POST_D1_MODEL_IDS");
    let idx = read_json(&repo_dir().join("models").join("INDEX_POST_D1.json"));
    assert_eq!(m["models_index_post_d1_sha256"].as_str(), Some(sha256_hex(&std::fs::read(repo_dir().join("models").join("INDEX_POST_D1.json")).unwrap()).as_str()));
    assert_eq!(idx["models"].as_array().unwrap().len(), 1);
    assert_eq!(r.post_stats.len(), 1);
    for s in &r.post_stats {
        eprintln!(
            "{:<24} satır {:>4}  geçen {:>4}  bit-eşit {:>4} ({:.4})  maks |Δ| {:e}  ret {}  hata {}",
            s.model_id,
            s.rows,
            s.passed,
            s.bit_equal_rows,
            s.bit_equal_rows as f64 / s.rows as f64,
            s.max_abs,
            s.refused_rows,
            s.error_rows
        );
        assert!(s.rows >= 220, "{}: {} satır (≥ 220)", s.model_id, s.rows);
        assert_eq!(m["post_d1_rows"][&s.model_id], json!(s.rows));
        assert_eq!(s.passed, s.rows, "{}: {} uyuşmazlık", s.model_id, s.rows - s.passed);
        assert!(s.max_abs <= TOL, "{}: maks |Δ| {}", s.model_id, s.max_abs);
    }
    assert!(r.failures.is_empty(), "{:?}", &r.failures[..r.failures.len().min(20)]);
    // yamalı 8 satır: ilk hata kodu (PARAMS_INVALID × 7, SCHEMA_UNSUPPORTED × 1)
    let prow: Vec<Value> = read_jsonl(&golden_dir().join("_patched_params.jsonl"))
        .into_iter()
        .filter(|row| row["model_id"] == json!("post_d1_hazard_v0"))
        .collect();
    assert_eq!(prow.len(), 8, "D1 sonrası yamalı satır");
    let codes: Vec<&str> = prow.iter().map(|row| row["expected"]["error"]["code"].as_str().unwrap()).collect();
    assert_eq!(codes.iter().filter(|c| **c == "PARAMS_INVALID").count(), 7);
    assert_eq!(codes.iter().filter(|c| **c == "SCHEMA_UNSUPPORTED").count(), 1);
    assert_eq!(r.patched.passed, r.patched.rows);
}

/// U77 (EK 3 §8.3): dört (C) dosyası ≥ 560 satır, `p_up` |Δ| ≤ 1e-9 (beklenti bit-eşit), `direction` ve `add_sale_used`
/// birebir, `return*`/`price` null ↔ null; yamalı 10 satır (dosyanın sonunda): PARAMS_INVALID × 7, SCHEMA_UNSUPPORTED × 1,
/// F3_FILTER_STATUS_CONFLICT reddi × 1, çelişkisiz tahmin × 1.
#[test]
fn fall_parity() {
    let r = run();
    let m = manifest();
    assert_eq!(m["fall_model_ids"], json!(FALL_IDS));
    for id in FALL_IDS {
        let s = r.stats.iter().find(|s| s.model_id == id).expect("(C) modeli koşuda");
        eprintln!(
            "{:<26} satır {:>4}  geçen {:>4}  bit-eşit {:>4} ({:.4})  maks |Δ| {:e}  ret {}  hata {}",
            s.model_id, s.rows, s.passed, s.bit_equal_rows, s.bit_equal_rows as f64 / s.rows as f64, s.max_abs, s.refused_rows, s.error_rows
        );
        assert!(s.rows >= 560, "{id}: {} satır", s.rows);
        assert_eq!(s.passed, s.rows, "{id}: {} uyuşmazlık", s.rows - s.passed);
        assert!(s.max_abs <= TOL, "{id}: maks |Δ| {}", s.max_abs);
    }
    let prow: Vec<Value> = read_jsonl(&golden_dir().join("_patched_params.jsonl"));
    let fall: Vec<&Value> = prow.iter().filter(|row| FALL_IDS.contains(&row["model_id"].as_str().unwrap())).collect();
    assert_eq!(fall.len(), 10, "(C) yamalı satır");
    assert!(prow[prow.len() - 10..].iter().all(|row| FALL_IDS.contains(&row["model_id"].as_str().unwrap())), "(C) yamalı satırlar sonda");
    let codes: Vec<String> = fall
        .iter()
        .map(|row| {
            let e = &row["expected"];
            e["error"]["code"].as_str().or(e["output"]["refused"]["code"].as_str()).unwrap_or("PREDICTED").to_string()
        })
        .collect();
    let n = |c: &str| codes.iter().filter(|x| *x == c).count();
    assert_eq!((n("PARAMS_INVALID"), n("SCHEMA_UNSUPPORTED"), n("F3_FILTER_STATUS_CONFLICT"), n("PREDICTED")), (7, 1, 1, 1), "{codes:?}");
    assert_eq!(r.patched.passed, r.patched.rows);
}

/// U43: tavan yolu koşullu karışım paritesi (durum 1, sapma, durum 2, ön koşul ihlalleri).
#[test]
fn conditional_path_parity() {
    let r = run();
    assert_eq!(r.path_cond.len(), 3, "üç tavan yolu modeli");
    for s in &r.path_cond {
        eprintln!(
            "{:<24} taban {:>3}  durum1+sapma {:>4}  durum2 {:>4}  ihlal {:>2}  maks |Δ| {:e}",
            s.model_id, s.base_rows, s.vectors, s.after_break_vectors, s.invalid_vectors, s.max_abs
        );
        assert!(s.failures.is_empty(), "{}: {:?}", s.model_id, &s.failures[..s.failures.len().min(10)]);
        assert_eq!(s.base_rows, 40, "{}: 40 taban satır", s.model_id);
        assert_eq!(s.vectors, 40 * 13, "{}: 10 j + 3 sapma vektörü", s.model_id);
        assert_eq!(s.after_break_vectors, 40 * 10, "{}: t = 0..9", s.model_id);
        assert_eq!(s.invalid_vectors, 5, "{}: ön koşul ihlalleri", s.model_id);
        assert_eq!(s.mismatch_flagged, 3 * 40, "{}: sapma satırlarında bayrak 1", s.model_id);
        assert!(s.j0_bit_equal, "{}: j = 0 koşulsuzla bit-eşit değil", s.model_id);
        assert!(s.max_abs <= TOL, "{}: maks |Δ| {}", s.model_id, s.max_abs);
    }
}

/// U45: `ceiling_path` S/hazard/P_L/P_close_ceiling ve ret kodları gömülü seri modeliyle bit-eşit.
#[test]
fn survival_passthrough_bit_equal() {
    let r = run();
    assert!(r.passthrough.is_empty(), "{:?}", &r.passthrough[..r.passthrough.len().min(10)]);
    assert_eq!(r.report["survival_passthrough_failures"], json!(0));
}

/// U37: j = 0..9 koşullu vektörler |Δ| ≤ 1e-12; j = 0 bit-eşit; S_j = 0 ve j ≥ 10 tanımsız.
#[test]
fn conditional_parity() {
    let r = run();
    let cond: Vec<&ModelStat> = r.stats.iter().filter(|s| s.cond_rows > 0).collect();
    assert_eq!(cond.len(), 10, "10 tavan modeli (hazard + km; 4'ü Faz 7 v1)");
    for s in cond {
        assert!(s.cond_failures.is_empty(), "{}: {:?}", s.model_id, &s.cond_failures[..s.cond_failures.len().min(10)]);
        assert!(s.cond_j0_bit_equal, "{}: j = 0 bit-eşit değil", s.model_id);
        assert!(s.cond_max_abs <= TOL_CONDITIONAL, "{}: maks |Δ| {}", s.model_id, s.cond_max_abs);
        assert!(s.cond_undefined >= s.cond_rows, "{}: j = 10 her satırda tanımsız olmalı", s.model_id);
    }
}

/// Karşılaştırıcının kendisi: bozulmuş beklenen değerler yakalanır (sayı 1e-8, ret kodu/alanı,
/// uyarı çok kümesi, yön, sonlu olmayan değer, hata türü).
#[test]
fn comparator_detects_mismatch() {
    let params = load_params();
    let rows = read_jsonl(&golden_dir().join("v1_5_h99.jsonl"));
    let (p, _) = &params["v1_5_h99"];
    let ok_row = rows.iter().find(|r| r["expected"]["output"]["refused"].is_null() && !r["expected"]["output"]["warnings"].as_array().unwrap().is_empty()).unwrap();
    let refused_row = rows.iter().find(|r| r["expected"]["output"]["refused"].is_object()).unwrap();
    let actual_ok = run_row(p, ok_row);
    let actual_ref = run_row(p, refused_row);
    let fails = |exp: &Value, act: &Result<borsai_predict::Output, borsai_predict::PredictError>| {
        let mut c = RowCmp::new();
        cmp_expected(exp, act, &mut c);
        !c.failures.is_empty()
    };
    assert!(!fails(&ok_row["expected"], &actual_ok));
    let mut e = ok_row["expected"].clone();
    let v = e["output"]["D5"]["p_up"].as_f64().unwrap();
    e["output"]["D5"]["p_up"] = json!(v + 1e-8);
    assert!(fails(&e, &actual_ok), "1e-8 sayısal fark yakalanmalı");
    let mut e = ok_row["expected"].clone();
    e["output"]["D1"]["direction"] = json!(if e["output"]["D1"]["direction"] == json!("UP") { "DOWN" } else { "UP" });
    assert!(fails(&e, &actual_ok), "yön farkı yakalanmalı");
    let mut e = ok_row["expected"].clone();
    e["output"]["warnings"].as_array_mut().unwrap().pop();
    assert!(fails(&e, &actual_ok), "eksik uyarı yakalanmalı");
    let mut e = ok_row["expected"].clone();
    e["output"]["D10"]["return"] = json!("NaN");
    assert!(fails(&e, &actual_ok), "NaN ↔ sayı yakalanmalı");
    let mut e = refused_row["expected"].clone();
    e["output"]["refused"]["field"] = json!("başka_alan");
    assert!(fails(&e, &actual_ref), "ret alanı farkı yakalanmalı");
    let mut e = refused_row["expected"].clone();
    e["output"]["refused"]["code"] = json!("INPUT_MISSING_X");
    assert!(fails(&e, &actual_ref), "ret kodu farkı yakalanmalı");
    assert!(fails(&json!({"error": {"code": "PARAMS_INVALID"}}), &actual_ok), "hata ↔ çıktı yakalanmalı");
    assert!(fails(&json!({"exception": "ValueError"}), &actual_ok), "istisna ↔ çıktı yakalanmalı");
}
