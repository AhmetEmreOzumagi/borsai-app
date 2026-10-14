//! Hata ve ret türleri. Ret kodları Python sabitleriyle birebir (SPEC_APP §3b.1, T-2).
use serde::Serialize;
use std::fmt;

pub const PARAMS_INVALID: &str = "PARAMS_INVALID";
pub const SCHEMA_UNSUPPORTED: &str = "SCHEMA_UNSUPPORTED";
/// Python'un etiketsiz istisna fırlattığı girdiler (ör. f1 binary64'te 0'a düşer ve `math.log(0.0)`
/// ValueError verir; 28 haneli bağlamda `decimal.Overflow`; `int / int` OverflowError). Python'da
/// kayıt yazılmaz; Rust tahmin üretmez, bu kodla hata döner.
pub const DOMAIN_ERROR: &str = "DOMAIN_ERROR";

// features.py
pub const INPUT_MISSING: &str = "INPUT_MISSING";
pub const INPUT_NOT_NUMERIC: &str = "INPUT_NOT_NUMERIC";
pub const INPUT_NOT_POSITIVE: &str = "INPUT_NOT_POSITIVE";
pub const INPUT_NEGATIVE: &str = "INPUT_NEGATIVE";
pub const DIVISION_BY_ZERO: &str = "DIVISION_BY_ZERO";
pub const INPUT_INCONSISTENT: &str = "INPUT_INCONSISTENT";
pub const PB_FIELD_MISSING: &str = "PB_FIELD_MISSING";
pub const PB_IDENTITY: &str = "PB_IDENTITY";
pub const PB_PRICE_RANGE: &str = "PB_PRICE_RANGE";
// predict.py, predict_hazard.py, predict_market20.py
pub const F3_MISSING: &str = "F3_MISSING";
pub const F3_FILTER_STATUS_CONFLICT: &str = "F3_FILTER_STATUS_CONFLICT";
pub const FEATURE_NOT_PROVIDED: &str = "FEATURE_NOT_PROVIDED";
pub const MARKET20_PREFIX: &str = "MARKET20_";
// predict_hazard.py, tufe.py (Faz 7 `ceiling_hazard_v1`; SPEC_APP EK 3 §2.5)
pub const TUFE_MISSING: &str = "TUFE_MISSING";
pub const TUFE_NOT_PIT: &str = "TUFE_NOT_PIT";
pub const TUFE_FILE_MISMATCH: &str = "TUFE_FILE_MISMATCH";
pub const TUFE_REFUSALS: [&str; 3] = [TUFE_MISSING, TUFE_NOT_PIT, TUFE_FILE_MISMATCH];
pub const REGIME_UNKNOWN: &str = "REGIME_UNKNOWN";
// predict_fall.py (Faz 7C `fall_d10_v0`; SPEC_APP EK 3 §8.2, KARARLAR_C C4: boş alan 0 sayılmaz)
pub const ADDITIONAL_SALE_MISSING: &str = "ADDITIONAL_SALE_MISSING";
// predict_post_d1.py (SPEC_APP EK 3 §6.3; SPEC_DEVIATIONS H23: öneksiz B3 biçimi)
/// D_1 işlem görmemiş: kayıt yazılmaz (Python `PredictError`; `run_post_d1` → ERROR).
pub const D1_NOT_TRADED: &str = "D1_NOT_TRADED";
pub const D1_LIMIT_NA: &str = "D1_LIMIT_NA";
pub const D1_VOLUME_INVALID: &str = "D1_VOLUME_INVALID";
pub const D1_FIELD_INVALID: &str = "D1_FIELD_INVALID";
pub const INPUT_SHARES_OFFERED: &str = "INPUT_SHARES_OFFERED";
/// Kapsam dışı (ret değil): `not_applicable.code`.
pub const D1_NOT_CEILING: &str = "D1_NOT_CEILING";
pub const WARN_D1_HALF_DAY: &str = "WARN_D1_HALF_DAY";
pub const WARN_D1_INTRADAY_HALT: &str = "WARN_D1_INTRADAY_HALT";
pub const WARN_D1_SPECIAL_TRADES: &str = "WARN_D1_SPECIAL_TRADES";
pub const WARN_D1_LOCK_INCONSISTENT: &str = "WARN_D1_LOCK_INCONSISTENT";
pub const WARN_D1_TURNOVER_CLIPPED: &str = "D1_TURNOVER_CLIPPED_TO_TRAINING_P05_P95";
// uyarılar
pub const WARN_OUT_OF_TRAINING_RANGE: &str = "OUT_OF_TRAINING_RANGE";
pub const WARN_F4_ZERO: &str = "F4_ZERO_NO_TRAINING_EXAMPLE";
pub const WARN_F3_WINSORIZED: &str = "F3_WINSORIZED";
pub const WARN_F3_CLIPPED: &str = "F3_CLIPPED_TO_TRAINING_P05_P95";
/// `ceiling_hazard_v1`: her özellik eğitim p05/p95'ine kırpılır (v0'ın F3_CLIPPED kodu v0'da aynen kalır).
pub const WARN_FEATURE_CLIPPED: &str = "FEATURE_CLIPPED_TO_TRAINING_P05_P95";
pub const WARN_RETURN_CLIPPED: &str = "RETURN_CLIPPED_TO_PHYSICAL_BOUND";
pub const WARN_PB4_POSITIVE: &str = "PB4_ADDITIONAL_SALE_CEILING";
/// predict_path: arz fiyatı fiyat adımı ızgarasında değil (D1 baz fiyatı HALF_UP ile oturtuldu).
pub const WARN_IPO_PRICE_NOT_ON_TICK_GRID: &str = "IPO_PRICE_NOT_ON_TICK_GRID";

/// Parametre dosyası hatası ya da tanım dışı girdi (Python: PredictError ya da etiketsiz istisna).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct PredictError {
    pub code: String,
    pub message: String,
}

impl PredictError {
    pub fn new(code: &str, message: impl Into<String>) -> Self {
        PredictError { code: code.to_string(), message: message.into() }
    }
    pub fn params(message: impl Into<String>) -> Self {
        Self::new(PARAMS_INVALID, message)
    }
    pub fn domain(message: impl Into<String>) -> Self {
        Self::new(DOMAIN_ERROR, message)
    }
}

impl fmt::Display for PredictError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for PredictError {}

/// Etiketli ret: `{code, field, reason}`. `reason` Türkçe ve Rust'ın kendi metnidir (parite dışı).
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Refusal {
    pub code: String,
    pub field: Option<String>,
    pub reason: String,
}

impl Refusal {
    pub fn new(code: &str, field: Option<&str>, reason: impl Into<String>) -> Self {
        Refusal { code: code.to_string(), field: field.map(str::to_string), reason: reason.into() }
    }
}

/// Özellik hesabının sonucu: etiketli ret ya da Python'daki etiketsiz istisnanın karşılığı.
#[derive(Debug, Clone, PartialEq)]
pub enum FeatureFail {
    Refuse(Refusal),
    Domain(String),
}

impl FeatureFail {
    pub fn refuse(code: &str, field: &str, reason: impl Into<String>) -> Self {
        FeatureFail::Refuse(Refusal::new(code, Some(field), reason))
    }
}
