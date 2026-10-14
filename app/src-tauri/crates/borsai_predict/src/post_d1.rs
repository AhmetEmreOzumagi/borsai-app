//! D1 sonrası güncelleme: `borsai/predict_post_d1.py` (`post_d1_hazard_v0`; SPEC_POST_D1_V0 §2, §3.1, §12;
//! SPEC_APP EK 3 §6.2–§6.3).
//!
//! η^base_d = dondurulmuş `ceiling_hazard_v0`'ın doğrusal öngörücüsü (`hazard::linear`; ofset, yeniden fit yok);
//! h_1 = sigmoid(η_1) ana modelden aynen; h_d = sigmoid(η_d + δ·u), d = 2..10, u = z-skorlu (d1_lock, d1_turnover).
//! δ = 0 için özel dal yoktur (`+ 0.0` bit-eşit; H2). Koşullu görünüm j = 1 `path::conditional_weights`'tan (tek tanım),
//! ikincil `path_conditional` `path::conditional`'dan (tek tanım). Ret kodları öneksiz (H23).
//!
//! `predict` dağıtımı (listeleme öncesi akış, `predict_all`) bu türü ÇALIŞTIRMAZ: giriş `run_post_d1` / `predict`.
use serde_json::{Map, Value};

use crate::dec::{self, Dec};
use crate::error::*;
use crate::features::{number_text, parse_decimal};
use crate::hazard::{self, div_ctx};
use crate::linear::range_warning;
use crate::output::{jnum, ConditionalJ1, D1Features, NotApplicable, Output, PostD1Output, Warning};
use crate::params::{parse_hazard, parse_path, parse_post_d1, HazardParams, Kind, PathParams, PostD1Params, D1_COLUMNS};
use crate::path::{self, CONDITIONAL_INVALID};
use crate::sum::{py_max, py_min, py_sum};
use crate::survival::{p_close, p_streak, sigmoid, survival, DAYS};
use crate::{RunResult, STATUS_ERROR, STATUS_PREDICTED, STATUS_REFUSED};

/// Kapsam dışı hücrenin durumu (`freeze.run_post_d1_model`; EK 3 §6.2).
pub const STATUS_NOT_APPLICABLE: &str = "NOT_APPLICABLE";
/// ln(hacim / arz edilen pay): `Context(prec=60, ROUND_HALF_EVEN)`, bir kez binary64.
pub const LN_PREC: u64 = 60;
/// Koşullu görünümün j'si (`CONDITION_J`).
pub const CONDITION_J: usize = 1;

const NOT_TRADED_TEXT: &str =
    "D_1 işlem görmemiş (sözleşme sayısı ya da kapanış yok/≤ 0; SPEC_SCORING §2): D_1 henüz oluşmadı, POST_D1 kaydı yazılamaz";

/// D_1 satırından iki özellik ve tutarlılık bilgisi (`predict_post_d1.D1Values`).
#[derive(Debug, Clone, PartialEq)]
pub struct D1Values {
    pub lock: u8,
    /// hacim / arz edilen pay (60 hane; kesinse libmpdec üs kuralı).
    pub turnover_ratio: Dec,
    /// ln(oran), bir kez binary64 (`dec::ln_to_f64`; Python 60 haneli `Decimal.ln()` → `float`, |Δ| ≤ 5e-15).
    pub turnover_ln: f64,
    /// `open_at_U`, `high_at_U`, `close_at_U` (Decimal değer eşitliği).
    pub lock_consistency: Vec<(String, bool)>,
    pub warnings: Vec<Warning>,
}

/// `evaluate_d1`'in etiketli sonuçları (Python: `PredictError(D1_NOT_TRADED)`, `D1Refusal`, `D1NotApplicable`; etiketsiz
/// istisna → `Domain`).
#[derive(Debug, Clone, PartialEq)]
pub enum D1Fail {
    NotTraded(PredictError),
    Refuse(Refusal),
    NotApplicable(NotApplicable),
    Domain(String),
}

