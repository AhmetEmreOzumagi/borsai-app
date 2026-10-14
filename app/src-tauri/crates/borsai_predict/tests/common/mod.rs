//! Parite testlerinin ortak kodu: yollar, altın satırlar, SPEC_APP §1.3 karşılaştırma kuralları.
#![allow(dead_code)]

use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

pub const TOL: f64 = 1e-9;
pub const TOL_CONDITIONAL: f64 = 1e-12;

pub fn crate_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// app/
pub fn app_dir() -> PathBuf {
    crate_dir().join("../../..").canonicalize().unwrap()
}

/// Repo kökü (app/..).
pub fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

pub fn golden_dir() -> PathBuf {
    app_dir().join("parity").join("golden")
}

/// Çalışma alanının target dizini (CARGO_TARGET_TMPDIR = <target>/tmp).
pub fn target_dir() -> PathBuf {
    Path::new(env!("CARGO_TARGET_TMPDIR")).parent().unwrap().to_path_buf()
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

pub fn read_json(path: &Path) -> Value {
    let bytes = std::fs::read(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    serde_json::from_slice(&bytes).unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

pub fn read_jsonl(path: &Path) -> Vec<Value> {
    let text = std::fs::read_to_string(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap_or_else(|e| panic!("{}: {e}", path.display())))
        .collect()
}

pub fn manifest() -> Value {
    read_json(&golden_dir().join("MANIFEST.json"))
}

/// INDEX'in ilk n kaydı: (model_id, dosya, sha256).
pub fn index_entries(n: usize) -> Vec<(String, String, String)> {
    let idx = read_json(&repo_dir().join("models").join("INDEX.json"));
    idx["models"].as_array().unwrap()[..n]
        .iter()
        .map(|e| {
            (
                e["model_id"].as_str().unwrap().to_string(),
                e["file"].as_str().unwrap().to_string(),
                e["sha256"].as_str().unwrap().to_string(),
            )
        })
        .collect()
}

/// Model parametreleri (repo models/, sha INDEX ile doğrulanmış).
pub fn load_params() -> BTreeMap<String, (Value, String)> {
    let ids: Vec<String> =
        manifest()["model_ids"].as_array().unwrap().iter().map(|v| v.as_str().unwrap().to_string()).collect();
    let mut out = BTreeMap::new();
    for (mid, file, sha) in index_entries(ids.len()) {
        let bytes = std::fs::read(repo_dir().join("models").join(&file)).unwrap();
        assert_eq!(sha256_hex(&bytes), sha, "{mid}: model dosyası sha256 INDEX ile uyuşmuyor");
        out.insert(mid, (serde_json::from_slice(&bytes).unwrap(), sha));
    }
    out
}

/// İkinci dizin (`models/INDEX_POST_D1.json`; EK 3 §6.4): model_id → (parametreler, sha256), sha dizinle doğrulanmış.
pub fn load_post_d1_params() -> BTreeMap<String, (Value, String)> {
    let idx = read_json(&repo_dir().join("models").join("INDEX_POST_D1.json"));
    let mut out = BTreeMap::new();
    for e in idx["models"].as_array().unwrap() {
        let (mid, file, sha) = (e["model_id"].as_str().unwrap(), e["file"].as_str().unwrap(), e["sha256"].as_str().unwrap());
        let bytes = std::fs::read(repo_dir().join("models").join(file)).unwrap();
        assert_eq!(sha256_hex(&bytes), sha, "{mid}: model dosyası sha256 INDEX_POST_D1 ile uyuşmuyor");
        out.insert(mid.to_string(), (serde_json::from_slice(&bytes).unwrap(), sha.to_string()));
    }
    out
}

/// MANIFEST'in D1 sonrası model kümesi (`PINNED_POST_D1_MODEL_IDS`).
pub fn post_d1_ids() -> Vec<String> {
    manifest()["post_d1_model_ids"].as_array().map(|a| a.iter().map(|v| v.as_str().unwrap().to_string()).collect()).unwrap_or_default()
}

/// D1 sonrası satırı Rust'ta: ebeveyn `ceiling_hazard_v0`; `path_params: true` ise `ceiling_path_v0` (EK 3 §6.4).
pub fn run_post_d1_row(
    params: &Value,
    parent: &Value,
    path: &Value,
    row: &Value,
) -> Result<borsai_predict::Output, borsai_predict::PredictError> {
    let inputs = call_inputs(row);
    let with_path = row["path_params"].as_bool().unwrap_or(true);
    borsai_predict::post_d1::predict(params, parent, &inputs, &row["d1"], with_path.then_some(path)).map(borsai_predict::Output::PostD1)
}

/// Satırın çağrı girdisi: `{**inputs, **extra}`.
pub fn call_inputs(row: &Value) -> Map<String, Value> {
    let mut m = row["inputs"].as_object().cloned().unwrap_or_default();
    if let Some(extra) = row.get("extra").and_then(Value::as_object) {
        for (k, v) in extra {
            m.insert(k.clone(), v.clone());
        }
    }
    m
}

/// `params_patch`: [[yol, değer], ...]
pub fn apply_patch(params: &Value, patch: &Value) -> Value {
    let mut p = params.clone();
    for item in patch.as_array().unwrap() {
        let path = item[0].as_array().unwrap();
        let value = item[1].clone();
        let mut node = &mut p;
        for k in &path[..path.len() - 1] {
            node = match k {
                Value::String(s) => node.get_mut(s.as_str()).unwrap(),
                Value::Number(n) => node.get_mut(n.as_u64().unwrap() as usize).unwrap(),
                _ => panic!("yol öğesi"),
            };
        }
        match &path[path.len() - 1] {
            Value::String(s) => {
                node.as_object_mut().unwrap().insert(s.clone(), value);
            }
            Value::Number(n) => node[n.as_u64().unwrap() as usize] = value,
            _ => panic!("yol öğesi"),
        }
    }
    p
}

// ---------------------------------------------------------------- karşılaştırma (SPEC_APP §1.3)

#[derive(Debug, Default, Clone)]
pub struct RowCmp {
    pub max_abs: f64,
    pub bit_equal: bool,
    pub n_numbers: usize,
    pub failures: Vec<String>,
}

impl RowCmp {
    pub fn new() -> Self {
        RowCmp { max_abs: 0.0, bit_equal: true, n_numbers: 0, failures: Vec::new() }
    }
    pub fn fail(&mut self, msg: String) {
        self.bit_equal = false;
        self.failures.push(msg);
    }
}

fn nonfinite(s: &str) -> bool {
    matches!(s, "NaN" | "Infinity" | "-Infinity")
}

/// Sayısal alan: null ↔ null, sonlu olmayan metin birebir, sayılar |Δ| ≤ tol.
pub fn cmp_num(path: &str, exp: &Value, act: &Value, tol: f64, c: &mut RowCmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::String(a), Value::String(b)) if nonfinite(a) && a == b => c.n_numbers += 1,
        (Value::Number(a), Value::Number(b)) => {
            let (x, y) = (a.as_f64().unwrap(), b.as_f64().unwrap());
            c.n_numbers += 1;
            let d = (x - y).abs();
            if d > c.max_abs {
                c.max_abs = d;
            }
            if x.to_bits() != y.to_bits() {
                c.bit_equal = false;
            }
            if !(d <= tol) {
                c.fail(format!("{path}: beklenen {x:?}, Rust {y:?}, |Δ| = {d:e}"));
            }
        }
        _ => c.fail(format!("{path}: beklenen {exp}, Rust {act}")),
    }
}

fn cmp_exact(path: &str, exp: &Value, act: &Value, c: &mut RowCmp) {
    if exp != act {
        c.fail(format!("{path}: beklenen {exp}, Rust {act}"));
    }
}

fn cmp_num_array(path: &str, exp: &Value, act: &Value, tol: f64, c: &mut RowCmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::Array(a), Value::Array(b)) if a.len() == b.len() => {
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                cmp_num(&format!("{path}[{i}]"), x, y, tol, c);
            }
        }
        _ => c.fail(format!("{path}: beklenen {exp}, Rust {act}")),
    }
}

