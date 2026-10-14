//! U6: resmi kayıtlarla parite (SPEC_APP §5.1). `registry/records/**` altındaki her PREDICTION kaydı
//! için kayıttaki `model_inputs` (f6 dahil) ile Rust çıktısı kaydın `models[].output`'una §1.3
//! kurallarıyla eşit. Repo yolu `BORSAI_REPO` ortam değişkeninden. Test `#[ignore]`'dır: yalın
//! `cargo test`'te "ignored" görünür; `bash app/scripts/test.sh` `--include-ignored` ile koşar; env yoksa KIRMIZI.
//!
//! EK 2 §3.7: kayıtta olup portta olmayan model "kapsam dışı", portta olup KAYITTA olmayan model
//! "kayıt sürümü farklı" (kayıt INDEX'ten eski) sayılır; ikisi de UYUŞMAZLIK DEĞİLDİR ve raporlanır.
//! Bugün 7 kayıt 16 modelli → 7 × 16 hücre karşılaştırılır, 7 model "kayıtta yok" (3 tavan yolu + 4 Faz 7 v1;
//! EK 3 U59). Kayıttaki `model_inputs.tufe_index` / `tufe_refusal` Rust'a aynen geçer (TÜFE yeniden aranmaz).
//!   BORSAI_REPO=~/Desktop/BorsAi cargo test -p borsai_predict --test records_parity -- --ignored --nocapture
mod common;

use common::*;
use serde_json::{json, Value};
use std::path::PathBuf;

/// Port edilen model kümesi (MANIFEST, 23): başka model_id'ler "kapsam dışı" diye sayılır.
fn pinned() -> Vec<String> {
    manifest()["model_ids"].as_array().unwrap().iter().map(|v| v.as_str().unwrap().to_string()).collect()
}

fn record_files(repo: &PathBuf) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let dir = repo.join("registry").join("records");
    for t in std::fs::read_dir(&dir).unwrap().flatten() {
        if t.path().is_dir() {
            for f in std::fs::read_dir(t.path()).unwrap().flatten() {
                if f.path().extension().is_some_and(|e| e == "json") {
                    out.push(f.path());
                }
            }
        }
    }
    out.sort();
    out
}

