//! U4 + U47: sayısal alan kararları (SPEC_APP §1.3 tablo; EK 2 §2.2–§2.3 kesin bağlam ve limit
//! yolu). Beklenenler Python'dan:
//! `.venv/bin/python app/parity/gen_golden.py --dec-cases` -> app/parity/dec_cases.json.
//!   cargo test -p borsai_predict --test dec_semantics
mod common;

use borsai_predict::dec::{self, Dec, Parsed};
use borsai_predict::path;
use borsai_predict::sum::py_sum;
use common::*;
use num_bigint::BigInt;
use serde_json::Value;

fn cases() -> Value {
    read_json(&app_dir().join("parity").join("dec_cases.json"))
}

fn fin(s: &str) -> Dec {
    match dec::parse(s) {
        Some(Parsed::Finite(d)) => d,
        other => panic!("{s:?}: {other:?}"),
    }
}

fn f(v: &Value) -> f64 {
    match v {
        Value::Number(n) => n.as_f64().unwrap(),
        Value::String(s) if s == "NaN" => f64::NAN,
        Value::String(s) if s == "Infinity" => f64::INFINITY,
        Value::String(s) if s == "-Infinity" => f64::NEG_INFINITY,
        _ => panic!("sayı değil: {v}"),
    }
}

fn same_bits(a: f64, b: f64) -> bool {
    a.to_bits() == b.to_bits() || (a.is_nan() && b.is_nan())
}

/// Python `Decimal(str)`: sonlu/sonlu değil/hata ve (işaret, katsayı, üs) birebir.
#[test]
fn dec_semantics_parse() {
    for c in cases()["parse"].as_array().unwrap() {
        let text = c["text"].as_str().unwrap();
        let got = dec::parse(text);
        match c["result"].as_str().unwrap() {
            "finite" => match got {
                Some(Parsed::Finite(d)) => assert_eq!(d.tuple_text(), c["tuple"].as_str().unwrap(), "{text:?}"),
                other => panic!("{text:?}: beklenen sonlu, Rust {other:?}"),
            },
            "nonfinite" => assert_eq!(got, Some(Parsed::NonFinite), "{text:?}"),
            _ => assert_eq!(got, None, "{text:?}: beklenen hata"),
        }
    }
}

/// `_pct`: 28 hane HALF_EVEN, ×100, 10 ondalık HALF_UP (1/3, 2/3, 5/1e11, çift yuvarlama, 28+ hane).
#[test]
fn dec_semantics_pct() {
    for c in cases()["pct"].as_array().unwrap() {
        let (a, b) = (c["num"].as_str().unwrap(), c["den"].as_str().unwrap());
        let got = dec::pct(&fin(a), &fin(b));
        let want = fin(c["value"].as_str().unwrap());
        assert!(dec::eq(&got, &want), "_pct({a}, {b}): beklenen {}, Rust {}", want.tuple_text(), got.tuple_text());
        assert!(same_bits(got.to_f64(), f(&c["float"])), "_pct({a}, {b}) float");
    }
}

/// f1 = pay × fiyat, 28 hane HALF_EVEN; bağlam taşması Python'da decimal.Overflow.
#[test]
fn dec_semantics_mul28() {
    for c in cases()["mul28"].as_array().unwrap() {
        let (a, b) = (fin(c["a"].as_str().unwrap()), fin(c["b"].as_str().unwrap()));
        let got = dec::mul_round(&a, &b, 28);
        match c["result"].as_str().unwrap() {
            "OVERFLOW" => assert!(got.is_err(), "{c}: taşma bekleniyordu"),
            r => assert!(dec::eq(&got.expect("taşma yok"), &fin(r)), "{c}"),
        }
    }
}

/// `float(Decimal)` doğru yuvarlama (yarı noktalar, alt-normal, taşma).
#[test]
fn dec_semantics_to_float() {
    for c in cases()["to_float"].as_array().unwrap() {
        let t = c["text"].as_str().unwrap();
        assert!(same_bits(fin(t).to_f64(), f(&c["float"])), "float(Decimal({t:?}))");
    }
}

/// CPython 3.12 `sum()` Neumaier toplama; `[1e16, 1, −1e16]` → 1.0.
#[test]
fn dec_semantics_fsum() {
    let all = cases();
    let fs = all["fsum"].as_array().unwrap();
    assert!(fs.iter().any(|c| c["items"] == serde_json::json!([1e16, 1.0, -1e16]) && c["sum"] == serde_json::json!(1.0)));
    for c in fs {
        let items: Vec<f64> = c["items"].as_array().unwrap().iter().map(f).collect();
        assert!(same_bits(py_sum(items.clone()), f(&c["sum"])), "sum({items:?})");
    }
}