fn warning_key(w: &Value) -> (String, String) {
    let code = w["code"].as_str().unwrap_or("").to_string();
    let key = w
        .get("feature")
        .or_else(|| w.get("horizon"))
        .or_else(|| w.get("field"))
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    (code, key)
}

/// Uyarılar: (kod, özellik|ufuk) çok kümesi eşit; sıra ve `message` karşılaştırılmaz; sayısal alanlar |Δ| ≤ tol.
fn cmp_warnings(exp: &Value, act: &Value, c: &mut RowCmp) {
    let (Some(ea), Some(aa)) = (exp.as_array(), act.as_array()) else {
        return c.fail(format!("warnings: beklenen {exp}, Rust {act}"));
    };
    let mut groups_e: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    let mut groups_a: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    for w in ea {
        groups_e.entry(warning_key(w)).or_default().push(w);
    }
    for w in aa {
        groups_a.entry(warning_key(w)).or_default().push(w);
    }
    let ke: Vec<_> = groups_e.iter().map(|(k, v)| (k.clone(), v.len())).collect();
    let ka: Vec<_> = groups_a.iter().map(|(k, v)| (k.clone(), v.len())).collect();
    if ke != ka {
        return c.fail(format!("warnings çok kümesi: beklenen {ke:?}, Rust {ka:?}"));
    }
    for (k, ws) in &groups_e {
        for (i, (we, wa)) in ws.iter().zip(&groups_a[k]).enumerate() {
            let extra_e: Vec<&String> = we.as_object().unwrap().keys().filter(|x| *x != "message").collect();
            let extra_a: Vec<&String> = wa.as_object().unwrap().keys().filter(|x| *x != "message").collect();
            let mut se = extra_e.clone();
            let mut sa = extra_a.clone();
            se.sort();
            sa.sort();
            if se != sa {
                c.fail(format!("warning {k:?}#{i} alanları: beklenen {se:?}, Rust {sa:?}"));
                continue;
            }
            // sayısal alanlar |Δ| ≤ 1e-9; METİN alanlar (field, value, snapped, tick) birebir (§3.3)
            for f in se {
                if f == "code" {
                    continue;
                }
                let path = format!("warning {}:{}.{f}", k.0, k.1);
                let (a, b) = (&we[f], &wa[f]);
                // metin ve mantıksal alanlar (D1: `bool_fields`) birebir
                if a.is_string() || b.is_string() || a.is_boolean() || b.is_boolean() {
                    cmp_exact(&path, a, b, c);
                } else {
                    cmp_num(&path, a, b, TOL, c);
                }
            }
        }
    }
}

