//! `borsai.provenance.pretty_json_bytes` ile BAYT-EŞİT JSON yazıcı (SPEC_APP §3e adım 3).
//!
//! Python: `json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"`,
//! UTF-8. serde_json'un `to_string_pretty`'si bu kurala uymaz (bu derlemede `preserve_order` açık,
//! anahtarlar sıralanmaz; float biçimi de Python `repr`'i değildir), bu yüzden yazıcı burada elle
//! yazılmıştır. Denetim: `tests/stage3.rs::inputs_doc_bytes_match_python` NETGL girdi belgesini
//! ayrıştırıp yeniden yazar ve baytları karşılaştırır.
use serde_json::Value;

/// `allow_nan=False`: sonlu olmayan sayı yazılmaz.
pub const NON_FINITE: &str = "NON_FINITE_NUMBER";

/// Python `repr(float)`: en kısa gidiş-dönüş haneler; 1e-4 ≤ |x| < 1e16 sabit, dışı bilimsel.
/// (`src/render/format.ts: pyRepr` ile aynı kural; orada gösterim, burada dosya baytı.)
pub fn py_float(x: f64) -> String {
    if x == 0.0 {
        return if x.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    let sign = if x < 0.0 { "-" } else { "" };
    // {:e} en kısa gidiş-dönüş mantisi verir: "1.2345e-7"
    let sci = format!("{:e}", x.abs());
    let (mant, exp) = sci.split_once('e').expect("{:e} biçimi");
    let e: i32 = exp.parse().expect("üs");
    let digits: String = mant.chars().filter(|c| *c != '.').collect();
    if (-4..16).contains(&e) {
        if e >= 0 {
            let n = (e + 1) as usize;
            let int_part = if digits.len() >= n { digits[..n].to_string() } else { format!("{digits}{}", "0".repeat(n - digits.len())) };
            let frac = if digits.len() > n { &digits[n..] } else { "" };
            return format!("{sign}{int_part}.{}", if frac.is_empty() { "0" } else { frac });
        }
        return format!("{sign}0.{}{digits}", "0".repeat((-e - 1) as usize));
    }
    let m = if digits.len() > 1 { format!("{}.{}", &digits[..1], &digits[1..]) } else { digits };
    format!("{sign}{m}e{}{:02}", if e < 0 { "-" } else { "+" }, e.abs())
}

/// Python `json` kaçışları (ensure_ascii=False): yalnız `"`, `\` ve C0 denetim karakterleri.
fn write_string(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

fn write_value(out: &mut String, v: &Value, depth: usize) -> Result<(), String> {
    let pad = |n: usize| "  ".repeat(n);
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => match (n.as_i64(), n.as_u64(), n.as_f64()) {
            (Some(i), _, _) => out.push_str(&i.to_string()),
            (_, Some(u), _) => out.push_str(&u.to_string()),
            (_, _, Some(f)) if f.is_finite() => out.push_str(&py_float(f)),
            _ => return Err(format!("{NON_FINITE}: {n}")),
        },
        Value::String(s) => write_string(out, s),
        Value::Array(a) if a.is_empty() => out.push_str("[]"),
        Value::Array(a) => {
            out.push_str("[\n");
            for (i, item) in a.iter().enumerate() {
                out.push_str(&pad(depth + 1));
                write_value(out, item, depth + 1)?;
                out.push_str(if i + 1 == a.len() { "\n" } else { ",\n" });
            }
            out.push_str(&pad(depth));
            out.push(']');
        }
        Value::Object(o) if o.is_empty() => out.push_str("{}"),
        Value::Object(o) => {
            // sort_keys=True: Python str karşılaştırması kod noktası sırasıdır; UTF-8 bayt sırası aynıdır.
            let mut keys: Vec<&String> = o.keys().collect();
            keys.sort();
            out.push_str("{\n");
            for (i, k) in keys.iter().enumerate() {
                out.push_str(&pad(depth + 1));
                write_string(out, k);
                out.push_str(": ");
                write_value(out, &o[k.as_str()], depth + 1)?;
                out.push_str(if i + 1 == keys.len() { "\n" } else { ",\n" });
            }
            out.push_str(&pad(depth));
            out.push('}');
        }
    }
    Ok(())
}

/// Dosyaya yazılan baytlar: sıralı anahtar, 2 boşluk girinti, sonda LF.
pub fn pretty_json_bytes(v: &Value) -> Result<Vec<u8>, String> {
    let mut s = String::new();
    write_value(&mut s, v, 0)?;
    s.push('\n');
    Ok(s.into_bytes())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn python_format() {
        let v = json!({"b": 1, "a": ["x", {}, []], "ç": "tırnak \" ve \\ ve \n", "n": null, "t": true});
        let s = String::from_utf8(pretty_json_bytes(&v).unwrap()).unwrap();
        assert_eq!(
            s,
            "{\n  \"a\": [\n    \"x\",\n    {},\n    []\n  ],\n  \"b\": 1,\n  \"n\": null,\n  \"t\": true,\n  \
             \"ç\": \"tırnak \\\" ve \\\\ ve \\n\"\n}\n"
        );
        assert!(pretty_json_bytes(&json!({"x": [1, 2]})).is_ok());
    }

    #[test]
    fn python_repr_floats() {
        assert_eq!(py_float(0.1), "0.1");
        assert_eq!(py_float(1.0), "1.0");
        assert_eq!(py_float(-0.0), "-0.0");
        assert_eq!(py_float(1e16), "1e+16");
        assert_eq!(py_float(1e-5), "1e-05");
        assert_eq!(py_float(0.0001), "0.0001");
        assert_eq!(py_float(1234567890123456.0), "1234567890123456.0");
        assert_eq!(py_float(0.9129597115025806), "0.9129597115025806");
    }
}
