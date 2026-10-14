//! Fikstür karşılaştırması, macOS dışı (FAZ9_WINDOWS K-WIN-5). macOS'ta fikstür metni bayt bayt aynı olmalıdır (çağıran
//! `cfg!(target_os = "macos")` dalında eski iddia aynen durur). Windows libm'i `exp`/`ln`/`powi`'de son basamakta farklı
//! sonuç verir; orada JSON ayrıştırılır: yapı, anahtarlar ve sıraları, metinler, mantıksal değerler, null ve tamsayılar
//! birebir; kayan noktalı sayılar |Δ| ≤ 1e-9 (SPEC_APP §1.3 parite toleransı). Tolerans içindeki her fark
//! `CARGO_TARGET_TMPDIR/fixture_numeric/<fikstür>.txt`'ye yazılır (CI dökümü).
use serde_json::Value;

pub const NUM_TOL: f64 = 1e-9;

/// Sayısal fark satırları (JSON işaretçisi, diskteki, üretilen, |Δ|) ve tolerans dışı / sayısal olmayan farklar.
#[derive(Default)]
pub struct Diff {
    pub numeric: Vec<String>,
    pub errors: Vec<String>,
}

pub fn compare(disk: &str, text: &str) -> Diff {
    let mut d = Diff::default();
    match (serde_json::from_str::<Value>(disk), serde_json::from_str::<Value>(text)) {
        (Ok(a), Ok(b)) => walk("", &a, &b, &mut d),
        (a, b) => d.errors.push(format!("JSON ayrıştırılamadı: disk {:?}, üretilen {:?}", a.err(), b.err())),
    }
    d
}

fn walk(at: &str, a: &Value, b: &Value, d: &mut Diff) {
    match (a, b) {
        (Value::Object(x), Value::Object(y)) => {
            let (kx, ky): (Vec<&String>, Vec<&String>) = (x.keys().collect(), y.keys().collect());
            if kx != ky {
                d.errors.push(format!("{at}: anahtarlar {kx:?} ≠ {ky:?}"));
                return;
            }
            for (k, v) in x {
                walk(&format!("{at}/{k}"), v, &y[k], d);
            }
        }
        (Value::Array(x), Value::Array(y)) => {
            if x.len() != y.len() {
                d.errors.push(format!("{at}: uzunluk {} ≠ {}", x.len(), y.len()));
                return;
            }
            for (i, (v, w)) in x.iter().zip(y).enumerate() {
                walk(&format!("{at}/{i}"), v, w, d);
            }
        }
        (Value::Number(x), Value::Number(y)) if x.is_f64() && y.is_f64() => {
            let (p, q) = (x.as_f64().unwrap(), y.as_f64().unwrap());
            if p != q {
                let delta = (p - q).abs();
                let line = format!("{at}: {p:?} → {q:?} |Δ| {delta:e}");
                if delta <= NUM_TOL {
                    d.numeric.push(line);
                } else {
                    d.errors.push(format!("{line} > {NUM_TOL:e}"));
                }
            }
        }
        _ if a == b => {}
        _ => d.errors.push(format!("{at}: {a} ≠ {b}")),
    }
}

/// macOS dışı fikstür iddiası: sayısal olmayan fark ya da tolerans dışı sayı → KIRMIZI (bütün farklar mesajda).
pub fn assert_close(name: &str, disk: &str, text: &str, update_hint: &str) {
    assert!(!disk.is_empty(), "{name} yok; {update_hint}");
    if disk == text {
        return;
    }
    let d = compare(disk, text);
    assert!(
        d.errors.is_empty(),
        "{name}: sayısal olmayan ya da tolerans dışı fark ({} adet; {update_hint}):\n{}",
        d.errors.len(),
        d.errors.iter().take(40).cloned().collect::<Vec<_>>().join("\n")
    );
    let dir = std::path::Path::new(env!("CARGO_TARGET_TMPDIR")).join("fixture_numeric");
    let _ = std::fs::create_dir_all(&dir);
    let _ = std::fs::write(dir.join(format!("{name}.txt")), d.numeric.join("\n") + "\n");
}