const CELL_NUMS: [&str; 4] = ["return", "return_unclipped", "price", "p_up"];
const CELL_EXACT: [&str; 2] = ["return_clipped", "direction"];
/// `ceiling_path` D-hücresinde toleranslı alanlar; kalanlar (`status`, `n_atoms`, `post_break`) birebir.
pub const PATH_CELL_NUMS: [&str; 10] = [
    "return", "p_up", "mean", "q10", "q50", "q90", "limit_path_return", "S_h", "p_limit_path", "realized_return",
];

/// `ceiling_path` D-hücresi (koşulsuz ve koşullu): anahtar kümesi eşit; sayı |Δ| ≤ tol, kalan birebir.
pub fn cmp_path_cell(h: &str, exp: &Value, act: &Value, c: &mut RowCmp) {
    let (Some(eo), Some(ao)) = (exp.as_object(), act.as_object()) else {
        return c.fail(format!("{h}: beklenen {exp}, Rust {act}"));
    };
    let mut ke: Vec<&String> = eo.keys().collect();
    let mut ka: Vec<&String> = ao.keys().collect();
    ke.sort();
    ka.sort();
    if ke != ka {
        return c.fail(format!("{h} anahtarları: beklenen {ke:?}, Rust {ka:?}"));
    }
    for k in ke {
        let path = format!("{h}.{k}");
        if PATH_CELL_NUMS.contains(&k.as_str()) {
            cmp_num(&path, &eo[k], &ao[k], TOL, c);
        } else {
            cmp_exact(&path, &eo[k], &ao[k], c);
        }
    }
}

/// Koşullu güncelleme çıktısı (§3.3): üst alanlar birebir, `S_j`/`S_cond`/`P_L_cond` ≤ 1e-12,
/// D-hücreleri D kurallarıyla.
pub fn cmp_conditional(exp: &Value, act: &Value, c: &mut RowCmp) {
    let (Some(eo), Some(ao)) = (exp.as_object(), act.as_object()) else {
        return c.fail(format!("koşullu: beklenen {exp}, Rust {act}"));
    };
    let mut ke: Vec<&String> = eo.keys().collect();
    let mut ka: Vec<&String> = ao.keys().collect();
    ke.sort();
    ka.sort();
    if ke != ka {
        return c.fail(format!("koşullu anahtarlar: beklenen {ke:?}, Rust {ka:?}"));
    }
    for (k, ev) in eo {
        let av = &ao[k];
        match k.as_str() {
            "state" | "j" | "t" | "note" | "limit_path_mismatch" => cmp_exact(k, ev, av, c),
            "S_j" => cmp_num(k, ev, av, TOL_CONDITIONAL, c),
            "S_cond" | "P_L_cond" => {
                let (Some(e), Some(a)) = (ev.as_object(), av.as_object()) else {
                    c.fail(format!("{k}: beklenen {ev}, Rust {av}"));
                    continue;
                };
                let (mut kes, mut kas): (Vec<&String>, Vec<&String>) = (e.keys().collect(), a.keys().collect());
                kes.sort();
                kas.sort();
                if kes != kas {
                    c.fail(format!("{k} anahtarları: beklenen {kes:?}, Rust {kas:?}"));
                    continue;
                }
                for key in kes {
                    cmp_num(&format!("{k}[{key}]"), &e[key], &a[key], TOL_CONDITIONAL, c);
                }
            }
            h => cmp_path_cell(h, ev, av, c),
        }
    }
}