/// `_raw`: bülten alanı; boş, eksik, sayı olmayan ya da sonlu olmayan → `None`.
fn raw(f: &Map<String, Value>, name: &str) -> Option<Dec> {
    parse_decimal(f.get(name), name, false).ok().flatten()
}

fn positive(x: &Option<Dec>) -> bool {
    x.as_ref().is_some_and(|d| d.signum() > 0)
}

/// Python `int(v or 0)` doğruluk değeri (yarım gün / durdurma bayrağı). `int()` istisnası → `Err`.
fn py_int_flag(v: Option<&Value>) -> Result<bool, String> {
    match v {
        None | Some(Value::Null) => Ok(false),
        Some(Value::Bool(b)) => Ok(*b),
        Some(Value::Number(n)) => {
            if let Some(i) = n.as_i64() {
                return Ok(i != 0);
            }
            if let Some(u) = n.as_u64() {
                return Ok(u != 0);
            }
            let f = n.as_f64().unwrap_or(f64::NAN);
            if !f.is_finite() {
                return Err(format!("int({f:?})"));
            }
            Ok(f.trunc() != 0.0)
        }
        Some(Value::String(s)) if s.is_empty() => Ok(false),
        Some(Value::String(s)) => {
            // Python int(str): boşluk kırpılır, isteğe bağlı işaret, rakamlar (rakamlar arasında tek alt çizgi)
            let t = dec::py_strip(s);
            let body = t.strip_prefix(['+', '-']).unwrap_or(t);
            let ok = !body.is_empty()
                && !body.starts_with('_')
                && !body.ends_with('_')
                && !body.contains("__")
                && body.chars().all(|c| c.is_ascii_digit() || c == '_');
            if !ok {
                return Err(format!("int({s:?})"));
            }
            Ok(body.chars().any(|c| c.is_ascii_digit() && c != '0'))
        }
        Some(Value::Array(a)) if a.is_empty() => Ok(false),
        Some(Value::Object(o)) if o.is_empty() => Ok(false),
        Some(other) => Err(format!("int({other})")),
    }
}

