//! U56 (SPEC_APP EK 3 §3.2, §3.5): TÜFE tablosu okuma ve denetimi Python `borsai/tufe.py` ile birebir.
//! Beklenenler `.venv/bin/python app/parity/gen_golden.py --tufe-cases` → `app/parity/tufe_cases.json`. Taban, gerçek
//! dosyanın pin ayına (`TUFE_PIN.through_month`) kadarki önekidir (sha pinle aynı): durumlar aylık eklemeyle değişmez.
//!   cargo test -p borsai_predict --test tufe_semantics
mod common;

use borsai_predict::tufe::{self, DeflatorPin, TufeRow, TufeTable};
use common::*;
use serde_json::Value;

fn cases() -> Value {
    read_json(&app_dir().join("parity").join("tufe_cases.json"))
}

/// Gerçek dosyanın öneki (pin ayına kadar); sha pinle aynı olmalı.
fn base(c: &Value) -> Vec<u8> {
    let raw = std::fs::read(repo_dir().join(c["file"].as_str().unwrap())).unwrap();
    let table = tufe::parse(&raw).expect("gerçek TÜFE dosyası ayrıştırılır");
    let through = c["base"]["through_month"].as_str().unwrap();
    let prefix = table.prefix_bytes(through).unwrap();
    assert_eq!(sha256_hex(&prefix), c["base"]["prefix_sha256"].as_str().unwrap(), "önek pinle aynı değil");
    prefix
}

/// Python `_edit` ile aynı düzenleme dili.
fn edit(base: &[u8], ops: &Value) -> Vec<u8> {
    let mut out = String::from_utf8(base.to_vec()).unwrap();
    for op in ops.as_array().unwrap() {
        let a = op.as_array().unwrap();
        match a[0].as_str().unwrap() {
            "replace" => {
                let (old, new) = (a[1].as_str().unwrap(), a[2].as_str().unwrap());
                assert!(out.contains(old), "{old:?}");
                out = out.replacen(old, new, 1);
            }
            "append" => {
                out.push_str(a[1].as_str().unwrap());
                out.push('\n');
            }
            "crlf" => out = out.replace('\n', "\r\n"),
            "delete_line" => {
                let p = a[1].as_str().unwrap();
                let lines: Vec<&str> = out.split('\n').collect();
                let i = lines.iter().position(|l| l.starts_with(p)).unwrap();
                out = lines.iter().enumerate().filter(|(j, _)| *j != i).map(|(_, l)| *l).collect::<Vec<_>>().join("\n");
            }
            other => panic!("düzenleme {other}"),
        }
    }
    out.into_bytes()
}

#[test]
fn tufe_month_for() {
    for c in cases()["month_for"].as_array().unwrap() {
        let t = c["t"].as_str().unwrap();
        assert_eq!(tufe::month_for(t).as_deref(), c["month"].as_str(), "{t}");
    }
}

#[test]
fn tufe_parse_prefix_and_index() {
    let cs = cases();
    let base = base(&cs);
    let mut tables = std::collections::BTreeMap::new();
    for c in cs["parse"].as_array().unwrap() {
        let name = c["name"].as_str().unwrap();
        let got = tufe::parse(&edit(&base, &c["ops"]));
        match c["result"].as_str().unwrap() {
            "error" => assert!(got.is_err(), "{name}: TufeError bekleniyordu"),
            _ => {
                let t = got.unwrap_or_else(|e| panic!("{name}: {e:?}"));
                assert_eq!(t.rows.len() as u64, c["months"].as_u64().unwrap(), "{name}");
                assert_eq!(t.last_month(), c["last_month"].as_str().unwrap(), "{name}");
                assert_eq!(t.file_sha256, c["file_sha256"].as_str().unwrap(), "{name}");
                tables.insert(name.to_string(), t);
            }
        }
    }
    assert!(tables.contains_key("append_2026_09") && tables.contains_key("old_row_changed"));
    let mut n_pin = 0;
    for c in cs["prefix"].as_array().unwrap() {
        let t = &tables[c["variant"].as_str().unwrap()];
        if let Some(pin) = c.get("pin") {
            let pin = DeflatorPin {
                through_month: pin["through_month"].as_str().unwrap().into(),
                prefix_sha256: pin["prefix_sha256"].as_str().unwrap().into(),
            };
            let got = tufe::verify_pin(t, &pin).map(|_| "ok").unwrap_or_else(|r| r.code);
            assert_eq!(got, c["result"].as_str().unwrap(), "{}: pin", c["variant"]);
            n_pin += 1;
        } else {
            let m = c["month"].as_str().unwrap();
            assert_eq!(t.prefix_sha256(m).unwrap(), c["prefix_sha256"].as_str().unwrap(), "{}: önek {m}", c["variant"]);
        }
    }
    assert!(n_pin >= 3);
    for c in cs["index_for"].as_array().unwrap() {
        let t = &tables[c["variant"].as_str().unwrap()];
        let tt = c["t"].as_str().unwrap();
        match (tufe::index_for(tt, t), c["result"].as_str().unwrap()) {
            (Ok(row), "ok") => {
                assert_eq!(row.month, c["month"].as_str().unwrap());
                assert_eq!(row.index, c["index"].as_str().unwrap());
                assert_eq!(row.release_date, c["release_date"].as_str().unwrap());
            }
            (Err(r), code) => {
                assert_eq!(r.code, code, "{} T = {tt}", c["variant"]);
                assert_eq!(r.month.as_deref(), c["month"].as_str(), "{} T = {tt}", c["variant"]);
            }
            (got, want) => panic!("{} T = {tt}: beklenen {want}, Rust {got:?}", c["variant"]),
        }
    }
}

/// Bekçi: yayım günü T'den önce değilse TUFE_NOT_PIT (biçim denetimsiz tablo; kural gereği olamaz).
#[test]
fn tufe_not_pit_guard() {
    for c in cases()["index_for_guard"].as_array().unwrap() {
        let row = TufeRow {
            month: "2026-07".into(),
            index: "132.31".into(),
            release_date: c["release_date"].as_str().unwrap().into(),
            bulletin_id: "58297".into(),
            source_url: "https://example.invalid/tufe".into(),
            source_sha256: "0".repeat(64),
        };
        let t = TufeTable::from_rows_unchecked(vec![row]);
        let got = tufe::index_for(c["t"].as_str().unwrap(), &t).map(|_| "ok").unwrap_or_else(|r| r.code);
        assert_eq!(got, c["result"].as_str().unwrap(), "{c}");
    }
}

/// Aylık ekleme komutu Python metniyle birebir (ekranda gösterilir; uygulama çalıştırmaz).
#[test]
fn tufe_append_command_matches_python() {
    let c = cases();
    assert_eq!(tufe::APPEND_COMMAND, c["append_command"].as_str().unwrap());
    assert_eq!(tufe::append_command("2026-09", None), c["append_command_example"].as_str().unwrap());
    // ve Python kaynağındaki dize (gen_golden'dan bağımsız ikinci kanıt)
    let src = std::fs::read_to_string(repo_dir().join("borsai").join("tufe.py")).unwrap();
    let first = tufe::APPEND_COMMAND.split(" --bulletin-id").next().unwrap();
    assert!(src.contains(first), "borsai/tufe.py APPEND_COMMAND başı değişmiş");
}
