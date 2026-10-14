//! Python `decimal` davranışının predict yolunun kullandığı kadarı (SPEC_APP §1.3 sayısal kararlar).
//!
//! - Ayrıştırma: `Decimal(str(value).strip())` (CPython 3.12 `_decimal` + libmpdec): Unicode boşluk
//!   kırpma, alt çizgilerin atılması, Unicode ondalık rakamların ASCII'ye çevrilmesi, `inf`/`nan`,
//!   tam kesinlik ve üs sınırları (`MAX_EMAX`, `MIN_ETINY`). Değer kesin tutulur: katsayı × 10^üs.
//! - 28 anlamlı hane ROUND_HALF_EVEN çarpma/bölme (`LEGACY_DECIMAL_CONTEXT`), 10 ondalığa
//!   ROUND_HALF_UP (`_pct`), 200 haneli kesin toplama/çarpma (`_EXACT_CONTEXT`, Inexact tuzağı).
//! - Decimal → binary64: ondalık metne yazılır, `str::parse::<f64>()` ile doğru yuvarlanır.
//! - Tamsayı oranı → binary64: `int / int` gibi doğru yuvarlanmış (HALF_EVEN, alt-normal dahil).
use num_bigint::{BigInt, BigUint, Sign};
use num_integer::Integer;
use num_traits::{One, Signed, ToPrimitive, Zero};
use std::cmp::Ordering;

/// libmpdec `MPD_MAX_EMAX` (64 bit): `Decimal(str)` bu düzeltilmiş üssü aşan metni reddeder.
pub const MAX_EMAX: i64 = 999_999_999_999_999_999;
/// libmpdec `MPD_MIN_ETINY` (64 bit): daha küçük üs `Decimal(str)`'de reddedilir.
pub const MIN_ETINY: i64 = -1_999_999_999_999_999_997;
/// Python varsayılan bağlamı (`Context(prec=28)` ve `Context(prec=200)`): Emax/Emin.
pub const CTX_EMAX: i64 = 999_999;
pub const CTX_EMIN: i64 = -999_999;

/// Kesin ondalık: (-1)^neg × coeff × 10^exp. Sıfırın işareti tutulur ama değerde önemsizdir.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Dec {
    pub neg: bool,
    pub coeff: BigUint,
    pub exp: i64,
}

/// `Decimal(metin)` sonucu.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Parsed {
    Finite(Dec),
    /// Infinity, NaN, sNaN (Decimal oluşur ama `is_finite()` yanlış).
    NonFinite,
}

// ---------------------------------------------------------------- Unicode tabloları (Python 3.12, Unicode 15.0.0)

/// `str.isspace()` doğru olan karakterler (CPython 3.12.14'ten üretildi).
const PY_SPACE: [u32; 29] = [
    0x9, 0xa, 0xb, 0xc, 0xd, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003,
    0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000,
];

/// `unicodedata.decimal(ch) == 0` olan karakterler; her blok 0..9 ardışık (CPython 3.12.14'ten üretildi).
const ND_ZEROS: [u32; 68] = [
    0x30, 0x660, 0x6f0, 0x7c0, 0x966, 0x9e6, 0xa66, 0xae6, 0xb66, 0xbe6, 0xc66, 0xce6, 0xd66, 0xde6, 0xe50,
    0xed0, 0xf20, 0x1040, 0x1090, 0x17e0, 0x1810, 0x1946, 0x19d0, 0x1a80, 0x1a90, 0x1b50, 0x1bb0, 0x1c40,
    0x1c50, 0xa620, 0xa8d0, 0xa900, 0xa9d0, 0xa9f0, 0xaa50, 0xabf0, 0xff10, 0x104a0, 0x10d30, 0x11066,
    0x110f0, 0x11136, 0x111d0, 0x112f0, 0x11450, 0x114d0, 0x11650, 0x116c0, 0x11730, 0x118e0, 0x11950,
    0x11c50, 0x11d50, 0x11da0, 0x11f50, 0x16a60, 0x16ac0, 0x16b50, 0x1d7ce, 0x1d7d8, 0x1d7e2, 0x1d7ec,
    0x1d7f6, 0x1e140, 0x1e2f0, 0x1e4f0, 0x1e950, 0x1fbf0,
];

pub fn py_isspace(ch: char) -> bool {
    PY_SPACE.contains(&(ch as u32))
}

fn unicode_decimal(ch: char) -> Option<u32> {
    let c = ch as u32;
    ND_ZEROS.iter().find(|&&z| c >= z && c < z + 10).map(|z| c - z)
}