/// `predict_post_d1.evaluate_d1(d1, shares_offered)` (§2 tanımları, ret/uyarı tablosu; sıra H9).
pub fn evaluate_d1(d1: &Value, shares_offered: Option<&Value>) -> Result<D1Values, D1Fail> {
    let empty = Map::new();
    // `d1.get("fields_raw") or {}`
    let f = d1.get("fields_raw").and_then(Value::as_object).unwrap_or(&empty);
    let (close, trades) = (raw(f, "close"), raw(f, "trade_count"));
    if !positive(&close) || !positive(&trades) {
        return Err(D1Fail::NotTraded(PredictError::new(D1_NOT_TRADED, NOT_TRADED_TEXT)));
    }
    let close = close.expect("pozitif");
    let upper = raw(f, "upper_limit");
    if !positive(&upper) {
        return Err(D1Fail::Refuse(Refusal::new(
            D1_LIMIT_NA,
            Some("upper_limit"),
            "D_1 THM üst limiti yok ya da ≤ 0 (tavan etiketi NA; SPEC_SCORING §3)",
        )));
    }
    let upper = upper.expect("pozitif");
    if !dec::eq(&close, &upper) {
        return Err(D1Fail::NotApplicable(NotApplicable {
            code: D1_NOT_CEILING.into(),
            reason: format!(
                "D_1 kapanışı {} ≠ üst limit {}: model yalnız D1'i tavanda kapatan arzlarda tanımlı",
                dec::py_str(&close),
                dec::py_str(&upper)
            ),
        }));
    }
    let volume = raw(f, "volume");
    if !positive(&volume) {
        return Err(D1Fail::Refuse(Refusal::new(
            D1_VOLUME_INVALID,
            Some("volume"),
            "TOPLAM ISLEM ADEDI boş/≤ 0 iken sözleşme sayısı > 0 (veri tutarsızlığı; bülten satırı elle incelenir)",
        )));
    }
    let volume = volume.expect("pozitif");
    // Python sözlük sırası: low, open, high (üçü önce okunur, sonra sırayla denetlenir)
    let prices: Vec<(&str, Option<Dec>)> = ["low", "open", "high"].iter().map(|n| (*n, raw(f, n))).collect();
    for (name, value) in &prices {
        if !positive(value) {
            return Err(D1Fail::Refuse(Refusal::new(
                D1_FIELD_INVALID,
                Some(name),
                format!("D_1 THB {name} alanı yok ya da ≤ 0 (veri tutarsızlığı)"),
            )));
        }
    }
    let shares = match parse_decimal(shares_offered, "shares_offered", true) {
        Ok(Some(s)) => s,
        Ok(None) => unreachable!("required"),
        Err(r) => return Err(D1Fail::Refuse(Refusal::new(INPUT_SHARES_OFFERED, Some("shares_offered"), r.reason))),
    };
    if shares.signum() <= 0 {
        return Err(D1Fail::Refuse(Refusal::new(
            INPUT_SHARES_OFFERED,
            Some("shares_offered"),
            format!("arz edilen pay pozitif değil: {}", dec::py_str(&shares)),
        )));
    }
    let price = |n: &str| prices.iter().find(|(k, _)| *k == n).and_then(|(_, v)| v.clone()).expect("pozitif");
    let (low, open, high) = (price("low"), price("open"), price("high"));
    let lock = u8::from(dec::eq(&low, &upper));
    let lock_consistency = vec![
        ("open_at_U".to_string(), dec::eq(&open, &upper)),
        ("high_at_U".to_string(), dec::eq(&high, &upper)),
        ("close_at_U".to_string(), dec::eq(&close, &upper)),
    ];
    let mut warnings = Vec::new();
    if lock == 1 && !lock_consistency.iter().all(|(_, b)| *b) {
        warnings.push(Warning {
            code: WARN_D1_LOCK_INCONSISTENT.into(),
            message: "en düşük = üst limit ama açılış/en yüksek/kapanış üst limite eşit değil; bülten satırı elle incelenmeli"
                .into(),
            bool_fields: lock_consistency.clone(),
            ..Default::default()
        });
    }
    if py_int_flag(d1.get("half_day")).map_err(D1Fail::Domain)? {
        warnings.push(Warning {
            code: WARN_D1_HALF_DAY.into(),
            message: "D1 yarım gün: el değiştirme kısa seansta ölçüldü (H99'da örnek yok)".into(),
            ..Default::default()
        });
    }
    if py_int_flag(d1.get("halt_flag")).map_err(D1Fail::Domain)? {
        warnings.push(Warning {
            code: WARN_D1_INTRADAY_HALT.into(),
            message: "D1'de gün içi geçici durdurma (H99'da örnek yok)".into(),
            ..Default::default()
        });
    }
    if let Some(special) = raw(f, "special_trade_volume").filter(|s| s.signum() > 0) {
        warnings.push(Warning {
            code: WARN_D1_SPECIAL_TRADES.into(),
            message: "özel işlem bildirimi hacmi > 0; hacim düzeltilmedi (resmi toplam)".into(),
            text_fields: vec![
                ("special_trade_volume".into(), dec::py_str(&special)),
                ("volume".into(), dec::py_str(&volume)),
            ],
            ..Default::default()
        });
    }
    let ratio = div_ctx(&volume, &shares, LN_PREC).map_err(|e| D1Fail::Domain(e.message))?;
    let turnover_ln = dec::ln_to_f64(&ratio);
    Ok(D1Values { lock, turnover_ratio: ratio, turnover_ln, lock_consistency, warnings })
}

/// `d1["fields_raw"]["close"]` metni (`Decimal(str(c))` girdisi): metin aynen, sayı Python `str`'i.
fn close_text(d1: &Value) -> String {
    match d1.get("fields_raw").and_then(|f| f.get("close")) {
        Some(Value::String(s)) => s.clone(),
        Some(Value::Number(n)) => number_text(n),
        Some(other) => other.to_string(),
        None => String::new(),
    }
}