/// PB `int / int`: < 2^53 IEEE bölme, üstü BigInt; HALF_EVEN, alt-normal, OverflowError.
#[test]
fn dec_semantics_int_ratio() {
    for c in cases()["int_ratio"].as_array().unwrap() {
        let n: BigInt = c["n"].as_str().unwrap().parse().unwrap();
        let d: BigInt = c["d"].as_str().unwrap().parse().unwrap();
        let got = dec::ratio_to_f64(&n, &d);
        match &c["float"] {
            Value::String(s) if s == "OVERFLOW" => assert!(got.is_err(), "{n}/{d}: taşma bekleniyordu"),
            v => assert!(same_bits(got.expect("taşma yok"), f(v)), "{n}/{d}"),
        }
    }
}

/// PB `_EXACT_CONTEXT` (200 hane, Inexact tuzağı): kesinlik, Emax/Etiny, sadeleşme.
#[test]
fn dec_semantics_exact200() {
    for c in cases()["exact200"].as_array().unwrap() {
        let (a, b) = (fin(c["a"].as_str().unwrap()), fin(c["b"].as_str().unwrap()));
        let got = if c["op"] == "add" { dec::add_exact(&a, &b, 200) } else { dec::mul_exact(&a, &b, 200) };
        match c["result"].as_str().unwrap() {
            "INEXACT" => assert!(got.is_err(), "{} {} {}: Inexact bekleniyordu", c["op"], c["a"], c["b"]),
            r => assert!(dec::eq(&got.expect("kesin"), &fin(r)), "{c}"),
        }
    }
}

/// pb1 = ln(fiyat × taban): §1.3 "≤ 5e-15" (binary64 aralığında); dışında yedek yol ≤ 1e-12.
#[test]
fn dec_semantics_pb1_ln() {
    for c in cases()["pb1_ln"].as_array().unwrap() {
        let v = dec::mul_exact(&fin(c["price"].as_str().unwrap()), &fin(c["base"].as_str().unwrap()), 200).unwrap();
        let got = dec::ln_to_f64(&v);
        let want = f(&c["pb1"]);
        let in_range = v.to_f64().is_finite() && v.to_f64() >= f64::MIN_POSITIVE;
        let tol = if in_range { 5e-15 } else { 1e-12 };
        assert!((got - want).abs() <= tol, "pb1 {c}: Rust {got:?}, |Δ| {:e}", (got - want).abs());
    }
}

// ---------------------------------------------------------------- U47: kesin bağlam ve limit yolu

fn lp() -> Value {
    cases()["limit_path"].clone()
}

/// `div_exact` libmpdec üs kuralı, `to_integral` üs koruması, `py_str`, `ctx_round`.
#[test]
fn dec_semantics_exact_context() {
    let c = lp();
    for r in c["div_exact"].as_array().unwrap() {
        let (a, b) = (fin(r["a"].as_str().unwrap()), fin(r["b"].as_str().unwrap()));
        let got = dec::div_exact(&a, &b, 60);
        match r["result"].as_str().unwrap() {
            "INEXACT" => assert!(got.is_err(), "{r}: Inexact bekleniyordu"),
            want => assert_eq!(dec::py_str(&got.expect("kesin")), want, "{r}"),
        }
    }
    for r in c["to_integral"].as_array().unwrap() {
        let x = fin(r["text"].as_str().unwrap());
        assert_eq!(dec::py_str(&dec::to_integral(&x, dec::Rounding::Floor)), r["floor"].as_str().unwrap(), "floor {r}");
        assert_eq!(
            dec::py_str(&dec::to_integral(&x, dec::Rounding::HalfUp)),
            r["half_up"].as_str().unwrap(),
            "half_up {r}"
        );
    }
    for r in c["py_str"].as_array().unwrap() {
        assert_eq!(dec::py_str(&fin(r["text"].as_str().unwrap())), r["str"].as_str().unwrap(), "{r}");
    }
    for r in c["ctx_round"].as_array().unwrap() {
        let got = dec::mul_ctx(&fin(r["text"].as_str().unwrap()), &fin("1"), 60);
        match r["result"].as_str().unwrap() {
            "INEXACT" | "OVERFLOW" => assert!(got.is_err(), "{r}: hata bekleniyordu"),
            want => assert_eq!(dec::py_str(&got.expect("kesin")), want, "{r}"),
        }
    }
}