/// Python `str.strip()`.
pub fn py_strip(s: &str) -> &str {
    s.trim_matches(py_isspace)
}

// ---------------------------------------------------------------- ayrıştırma

/// `Decimal(s)` (s bir `str`). `None`: InvalidOperation (ConversionSyntax ya da kesin olmayan üs).
pub fn parse(s: &str) -> Option<Parsed> {
    // _decimal numeric_as_ascii: önce Unicode boşluk kırpma, sonra dönüştürme.
    let stripped = py_strip(s);
    let mut ascii = String::with_capacity(stripped.len());
    for ch in stripped.chars() {
        if ch == '_' {
            continue;
        }
        let c = ch as u32;
        if c > 0 && c <= 127 {
            ascii.push(ch);
        } else if py_isspace(ch) {
            ascii.push(' ');
        } else if let Some(d) = unicode_decimal(ch) {
            ascii.push(char::from(b'0' + d as u8));
        } else {
            return None;
        }
    }
    parse_ascii(ascii.as_bytes())
}

fn eq_ci(s: &[u8], lower: &[u8]) -> bool {
    s.len() >= lower.len() && s.iter().zip(lower).all(|(a, b)| a.to_ascii_lowercase() == *b)
}

/// libmpdec `mpd_qset_string` + tam kesinlikli bitiş (`PyDecType_FromCStringExact`).
fn parse_ascii(b: &[u8]) -> Option<Parsed> {
    let mut i = 0;
    let mut neg = false;
    if b.first() == Some(&b'+') {
        i = 1;
    } else if b.first() == Some(&b'-') {
        neg = true;
        i = 1;
    }
    let s = &b[i..];
    if eq_ci(s, b"nan") || eq_ci(s, b"snan") {
        let rest = if eq_ci(s, b"nan") { &s[3..] } else { &s[4..] };
        // yük (payload) yalnız rakam
        return rest.iter().all(|c| c.is_ascii_digit()).then_some(Parsed::NonFinite);
    }
    if eq_ci(s, b"inf") {
        let rest = &s[3..];
        return (rest.is_empty() || (rest.len() == 5 && eq_ci(rest, b"inity"))).then_some(Parsed::NonFinite);
    }
    // scan_dpoint_exp
    let mut dpoint: Option<usize> = None;
    let mut exp_at: Option<usize> = None;
    let mut have_coeff_digit = false;
    let mut k = 0;
    while k < s.len() {
        match s[k] {
            b'.' => {
                if dpoint.is_some() || exp_at.is_some() {
                    return None;
                }
                dpoint = Some(k);
            }
            b'e' | b'E' => {
                if exp_at.is_some() {
                    return None;
                }
                exp_at = Some(k);
                if k + 1 < s.len() && (s[k + 1] == b'+' || s[k + 1] == b'-') {
                    k += 1;
                }
            }
            c if c.is_ascii_digit() => {
                if exp_at.is_none() {
                    have_coeff_digit = true;
                }
            }
            _ => return None,
        }
        k += 1;
    }
    if !have_coeff_digit {
        return None;
    }
    let coeff_end = exp_at.unwrap_or(s.len());
    // üs: strtoll anlamı (doygun), boş ya da rakamsız -> hata
    let mut exp: i128 = 0;
    if let Some(e) = exp_at {
        let t = &s[e + 1..];
        let (eneg, digits) = match t.first() {
            Some(b'+') => (false, &t[1..]),
            Some(b'-') => (true, &t[1..]),
            _ => (false, t),
        };
        if digits.is_empty() {
            return None;
        }
        let mut v: i128 = 0;
        for &c in digits {
            v = (v * 10 + (c - b'0') as i128).min(i128::from(i64::MAX) + 1);
        }
        exp = if eneg { -v } else { v };
    }
    let mut digits = String::with_capacity(coeff_end);
    let mut frac = 0i128;
    for (idx, &c) in s[..coeff_end].iter().enumerate() {
        if c == b'.' {
            continue;
        }
        digits.push(c as char);
        if matches!(dpoint, Some(d) if idx > d) {
            frac += 1;
        }
    }
    let coeff: BigUint = digits.parse().ok()?;
    let exp = exp - frac;
    let nd = ndigits(&coeff) as i128;
    let adjusted = exp + nd - 1;
    if adjusted > MAX_EMAX as i128 || exp < MIN_ETINY as i128 {
        return None;
    }
    Some(Parsed::Finite(Dec { neg, coeff, exp: exp as i64 }))
}

// ---------------------------------------------------------------- temel işlemler