fn sorted_keys(v: &Value) -> Vec<&String> {
    let mut k: Vec<&String> = v.as_object().map(|o| o.keys().collect()).unwrap_or_default();
    k.sort();
    k
}

/// D1 sonrası `conditional_j1` (EK 3 §6.3): anahtar kümeleri birebir, S_cond/P_L_cond ve p_break_next |Δ| ≤ 1e-12.
fn cmp_conditional_j1(exp: &Value, act: &Value, c: &mut RowCmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::Object(_), Value::Object(_)) => {
            if sorted_keys(exp) != sorted_keys(act) {
                return c.fail(format!("conditional_j1 anahtarları: beklenen {:?}, Rust {:?}", sorted_keys(exp), sorted_keys(act)));
            }
            for k in ["S_cond", "P_L_cond"] {
                let (e, a) = (&exp[k], &act[k]);
                if !e.is_object() || !a.is_object() || sorted_keys(e) != sorted_keys(a) {
                    c.fail(format!("conditional_j1.{k} anahtarları: beklenen {e}, Rust {a}"));
                    continue;
                }
                for key in sorted_keys(e) {
                    cmp_num(&format!("conditional_j1.{k}[{key}]"), &e[key], &a[key], TOL_CONDITIONAL, c);
                }
            }
            cmp_num("conditional_j1.p_break_next", &exp["p_break_next"], &act["p_break_next"], TOL_CONDITIONAL, c);
        }
        _ => c.fail(format!("conditional_j1: beklenen {exp}, Rust {act}")),
    }
}

/// D1 sonrası `d1_features` (EK 3 §6.3): oran metni, kilit, kırpma bayrağı, ceiling_close_D1 ve tutarlılık birebir;
/// ln, kullanılan değer ve z |Δ| ≤ 1e-9.
fn cmp_d1_features(exp: &Value, act: &Value, c: &mut RowCmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::Object(_), Value::Object(_)) => {
            if sorted_keys(exp) != sorted_keys(act) {
                return c.fail(format!("d1_features anahtarları: beklenen {:?}, Rust {:?}", sorted_keys(exp), sorted_keys(act)));
            }
            for k in sorted_keys(exp) {
                let path = format!("d1_features.{k}");
                match k.as_str() {
                    "d1_turnover_ln" | "d1_turnover_used" => cmp_num(&path, &exp[k], &act[k], TOL, c),
                    "z" => {
                        if sorted_keys(&exp[k]) != sorted_keys(&act[k]) {
                            c.fail(format!("{path} anahtarları: beklenen {}, Rust {}", exp[k], act[k]));
                            continue;
                        }
                        for col in sorted_keys(&exp[k]) {
                            cmp_num(&format!("{path}.{col}"), &exp[k][col], &act[k][col], TOL, c);
                        }
                    }
                    _ => cmp_exact(&path, &exp[k], &act[k], c),
                }
            }
        }
        _ => c.fail(format!("d1_features: beklenen {exp}, Rust {act}")),
    }
}

