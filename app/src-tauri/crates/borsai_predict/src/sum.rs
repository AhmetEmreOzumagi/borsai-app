//! CPython 3.12 `sum()` float yolu: Neumaier telafili toplama (`bltinmodule.c`).
//! `sum([1e16, 1.0, -1e16]) == 1.0`. Başlangıç tamsayı 0'dır: boş toplam 0, ilk öğe `0 + x`.

pub fn py_sum<I: IntoIterator<Item = f64>>(items: I) -> f64 {
    let mut it = items.into_iter();
    let mut f = match it.next() {
        None => return 0.0,
        Some(x) => 0.0 + x,
    };
    let mut c = 0.0f64;
    for x in it {
        let t = f + x;
        if f.abs() >= x.abs() {
            c += (f - t) + x;
        } else {
            c += (x - t) + f;
        }
        f = t;
    }
    if c != 0.0 && c.is_finite() {
        f += c;
    }
    f
}

/// Python `max(a, b)`: b > a değilse a (NaN a'yı korur).
pub fn py_max(a: f64, b: f64) -> f64 {
    if b > a {
        b
    } else {
        a
    }
}

/// Python `min(a, b)`: b < a değilse a.
pub fn py_min(a: f64, b: f64) -> f64 {
    if b < a {
        b
    } else {
        a
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn neumaier_like_cpython() {
        assert_eq!(py_sum([1e16, 1.0, -1e16]), 1.0);
        assert_eq!(py_sum(std::iter::empty()), 0.0);
        assert_eq!(py_sum([0.1; 10]), 1.0);
        assert!(py_sum([f64::INFINITY, 1.0]).is_infinite());
        assert!(py_sum([f64::INFINITY, f64::NEG_INFINITY]).is_nan());
    }
}