pub fn ndigits(x: &BigUint) -> i64 {
    if x.is_zero() {
        1
    } else {
        x.to_str_radix(10).len() as i64
    }
}

pub fn pow10(n: u64) -> BigUint {
    assert!(n <= u32::MAX as u64, "pow10: üs çok büyük ({n})");
    BigUint::from(10u32).pow(n as u32)
}

impl Dec {
    pub fn zero() -> Dec {
        Dec { neg: false, coeff: BigUint::zero(), exp: 0 }
    }

    pub fn from_i64(v: i64) -> Dec {
        Dec { neg: v < 0, coeff: BigUint::from(v.unsigned_abs()), exp: 0 }
    }

    pub fn is_zero(&self) -> bool {
        self.coeff.is_zero()
    }

    /// -1, 0, 1
    pub fn signum(&self) -> i32 {
        if self.is_zero() {
            0
        } else if self.neg {
            -1
        } else {
            1
        }
    }

    /// Düzeltilmiş üs (en yüksek hanenin konumu).
    pub fn adjusted(&self) -> i128 {
        self.exp as i128 + ndigits(&self.coeff) as i128 - 1
    }

    /// Sondaki sıfırları atılmış eşdeğer (değer aynı). Sıfır için katsayı 0, üs korunur.
    pub fn stripped(&self) -> Dec {
        if self.is_zero() {
            return self.clone();
        }
        let s = self.coeff.to_str_radix(10);
        let trimmed = s.trim_end_matches('0');
        let tz = (s.len() - trimmed.len()) as i64;
        Dec { neg: self.neg, coeff: trimmed.parse().unwrap(), exp: self.exp + tz }
    }

    /// Doğru yuvarlanmış binary64 (Python `float(Decimal)`).
    pub fn to_f64(&self) -> f64 {
        let text = format!("{}{}e{}", if self.neg { "-" } else { "" }, self.coeff, self.exp);
        text.parse::<f64>().expect("ondalık metin f64'e ayrıştırılamadı")
    }

    /// Python `str(Decimal)` değil; sınama için kanonik (işaret, katsayı, üs) metni.
    pub fn tuple_text(&self) -> String {
        format!("{}|{}|{}", if self.neg { 1 } else { 0 }, self.coeff, self.exp)
    }

    /// Kesin rasyonel (pay, payda > 0), `Decimal.as_integer_ratio()` gibi ama sadeleştirilmemiş.
    pub fn as_ratio(&self) -> (BigInt, BigInt) {
        if self.is_zero() {
            return (BigInt::zero(), BigInt::one());
        }
        let s = self.stripped();
        let sign = if s.neg { Sign::Minus } else { Sign::Plus };
        if s.exp >= 0 {
            (BigInt::from_biguint(sign, s.coeff * pow10(s.exp as u64)), BigInt::one())
        } else {
            (BigInt::from_biguint(sign, s.coeff), BigInt::from(pow10((-s.exp) as u64)))
        }
    }
}

/// Kesin değer karşılaştırması.
pub fn cmp(a: &Dec, b: &Dec) -> Ordering {
    let (sa, sb) = (a.signum(), b.signum());
    if sa != sb {
        return sa.cmp(&sb);
    }
    if sa == 0 {
        return Ordering::Equal;
    }
    let m = cmp_mag(a, b);
    if sa > 0 {
        m
    } else {
        m.reverse()
    }
}

fn cmp_mag(a: &Dec, b: &Dec) -> Ordering {
    let (aa, ab) = (a.adjusted(), b.adjusted());
    if aa != ab {
        return aa.cmp(&ab);
    }
    // düzeltilmiş üsler eşit: kaydırma basamak sayıları farkıyla sınırlı
    match a.exp.cmp(&b.exp) {
        Ordering::Equal => a.coeff.cmp(&b.coeff),
        Ordering::Greater => (&a.coeff * pow10((a.exp - b.exp) as u64)).cmp(&b.coeff),
        Ordering::Less => a.coeff.cmp(&(&b.coeff * pow10((b.exp - a.exp) as u64))),
    }
}

