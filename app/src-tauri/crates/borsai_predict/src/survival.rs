//! Tavan serisi eğrileri (`borsai/survival.py`) ve koşullu güncelleme (SPEC_APP §3g, EK 1).
//! Hepsi doğrudan ifade; toplama yok.

pub const DAYS: usize = 10;
pub const GROUP_NAMES: [&str; 3] = ["g1", "g2", "g3"];
pub const DAY_GROUPS: [(&str, &[u32]); 3] = [("g1", &[1]), ("g2", &[2, 3]), ("g3", &[4, 5, 6, 7, 8, 9, 10])];

/// g(d): 0, 1, 2.
pub fn group_of_day(d: usize) -> usize {
    match d {
        1 => 0,
        2 | 3 => 1,
        _ => 2,
    }
}

/// S_k = Π_{d ≤ k} (1 − h_d), soldan sağa.
pub fn survival(hazards: &[f64]) -> Vec<f64> {
    let mut out = Vec::with_capacity(hazards.len());
    let mut s = 1.0f64;
    for &h in hazards {
        s *= 1.0 - h;
        out.push(s);
    }
    out
}

/// P(L = l), l = 0..10.
pub fn p_streak(s: &[f64]) -> Vec<f64> {
    let mut out = Vec::with_capacity(DAYS + 1);
    out.push(1.0 - s[0]);
    for l in 1..DAYS {
        out.push(s[l - 1] - s[l]);
    }
    out.push(s[DAYS - 1]);
    out
}

/// P(Dk'de tavan kapanışı): k = 1 → S_1; k ≥ 2 → S_k + (1 − S_k)·r, r = r_a (k ≤ 4) ya da r_b.
pub fn p_close(s: &[f64], r_a: f64, r_b: f64) -> Vec<f64> {
    let mut out = Vec::with_capacity(DAYS);
    out.push(s[0]);
    for k in 2..=DAYS {
        let r = if k <= 4 { r_a } else { r_b };
        out.push(s[k - 1] + (1.0 - s[k - 1]) * r);
    }
    out
}

pub fn sigmoid(x: f64) -> f64 {
    if x >= 0.0 {
        1.0 / (1.0 + (-x).exp())
    } else {
        let e = x.exp();
        e / (1.0 + e)
    }
}

/// "Seri j gün sürdü" koşulunda (SPEC_APP §3g). Tanımsız hücreler `None`.
#[derive(Debug, Clone, PartialEq)]
pub struct Conditional {
    pub j: usize,
    /// k = 1..10: P(L ≥ k | L ≥ j) = S_k / S_j (k > j); k ≤ j için `None`.
    pub s_cond: Vec<Option<f64>>,
    /// l = 0..10: P(L = l | L ≥ j) = P_L[l] / S_j (l ≥ j); l < j için `None`.
    pub p_l_cond: Vec<Option<f64>>,
    /// P(L = j | L ≥ j) = 1 − S_{j+1} / S_j ("yarın bozulur").
    pub p_break_next: f64,
}

/// S_0 = 1. j ≥ 10 ya da S_j = 0 → tanımsız (`None`). Her hücre tek bölme; model yeniden çalışmaz.
pub fn conditional(s: &[f64], j: usize) -> Option<Conditional> {
    if j >= DAYS || s.len() != DAYS {
        return None;
    }
    let sj = if j == 0 { 1.0 } else { s[j - 1] };
    if sj == 0.0 {
        return None;
    }
    let p_l = p_streak(s);
    Some(Conditional {
        j,
        s_cond: (1..=DAYS).map(|k| (k > j).then(|| s[k - 1] / sj)).collect(),
        p_l_cond: (0..=DAYS).map(|l| (l >= j).then(|| p_l[l] / sj)).collect(),
        p_break_next: 1.0 - s[j] / sj,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn conditional_j0_is_unconditional() {
        let s = survival(&[0.2, 0.1, 0.1, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]);
        let c = conditional(&s, 0).unwrap();
        for k in 0..DAYS {
            assert_eq!(c.s_cond[k].unwrap().to_bits(), s[k].to_bits());
        }
        assert_eq!(c.p_break_next.to_bits(), p_streak(&s)[0].to_bits());
        assert!(conditional(&s, 10).is_none());
        let zero = [0.0; 10];
        assert!(conditional(&zero, 3).is_none());
        assert!(conditional(&zero, 0).is_some());
    }
}
