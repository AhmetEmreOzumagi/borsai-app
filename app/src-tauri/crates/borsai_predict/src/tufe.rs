//! TÜİK TÜFE genel endeksi (2025=100) ve T − 2 ay kuralı: `borsai/tufe.py`'nin yalnız okuma ve denetim
//! kısmının portu (SPEC_APP EK 3 §3.2). Saf: dosya okumaz, çağıran baytları verir. Deflasyon aritmetiği
//! (f1r = büyüklük / (endeks / 100)) tahmin yolundadır: `hazard.rs` (`real_size`).
//!
//!   month_for(T)  = T'nin ayı − 2                 ("2026-09-25" → "2026-07", "2020-01-06" → "2019-11")
//!   index_for(T)  = o ayın satırı; ay yoksa RET TUFE_MISSING, `release_date < T` değilse RET TUFE_NOT_PIT
//!   prefix_sha256 = başlık dahil `through_month` satırına kadarki baytların sha256'sı (pin; ekleme onu değiştirmez)
use sha2::{Digest, Sha256};

use crate::error::{TUFE_FILE_MISMATCH, TUFE_MISSING, TUFE_NOT_PIT};

pub const TUFE_REL: &str = "data/raw/tuik/tufe_genel_2025_100.csv";
pub const COLUMNS: [&str; 6] = ["month", "index", "release_date", "bulletin_id", "source_url", "source_sha256"];
pub const SERIES: &str = "TUIK_TUFE_GENEL_2025_100";
pub const MONTH_RULE: &str = "T_MONTH_MINUS_2";
/// Eski kohortun ilk T'si 2020-01 → 2019-11 (dosyanın ilk satırı).
pub const FIRST_MONTH: &str = "2019-11";
pub const LAG_MONTHS: i64 = 2;

/// Python `borsai.tufe.APPEND_COMMAND` metni BİREBİR (aylık ekleme komutu; `{month}` yer tutucu). Uygulama bu
/// komutu ÇALIŞTIRMAZ, yalnız kopyalanabilir metin olarak gösterir. Yorumlayıcı parçası Python tarafının
/// kendi kuralıdır; repo modunda ekranda ayardaki Python yoluyla değiştirilir (`append_command`).
pub const APPEND_COMMAND: &str = ".venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month {month} --bulletin-id <bülten sayısı> \
--release <YYYY-MM-DDT10:00:00+03:00> --xls <indirilen tablo .xls> --download-url '<indirme bağlantısı>' \
--sha256 <indirilen tablonun sha256'sı>";