/// `predict_post_d1` gövdesi (parametreler ayrıştırılmış; Python sırası §6.2 adım 1–7). `D1_NOT_TRADED` ve etiketsiz
/// istisnalar `Err`; ret ve kapsam dışı `Ok` çıktıda.
pub fn predict_post_d1(
    p: &PostD1Params,
    parent: &HazardParams,
    inputs: &Map<String, Value>,
    d1: &Value,
    path: Option<&PathParams>,
) -> Result<PostD1Output, PredictError> {
    let base = hazard::linear(parent, inputs)?;
    let mut out = PostD1Output {
        model_id: p.model_id.clone(),
        warnings: base.warnings.clone(),
        clipped: base.clipped,
        ..Default::default()
    };
    if base.refused.is_some() {
        out.refused = base.refused;
        return Ok(out);
    }
    let values = match evaluate_d1(d1, inputs.get("shares_offered")) {
        Ok(v) => v,
        Err(D1Fail::NotTraded(e)) => return Err(e),
        Err(D1Fail::Refuse(r)) => {
            out.refused = Some(r);
            return Ok(out);
        }
        Err(D1Fail::NotApplicable(n)) => {
            out.not_applicable = Some(n);
            return Ok(out);
        }
        Err(D1Fail::Domain(m)) => return Err(PredictError::domain(m)),
    };
    out.warnings.extend(values.warnings.iter().cloned());
    let lock_f = f64::from(values.lock);
    let raw_t = values.turnover_ln;
    // OUT_OF_TRAINING_RANGE: ham değer (kırpma öncesi), D1_COLUMNS sırasıyla
    for (fid, x) in [(D1_COLUMNS[0], lock_f), (D1_COLUMNS[1], raw_t)] {
        if let Some(r) = p.range_of(fid) {
            if !(r.min <= x && x <= r.max) {
                out.warnings.push(range_warning(r, x));
            }
        }
    }
    // d1_transform: d1_turnover [p05, p95]'e kırpılır; aktif kolonlar z-skor
    let used = py_min(py_max(raw_t, p.clip.p05), p.clip.p95);
    let clipped = !(p.clip.p05 <= raw_t && raw_t <= p.clip.p95);
    let mut u: Vec<(String, f64)> = Vec::with_capacity(p.columns.len());
    for c in &p.columns {
        let x = if c == D1_COLUMNS[0] { lock_f } else { used };
        let (m, s) = (p.mean_of(c).expect("check_params"), p.std_of(c).expect("check_params"));
        u.push((c.clone(), (x - m) / s));
    }
    if clipped {
        out.warnings.push(Warning {
            code: WARN_D1_TURNOVER_CLIPPED.into(),
            message: format!("d1_turnover = {raw_t:?} eğitim p05/p95 sınırına kırpıldı: {used:?}"),
            feature: Some(D1_COLUMNS[1].into()),
            value: Some(raw_t),
            used: Some(used),
            ..Default::default()
        });
    }
    // updated_hazards: h_1 = sigmoid(η_1); h_d = sigmoid(η_d + δ·u), d = 2..10
    let shift = py_sum(u.iter().map(|(c, x)| p.delta_of(c).expect("check_params") * x));
    let mut hazards = Vec::with_capacity(DAYS);
    hazards.push(sigmoid(base.eta[0]));
    for d in 2..=DAYS {
        hazards.push(sigmoid(base.eta[d - 1] + shift));
    }
    // curves: standart hazard şeması + j = 1 koşullu görünüm (tek tanım `conditional_weights`)
    let s = survival(&hazards);
    let (s_cond, p_l_cond) = path::conditional_weights(&s, CONDITION_J).map_err(|e| PredictError::domain(e.message))?;
    out.conditional_j1 = Some(ConditionalJ1 { p_break_next: 1.0 - s_cond[0], s_cond, p_l_cond });
    out.p_l = Some(p_streak(&s));
    out.p_close_ceiling = Some(p_close(&s, parent.r_a, parent.r_b));
    out.hazard = Some(hazards);
    out.d1_features = Some(D1Features {
        d1_lock: values.lock,
        d1_turnover_ratio: dec::py_str(&values.turnover_ratio),
        d1_turnover_ln: raw_t,
        clipped,
        d1_turnover_used: used,
        z: u,
        ceiling_close_d1: 1,
        lock_consistency: values.lock_consistency.clone(),
    });
    if let Some(pp) = path {
        // ikincil: ceiling_path_v0'ın hücreleri ve limit yolu, S yerine bu modelin S'i, j = 1, [kapanış(D_1)]
        let po = path::predict_path(pp, inputs)?;
        if po.refused.is_none() && po.limit_path.is_some() {
            let mut doc = Output::Path(po).to_json();
            doc["S"] = Value::Array(s.iter().copied().map(jnum).collect());
            let cond = path::conditional(pp, &doc, CONDITION_J, &[close_text(d1)]).map_err(|e| {
                // Python `ValueError` (etiketsiz) → DOMAIN_ERROR; parametre hatası kodu aynen
                if e.code == CONDITIONAL_INVALID {
                    PredictError::domain(e.message)
                } else {
                    e
                }
            })?;
            out.path_conditional = Some(cond);
        }
    }
    out.s = Some(s);
    Ok(out)
}

