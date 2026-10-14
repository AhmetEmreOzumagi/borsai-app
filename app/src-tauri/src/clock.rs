//! Europe/Istanbul saati: uygulama UTC+3 sabit alır (Türkiye 2016'dan beri yaz saati uygulamaz;
//! SPEC_APP §3a.2). Tarih hesabı std ile (Howard Hinnant, `civil_from_days`).
use std::time::{SystemTime, UNIX_EPOCH};

pub const ISTANBUL_OFFSET_SECS: i64 = 3 * 3600;

/// Unix gününden (1970-01-01 = 0) proleptik Gregoryen (yıl, ay, gün).
pub fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

fn unix_now() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

/// Unix saniyesinin Istanbul yerel zamanı: ("YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS+03:00").
pub fn istanbul(unix_secs: i64) -> (String, String) {
    let local = unix_secs + ISTANBUL_OFFSET_SECS;
    let (y, m, d) = civil_from_days(local.div_euclid(86_400));
    let s = local.rem_euclid(86_400);
    let date = format!("{y:04}-{m:02}-{d:02}");
    let stamp = format!("{date}T{:02}:{:02}:{:02}+03:00", s / 3600, (s % 3600) / 60, s % 60);
    (date, stamp)
}

pub fn today_istanbul() -> String {
    istanbul(unix_now()).0
}

pub fn now_istanbul() -> String {
    istanbul(unix_now()).1
}

/// Şimdi, UTC: kayıt dosyası adlarındaki biçim (`20260922T121936Z`).
pub fn now_utc_stamp() -> String {
    let s = unix_now();
    let (y, m, d) = civil_from_days(s.div_euclid(86_400));
    let t = s.rem_euclid(86_400);
    format!("{y:04}{m:02}{d:02}T{:02}{:02}{:02}Z", t / 3600, (t % 3600) / 60, t % 60)
}

pub fn unix_millis() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0)
}

/// Katı ISO tarih (YYYY-MM-DD, geçerli takvim günü).
pub fn is_iso_date(s: &str) -> bool {
    let b = s.as_bytes();
    if b.len() != 10 || b[4] != b'-' || b[7] != b'-' {
        return false;
    }
    let num = |r: std::ops::Range<usize>| s.get(r).filter(|t| t.bytes().all(|c| c.is_ascii_digit())).and_then(|t| t.parse::<u32>().ok());
    let (Some(y), Some(m), Some(d)) = (num(0..4), num(5..7), num(8..10)) else {
        return false;
    };
    if !(1..=12).contains(&m) || d == 0 {
        return false;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let days = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][(m - 1) as usize];
    d <= days
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn istanbul_dates() {
        // 2026-09-22T00:30:00+03:00 = 2026-09-21T21:30:00Z
        assert_eq!(istanbul(1_790_026_200), ("2026-09-22".into(), "2026-09-22T00:30:00+03:00".into()));
        assert_eq!(civil_from_days(0), (1970, 1, 1));
        assert_eq!(civil_from_days(-1), (1969, 12, 31));
        assert!(is_iso_date("2024-02-29") && !is_iso_date("2026-02-29") && !is_iso_date("2026-9-22"));
    }
}