/// Fiyat adımı tablosu, üst limit (adım yuvarlanacak değerin KENDİ seviyesinden) ve fiziksel sınırlar.
#[test]
fn dec_semantics_tick_and_bounds() {
    let c = lp();
    for r in c["ticks"].as_array().unwrap() {
        let got = path::tick(&fin(r["x"].as_str().unwrap()));
        assert_eq!(dec::py_str(&got), r["tick"].as_str().unwrap(), "tick {r}");
    }
    for r in c["upper"].as_array().unwrap() {
        let got = path::upper_limit(&fin(r["base"].as_str().unwrap())).expect("kesin");
        assert_eq!(dec::py_str(&got), r["upper"].as_str().unwrap(), "upper {r}");
    }
    for r in c["physical_bounds"].as_array().unwrap() {
        let m = r["m"].as_i64().unwrap() as i32;
        let (lo, hi) = path::physical_bounds(m);
        assert!(same_bits(lo, f(&r["lo"])), "m = {m} alt sınır: Rust {lo:?}, Python {}", r["lo"]);
        assert!(same_bits(hi, f(&r["hi"])), "m = {m} üst sınır: Rust {hi:?}, Python {}", r["hi"]);
    }
}

/// U47 limit yolu tablosu: `ipo_price`, `snapped_ipo_price`, `tick`, `C[k]` metin BİREBİR; `rho`/`scale`
/// bit-eşit; `decimal.Inexact` -> DOMAIN_ERROR.
#[test]
fn dec_semantics_limit_path() {
    let rows = lp();
    let rows = rows["rows"].as_array().unwrap();
    assert!(rows.len() >= 14, "§2.3 tablosu en az 14 satır: {}", rows.len());
    for r in rows {
        let price = fin(r["text"].as_str().unwrap());
        let got = path::limit_path(&price);
        if let Some(exc) = r.get("exception").and_then(Value::as_str) {
            let e = got.expect_err(&format!("{r}: {exc} bekleniyordu"));
            assert_eq!(e.code, borsai_predict::error::DOMAIN_ERROR, "{r}");
            continue;
        }
        let g = got.unwrap_or_else(|e| panic!("{r}: {e}"));
        assert_eq!(dec::py_str(&g.price), r["ipo_price"].as_str().unwrap(), "ipo_price {}", r["text"]);
        assert_eq!(dec::py_str(&g.snapped), r["snapped"].as_str().unwrap(), "snapped {}", r["text"]);
        assert_eq!(dec::py_str(&g.tick), r["tick"].as_str().unwrap(), "tick {}", r["text"]);
        let want_c: Vec<&str> = r["C"].as_array().unwrap().iter().map(|v| v.as_str().unwrap()).collect();
        let got_c: Vec<String> = g.c.iter().map(dec::py_str).collect();
        assert_eq!(got_c, want_c, "C {}", r["text"]);
        for (i, want) in r["rho"].as_array().unwrap().iter().enumerate() {
            assert!(same_bits(g.rho[i], f(want)), "rho[{i}] {}: Rust {:?}, Python {want}", r["text"], g.rho[i]);
        }
        for (i, want) in r["scale"].as_array().unwrap().iter().enumerate() {
            assert!(same_bits(g.scale[i], f(want)), "scale[{i}] {}: Rust {:?}", r["text"], g.scale[i]);
        }
        // uyarı koşulu: DEĞER eşitsizliği ("136" ↔ "136.0" uyarı vermez)
        assert_eq!(!dec::eq(&g.snapped, &price), r["warning"].as_bool().unwrap(), "uyarı {}", r["text"]);
    }
}

/// U56 (SPEC_APP EK 3 §2.3, §4.2): `real_size` = büyüklük / (TÜFE / 100), 60 hane; metin (`str(Decimal)`) ve
/// binary64 birebir, taşma DOMAIN_ERROR; k-katı değişmezliği (Δ = 0).
#[test]
fn dec_semantics_real_size() {
    let rows = cases()["real_size"].as_array().unwrap().clone();
    assert!(rows.len() >= 7);
    let mut floats = std::collections::BTreeMap::new();
    for c in &rows {
        let (size, idx) = (c["size"].as_str().unwrap(), c["tufe_index"].as_str().unwrap());
        let got = borsai_predict::hazard::real_size(&fin(size), &fin(idx));
        match c["f1r_dec"].as_str().unwrap() {
            "OVERFLOW" => {
                let e = got.expect_err(&format!("{size}/{idx}: taşma bekleniyordu"));
                assert_eq!(e.code, borsai_predict::error::DOMAIN_ERROR);
            }
            text => {
                let d = got.unwrap_or_else(|e| panic!("{size}/{idx}: {e}"));
                assert_eq!(dec::py_str(&d), text, "{size}/{idx}: str(Decimal)");
                assert!(same_bits(d.to_f64(), f(&c["float"])), "{size}/{idx}: float {} != {}", d.to_f64(), c["float"]);
                floats.insert((size, idx), d.to_f64());
            }
        }
    }
    let k = floats[&("4466000000", "269.5")];
    assert_eq!(k.to_bits(), floats[&("2233000000", "134.75")].to_bits(), "k-katı değişmezliği");
    assert_eq!(k.to_bits(), floats[&("2233000000", "134.750")].to_bits());
}
