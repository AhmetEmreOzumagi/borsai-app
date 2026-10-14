//! KITAP_AUDIT_4: uygulama katmanı TÜFE hazırlığı (commands/predict.rs tufe_for_inputs) ↔ Python freeze.tufe_for_record
use std::io::{BufRead, Write};
use std::path::PathBuf;

#[test]
#[ignore]
fn audit4_tufe_app_layer() {
    let root = PathBuf::from(std::env::var("AUDIT4_ROOT").unwrap());
    let out = PathBuf::from(std::env::var("AUDIT4_OUT").unwrap());
    let src = borsai_app_lib::commands::predict::tufe_source_repo(&root);
    let pins = borsai_app_lib::commands::predict::embedded_deflator_pins();
    assert_eq!(pins.len(), 4);
    let f = std::fs::File::open(out.join("tufe_expect.jsonl")).unwrap();
    let mut fo = std::fs::File::create(out.join("rust_tufe_out.jsonl")).unwrap();
    for l in std::io::BufReader::new(f).lines() {
        let row: serde_json::Value = serde_json::from_str(&l.unwrap()).unwrap();
        let t = row["T"].as_str();
        let (idx, refusal, info) = borsai_app_lib::commands::predict::tufe_for_inputs(t, &src, pins, None);
        writeln!(fo, "{}", serde_json::json!({"T": t, "tufe_index": idx, "tufe_refusal": refusal, "reason": info.reason, "month": info.month, "append": info.append_command.is_some()})).unwrap();
    }
    // Gömülü kopya da aynı mı (bağımsız mod)?
    let emb = borsai_app_lib::commands::predict::tufe_source_embedded().unwrap();
    let (a, ra, _) = borsai_app_lib::commands::predict::tufe_for_inputs(Some("2026-10-05"), &emb, pins, None);
    let (b, rb, _) = borsai_app_lib::commands::predict::tufe_for_inputs(Some("2026-10-05"), &src, pins, None);
    assert_eq!((a, ra), (b, rb));
}
