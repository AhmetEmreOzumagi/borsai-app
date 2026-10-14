//! Dondurulmuş kaydın parite denetimi (SPEC_APP §3e adım 6, §1.3 karşılaştırma kuralları).
//!
//! Kayıt esastır: uyuşmazlık kaydı geçersiz kılmaz, yalnız raporlanır ve olay dosyasına yazılır.
//! **Desteklenen küme gömülü veriden okunur** (`AppState::models`); kodda model sayısı sabiti YOKTUR.
//! Kayıtta olup uygulamada olmayan modeller adıyla listelenir; bu bir uyuşmazlık DEĞİLDİR ve olay
//! dosyasına yazılmaz. Uygulamada olup KAYITTA olmayan modeller de uyuşmazlık değildir: kayıt
//! INDEX'ten eskidir (`missing_in_record`; SPEC_APP EK 2 §3.7).
use serde::Serialize;
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::path::Path;

use super::{io_error, AppError};
use crate::clock::now_utc_stamp;
use crate::json_out::pretty_json_bytes;

/// SPK_APP §1.3: sayısal alanlarda kabul edilen en büyük fark.
pub const TOL: f64 = 1e-9;
/// EK 3 §6.3: D1 sonrası koşullu görünüm (`conditional_j1`, `path_conditional` S_cond/P_L_cond/S_j) ve
/// `comparators_conditional` kopyaları için.
pub const TOL_CONDITIONAL: f64 = 1e-12;

#[derive(Debug, Default, Clone)]
struct Cmp {
    max_abs: f64,
    bit_equal: bool,
    n_numbers: usize,
    failures: Vec<String>,
}

impl Cmp {
    fn new() -> Self {
        Cmp { max_abs: 0.0, bit_equal: true, n_numbers: 0, failures: Vec::new() }
    }
    fn fail(&mut self, msg: String) {
        self.bit_equal = false;
        self.failures.push(msg);
    }
}

fn nonfinite(s: &str) -> bool {
    matches!(s, "NaN" | "Infinity" | "-Infinity")
}

fn cmp_num(path: &str, exp: &Value, act: &Value, c: &mut Cmp) {
    cmp_num_tol(path, exp, act, TOL, c)
}

fn cmp_num_tol(path: &str, exp: &Value, act: &Value, tol: f64, c: &mut Cmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::String(a), Value::String(b)) if nonfinite(a) && a == b => c.n_numbers += 1,
        (Value::Number(a), Value::Number(b)) => {
            let (x, y) = (a.as_f64().unwrap_or(f64::NAN), b.as_f64().unwrap_or(f64::NAN));
            c.n_numbers += 1;
            let d = (x - y).abs();
            if d > c.max_abs {
                c.max_abs = d;
            }
            if x.to_bits() != y.to_bits() {
                c.bit_equal = false;
            }
            if !(d <= tol) {
                c.fail(format!("{path}: kayıt {x:?}, uygulama {y:?}, |Δ| = {d:e}"));
            }
        }
        _ => c.fail(format!("{path}: kayıt {exp}, uygulama {act}")),
    }
}

fn cmp_exact(path: &str, exp: &Value, act: &Value, c: &mut Cmp) {
    if exp != act {
        c.fail(format!("{path}: kayıt {exp}, uygulama {act}"));
    }
}