/// Bir model çıktısının tamamı (Python sözlüğü ↔ Rust `Output::to_json`).
pub fn cmp_output(exp: &Value, act: &Value, c: &mut RowCmp) {
    let (Some(eo), Some(ao)) = (exp.as_object(), act.as_object()) else {
        return c.fail(format!("çıktı: beklenen {exp}, Rust {act}"));
    };
    // §3.3: çıktıda `limit_path` anahtarı varsa tavan yolu dalı
    let is_path = eo.contains_key("limit_path") || ao.contains_key("limit_path");
    let mut ke: Vec<&String> = eo.keys().collect();
    let mut ka: Vec<&String> = ao.keys().collect();
    ke.sort();
    ka.sort();
    if ke != ka {
        return c.fail(format!("çıktı anahtarları: beklenen {ke:?}, Rust {ka:?}"));
    }
    for (k, ev) in eo {
        let av = &ao[k];
        match k.as_str() {
            "model_id" | "clipped" => cmp_exact(k, ev, av, c),
            // Faz 7 v1 (EK 3 §2.7): liste/metin/tamsayı birebir; f1r_raw göreli |Δ| ≤ 1e-9 · max(1, |beklenen|)
            "clipped_features" | "tufe_index_used" | "regime_value_used" | "regime_source" => cmp_exact(k, ev, av, c),
            // Faz 7C (EK 3 §8.3): ek satış bayrağı birebir (0 | 1 | null)
            "add_sale_used" => cmp_exact(k, ev, av, c),
            "f1r_raw" => {
                let scale = ev.as_f64().map_or(1.0, |x| x.abs().max(1.0));
                cmp_num(k, ev, av, TOL * scale, c)
            }
            "refused" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    cmp_exact("refused.code", &ev["code"], &av["code"], c);
                    cmp_exact("refused.field", &ev["field"], &av["field"], c);
                }
                _ => c.fail(format!("refused: beklenen {ev}, Rust {av}")),
            },
            "warnings" => cmp_warnings(ev, av, c),
            "hazard" | "S" | "P_L" | "P_close_ceiling" => cmp_num_array(k, ev, av, TOL, c),
            "f6_market20" => cmp_num(k, ev, av, TOL, c),
            // D1 sonrası (EK 3 §6.3; çıktıda `stage == "POST_D1"`)
            "stage" => cmp_exact(k, ev, av, c),
            "not_applicable" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    cmp_exact("not_applicable.code", &ev["code"], &av["code"], c);
                    cmp_exact("not_applicable.field", &ev["field"], &av["field"], c);
                }
                _ => c.fail(format!("not_applicable: beklenen {ev}, Rust {av}")),
            },
            "conditional_j1" => cmp_conditional_j1(ev, av, c),
            "path_conditional" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => cmp_conditional(ev, av, c),
                _ => c.fail(format!("path_conditional: beklenen {ev}, Rust {av}")),
            },
            "d1_features" => cmp_d1_features(ev, av, c),
            "limit_path" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    // metinler BİREBİR (üs biçimi dahil), rho |Δ| ≤ 1e-9
                    for f in ["ipo_price", "snapped_ipo_price", "tick", "C"] {
                        cmp_exact(&format!("limit_path.{f}"), &ev[f], &av[f], c);
                    }
                    cmp_num_array("limit_path.rho", &ev["rho"], &av["rho"], TOL, c);
                }
                _ => c.fail(format!("limit_path: beklenen {ev}, Rust {av}")),
            },
            "features" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(fe), Value::Object(_)) => {
                    for f in fe.keys() {
                        cmp_num(&format!("features.{f}"), &ev[f], &av[f], TOL, c);
                    }
                }
                _ => c.fail(format!("features: beklenen {ev}, Rust {av}")),
            },
            h if is_path => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => cmp_path_cell(h, ev, av, c),
                _ => c.fail(format!("{h}: beklenen {ev}, Rust {av}")),
            },
            h => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    for f in CELL_NUMS {
                        cmp_num(&format!("{h}.{f}"), &ev[f], &av[f], TOL, c);
                    }
                    for f in CELL_EXACT {
                        cmp_exact(&format!("{h}.{f}"), &ev[f], &av[f], c);
                    }
                }
                _ => c.fail(format!("{h}: beklenen {ev}, Rust {av}")),
            },
        }
    }
}

/// Beklenen `{output}` | `{error: {code}}` | `{exception}` ile Rust sonucu.
pub fn cmp_expected(expected: &Value, actual: &Result<borsai_predict::Output, borsai_predict::PredictError>, c: &mut RowCmp) {
    match (expected.get("output"), expected.get("error"), expected.get("exception"), actual) {
        (Some(e), _, _, Ok(out)) => cmp_output(e, &out.to_json(), c),
        (_, Some(err), _, Err(pe)) => {
            if err["code"].as_str() != Some(pe.code.as_str()) {
                c.fail(format!("hata kodu: beklenen {}, Rust {}", err["code"], pe.code));
            }
        }
        (_, _, Some(_), Err(pe)) if pe.code == borsai_predict::error::DOMAIN_ERROR => {}
        _ => c.fail(format!(
            "sonuç türü: beklenen {expected}, Rust {}",
            match actual {
                Ok(o) => o.to_json().to_string(),
                Err(e) => format!("Err({e})"),
            }
        )),
    }
}

/// Satırı Rust'ta çalıştır (entry: run_model | core).
pub fn run_row(params: &Value, row: &Value) -> Result<borsai_predict::Output, borsai_predict::PredictError> {
    let inputs = call_inputs(row);
    match row.get("entry").and_then(Value::as_str) {
        Some("core") => borsai_predict::predict_core_only(params, &inputs),
        _ => borsai_predict::predict(params, &inputs),
    }
}
