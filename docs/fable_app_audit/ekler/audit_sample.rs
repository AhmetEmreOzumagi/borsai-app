//! FAZ3_FABLE_APP_AUDIT adım 4: bağımsız parite örneklemi. Satırlar /tmp/borsai_app_audit/sample.jsonl
//! (gen_sample.py, gen_golden.py KULLANILMADI). Karşılaştırma common::cmp_expected (§1.3 kuralları).
mod common;

use common::*;
use serde_json::{json, Value};
use std::collections::BTreeMap;

#[test]
fn audit_sample_parity() {
    let path = std::env::var("AUDIT_SAMPLE").expect("AUDIT_SAMPLE");
    let report_path = std::env::var("AUDIT_REPORT").expect("AUDIT_REPORT");
    let rows = read_jsonl(std::path::Path::new(&path));
    let params = load_params();
    let mut per: BTreeMap<String, (usize, usize, f64, usize, usize)> = BTreeMap::new(); // rows, passed, max_abs, bit_equal, numbers
    let mut failures: Vec<String> = Vec::new();
    let mut max_abs = 0.0f64;
    let mut case_ids = std::collections::BTreeSet::new();
    for row in &rows {
        let mid = row["model_id"].as_str().unwrap();
        case_ids.insert(row["case_id"].as_str().unwrap().split_once('/').map(|x| x.1.to_string()).unwrap_or_default());
        let (p, sha) = &params[mid];
        assert_eq!(row["params_sha256"].as_str(), Some(sha.as_str()));
        let actual = run_row(p, row);
        let mut c = RowCmp::new();
        cmp_expected(&row["expected"], &actual, &mut c);
        let e = per.entry(mid.to_string()).or_insert((0, 0, 0.0, 0, 0));
        e.0 += 1;
        e.4 += c.n_numbers;
        if c.max_abs > e.2 {
            e.2 = c.max_abs;
        }
        if c.max_abs > max_abs {
            max_abs = c.max_abs;
        }
        if c.failures.is_empty() {
            e.1 += 1;
            if c.bit_equal {
                e.3 += 1;
            }
        } else {
            for f in c.failures {
                failures.push(format!("{}: {f}", row["case_id"]));
            }
        }
    }
    let models: Vec<Value> = per
        .iter()
        .map(|(m, (r, p, mx, b, n))| json!({"model_id": m, "rows": r, "passed": p, "max_abs_delta": mx, "bit_equal_rows": b, "numbers": n}))
        .collect();
    let report = json!({
        "sample": path,
        "n_cases": case_ids.len(),
        "n_models": per.len(),
        "rows": rows.len(),
        "max_abs_delta": max_abs,
        "failures": failures.len(),
        "failures_first_50": failures.iter().take(50).collect::<Vec<_>>(),
        "models": models,
    });
    std::fs::write(&report_path, serde_json::to_string_pretty(&report).unwrap() + "\n").unwrap();
    eprintln!("{}", serde_json::to_string_pretty(&report).unwrap());
    assert!(failures.is_empty(), "{} uyuşmazlık", failures.len());
    assert!(max_abs <= TOL);
}