/// `predict_post_d1(params, parent, inputs, d1, path_params=path)` JSON girişi, Python sırasıyla: `check_params` →
/// ebeveynin parametre denetimi (`linear_predictor`) → tahmin. Tavan yolu parametreleri burada ayrıştırılır (Python'da
/// `pth.predict` en sonda; dondurulmuş `ceiling_path_v0` bütünlük denetiminden geçtiği için sıra farkı gözlenmez).
pub fn predict(
    params: &Value,
    parent: &Value,
    inputs: &Map<String, Value>,
    d1: &Value,
    path: Option<&Value>,
) -> Result<PostD1Output, PredictError> {
    let p = parse_post_d1(params, parent, path)?;
    let parent_p = parse_hazard(parent)?;
    let path_p = path.map(parse_path).transpose()?;
    predict_post_d1(&p, &parent_p, inputs, d1, path_p.as_ref())
}

/// `freeze.run_post_d1_model`'in model kısmı: durum PREDICTED / REFUSED / NOT_APPLICABLE; `refusal` = ret ya da kapsam
/// dışı (`{code, reason}`); `D1_NOT_TRADED` ve parametre hataları ERROR (kayıt yazılmaz).
pub fn run_post_d1(params: &Value, parent: &Value, inputs: &Map<String, Value>, d1: &Value, path: Option<&Value>) -> RunResult {
    match predict(params, parent, inputs, d1, path) {
        Ok(out) => {
            let (status, refusal) = match (&out.refused, &out.not_applicable) {
                (Some(r), _) => (STATUS_REFUSED, Some(r.clone())),
                (None, Some(n)) => (STATUS_NOT_APPLICABLE, Some(Refusal { code: n.code.clone(), field: None, reason: n.reason.clone() })),
                (None, None) => (STATUS_PREDICTED, None),
            };
            RunResult { kind: Kind::PostD1, status, refusal, output: Some(Output::PostD1(out)) }
        }
        Err(e) => RunResult {
            kind: Kind::PostD1,
            status: STATUS_ERROR,
            refusal: Some(Refusal { code: e.code.clone(), field: None, reason: e.message.clone() }),
            output: None,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn d1(fields: Value) -> Value {
        json!({"fields_raw": fields, "half_day": 0, "halt_flag": 0})
    }

    fn base_fields() -> Value {
        json!({"open": "28.06", "high": "28.06", "low": "28.06", "close": "28.06", "volume": "8750000",
               "trade_count": "1200", "upper_limit": "28.06", "special_trade_volume": "0"})
    }

    #[test]
    fn evaluate_order_and_codes() {
        let shares = json!("87500000");
        let v = evaluate_d1(&d1(base_fields()), Some(&shares)).unwrap();
        assert_eq!((v.lock, dec::py_str(&v.turnover_ratio)), (1, "0.1".to_string()));
        assert_eq!(v.turnover_ln, 0.1f64.ln());
        let with = |k: &str, val: Value| {
            let mut f = base_fields();
            f[k] = val;
            evaluate_d1(&d1(f), Some(&shares))
        };
        assert!(matches!(with("trade_count", json!("0")), Err(D1Fail::NotTraded(e)) if e.code == D1_NOT_TRADED));
        assert!(matches!(with("close", json!("")), Err(D1Fail::NotTraded(_))));
        assert!(matches!(with("upper_limit", json!("")), Err(D1Fail::Refuse(r)) if r.code == D1_LIMIT_NA));
        assert!(matches!(with("close", json!("28.04")), Err(D1Fail::NotApplicable(n)) if n.code == D1_NOT_CEILING));
        assert!(matches!(with("volume", json!("0")), Err(D1Fail::Refuse(r)) if r.code == D1_VOLUME_INVALID));
        for k in ["low", "open", "high"] {
            assert!(matches!(with(k, json!("abc")), Err(D1Fail::Refuse(r)) if r.code == D1_FIELD_INVALID && r.field.as_deref() == Some(k)));
        }
        // fiyat alanlarının sırası low → open → high
        let mut f = base_fields();
        f["high"] = json!("");
        f["open"] = json!("-1");
        assert!(matches!(evaluate_d1(&d1(f), Some(&shares)), Err(D1Fail::Refuse(r)) if r.field.as_deref() == Some("open")));
    }

    /// INPUT_SHARES_OFFERED: ana model önce reddettiği için altın vektörde ulaşılmaz (kapsama muafiyeti; EK 3 §6.2).
    #[test]
    fn input_shares_offered_unit() {
        for bad in [Value::Null, json!(""), json!("abc"), json!(true), json!("0"), json!("-5"), json!("inf")] {
            let r = evaluate_d1(&d1(base_fields()), Some(&bad));
            assert!(
                matches!(&r, Err(D1Fail::Refuse(x)) if x.code == INPUT_SHARES_OFFERED && x.field.as_deref() == Some("shares_offered")),
                "{bad}: {r:?}"
            );
        }
        assert!(matches!(evaluate_d1(&d1(base_fields()), None), Err(D1Fail::Refuse(x)) if x.code == INPUT_SHARES_OFFERED));
    }

    #[test]
    fn warnings_and_flags() {
        let shares = json!("87500000");
        let mut f = base_fields();
        f["open"] = json!("27.00");
        f["special_trade_volume"] = json!("1500");
        let doc = json!({"fields_raw": f, "half_day": 1, "halt_flag": "1"});
        let v = evaluate_d1(&doc, Some(&shares)).unwrap();
        let codes: Vec<&str> = v.warnings.iter().map(|w| w.code.as_str()).collect();
        assert_eq!(codes, [WARN_D1_LOCK_INCONSISTENT, WARN_D1_HALF_DAY, WARN_D1_INTRADAY_HALT, WARN_D1_SPECIAL_TRADES]);
        let lock = &v.warnings[0].to_json();
        assert_eq!(lock, &json!({"code": WARN_D1_LOCK_INCONSISTENT, "message": v.warnings[0].message,
                                  "open_at_U": false, "high_at_U": true, "close_at_U": true}));
        assert_eq!(v.warnings[3].text_fields, vec![("special_trade_volume".into(), "1500".into()), ("volume".into(), "8750000".into())]);
        // int(v or 0): 0.5 → 0 (uyarı yok); "x" → istisna
        assert_eq!(py_int_flag(Some(&json!(0.5))), Ok(false));
        assert_eq!(py_int_flag(Some(&json!(" 1 "))), Ok(true));
        assert!(py_int_flag(Some(&json!("x"))).is_err());
        assert_eq!(py_int_flag(Some(&json!(""))), Ok(false));
    }
}