/// Aylık ekleme komutu. `python` verilirse ilk sözcük (yorumlayıcı) onunla değiştirilir; verilmezse Python metni aynen.
pub fn append_command(month: &str, python: Option<&str>) -> String {
    let text = APPEND_COMMAND.replace("{month}", month);
    match python {
        Some(py) => match text.split_once(' ') {
            Some((_, rest)) => format!("{py} {rest}"),
            None => text,
        },
        None => text,
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct TufeRow {
    pub month: String,
    /// Kaynak metni (kırpılmamış; `Decimal` ile okunur).
    pub index: String,
    /// O ayın kendi bülteninin yayım günü (Europe/Istanbul).
    pub release_date: String,
    pub bulletin_id: String,
    pub source_url: String,
    pub source_sha256: String,
}

/// Ayrıştırılmış tablo: satırlar dosya sırasıyla, ham baytlar (önek pini için) ve dosya sha256'sı.
#[derive(Debug, Clone, PartialEq)]
pub struct TufeTable {
    pub rows: Vec<TufeRow>,
    raw: Vec<u8>,
    pub file_sha256: String,
}

/// Dosya biçimi ya da süreklilik ihlali (Python `TufeError`: değer düzeltilmez, durulur).
#[derive(Debug, Clone, PartialEq)]
pub struct TufeError(pub String);

/// Tahmin girdisi hazırlanamadı: `code` ∈ {TUFE_MISSING, TUFE_NOT_PIT, TUFE_FILE_MISMATCH}, `month` ilgili ay.
#[derive(Debug, Clone, PartialEq)]
pub struct TufeRefusal {
    pub code: &'static str,
    pub month: Option<String>,
    pub message: String,
}

impl TufeRefusal {
    fn new(code: &'static str, month: Option<&str>, message: impl Into<String>) -> Self {
        TufeRefusal { code, month: month.map(str::to_string), message: message.into() }
    }
}

/// Model/veri sürümü pini (JSON `deflator.through_month`, `deflator.file_sha256`).
#[derive(Debug, Clone, PartialEq)]
pub struct DeflatorPin {
    pub through_month: String,
    pub prefix_sha256: String,
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

/// "YYYY-MM" düzgün mü (`^\d{4}-(0[1-9]|1[0-2])$`, ASCII).
fn is_month(m: &str) -> bool {
    let b = m.as_bytes();
    b.len() == 7
        && b[..4].iter().all(u8::is_ascii_digit)
        && b[4] == b'-'
        && matches!((b[5], b[6]), (b'0', b'1'..=b'9') | (b'1', b'0'..=b'2'))
}

/// "YYYY-MM-DD" biçimi (`^\d{4}-\d{2}-\d{2}$`, ASCII).
fn is_date(d: &str) -> bool {
    let b = d.as_bytes();
    b.len() == 10
        && b.iter().enumerate().all(|(i, c)| if i == 4 || i == 7 { *c == b'-' } else { c.is_ascii_digit() })
}

fn digits(s: &str) -> Option<i64> {
    (!s.is_empty() && s.bytes().all(|c| c.is_ascii_digit())).then(|| s.parse().ok()).flatten()
}

/// `month_add("2019-11", 1) == "2019-12"` (yalnız biçimi doğrulanmış ay).
pub fn month_add(month: &str, k: i64) -> String {
    let y: i64 = month[..4].parse().unwrap_or(0);
    let m = month[5..7].parse::<i64>().unwrap_or(1) - 1 + k;
    format!("{:04}-{:02}", y + m.div_euclid(12), m.rem_euclid(12) + 1)
}

/// T (YYYY-MM-DD, ilk işlem günü) → T'nin ayı − 2 (YYYY-MM). T'nin yılı ve ayı okunamazsa `None`.
pub fn month_for(t: &str) -> Option<String> {
    if t.len() < 7 || !t.is_char_boundary(4) || !t.is_char_boundary(5) || !t.is_char_boundary(7) {
        return None;
    }
    let (mut y, mut m) = (digits(&t[..4])?, digits(&t[5..7])?);
    m -= LAG_MONTHS;
    if m <= 0 {
        y -= 1;
        m += 12;
    }
    Some(format!("{y:04}-{m:02}"))
}

/// Biçim ve süreklilik denetimli okuma (`tufe.parse`). Aylar FIRST_MONTH'tan başlar ve boşluksuz artar; her
/// satırın yayımı referans ayını izleyen ayın ≥ 3. günü; endeks pozitif Decimal ve kırpılmamış metin; kimlik ve
/// sha biçimleri. Tırnaklı alan ya da sütun sayısı farkı da biçim ihlalidir (dosyada yoktur; durulur).
pub fn parse(raw: &[u8]) -> Result<TufeTable, TufeError> {
    let err = |m: String| Err(TufeError(format!("{TUFE_REL}: {m}")));
    let Ok(text) = std::str::from_utf8(raw) else {
        return err("UTF-8 değil".into());
    };
    if !raw.ends_with(b"\n") || raw.contains(&b'\r') {
        return err("satır sonu LF değil ya da dosya LF ile bitmiyor".into());
    }
    let mut lines = text.split('\n');
    let header: Vec<&str> = lines.next().unwrap_or("").split(',').collect();
    if header != COLUMNS {
        return err(format!("sütunlar {header:?} != {COLUMNS:?}"));
    }
    let mut rows: Vec<TufeRow> = Vec::new();
    let mut expect = FIRST_MONTH.to_string();
    for line in lines {
        if line.is_empty() {
            continue; // csv.DictReader boş satırı atlar
        }
        if line.contains('"') {
            return err(format!("tırnaklı alan beklenmiyor: {line:?}"));
        }
        let f: Vec<&str> = line.split(',').collect();
        if f.len() != COLUMNS.len() {
            return err(format!("sütun sayısı {} (6 bekleniyor): {line:?}", f.len()));
        }
        let (m, idx, rd, bid, url, sha) = (f[0], f[1], f[2], f[3], f[4], f[5]);
        if !is_month(m) || m != expect {
            return err(format!("ay {m:?} beklenen {expect} değil (süreklilik)"));
        }
        expect = month_add(m, 1);
        let positive = matches!(crate::dec::parse(idx), Some(crate::dec::Parsed::Finite(d)) if d.signum() > 0);
        if !positive || idx != crate::dec::py_strip(idx) {
            return err(format!("{m} endeks {idx:?}"));
        }
        let day_ok = is_date(rd) && rd[..7] == month_add(m, 1) && digits(&rd[8..10]).is_some_and(|d| d >= 3);
        if !day_ok {
            return err(format!("{m} yayım günü {rd:?} referans ayını izleyen ayın 3'ünden önce ya da o ayda değil"));
        }
        let sha_ok = sha.len() == 64 && sha.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c));
        if digits(bid).is_none() || !sha_ok || !url.starts_with("https://") {
            return err(format!("{m} bülten kimliği / kaynak biçimi"));
        }
        rows.push(TufeRow {
            month: m.into(),
            index: idx.into(),
            release_date: rd.into(),
            bulletin_id: bid.into(),
            source_url: url.into(),
            source_sha256: sha.into(),
        });
    }
    if rows.is_empty() {
        return err("satır yok".into());
    }
    Ok(TufeTable { rows, raw: raw.to_vec(), file_sha256: sha256_hex(raw) })
}

impl TufeTable {
    /// Biçim denetimsiz tablo (YALNIZ bekçi testleri için: `release_date ≥ T` satırı `parse`'tan geçemez).
    pub fn from_rows_unchecked(rows: Vec<TufeRow>) -> TufeTable {
        TufeTable { rows, raw: Vec::new(), file_sha256: String::new() }
    }

    pub fn row(&self, month: &str) -> Option<&TufeRow> {
        self.rows.iter().find(|r| r.month == month)
    }

    /// Dosyanın son ayı.
    pub fn last_month(&self) -> &str {
        self.rows.last().map(|r| r.month.as_str()).unwrap_or("")
    }

    /// Başlık + ilk satırdan `through_month` satırına kadar (dahil) dosya baytları (Python `prefix_bytes` aynen:
    /// fiziksel satır sayımı).
    pub fn prefix_bytes(&self, through_month: &str) -> Result<Vec<u8>, TufeRefusal> {
        let Some(pos) = self.rows.iter().position(|r| r.month == through_month) else {
            return Err(TufeRefusal::new(TUFE_FILE_MISMATCH, Some(through_month), format!("pin ayı {through_month} dosyada yok")));
        };
        let n = pos + 2;
        let lines: Vec<&[u8]> = self.raw.split(|b| *b == b'\n').collect();
        let mut out = lines[..n.min(lines.len())].join(&b'\n');
        out.push(b'\n');
        Ok(out)
    }

    pub fn prefix_sha256(&self, through_month: &str) -> Result<String, TufeRefusal> {
        self.prefix_bytes(through_month).map(|b| sha256_hex(&b))
    }
}

/// Önek pini: ekleme serbest; önekin değişmesi RET TUFE_FILE_MISMATCH (eski satır, temel yıl ya da zincirleme).
pub fn verify_pin(table: &TufeTable, pin: &DeflatorPin) -> Result<(), TufeRefusal> {
    let got = table.prefix_sha256(&pin.through_month)?;
    if got != pin.prefix_sha256 {
        return Err(TufeRefusal::new(
            TUFE_FILE_MISMATCH,
            Some(&pin.through_month),
            format!("{TUFE_REL} önek sha256 {got} != pin {} ({}'a kadar)", pin.prefix_sha256, pin.through_month),
        ));
    }
    Ok(())
}

/// T'nin deflatörü (`tufe.index_for`): ay yoksa RET TUFE_MISSING; yayım T'den önce değilse RET TUFE_NOT_PIT.
/// T'nin yılı ve ayı okunamazsa TUFE_MISSING (ay `None`).
pub fn index_for<'a>(t: &str, table: &'a TufeTable) -> Result<&'a TufeRow, TufeRefusal> {
    let Some(month) = month_for(t) else {
        return Err(TufeRefusal::new(TUFE_MISSING, None, format!("T = {t:?} YYYY-MM-DD değil; ay belirlenemez")));
    };
    let Some(row) = table.row(&month) else {
        return Err(TufeRefusal::new(TUFE_MISSING, Some(&month), format!("TÜFE {month} ayı {TUFE_REL} dosyasında yok (T = {t})")));
    };
    if row.release_date.as_str() >= t {
        return Err(TufeRefusal::new(TUFE_NOT_PIT, Some(&month), format!("TÜFE {month} yayımı {}, T = {t}'den önce değil", row.release_date)));
    }
    Ok(row)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn month_rule() {
        assert_eq!(month_for("2026-09-25").as_deref(), Some("2026-07"));
        assert_eq!(month_for("2026-10-01").as_deref(), Some("2026-08"));
        assert_eq!(month_for("2020-01-06").as_deref(), Some("2019-11"));
        assert_eq!(month_for("2026-02-01").as_deref(), Some("2025-12"));
        assert_eq!(month_for(""), None);
        assert_eq!(month_for("2026-9-17"), None);
        assert_eq!(month_add("2019-12", 1), "2020-01");
    }

    #[test]
    fn append_command_interpreter() {
        let v = append_command("2026-09", None);
        assert!(v.starts_with(".venv/bin/python data/raw/tuik/build_tufe_csv.py --append-month 2026-09 "));
        let w = append_command("2026-09", Some("py"));
        assert!(w.starts_with("py data/raw/tuik/build_tufe_csv.py --append-month 2026-09 "));
        assert_eq!(v.split_once(' ').unwrap().1, w.split_once(' ').unwrap().1);
    }
}