#[test]
#[ignore = "BORSAI_REPO (asıl repo; .venv Python'u) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn records_parity() {
    let repo = PathBuf::from(std::env::var_os("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let pinned = pinned();
    let mut n_records = 0;
    let mut n_cells = 0;
    let mut out_of_scope = Vec::new();
    let mut missing_in_record: std::collections::BTreeMap<String, usize> = std::collections::BTreeMap::new();
    let mut older_records = 0usize;
    let mut max_abs = 0.0f64;
    let mut bit_equal = 0;
    let mut failures = Vec::new();
    for path in record_files(&repo) {
        let rec = read_json(&path);
        if rec["record_type"] != json!("PREDICTION") {
            continue;
        }
        n_records += 1;
        let inputs = rec["model_inputs"].as_object().unwrap().clone();
        let present: std::collections::BTreeSet<&str> =
            rec["models"].as_array().unwrap().iter().filter_map(|c| c["model_id"].as_str()).collect();
        let missing: Vec<&String> = pinned.iter().filter(|m| !present.contains(m.as_str())).collect();
        if !missing.is_empty() {
            older_records += 1;
            for m in missing {
                *missing_in_record.entry(m.clone()).or_default() += 1;
            }
        }
        for cell in rec["models"].as_array().unwrap() {
            let mid = cell["model_id"].as_str().unwrap();
            if !pinned.iter().any(|p| p == mid) {
                out_of_scope.push(mid.to_string());
                continue;
            }
            let bytes = std::fs::read(repo.join(cell["file"].as_str().unwrap())).unwrap();
            assert_eq!(sha256_hex(&bytes), cell["params_sha256"].as_str().unwrap(), "{}: {mid} params sha", path.display());
            let params: Value = serde_json::from_slice(&bytes).unwrap();
            let run = borsai_predict::run_model(&params, &inputs);
            let mut c = RowCmp::new();
            if run.status != cell["status"].as_str().unwrap() {
                failures.push(format!("{} {mid}: status {} != {}", path.display(), run.status, cell["status"]));
                continue;
            }
            match (&cell["output"], &run.output) {
                (Value::Null, None) => {}
                (exp @ Value::Object(_), Some(out)) => cmp_output(exp, &out.to_json(), &mut c),
                _ => c.failures.push("çıktı varlığı".into()),
            }
            let (er, ar) = (&cell["refusal"], run.refusal.as_ref());
            match (er, ar) {
                (Value::Null, None) => {}
                (Value::Object(_), Some(r)) if er["code"] == json!(r.code) && er["field"] == json!(r.field) => {}
                _ => c.failures.push(format!("refusal: beklenen {er}, Rust {ar:?}")),
            }
            n_cells += 1;
            max_abs = max_abs.max(c.max_abs);
            if c.failures.is_empty() && c.bit_equal {
                bit_equal += 1;
            }
            for f in c.failures {
                failures.push(format!("{} {mid}: {f}", path.file_name().unwrap().to_string_lossy()));
            }
        }
    }
    eprintln!(
        "records_parity: {n_records} kayıt, {n_cells} model hücresi, bit-eşit {bit_equal}, maks |Δ| {max_abs:e}; \
         kapsam dışı: {out_of_scope:?}; kayıt INDEX'ten eski: {older_records} kayıt, kayıtta yok {missing_in_record:?}"
    );
    assert!(failures.is_empty(), "{}", failures.join("\n"));
    assert!(n_records >= 7, "en az 7 kayıt bekleniyordu");
    assert!(max_abs <= TOL);
    // Hücre sayımı kapalı: karşılaştırılan + kayıtta olmayan = kayıt × port kümesi (kodda sayı sabiti yok).
    let missing_total: usize = missing_in_record.values().sum();
    assert_eq!(n_cells + missing_total, n_records * pinned.len(), "hücre sayımı kapanmıyor");
    for m in ["ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0", "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real",
              "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"] {
        assert!(pinned.iter().any(|p| p == m), "{m} port kümesinde");
    }
    assert!(out_of_scope.iter().all(|m| m.starts_with("fall_d10_v0")), "kapsam dışı yalnız (C) olabilir: {out_of_scope:?}");
}

// ---------------------------------------------------------------- K-P2-4: gerçek D1 verisiyle POST_D1 paritesi

/// RFC 4180 (tırnaklı alan, `""` kaçışı) satırları; yalnız bu testin kohort okuyucusu.
fn csv_rows(text: &str) -> Vec<Vec<String>> {
    let mut rows = Vec::new();
    let (mut row, mut cur, mut quoted) = (Vec::new(), String::new(), false);
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        match (quoted, c) {
            (true, '"') if chars.peek() == Some(&'"') => {
                cur.push('"');
                chars.next();
            }
            (true, '"') => quoted = false,
            (true, c) => cur.push(c),
            (false, '"') if cur.is_empty() => quoted = true,
            (false, ',') => row.push(std::mem::take(&mut cur)),
            (false, '\n') => {
                row.push(std::mem::take(&mut cur));
                rows.push(std::mem::take(&mut row));
            }
            (false, '\r') => {}
            (false, c) => cur.push(c),
        }
    }
    if !cur.is_empty() || !row.is_empty() {
        row.push(cur);
        rows.push(row);
    }
    rows
}

/// Eski kohortun açık küme üyeleri (`status == MEMBER`, `vault != SEALED`): kasa (SEALED) dizinleri AÇILMAZ; kod
/// hiçbir çıktıya yazılmaz (sıra numarası kullanılır).
fn open_members(repo: &std::path::Path) -> Vec<String> {
    let text = std::fs::read_to_string(repo.join("registry").join("oot").join("cohort_pre_h99.csv")).unwrap();
    let rows = csv_rows(&text);
    let header = &rows[0];
    let col = |n: &str| header.iter().position(|h| h == n).unwrap_or_else(|| panic!("kohort sütunu yok: {n}"));
    let (ct, cs, cv) = (col("ticker"), col("status"), col("vault"));
    let open_set = ["OPEN", "EXPOSED_ARCHIVE", "EXPOSED_CODEX"];
    let mut out: Vec<String> = rows[1..]
        .iter()
        .filter(|r| r.len() == header.len() && r[cs] == "MEMBER" && r[cv] != "SEALED")
        .map(|r| {
            assert!(open_set.contains(&r[cv].as_str()), "açık küme değeri bilinmiyor (kod basılmıyor)");
            r[ct].clone()
        })
        .collect();
    out.sort();
    let n = out.len();
    out.dedup();
    assert_eq!(out.len(), n, "açık küme kodları tekil değil");
    out
}