fn cmp_num_array(path: &str, exp: &Value, act: &Value, c: &mut Cmp) {
    match (exp, act) {
        (Value::Null, Value::Null) => {}
        (Value::Array(a), Value::Array(b)) if a.len() == b.len() => {
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                cmp_num(&format!("{path}[{i}]"), x, y, c);
            }
        }
        _ => c.fail(format!("{path}: kayıt {exp}, uygulama {act}")),
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

/// Uyarılar: (kod, özellik|ufuk) çok kümesi eşit; sıra ve `message` karşılaştırılmaz.
fn cmp_warnings(exp: &Value, act: &Value, c: &mut Cmp) {
    let (Some(ea), Some(aa)) = (exp.as_array(), act.as_array()) else {
        return c.fail(format!("warnings: kayıt {exp}, uygulama {act}"));
    };
    let mut ge: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    let mut ga: BTreeMap<(String, String), Vec<&Value>> = BTreeMap::new();
    for w in ea {
        ge.entry(warning_key(w)).or_default().push(w);
    }
    for w in aa {
        ga.entry(warning_key(w)).or_default().push(w);
    }
    let ke: Vec<_> = ge.iter().map(|(k, v)| (k.clone(), v.len())).collect();
    let ka: Vec<_> = ga.iter().map(|(k, v)| (k.clone(), v.len())).collect();
    if ke != ka {
        return c.fail(format!("warnings çok kümesi: kayıt {ke:?}, uygulama {ka:?}"));
    }
    let keys_of = |w: &Value| -> Vec<String> {
        let mut v: Vec<String> =
            w.as_object().map(|o| o.keys().filter(|k| *k != "message").cloned().collect()).unwrap_or_default();
        v.sort();
        v
    };
    for (k, ws) in &ge {
        for (i, (we, wa)) in ws.iter().zip(&ga[k]).enumerate() {
            let (ke, ka) = (keys_of(we), keys_of(wa));
            if ke != ka {
                c.fail(format!("warning {}:{}#{i} anahtarları: kayıt {ke:?}, uygulama {ka:?}", k.0, k.1));
                continue;
            }
            for f in ke {
                if f == "code" {
                    continue;
                }
                let path = format!("warning {}:{}#{i}.{f}", k.0, k.1);
                let (a, b) = (&we[&f], &wa[&f]);
                // metin alanları (field, snapped, tick, metin value) ve mantıksal alanlar (D1 kilit tutarlılığı)
                // birebir; sayısal alanlar toleranslı
                if a.is_string() || b.is_string() || a.is_boolean() || b.is_boolean() {
                    cmp_exact(&path, a, b, c);
                } else {
                    cmp_num(&path, a, b, c);
                }
            }
        }
    }
}

const CELL_NUMS: [&str; 4] = ["return", "return_unclipped", "price", "p_up"];
const CELL_EXACT: [&str; 2] = ["return_clipped", "direction"];
/// `ceiling_path` D-hücresinde toleranslı alanlar; kalanlar (`status`, `n_atoms`, `post_break`) birebir.
const PATH_CELL_NUMS: [&str; 10] = [
    "return", "p_up", "mean", "q10", "q50", "q90", "limit_path_return", "S_h", "p_limit_path", "realized_return",
];

/// `ceiling_path` hücresi: metin ve tamsayı alanlar birebir, ondalıklar toleranslı.
fn cmp_path_cell(h: &str, exp: &Value, act: &Value, c: &mut Cmp) {
    let (Some(eo), Some(ao)) = (exp.as_object(), act.as_object()) else {
        return c.fail(format!("{h}: kayıt {exp}, uygulama {act}"));
    };
    let mut ke: Vec<&String> = eo.keys().collect();
    let mut ka: Vec<&String> = ao.keys().collect();
    ke.sort();
    ka.sort();
    if ke != ka {
        return c.fail(format!("{h} anahtarları: kayıt {ke:?}, uygulama {ka:?}"));
    }
    for k in ke {
        let path = format!("{h}.{k}");
        if PATH_CELL_NUMS.contains(&k.as_str()) {
            cmp_num(&path, &eo[k], &ao[k], c);
        } else {
            cmp_exact(&path, &eo[k], &ao[k], c);
        }
    }
}

fn sorted_keys(v: &Value) -> Vec<&String> {
    let mut k: Vec<&String> = v.as_object().map(|o| o.keys().collect()).unwrap_or_default();
    k.sort();
    k
}

/// Metin anahtarlı koşullu sözlük (`S_cond`, `P_L_cond`): anahtar kümesi birebir, değerler |Δ| ≤ 1e-12.
fn cmp_cond_map(path: &str, exp: &Value, act: &Value, c: &mut Cmp) {
    if !exp.is_object() || !act.is_object() || sorted_keys(exp) != sorted_keys(act) {
        return c.fail(format!("{path} anahtarları: kayıt {exp}, uygulama {act}"));
    }
    for k in sorted_keys(exp) {
        cmp_num_tol(&format!("{path}[{k}]"), &exp[k], &act[k], TOL_CONDITIONAL, c);
    }
}

/// `path_conditional` (EK 2 §3.3 koşullu kuralları): üst alanlar birebir, S_j/S_cond/P_L_cond ≤ 1e-12, D hücreleri.
fn cmp_path_conditional(exp: &Value, act: &Value, c: &mut Cmp) {
    if sorted_keys(exp) != sorted_keys(act) {
        return c.fail(format!("path_conditional anahtarları: kayıt {:?}, uygulama {:?}", sorted_keys(exp), sorted_keys(act)));
    }
    for k in sorted_keys(exp) {
        let path = format!("path_conditional.{k}");
        match k.as_str() {
            "state" | "j" | "t" | "note" | "limit_path_mismatch" => cmp_exact(&path, &exp[k], &act[k], c),
            "S_j" => cmp_num_tol(&path, &exp[k], &act[k], TOL_CONDITIONAL, c),
            "S_cond" | "P_L_cond" => cmp_cond_map(&path, &exp[k], &act[k], c),
            h => cmp_path_cell(&format!("path_conditional.{h}"), &exp[k], &act[k], c),
        }
    }
}

/// D1 sonrası çıktının kendine özgü alanları (EK 3 §6.3).
fn cmp_post_d1_field(k: &str, ev: &Value, av: &Value, c: &mut Cmp) {
    match (ev, av) {
        (Value::Null, Value::Null) => {}
        (Value::Object(_), Value::Object(_)) => match k {
            "not_applicable" => {
                cmp_exact("not_applicable.code", &ev["code"], &av["code"], c);
                cmp_exact("not_applicable.field", &ev["field"], &av["field"], c);
            }
            "conditional_j1" => {
                if sorted_keys(ev) != sorted_keys(av) {
                    return c.fail(format!("conditional_j1 anahtarları: kayıt {ev}, uygulama {av}"));
                }
                cmp_cond_map("conditional_j1.S_cond", &ev["S_cond"], &av["S_cond"], c);
                cmp_cond_map("conditional_j1.P_L_cond", &ev["P_L_cond"], &av["P_L_cond"], c);
                cmp_num_tol("conditional_j1.p_break_next", &ev["p_break_next"], &av["p_break_next"], TOL_CONDITIONAL, c);
            }
            "path_conditional" => cmp_path_conditional(ev, av, c),
            _ => {
                // d1_features: oran metni, kilit, kırpma, ceiling_close_D1, tutarlılık birebir; ln/used/z ≤ 1e-9
                if sorted_keys(ev) != sorted_keys(av) {
                    return c.fail(format!("d1_features anahtarları: kayıt {ev}, uygulama {av}"));
                }
                for f in sorted_keys(ev) {
                    let path = format!("d1_features.{f}");
                    match f.as_str() {
                        "d1_turnover_ln" | "d1_turnover_used" => cmp_num(&path, &ev[f], &av[f], c),
                        "z" if sorted_keys(&ev[f]) == sorted_keys(&av[f]) => {
                            for col in sorted_keys(&ev[f]) {
                                cmp_num(&format!("{path}.{col}"), &ev[f][col], &av[f][col], c);
                            }
                        }
                        _ => cmp_exact(&path, &ev[f], &av[f], c),
                    }
                }
            }
        },
        _ => c.fail(format!("{k}: kayıt {ev}, uygulama {av}")),
    }
}

fn cmp_output(exp: &Value, act: &Value, c: &mut Cmp) {
    let (Some(eo), Some(ao)) = (exp.as_object(), act.as_object()) else {
        return c.fail(format!("çıktı: kayıt {exp}, uygulama {act}"));
    };
    // SPEC_APP EK 2 §3.3: çıktıda `limit_path` anahtarı varsa tavan yolu dalı
    let is_path = eo.contains_key("limit_path") || ao.contains_key("limit_path");
    let mut ke: Vec<&String> = eo.keys().collect();
    let mut ka: Vec<&String> = ao.keys().collect();
    ke.sort();
    ka.sort();
    if ke != ka {
        return c.fail(format!("çıktı anahtarları: kayıt {ke:?}, uygulama {ka:?}"));
    }
    for (k, ev) in eo {
        let av = &ao[k];
        match k.as_str() {
            "model_id" | "clipped" => cmp_exact(k, ev, av, c),
            // Faz 7 v1 (EK 3 §2.7): liste/metin/tamsayı birebir; f1r_raw göreli |Δ| ≤ 1e-9 · max(1, |kayıt|)
            "clipped_features" | "tufe_index_used" | "regime_value_used" | "regime_source" => cmp_exact(k, ev, av, c),
            // Faz 7C (EK 3 §8.3): ek satış bayrağı birebir
            "add_sale_used" => cmp_exact(k, ev, av, c),
            "f1r_raw" => cmp_num_tol(k, ev, av, TOL * ev.as_f64().map_or(1.0, |x| x.abs().max(1.0)), c),
            "refused" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    cmp_exact("refused.code", &ev["code"], &av["code"], c);
                    cmp_exact("refused.field", &ev["field"], &av["field"], c);
                }
                _ => c.fail(format!("refused: kayıt {ev}, uygulama {av}")),
            },
            "warnings" => cmp_warnings(ev, av, c),
            "hazard" | "S" | "P_L" | "P_close_ceiling" => cmp_num_array(k, ev, av, c),
            "limit_path" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    for f in ["ipo_price", "snapped_ipo_price", "tick", "C"] {
                        cmp_exact(&format!("limit_path.{f}"), &ev[f], &av[f], c);
                    }
                    cmp_num_array("limit_path.rho", &ev["rho"], &av["rho"], c);
                }
                _ => c.fail(format!("limit_path: kayıt {ev}, uygulama {av}")),
            },
            "f6_market20" => cmp_num(k, ev, av, c),
            // D1 sonrası (EK 3 §6.3; çıktıda `stage == "POST_D1"`)
            "stage" => cmp_exact(k, ev, av, c),
            "not_applicable" | "conditional_j1" | "path_conditional" | "d1_features" => cmp_post_d1_field(k, ev, av, c),
            "features" => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(fe), Value::Object(_)) => {
                    for f in fe.keys() {
                        cmp_num(&format!("features.{f}"), &ev[f], &av[f], c);
                    }
                }
                _ => c.fail(format!("features: kayıt {ev}, uygulama {av}")),
            },
            h if is_path => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => cmp_path_cell(h, ev, av, c),
                _ => c.fail(format!("{h}: kayıt {ev}, uygulama {av}")),
            },
            h => match (ev, av) {
                (Value::Null, Value::Null) => {}
                (Value::Object(_), Value::Object(_)) => {
                    for f in CELL_NUMS {
                        cmp_num(&format!("{h}.{f}"), &ev[f], &av[f], c);
                    }
                    for f in CELL_EXACT {
                        cmp_exact(&format!("{h}.{f}"), &ev[f], &av[f], c);
                    }
                }
                _ => c.fail(format!("{h}: kayıt {ev}, uygulama {av}")),
            },
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ParityCell {
    pub model_id: String,
    pub ok: bool,
    pub bit_equal: bool,
    pub max_abs: f64,
    pub n_numbers: usize,
    pub failures: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ParityReport {
    /// Kayıttaki toplam model sayısı (dondurma sonrası 27; eski kayıtlar 16).
    pub n_record_models: usize,
    /// Uygulamanın desteklediği (gömülü) modellerden kayıtta bulunanlar.
    pub n_supported: usize,
    pub n_matched: usize,
    pub max_abs: f64,
    pub n_bit_equal: usize,
    /// Kayıtta olup uygulamada henüz olmayan modeller (uyuşmazlık DEĞİL).
    pub unsupported: Vec<String>,
    /// Uygulamada (INDEX'te) olup KAYITTA olmayan modeller: kayıt INDEX'ten eski (uyuşmazlık DEĞİL).
    pub missing_in_record: Vec<String>,
    pub mismatches: Vec<ParityCell>,
    /// Uyuşmazlık varsa yazılan olay dosyası (repo'ya göre).
    pub incident_rel_path: Option<String>,
}

impl ParityReport {
    pub fn ok(&self) -> bool {
        self.mismatches.is_empty()
    }
}

/// Kaydın her hücresini gömülü modellerle karşılaştırır. `models`: doğrulanmış gömülü küme.
pub fn compare_record(record: &Value, models: &[borsai_predict::ModelRef]) -> ParityReport {
    let empty = Vec::new();
    let cells = record.get("models").and_then(Value::as_array).unwrap_or(&empty);
    let inputs: Map<String, Value> = record.get("model_inputs").and_then(Value::as_object).cloned().unwrap_or_default();
    let mut report = ParityReport {
        n_record_models: cells.len(),
        n_supported: 0,
        n_matched: 0,
        max_abs: 0.0,
        n_bit_equal: 0,
        unsupported: Vec::new(),
        missing_in_record: Vec::new(),
        mismatches: Vec::new(),
        incident_rel_path: None,
    };
    let present: std::collections::BTreeSet<&str> = cells.iter().filter_map(|c| c["model_id"].as_str()).collect();
    report.missing_in_record =
        models.iter().filter(|m| !present.contains(m.model_id.as_str())).map(|m| m.model_id.clone()).collect();
    for cell in cells {
        let mid = cell["model_id"].as_str().unwrap_or("?");
        let Some(m) = models.iter().find(|m| m.model_id == mid) else {
            report.unsupported.push(mid.to_string());
            continue;
        };
        report.n_supported += 1;
        let mut c = Cmp::new();
        if cell["params_sha256"].as_str() != Some(m.params_sha256.as_str()) {
            c.fail(format!("params_sha256: kayıt {}, uygulama {}", cell["params_sha256"], m.params_sha256));
        }
        let run = borsai_predict::run_model(&m.params, &inputs);
        if cell["status"].as_str() != Some(run.status) {
            c.fail(format!("status: kayıt {}, uygulama {}", cell["status"], run.status));
        } else {
            match (&cell["output"], &run.output) {
                (Value::Null, None) => {}
                (exp @ Value::Object(_), Some(out)) => cmp_output(exp, &out.to_json(), &mut c),
                _ => c.fail("çıktı varlığı".into()),
            }
            match (&cell["refusal"], run.refusal.as_ref()) {
                (Value::Null, None) => {}
                (e @ Value::Object(_), Some(r)) if e["code"] == serde_json::json!(r.code) && e["field"] == serde_json::json!(r.field) => {}
                (e, a) => c.fail(format!("refusal: kayıt {e}, uygulama {a:?}")),
            }
        }
        if c.max_abs > report.max_abs {
            report.max_abs = c.max_abs;
        }
        let ok = c.failures.is_empty();
        if ok {
            report.n_matched += 1;
        }
        if ok && c.bit_equal {
            report.n_bit_equal += 1;
        }
        if !ok {
            report.mismatches.push(ParityCell {
                model_id: mid.to_string(),
                ok,
                bit_equal: c.bit_equal,
                max_abs: c.max_abs,
                n_numbers: c.n_numbers,
                failures: c.failures,
            });
        }
    }
    report
}

/// D1 sonrası kaydın paritesi (EK 3 §6.6 adım 3; K-P2-4): kaydın her POST_D1 hücresi gömülü ikinci dizin modeliyle, kaydın
/// `base_record` dosyasındaki `model_inputs` (girdi belgesi değil; H36) ve kaydın `d1` bloğu (`fields_raw`, `half_day`,
/// `halt_flag`) ile Rust'ta yeniden koşulur. `path_params` yalnız base kaydında `ceiling_path_v0` PREDICTED ise verilir
/// (`freeze.run_post_d1_model`; eski kohortta rejim dışı hücre aday değildir). Tolerans gevşetilmez.
pub fn compare_post_d1_record(
    record: &Value,
    base_inputs: &Map<String, Value>,
    base_cells: &[Value],
    verified: &super::models::VerifiedModels,
) -> ParityReport {
    let empty = Vec::new();
    let cells = record.get("models").and_then(Value::as_array).unwrap_or(&empty);
    let mut report = ParityReport {
        n_record_models: cells.len(),
        n_supported: 0,
        n_matched: 0,
        max_abs: 0.0,
        n_bit_equal: 0,
        unsupported: Vec::new(),
        missing_in_record: Vec::new(),
        mismatches: Vec::new(),
        incident_rel_path: None,
    };
    let present: std::collections::BTreeSet<&str> = cells.iter().filter_map(|c| c["model_id"].as_str()).collect();
    report.missing_in_record =
        verified.post_d1.iter().filter(|m| !present.contains(m.model_id.as_str())).map(|m| m.model_id.clone()).collect();
    let d1 = serde_json::json!({
        "fields_raw": record.pointer("/d1/fields_raw").cloned().unwrap_or(Value::Null),
        "half_day": record.pointer("/d1/half_day").cloned().unwrap_or(Value::Null),
        "halt_flag": record.pointer("/d1/halt_flag").cloned().unwrap_or(Value::Null),
    });
    for cell in cells {
        let mid = cell["model_id"].as_str().unwrap_or("?");
        let Some(m) = verified.post_d1_by_id(mid) else {
            report.unsupported.push(mid.to_string());
            continue;
        };
        report.n_supported += 1;
        let mut c = Cmp::new();
        if cell["params_sha256"].as_str() != Some(m.params_sha256.as_str()) {
            c.fail(format!("params_sha256: kayıt {}, uygulama {}", cell["params_sha256"], m.params_sha256));
        }
        let parent_id = m.params.pointer("/parent/model_id").and_then(Value::as_str).unwrap_or("");
        let path_id = m.params.pointer("/path_secondary/model_id").and_then(Value::as_str).unwrap_or("");
        let (Some(parent), Some(path)) = (verified.by_id(parent_id), verified.by_id(path_id)) else {
            c.fail(format!("ebeveyn {parent_id:?} ya da tavan yolu {path_id:?} gömülü değil"));
            report.mismatches.push(ParityCell { model_id: mid.into(), ok: false, bit_equal: false, max_abs: 0.0, n_numbers: 0, failures: c.failures });
            continue;
        };
        let path_given = base_cells
            .iter()
            .any(|b| b["model_id"].as_str() == Some(path_id) && b["status"].as_str() == Some(borsai_predict::STATUS_PREDICTED));
        let run = borsai_predict::post_d1::run_post_d1(&m.params, &parent.params, base_inputs, &d1, path_given.then_some(&path.params));
        if cell["status"].as_str() != Some(run.status) {
            c.fail(format!("status: kayıt {}, uygulama {}", cell["status"], run.status));
        } else {
            match (&cell["output"], &run.output) {
                (Value::Null, None) => {}
                (exp @ Value::Object(_), Some(out)) => cmp_output(exp, &out.to_json(), &mut c),
                _ => c.fail("çıktı varlığı".into()),
            }
            match (&cell["refusal"], run.refusal.as_ref()) {
                (Value::Null, None) => {}
                (e @ Value::Object(_), Some(r)) if e["code"] == serde_json::json!(r.code) && e["field"] == serde_json::json!(r.field) => {}
                (e, a) => c.fail(format!("refusal: kayıt {e}, uygulama {a:?}")),
            }
        }
        report.max_abs = report.max_abs.max(c.max_abs);
        let ok = c.failures.is_empty();
        report.n_matched += usize::from(ok);
        report.n_bit_equal += usize::from(ok && c.bit_equal);
        if !ok {
            report.mismatches.push(ParityCell {
                model_id: mid.to_string(),
                ok,
                bit_equal: c.bit_equal,
                max_abs: c.max_abs,
                n_numbers: c.n_numbers,
                failures: c.failures,
            });
        }
    }
    report
}

/// `comparators_conditional` kopyalarının denetimi (EK 3 §6.6 adım 3, bilgi): her kopyanın `S_cond`'u Rust
/// `survival::conditional(S, 1)` ile |Δ| ≤ 1e-12. Dönen: (denetlenen karşılaştırıcı sayısı, maks |Δ|, sapmalar).
pub fn check_comparators_conditional(record: &Value) -> (usize, f64, Vec<String>) {
    let mut c = Cmp::new();
    let mut n = 0usize;
    if let Some(map) = record.get("comparators_conditional").and_then(Value::as_object) {
        for (rid, comp) in map {
            let s: Option<Vec<f64>> = comp.get("S").and_then(|v| serde_json::from_value(v.clone()).ok());
            match (s, comp.get("S_cond")) {
                (None, Some(Value::Null) | None) => {}
                (Some(s), Some(exp @ Value::Object(_))) => {
                    n += 1;
                    match borsai_predict::survival::conditional(&s, 1) {
                        Some(cond) => {
                            let act: Map<String, Value> = (2..=borsai_predict::survival::DAYS)
                                .map(|k| (k.to_string(), cond.s_cond[k - 1].map(Value::from).unwrap_or(Value::Null)))
                                .collect();
                            cmp_cond_map(&format!("comparators_conditional.{rid}.S_cond"), exp, &Value::Object(act), &mut c);
                        }
                        None => c.fail(format!("comparators_conditional.{rid}: koşul tanımsız (S_1 = 0) ama kopya dolu")),
                    }
                }
                (s, e) => c.fail(format!("comparators_conditional.{rid}: S {} / S_cond {:?}", s.is_some(), e)),
            }
        }
    }
    (n, c.max_abs, c.failures)
}

/// Uyuşmazlık olayı: `<repo>/app/parity/incidents/<UTC>.json`. Yalnız `app/` altına yazılır.
pub fn write_incident(repo: &Path, record_rel: &str, report: &ParityReport) -> Result<String, AppError> {
    let rel = format!("app/parity/incidents/{}.json", now_utc_stamp());
    let path = repo.join(&rel);
    let payload = serde_json::json!({
        "schema_version": "borsai.app_parity_incident/1",
        "record": record_rel,
        "app_version": env!("CARGO_PKG_VERSION"),
        "build_git_head": crate::embedded::BUILD_INFO.git_head,
        "index_sha256": crate::embedded::BUILD_INFO.index_sha256,
        "report": report,
    });
    std::fs::create_dir_all(path.parent().expect("incidents dizini")).map_err(|e| io_error("incidents", e))?;
    let bytes = pretty_json_bytes(&payload).map_err(|e| AppError::new("IO_ERROR", e))?;
    std::fs::write(&path, bytes).map_err(|e| io_error(&rel, e))?;
    Ok(rel)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn numeric_tolerance_and_keys() {
        let mut c = Cmp::new();
        cmp_output(
            &json!({"model_id": "m", "refused": null, "warnings": [], "S": [0.5, 0.25]}),
            &json!({"model_id": "m", "refused": null, "warnings": [], "S": [0.5, 0.25 + 1e-12]}),
            &mut c,
        );
        assert!(c.failures.is_empty() && !c.bit_equal && c.max_abs > 0.0);
        let mut c2 = Cmp::new();
        cmp_output(&json!({"S": [0.5]}), &json!({"S": [0.6]}), &mut c2);
        assert_eq!(c2.failures.len(), 1);
        let mut c3 = Cmp::new();
        cmp_output(&json!({"S": [0.5]}), &json!({"P_L": [0.5]}), &mut c3);
        assert!(c3.failures[0].contains("anahtarları"));
        // Faz 7C: ek satış bayrağı birebir
        let mut c4 = Cmp::new();
        cmp_output(&json!({"add_sale_used": 0}), &json!({"add_sale_used": 0}), &mut c4);
        assert!(c4.failures.is_empty());
        cmp_output(&json!({"add_sale_used": 0}), &json!({"add_sale_used": 1}), &mut c4);
        assert_eq!(c4.failures.len(), 1);
    }
}
