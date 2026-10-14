//! Ufuklar ve fiziksel getiri sınırı (`borsai/horizons.py`).
//! R_h ∈ [0.9^h − 1, 1.1^h − 1]; Python sınırı Decimal ile kesin hesaplayıp bir kez binary64'e
//! çevirir. Burada aynı kesin değerlerin metni ayrıştırılır (SPEC_APP §1.3).

pub const HORIZONS: [&str; 4] = ["D1", "D3", "D5", "D10"];

pub fn horizon_days(h: &str) -> Option<u32> {
    match h {
        "D1" => Some(1),
        "D3" => Some(3),
        "D5" => Some(5),
        "D10" => Some(10),
        _ => None,
    }
}

/// (alt, üst) = (0.9^h − 1, 1.1^h − 1).
pub fn physical_return_bounds(h: &str) -> Option<(f64, f64)> {
    let (lo, hi) = match h {
        "D1" => ("-0.1", "0.1"),
        "D3" => ("-0.271", "0.331"),
        "D5" => ("-0.40951", "0.61051"),
        "D10" => ("-0.6513215599", "1.5937424601"),
        _ => return None,
    };
    Some((lo.parse().unwrap(), hi.parse().unwrap()))
}