/// K-P2-4 (orkestratör kararı; EK 3'e ek): Rust `predict_post_d1`, `registry/oot/post_d1/` altındaki KASA DIŞI kayıtlarla
/// koşulur. Girdiler kaydın `base_record` dosyasının `model_inputs`'u ve kaydın `d1` bloğu (`fields_raw`, `half_day`,
/// `halt_flag`); `path_params` yalnız base kaydında `ceiling_path_v0` PREDICTED ise (Python `run_post_d1_model`; rejim
/// dışı hücre aday değil). Çıktı kaydın `models[post_d1_hazard_v0]` hücresiyle §6.3 kurallarıyla. Önceden yazılı
/// beklenti: 71 kayıt; 59 PREDICTED, 9 NOT_APPLICABLE (D1_NOT_CEILING), 3 REFUSED (F3_MISSING); parite 71/71.
/// Çıktıda yalnız sayılar.
///   BORSAI_REPO=~/Desktop/BorsAi cargo test -p borsai_predict --test records_parity post_d1_oot_open -- --ignored --nocapture
#[test]
#[ignore = "BORSAI_REPO (asıl repo) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn post_d1_oot_open() {
    let repo = PathBuf::from(std::env::var_os("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let post = load_post_d1_params();
    let params = load_params();
    let (parent, path) = (&params["ceiling_hazard_v0"].0, &params["ceiling_path_v0"].0);
    let members = open_members(&repo);
    let mut counts: std::collections::BTreeMap<String, usize> = std::collections::BTreeMap::new();
    let (mut n_records, mut n_match, mut bit_equal, mut with_path) = (0usize, 0usize, 0usize, 0usize);
    let mut max_abs = 0.0f64;
    let mut failures = Vec::new();
    for (i, ticker) in members.iter().enumerate() {
        let dir = repo.join("registry").join("oot").join("post_d1").join(ticker);
        let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
            .map(|d| d.flatten().map(|e| e.path()).filter(|p| p.extension().is_some_and(|x| x == "json")).collect())
            .unwrap_or_default();
        files.sort();
        for f in files {
            let rec = read_json(&f);
            if rec["record_type"] != json!("PREDICTION") {
                continue;
            }
            assert_eq!(rec["schema_version"], json!("borsai.oot_post_d1_record/1"), "açık üye #{i}: şema");
            n_records += 1;
            let base = read_json(&repo.join(rec["base_record"]["file"].as_str().unwrap()));
            let inputs = base["model_inputs"].as_object().unwrap().clone();
            let path_given = base["models"].as_array().unwrap().iter().any(|c| c["model_id"] == json!("ceiling_path_v0") && c["status"] == json!("PREDICTED"));
            with_path += usize::from(path_given);
            let d1 = json!({"fields_raw": rec["d1"]["fields_raw"], "half_day": rec["d1"]["half_day"], "halt_flag": rec["d1"]["halt_flag"]});
            for cell in rec["models"].as_array().unwrap() {
                let mid = cell["model_id"].as_str().unwrap();
                let Some((p, sha)) = post.get(mid) else {
                    failures.push(format!("açık üye #{i}: dizinde olmayan model {mid}"));
                    continue;
                };
                assert_eq!(cell["params_sha256"].as_str(), Some(sha.as_str()), "açık üye #{i}: params sha");
                let run = borsai_predict::post_d1::run_post_d1(p, parent, &inputs, &d1, path_given.then_some(path));
                let status = cell["status"].as_str().unwrap_or("?");
                *counts.entry(match cell["refusal"]["code"].as_str() {
                    Some(code) => format!("{status}:{code}"),
                    None => status.to_string(),
                }).or_default() += 1;
                let mut c = RowCmp::new();
                if run.status != status {
                    c.fail(format!("status {} != {status}", run.status));
                } else {
                    match (&cell["output"], &run.output) {
                        (Value::Null, None) => {}
                        (exp @ Value::Object(_), Some(out)) => cmp_output(exp, &out.to_json(), &mut c),
                        _ => c.fail("çıktı varlığı".into()),
                    }
                    let (er, ar) = (&cell["refusal"], run.refusal.as_ref());
                    match (er, ar) {
                        (Value::Null, None) => {}
                        (Value::Object(_), Some(r)) if er["code"] == json!(r.code) && er["field"] == json!(r.field) => {}
                        _ => c.fail(format!("refusal kodu/alanı farklı ({:?})", ar.map(|r| &r.code))),
                    }
                }
                max_abs = max_abs.max(c.max_abs);
                if c.failures.is_empty() {
                    n_match += 1;
                    bit_equal += usize::from(c.bit_equal);
                }
                for f in c.failures {
                    failures.push(format!("açık üye #{i} {mid}: {f}"));
                }
            }
        }
    }
    eprintln!(
        "post_d1_oot_open: açık üye {}, kayıt {n_records}, parite {n_match}/{n_records}, bit-eşit {bit_equal}, maks |Δ| {max_abs:e}, \
         path verilen {with_path}, durumlar {counts:?}",
        members.len()
    );
    assert!(failures.is_empty(), "{}", failures.join("\n"));
    assert_eq!(members.len(), 71, "açık küme");
    assert_eq!(n_records, 71, "kasa dışı POST_D1 kaydı");
    assert_eq!(n_match, 71, "parite 71/71");
    assert!(max_abs <= TOL);
    let n = |k: &str| counts.get(k).copied().unwrap_or(0);
    assert_eq!((n("PREDICTED"), n("NOT_APPLICABLE:D1_NOT_CEILING"), n("REFUSED:F3_MISSING")), (59, 9, 3), "{counts:?}");
}

// ---------------------------------------------------------------- K-P4-3: gerçek kayıtlarla (C) paritesi

const FALL_IDS: [&str; 4] = ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"];

/// K-P4-3 (orkestratör kararı; EK 3'e ek, K-P2-4 kalıbı): Rust `predict_fall`, eski kohortun açık küme kayıtlarıyla
/// (`registry/oot/records/<T>/`, yalnız `status == MEMBER` ve `vault != SEALED`; SEALED dizinleri AÇILMAZ) koşulur. Girdiler
/// kaydın `model_inputs`'u (`tufe_index` dahil); her (C) hücresi kaydın `status`, `refusal {code, field}` ve `output`'u ile
/// §1.3/§8.3 kurallarıyla karşılaştırılır. Önceden yazılı beklenti: 284 hücre, parite 284/284; durumlar
/// addsale 70 PREDICTED + 1 ADDITIONAL_SALE_MISSING; h99 ve pooled 67 PREDICTED + 1 ADDITIONAL_SALE_MISSING + 3 F3_MISSING;
/// @ZERO 71 PREDICTED. Çıktıda yalnız sayılar.
///   BORSAI_REPO=~/Desktop/BorsAi cargo test -p borsai_predict --test records_parity fall_oot_open -- --ignored --nocapture
#[test]
#[ignore = "BORSAI_REPO (asıl repo) ister: bash app/scripts/test.sh --include-ignored ile koşar"]
fn fall_oot_open() {
    let repo = PathBuf::from(std::env::var_os("BORSAI_REPO").expect("BORSAI_REPO gerekli (bash app/scripts/test.sh verir)"));
    let params = load_params();
    let members = open_members(&repo);
    let mut counts: std::collections::BTreeMap<(String, String), usize> = std::collections::BTreeMap::new();
    let (mut n_records, mut n_cells, mut n_match, mut bit_equal) = (0usize, 0usize, 0usize, 0usize);
    let mut max_abs = 0.0f64;
    let mut failures = Vec::new();
    for (i, ticker) in members.iter().enumerate() {
        let dir = repo.join("registry").join("oot").join("records").join(ticker);
        let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
            .map(|d| d.flatten().map(|e| e.path()).filter(|p| p.extension().is_some_and(|x| x == "json")).collect())
            .unwrap_or_default();
        files.sort();
        for f in files {
            let rec = read_json(&f);
            let cells: Vec<&Value> = rec["models"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|c| FALL_IDS.contains(&c["model_id"].as_str().unwrap_or("")))
                .collect();
            if rec["record_type"] != json!("PREDICTION") || cells.is_empty() {
                continue;
            }
            n_records += 1;
            let inputs = rec["model_inputs"].as_object().unwrap().clone();
            assert!(inputs.contains_key("tufe_index"), "açık üye #{i}: kayıt tufe_index taşımıyor");
            for cell in cells {
                let mid = cell["model_id"].as_str().unwrap();
                let (p, sha) = &params[mid];
                assert_eq!(cell["params_sha256"].as_str(), Some(sha.as_str()), "açık üye #{i}: params sha");
                n_cells += 1;
                let run = borsai_predict::run_model(p, &inputs);
                let status = cell["status"].as_str().unwrap_or("?").to_string();
                let code = cell["refusal"]["code"].as_str().map(str::to_string).unwrap_or_default();
                *counts.entry((mid.to_string(), if code.is_empty() { status.clone() } else { format!("{status}:{code}") })).or_default() += 1;
                let mut c = RowCmp::new();
                if run.kind.as_str() != "fall" || cell["kind"] != json!("fall") {
                    c.fail(format!("tür {} / kayıt {}", run.kind.as_str(), cell["kind"]));
                }
                if run.status != status {
                    c.fail(format!("status {} != {status}", run.status));
                } else {
                    match (&cell["output"], &run.output) {
                        (Value::Null, None) => {}
                        (exp @ Value::Object(_), Some(out)) => cmp_output(exp, &out.to_json(), &mut c),
                        _ => c.fail("çıktı varlığı".into()),
                    }
                    let (er, ar) = (&cell["refusal"], run.refusal.as_ref());
                    match (er, ar) {
                        (Value::Null, None) => {}
                        (Value::Object(_), Some(r)) if er["code"] == json!(r.code) && er["field"] == json!(r.field) => {}
                        _ => c.fail(format!("refusal kodu/alanı farklı ({:?})", ar.map(|r| &r.code))),
                    }
                }
                max_abs = max_abs.max(c.max_abs);
                if c.failures.is_empty() {
                    n_match += 1;
                    bit_equal += usize::from(c.bit_equal);
                }
                for f in c.failures {
                    failures.push(format!("açık üye #{i} {mid}: {f}"));
                }
            }
        }
    }
    eprintln!(
        "fall_oot_open: açık üye {}, (C)'li kayıt {n_records}, hücre {n_cells}, parite {n_match}/{n_cells}, bit-eşit {bit_equal}, \
         maks |Δ| {max_abs:e}",
        members.len()
    );
    for ((m, s), n) in &counts {
        eprintln!("  {m:<26} {s:<36} {n}");
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
    assert_eq!((members.len(), n_records), (71, 71), "açık küme ve (C)'li kayıt");
    assert_eq!((n_cells, n_match), (284, 284), "parite 284/284");
    assert!(max_abs <= TOL);
    let n = |m: &str, s: &str| counts.get(&(m.to_string(), s.to_string())).copied().unwrap_or(0);
    let miss = "REFUSED:ADDITIONAL_SALE_MISSING";
    assert_eq!((n("fall_d10_v0_addsale", "PREDICTED"), n("fall_d10_v0_addsale", miss)), (70, 1), "{counts:?}");
    for m in ["fall_d10_v0_h99", "fall_d10_v0_pooled"] {
        assert_eq!((n(m, "PREDICTED"), n(m, miss), n(m, "REFUSED:F3_MISSING")), (67, 1, 3), "{m}: {counts:?}");
    }
    assert_eq!(n("fall_d10_v0_pooled@ZERO", "PREDICTED"), 71, "{counts:?}");
    assert_eq!(counts.values().sum::<usize>(), 284);
}