pub fn eq(a: &Dec, b: &Dec) -> bool {
    cmp(a, b) == Ordering::Equal
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Rounding {
    HalfEven,
    /// decimal.ROUND_HALF_UP: yarıda sıfırdan uzağa.
    HalfUp,
    /// decimal.ROUND_FLOOR: −∞'a doğru. `round_drop` büyüklük üzerinde çalıştığından yalnız
    /// `to_integral` bu modu doğru (işaretli) uygular; pozitif değerlerde kesme ile aynıdır.
    Floor,
}

/// Katsayıyı `drop` hane kısalt; (yeni katsayı, üste eklenecek) — büyüklük üzerinde.
fn round_drop(coeff: &BigUint, drop: u64, mode: Rounding) -> BigUint {
    if drop == 0 {
        return coeff.clone();
    }
    let p = pow10(drop);
    let (q, r) = coeff.div_rem(&p);
    let twice = &r * 2u32;
    if mode == Rounding::Floor {
        return q;
    }
    let up = match twice.cmp(&p) {
        Ordering::Greater => true,
        Ordering::Less => false,
        Ordering::Equal => match mode {
            Rounding::HalfUp => true,
            Rounding::HalfEven => q.is_odd(),
            Rounding::Floor => false,
        },
    };
    if up {
        q + 1u32
    } else {
        q
    }
}

/// `prec` anlamlı haneye yuvarla (bağlam yuvarlaması).
pub fn round_sig(x: &Dec, prec: u64, mode: Rounding) -> Dec {
    let nd = ndigits(&x.coeff) as u64;
    if nd <= prec {
        return x.clone();
    }
    let drop = nd - prec;
    let mut q = round_drop(&x.coeff, drop, mode);
    let mut exp = x.exp + drop as i64;
    if ndigits(&q) as u64 > prec {
        q /= 10u32;
        exp += 1;
    }
    Dec { neg: x.neg, coeff: q, exp }
}

/// `quantize(Decimal(1).scaleb(-places), rounding)`: `places` ondalığa yuvarla.
pub fn quantize(x: &Dec, places: i64, mode: Rounding) -> Dec {
    let target = -places;
    if x.exp >= target {
        return x.clone();
    }
    let drop = (target - x.exp) as u64;
    // drop katsayı hanesinden büyükse sonuç 0 ya da 1 birim
    let nd = ndigits(&x.coeff) as u64;
    let coeff = if drop > nd + 1 {
        BigUint::zero()
    } else {
        round_drop(&x.coeff, drop, mode)
    };
    Dec { neg: x.neg, coeff, exp: target }
}

/// Bağlam taşması (Python `decimal.Overflow` tuzağı).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Overflow;

/// `Context(prec, ROUND_HALF_EVEN)` içinde a × b. Düzeltilmiş üs `CTX_EMAX`'ı aşarsa Overflow.
pub fn mul_round(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, Overflow> {
    let exact = Dec { neg: a.neg != b.neg, coeff: &a.coeff * &b.coeff, exp: a.exp + b.exp };
    let r = round_sig(&exact, prec, Rounding::HalfEven);
    if !r.is_zero() && r.adjusted() > CTX_EMAX as i128 {
        return Err(Overflow);
    }
    Ok(r)
}

/// `Context(prec, ROUND_HALF_EVEN)` içinde a / b (b ≠ 0). Doğru yuvarlanmış bölüm.
pub fn div_round(a: &Dec, b: &Dec, prec: u64) -> Dec {
    assert!(!b.is_zero(), "div_round: payda sıfır");
    let neg = a.neg != b.neg;
    if a.is_zero() {
        return Dec { neg, coeff: BigUint::zero(), exp: 0 };
    }
    let (da, db) = (ndigits(&a.coeff), ndigits(&b.coeff));
    let mut s: i64 = prec as i64 - (da - db);
    loop {
        let (num, den) = if s >= 0 {
            (&a.coeff * pow10(s as u64), b.coeff.clone())
        } else {
            (a.coeff.clone(), &b.coeff * pow10((-s) as u64))
        };
        let (q, r) = num.div_rem(&den);
        let nq = ndigits(&q) as u64;
        if nq > prec {
            s -= 1;
            continue;
        }
        if nq < prec {
            s += 1;
            continue;
        }
        let twice = &r * 2u32;
        let up = match twice.cmp(&den) {
            Ordering::Greater => true,
            Ordering::Less => false,
            Ordering::Equal => q.is_odd(),
        };
        let mut q = if up { q + 1u32 } else { q };
        if ndigits(&q) as u64 > prec {
            q /= 10u32;
            s -= 1;
        }
        return Dec { neg, coeff: q, exp: a.exp - b.exp - s };
    }
}

/// `features._pct`: 28 hanede num/den, ×100, 10 ondalığa ROUND_HALF_UP.
pub fn pct(num: &Dec, den: &Dec) -> Dec {
    let q = div_round(num, den, 28);
    // q ≤ 28 hane: ×100 28 haneye yuvarlanınca yalnız iki sıfır düşer, değer kesin.
    let raw = Dec { neg: q.neg, coeff: q.coeff, exp: q.exp + 2 };
    quantize(&raw, 10, Rounding::HalfUp)
}

/// `Context(prec=200)` + Inexact tuzağı: kesin değilse (ya da Overflow) hata.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Inexact;

fn check_exact(x: Dec, prec: u64) -> Result<Dec, Inexact> {
    if x.is_zero() {
        return Ok(x);
    }
    let s = x.stripped();
    let etiny = CTX_EMIN - (prec as i64 - 1);
    if ndigits(&s.coeff) as u64 > prec || s.adjusted() > CTX_EMAX as i128 || s.exp < etiny {
        return Err(Inexact);
    }
    Ok(x)
}

pub fn add_exact(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, Inexact> {
    if a.is_zero() && b.is_zero() {
        return Ok(Dec::zero());
    }
    if a.is_zero() {
        return check_exact(b.clone(), prec);
    }
    if b.is_zero() {
        return check_exact(a.clone(), prec);
    }
    let (sa, sb) = (a.stripped(), b.stripped());
    let (adj_a, adj_b) = (sa.adjusted(), sb.adjusted());
    let spread = adj_a.max(adj_b) - (sa.exp.min(sb.exp) as i128);
    if (adj_a - adj_b).abs() >= 2 && sa.exp != sb.exp && spread > prec as i128 + 1 {
        // ℓ_a ≠ ℓ_b: toplamın en düşük sıfır olmayan hanesi min(ℓ), en yükseği ≥ max(adj) − 1: > prec hane
        return Err(Inexact);
    }
    let e = sa.exp.min(sb.exp);
    let ia = BigInt::from_biguint(if sa.neg { Sign::Minus } else { Sign::Plus }, sa.coeff * pow10((sa.exp - e) as u64));
    let ib = BigInt::from_biguint(if sb.neg { Sign::Minus } else { Sign::Plus }, sb.coeff * pow10((sb.exp - e) as u64));
    let sum = ia + ib;
    let neg = sum.is_negative();
    check_exact(Dec { neg, coeff: sum.magnitude().clone(), exp: e }, prec)
}

pub fn mul_exact(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, Inexact> {
    check_exact(Dec { neg: a.neg != b.neg, coeff: &a.coeff * &b.coeff, exp: a.exp + b.exp }, prec)
}

// ------------------------------------------- kesin bağlam (SPEC_CEILING_PATH_V0 §2 limit yolu)
//
// Python `predict_path._EXACT` = `Context(prec=60, ROUND_HALF_EVEN, traps=[InvalidOperation,
// DivisionByZero, Overflow, Inexact])`. Bu bağlamda bölme ve çarpma KESİN olmak zorundadır; kesin
// olmayan (ya da taşan) işlem etiketsiz istisna fırlatır ve Rust'ta `DOMAIN_ERROR` olur.
// Kesinlik yeterli değildir: sonucun ÜSSÜ de metne yansır (`str(C)` alanları birebir sınanır).

/// Bağlam yuvarlaması: katsayı `prec` haneyi aşarsa fazla haneler atılır; atılan haneler sıfır
/// değilse `Inexact`. Sondaki sıfırlar atılmaz (üs yükselir). Taşma ve Etiny altı da `Inexact`
/// (Python'da `Overflow` / `Inexact` tuzağı; ikisi de etiketsiz istisna → `DOMAIN_ERROR`).
pub fn ctx_round(x: &Dec, prec: u64) -> Result<Dec, Inexact> {
    if x.is_zero() {
        return Ok(x.clone());
    }
    let mut r = x.clone();
    let nd = ndigits(&r.coeff) as u64;
    if nd > prec {
        let drop = nd - prec;
        let (q, rem) = r.coeff.div_rem(&pow10(drop));
        if !rem.is_zero() {
            return Err(Inexact);
        }
        r = Dec { neg: r.neg, coeff: q, exp: r.exp + drop as i64 };
    }
    if r.adjusted() > CTX_EMAX as i128 {
        return Err(Inexact); // decimal.Overflow (tuzaklı)
    }
    let etiny = CTX_EMIN - (prec as i64 - 1);
    if r.exp < etiny {
        let drop = (etiny - r.exp) as u64;
        if drop > ndigits(&r.coeff) as u64 {
            return Err(Inexact);
        }
        let (q, rem) = r.coeff.div_rem(&pow10(drop));
        if !rem.is_zero() {
            return Err(Inexact);
        }
        r = Dec { neg: r.neg, coeff: q, exp: etiny };
    }
    Ok(r)
}

/// Kesin bağlamda çarpma: katsayılar çarpılır, üsler toplanır, sonra `ctx_round`.
pub fn mul_ctx(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, Inexact> {
    ctx_round(&Dec { neg: a.neg != b.neg, coeff: &a.coeff * &b.coeff, exp: a.exp + b.exp }, prec)
}

/// Kesin bağlamda bölme (libmpdec üs kuralı). Değer v = a/b kesin olmalıdır; sonucun üssü
/// `ideal = exp(a) − exp(b)`'den küçük ya da eşit, `v·10^(−e)` tamsayı olan EN BÜYÜK e'dir
/// (v = 0 için `e = ideal`). Ölçümler: `30.2500/0.02 → 1512.50`, `1E+2/0.10 → 1E+3`,
/// `100/0.10 → 1.0E+3`, `1/0.25 → 4`, `0/0.10 → 0E+2`, `110.0/0.10 → 1.10E+3`.
pub fn div_exact(a: &Dec, b: &Dec, prec: u64) -> Result<Dec, Inexact> {
    assert!(!b.is_zero(), "div_exact: payda sıfır");
    let neg = a.neg != b.neg;
    let ideal = a.exp - b.exp;
    if a.is_zero() {
        return ctx_round(&Dec { neg, coeff: BigUint::zero(), exp: ideal }, prec);
    }
    // B' = B / gcd(A, B) yalnız 2 ve 5 çarpanlıysa bölme kesindir; k = max(i, j) en küçük kaydırma.
    let g = a.coeff.gcd(&b.coeff);
    let mut rest = &b.coeff / &g;
    let two = BigUint::from(2u32);
    let five = BigUint::from(5u32);
    let (mut i, mut j) = (0u64, 0u64);
    while (&rest % &two).is_zero() {
        rest /= &two;
        i += 1;
    }
    while (&rest % &five).is_zero() {
        rest /= &five;
        j += 1;
    }
    if !rest.is_one() {
        return Err(Inexact);
    }
    let k = i.max(j);
    let coeff = (&a.coeff * pow10(k)) / &b.coeff;
    ctx_round(&Dec { neg, coeff, exp: ideal - k as i64 }, prec)
}

/// `Decimal.to_integral_value(rounding)`: `exp ≥ 0` ise değer ve ÜS korunur (`1E+3` → `1E+3`),
/// `exp < 0` ise 0 ondalığa yuvarlanır. `Floor` negatifte sıfırdan uzağa (ROUND_FLOOR).
pub fn to_integral(x: &Dec, mode: Rounding) -> Dec {
    if x.exp >= 0 {
        return x.clone();
    }
    if mode != Rounding::Floor {
        return quantize(x, 0, mode);
    }
    let drop = (-x.exp) as u64;
    let nd = ndigits(&x.coeff) as u64;
    let (q, rem) = if drop > nd {
        (BigUint::zero(), !x.coeff.is_zero())
    } else {
        let (q, r) = x.coeff.div_rem(&pow10(drop));
        (q, !r.is_zero())
    };
    let coeff = if x.neg && rem { q + 1u32 } else { q };
    Dec { neg: x.neg, coeff, exp: 0 }
}

/// CPython `Decimal.__str__` (bilimsel olmayan `to_sci_string`). Ölçümler: `1E2 → "1E+2"`,
/// `0.0000001 → "1E-7"`, `0.000001 → "0.000001"`, `10 → "10"`, `1.0 → "1.0"`, `0E-2 → "0.00"`,
/// `25.520 → "25.520"`, `1e400 → "1E+400"`, `0E+2 → "0E+2"`.
pub fn py_str(x: &Dec) -> String {
    let d = x.coeff.to_str_radix(10);
    let len = d.len() as i128;
    let e = x.exp as i128;
    let left = e + len;
    let dot = if e <= 0 && left > -6 { left } else { 1 };
    let mut out = String::new();
    if x.neg {
        out.push('-');
    }
    if dot <= 0 {
        out.push_str("0.");
        for _ in 0..(-dot) {
            out.push('0');
        }
        out.push_str(&d);
    } else if dot >= len {
        out.push_str(&d);
        for _ in 0..(dot - len) {
            out.push('0');
        }
    } else {
        out.push_str(&d[..dot as usize]);
        out.push('.');
        out.push_str(&d[dot as usize..]);
    }
    if left != dot {
        out.push('E');
        out.push(if left - dot >= 0 { '+' } else { '-' });
        out.push_str(&(left - dot).abs().to_string());
    }
    out
}

// ---------------------------------------------------------------- oran -> binary64

/// Python `int / int` taşması (`OverflowError: integer division result too large for a float`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FloatOverflow;

/// n / d (d ≠ 0), doğru yuvarlanmış binary64 (HALF_EVEN, alt-normal dahil). SPEC_APP §1.3:
/// pay ve payda < 2^53 ise IEEE bölmesi (bit-eşit), değilse BigInt ile 55 bit + yapışkan bit.
pub fn ratio_to_f64(n: &BigInt, d: &BigInt) -> Result<f64, FloatOverflow> {
    assert!(!d.is_zero(), "ratio_to_f64: payda sıfır");
    if n.is_zero() {
        return Ok(0.0);
    }
    let neg = n.is_negative() != d.is_negative();
    let (a, b) = (n.magnitude(), d.magnitude());
    let r = if a.bits() <= 53 && b.bits() <= 53 {
        a.to_f64().unwrap() / b.to_f64().unwrap()
    } else {
        big_ratio_to_f64(a, b)?
    };
    Ok(if neg { -r } else { r })
}

fn big_ratio_to_f64(a: &BigUint, b: &BigUint) -> Result<f64, FloatOverflow> {
    // q = floor(a·2^k / b), 2^54 ≤ q < 2^55; değer = (q + yapışkan) · 2^-k
    let mut k: i64 = 54 - (a.bits() as i64 - b.bits() as i64);
    let (q, sticky) = loop {
        let (num, den) = if k >= 0 { (a << (k as u64), b.clone()) } else { (a.clone(), b << ((-k) as u64)) };
        let (q, r) = num.div_rem(&den);
        match q.bits() {
            56.. => k -= 1,
            0..=54 => k += 1,
            _ => break (q, !r.is_zero()),
        }
    };
    let e = 54 - k; // en yüksek bitin üssü
    if e > 1023 {
        return Err(FloatOverflow);
    }
    // tutulan en düşük bitin üssü: normalde e − 52, alt-normalde −1074
    let lsb = (e - 52).max(-1074);
    let drop = (lsb + k) as u64; // q'dan atılacak bit sayısı (≥ 2)
    let (kept, round_up) = if drop > q.bits() + 1 {
        (BigUint::zero(), false)
    } else {
        let kept = &q >> drop;
        let rem = &q - (&kept << drop);
        let half = BigUint::one() << (drop - 1);
        let up = match rem.cmp(&half) {
            Ordering::Greater => true,
            Ordering::Less => false,
            Ordering::Equal => sticky || kept.is_odd(),
        };
        (kept, up)
    };
    let mut m = kept.to_u64().unwrap() + u64::from(round_up);
    let mut lsb = lsb;
    if m == 1u64 << 53 {
        m >>= 1;
        lsb += 1;
    }
    if m == 0 {
        return Ok(0.0);
    }
    if m < 1u64 << 52 {
        // alt-normal (lsb = −1074)
        return Ok(f64::from_bits(m));
    }
    let biased = lsb + 52 + 1023;
    if biased >= 2047 {
        return Err(FloatOverflow);
    }
    Ok(f64::from_bits(((biased as u64) << 52) | (m - (1u64 << 52))))
}

/// pb1 = ln(value), value > 0. SPEC_APP §1.3: kesin değer → binary64 (doğru yuvarlanmış) → `f64::ln`.
/// Değer binary64 normal aralığı dışındaysa (taşma/alt-normal; Python 60 haneli Decimal ln sonlu
/// verir) ln(m·10^E) = ln(m) + E·ln 10 ile hesaplanır, m ∈ [1, 10).
pub fn ln_to_f64(value: &Dec) -> f64 {
    let v = value.to_f64();
    if v.is_finite() && v >= f64::MIN_POSITIVE {
        return v.ln();
    }
    let digits = value.coeff.to_str_radix(10);
    let top = &digits[..digits.len().min(40)];
    let m: f64 = format!("{}.{}", &top[..1], &top[1..]).parse().unwrap();
    let e = value.exp as f64 + (digits.len() as f64 - 1.0);
    m.ln() + e * std::f64::consts::LN_10
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> Dec {
        match parse(s) {
            Some(Parsed::Finite(x)) => x,
            other => panic!("{s:?}: {other:?}"),
        }
    }

    #[test]
    fn parse_basics() {
        assert_eq!(d("2.84").tuple_text(), "0|284|-2");
        assert_eq!(d("1_000").tuple_text(), "0|1000|0");
        assert_eq!(d(" +.5e-3 ").tuple_text(), "0|5|-4");
        assert_eq!(d("１２").tuple_text(), "0|12|0");
        assert_eq!(parse("inf"), Some(Parsed::NonFinite));
        assert_eq!(parse("-NaN12"), Some(Parsed::NonFinite));
        assert_eq!(parse("Infinityx"), None);
        assert_eq!(parse("12,5"), None);
        assert_eq!(parse("_ 5"), None);
        assert_eq!(parse("10e999999999999999999"), None);
        assert!(parse("1e999999999999999999").is_some());
    }

    #[test]
    fn pct_matches_python_examples() {
        // features._pct("62500000", "87500000") == Decimal("71.4285714286")
        assert_eq!(pct(&d("62500000"), &d("87500000")).stripped().tuple_text(), "0|714285714286|-10");
        assert_eq!(pct(&d("1"), &d("3")).stripped().tuple_text(), "0|333333333333|-10");
        assert_eq!(pct(&d("2"), &d("3")).stripped().tuple_text(), "0|666666666667|-10");
    }

    #[test]
    fn exact_context_ops() {
        // libmpdec üs kuralı (ölçüm: Python prec 60, Inexact tuzağı)
        for (a, b, want) in [
            ("30.2500", "0.02", "1512.50"),
            ("1E+2", "0.10", "1E+3"),
            ("100", "0.10", "1.0E+3"),
            ("1", "0.25", "4"),
            ("0", "0.10", "0E+2"),
            ("110.0", "0.10", "1.10E+3"),
        ] {
            assert_eq!(py_str(&div_exact(&d(a), &d(b), 60).unwrap()), want, "{a} / {b}");
        }
        // kesin olmayan bölme -> Inexact
        assert_eq!(div_exact(&d("1"), &d("3"), 60), Err(Inexact));
        // çarpma: üs toplanır
        assert_eq!(py_str(&mul_ctx(&d("1.0E+2"), &d("0.10"), 60).unwrap()), "10.0");
        assert_eq!(py_str(&mul_ctx(&d("1E+3"), &d("1.00"), 60).unwrap()), "1.00E+3");
        // ctx_round: kesin kısalma (sondaki sıfırlar atılmaz, üs yükselir) ve Inexact
        let long = Dec { neg: false, coeff: pow10(61), exp: 0 };
        let r = ctx_round(&long, 60).unwrap();
        assert_eq!((ndigits(&r.coeff), r.exp), (60, 2));
        let odd = Dec { neg: false, coeff: pow10(61) + 1u32, exp: 0 };
        assert_eq!(ctx_round(&odd, 60), Err(Inexact));
        // to_integral: exp >= 0 ise üs korunur
        assert_eq!(to_integral(&d("1E+3"), Rounding::Floor).tuple_text(), "0|1|3");
        assert_eq!(to_integral(&d("1512.50"), Rounding::Floor).tuple_text(), "0|1512|0");
        assert_eq!(to_integral(&d("0.5"), Rounding::HalfUp).tuple_text(), "0|1|0");
        assert_eq!(to_integral(&d("0.05"), Rounding::HalfUp).tuple_text(), "0|0|0");
        assert_eq!(to_integral(&d("-1.5"), Rounding::Floor).tuple_text(), "1|2|0");
    }

    #[test]
    fn py_str_matches_cpython() {
        for (text, want) in [
            ("1E2", "1E+2"),
            ("0.0000001", "1E-7"),
            ("0.000001", "0.000001"),
            ("10", "10"),
            ("1.0", "1.0"),
            ("0E-2", "0.00"),
            ("0E+2", "0E+2"),
            ("25.520", "25.520"),
            ("1e400", "1E+400"),
            ("4E+399", "4E+399"),
            ("-25.52", "-25.52"),
        ] {
            assert_eq!(py_str(&d(text)), want, "{text}");
        }
    }

    #[test]
    fn ratio_rounding() {
        let r = ratio_to_f64(&BigInt::from(1), &BigInt::from(3)).unwrap();
        assert_eq!(r, 1.0 / 3.0);
        let big = (BigInt::one() << 60u32) + 1;
        let r = ratio_to_f64(&big, &BigInt::from(3)).unwrap();
        assert_eq!(r, 384307168202282325.33333333333333333f64);
        assert!(ratio_to_f64(&(BigInt::one() << 2000u32), &BigInt::one()).is_err());
        assert_eq!(ratio_to_f64(&BigInt::one(), &(BigInt::one() << 1075u32)).unwrap(), 0.0);
        assert_eq!(ratio_to_f64(&BigInt::from(3), &(BigInt::one() << 1076u32)).unwrap(), f64::from_bits(1));
    }
}
