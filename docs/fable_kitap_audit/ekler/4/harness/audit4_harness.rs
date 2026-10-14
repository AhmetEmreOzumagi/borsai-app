//! KITAP_AUDIT_4 adım 1: bağımsız girdilerle Rust çıktıları (yalnız klonda; asıl repoya girmez).
use serde_json::{json, Map, Value};
use std::io::{BufRead, Write};
use std::path::PathBuf;

fn read_jsonl(p: &PathBuf) -> Vec<Value> {
    let f = std::fs::File::open(p).unwrap();
    std::io::BufReader::new(f).lines().map(|l| serde_json::from_str(&l.unwrap()).unwrap()).collect()
}

#[test]
#[ignore]
fn audit4_rust_outputs() {
    let root = PathBuf::from(std::env::var("AUDIT4_ROOT").expect("AUDIT4_ROOT"));
    let out_dir = PathBuf::from(std::env::var("AUDIT4_OUT").expect("AUDIT4_OUT"));
    let index: Value = serde_json::from_slice(&std::fs::read(root.join("models").join("INDEX.json")).unwrap()).unwrap();
    let mut models: Vec<(String, Value)> = Vec::new();
    for e in index["models"].as_array().unwrap() {
        let raw = std::fs::read(root.join("models").join(e["file"].as_str().unwrap())).unwrap();
        models.push((e["model_id"].as_str().unwrap().to_string(), serde_json::from_slice(&raw).unwrap()));
    }
    assert_eq!(models.len(), 27);
    let post_idx: Value = serde_json::from_slice(&std::fs::read(root.join("models").join("INDEX_POST_D1.json")).unwrap()).unwrap();
    let post_e = &post_idx["models"][0];
    let post: Value = serde_json::from_slice(&std::fs::read(root.join("models").join(post_e["file"].as_str().unwrap())).unwrap()).unwrap();
    let parent = models.iter().find(|(m, _)| m == "ceiling_hazard_v0").unwrap().1.clone();
    let path = models.iter().find(|(m, _)| m == "ceiling_path_v0").unwrap().1.clone();

    let cases = read_jsonl(&out_dir.join("cases.jsonl"));
    let mut fo = std::fs::File::create(out_dir.join("rust_out.jsonl")).unwrap();
    for c in &cases {
        let inputs: Map<String, Value> = c["inputs"].as_object().unwrap().clone();
        let mut runs = Map::new();
        for (mid, params) in &models {
            runs.insert(mid.clone(), borsai_predict::run_model(params, &inputs).to_json());
        }
        writeln!(fo, "{}", json!({"case_id": c["case_id"], "runs": runs})).unwrap();
    }
    let pcases = read_jsonl(&out_dir.join("post_cases.jsonl"));
    let mut fp = std::fs::File::create(out_dir.join("rust_post_out.jsonl")).unwrap();
    for c in &pcases {
        let inputs: Map<String, Value> = c["inputs"].as_object().unwrap().clone();
        let give_path = c["give_path"].as_bool().unwrap();
        let r = borsai_predict::post_d1::run_post_d1(&post, &parent, &inputs, &c["d1"], if give_path { Some(&path) } else { None });
        writeln!(fp, "{}", json!({"case_id": c["case_id"], "post": r.to_json()})).unwrap();
    }
    // Koşullu tutarlılık ölçümü: 1 − h_{j+1} ile S_{j+1}/S_j (Python ile aynı tanım) — hazard türü modellerde
    let mut fc = std::fs::File::create(out_dir.join("rust_cond_check.jsonl")).unwrap();
    for c in cases.iter().take(60) {
        let inputs: Map<String, Value> = c["inputs"].as_object().unwrap().clone();
        for (mid, params) in &models {
            if !matches!(borsai_predict::model_kind(params), borsai_predict::Kind::Hazard | borsai_predict::Kind::Km) {
                continue;
            }
            let r = borsai_predict::run_model(params, &inputs);
            let Some(borsai_predict::Output::Hazard(h)) = r.output else { continue };
            if r.status != "PREDICTED" {
                continue;
            }
            let (Some(s), Some(hz)) = (h.s.as_ref(), h.hazard.as_ref()) else { continue };
            let mut rows = Vec::new();
            for j in 0..10usize {
                let sj = if j == 0 { 1.0 } else { s[j - 1] };
                let ratio = s[j] / sj;
                let one_minus_h = 1.0 - hz[j];
                rows.push(json!({"j": j, "ratio": ratio, "one_minus_h": one_minus_h, "delta": (ratio - one_minus_h).abs()}));
            }
            let cond = borsai_predict::survival::conditional(s, 3);
            let cj = cond.map(|x| json!({"S_cond": x.s_cond, "P_L_cond": x.p_l_cond, "p_break_next": x.p_break_next}));
            writeln!(fc, "{}", json!({"case_id": c["case_id"], "model_id": mid, "rows": rows, "cond3": cj})).unwrap();
        }
    }
}
