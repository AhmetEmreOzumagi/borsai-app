//! Tahmin çıktıları: Python sözlükleriyle alan alan aynı (SPEC_APP §1.2). JSON'da sonlu olmayan
//! binary64 metin olarak yazılır ("NaN", "Infinity", "-Infinity"); altın vektörler de böyle.
use serde_json::{json, Map, Value};

use crate::error::Refusal;
use crate::path::Horizon;
use crate::survival::Conditional;

pub fn jnum(x: f64) -> Value {
    if x.is_nan() {
        Value::String("NaN".into())
    } else if x == f64::INFINITY {
        Value::String("Infinity".into())
    } else if x == f64::NEG_INFINITY {
        Value::String("-Infinity".into())
    } else {
        json!(x)
    }
}

fn jopt(x: Option<f64>) -> Value {
    x.map(jnum).unwrap_or(Value::Null)
}

fn jvec(v: &Option<Vec<f64>>) -> Value {
    match v {
        Some(v) => Value::Array(v.iter().copied().map(jnum).collect()),
        None => Value::Null,
    }
}

fn jstr(s: &Option<String>) -> Value {
    s.as_ref().map(|s| Value::String(s.clone())).unwrap_or(Value::Null)
}

fn jrefusal(r: &Option<Refusal>) -> Value {
    match r {
        Some(r) => json!({"code": r.code, "field": r.field, "reason": r.reason}),
        None => Value::Null,
    }
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Warning {
    pub code: String,
    pub message: String,
    /// Metin alanları, Python `_warn(**extra)` sırasıyla (ör. `IPO_PRICE_NOT_ON_TICK_GRID`:
    /// `field`, `value`, `snapped`, `tick`). Sayısal `value` alanı bunlarla genişletilmez.
    pub text_fields: Vec<(String, String)>,
    /// Mantıksal alanlar, Python çağrı sırasıyla (EK 3 §2.4; P2'nin `WARN_D1_LOCK_INCONSISTENT` alanları için).
    pub bool_fields: Vec<(String, bool)>,
    pub feature: Option<String>,
    pub horizon: Option<String>,
    pub value: Option<f64>,
    pub used: Option<f64>,
    pub train_min: Option<f64>,
    pub train_max: Option<f64>,
}

impl Warning {
    pub fn to_json(&self) -> Value {
        let mut m = Map::new();
        m.insert("code".into(), Value::String(self.code.clone()));
        m.insert("message".into(), Value::String(self.message.clone()));
        for (k, v) in &self.text_fields {
            m.insert(k.clone(), Value::String(v.clone()));
        }
        for (k, v) in &self.bool_fields {
            m.insert(k.clone(), Value::Bool(*v));
        }
        if let Some(f) = &self.feature {
            m.insert("feature".into(), Value::String(f.clone()));
        }
        if let Some(h) = &self.horizon {
            m.insert("horizon".into(), Value::String(h.clone()));
        }
        for (k, v) in [("value", self.value), ("used", self.used), ("train_min", self.train_min), ("train_max", self.train_max)] {
            if let Some(x) = v {
                m.insert(k.into(), jnum(x));
            }
        }
        Value::Object(m)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct HorizonCell {
    pub ret: Option<f64>,
    pub return_unclipped: Option<f64>,
    /// "UPPER" | "LOWER"
    pub return_clipped: Option<String>,
    pub price: Option<f64>,
    pub p_up: Option<f64>,
    /// "UP" | "DOWN"
    pub direction: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PbFeatureValues {
    pub pb1: f64,
    pub pb2: f64,
    pub pb3: f64,
    pub pb4: f64,
}

/// linear / rule / pb / market20.
#[derive(Debug, Clone, PartialEq)]
pub struct LinearOutput {
    pub model_id: Option<String>,
    pub horizons: Vec<(String, Option<HorizonCell>)>,
    pub warnings: Vec<Warning>,
    pub refused: Option<Refusal>,
    /// Yalnız pb: `Some(None)` = JSON null.
    pub features: Option<Option<PbFeatureValues>>,
    /// Yalnız market20: `Some(None)` = JSON null.
    pub f6_market20: Option<Option<f64>>,
    /// Yalnız Faz 7C `fall_d10_v0` ailesi (`predict_fall.predict` ek anahtarları; her zaman yazılır, boşsa null).
    pub fall: Option<FallOut>,
}

/// `fall_d10_v0` çıktı ekleri (Python `predict_fall.predict` sözlük sırası: `clipped`, `clipped_features`, `f1r_raw`,
/// `tufe_index_used`, `add_sale_used`). Ret anında o ana kadar dolan alanlar korunur (Python `out` sözlüğü).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct FallOut {
    pub clipped: Option<bool>,
    /// Kırpılan sütunlar (`prep.columns` sırası).
    pub clipped_features: Option<Vec<String>>,
    /// f1r'nin ham değeri (2025 TL); yalnız TÜFE girdisi geçerliyken.
    pub f1r_raw: Option<f64>,
    /// Kullanılan TÜFE endeksi (`str(Decimal)`).
    pub tufe_index_used: Option<String>,
    /// Ek satış bayrağı (0 | 1).
    pub add_sale_used: Option<u8>,
}

/// `ceiling_hazard_v1` çıktı ekleri (Python `_V1_OUTPUT_KEYS` sırası): yalnız v1 ailesinde ve yalnız doğrusal
/// öngörücünün doldurduğu alanlar (EK 3 §2.4).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct V1Out {
    /// Her zaman yazılır: kırpılan sütunlar (`prep.columns` sırası) ya da null (özellik yok / TÜFE reddi / erken ret).
    pub clipped_features: Option<Vec<String>>,
    /// f1r'nin ham değeri (2025 TL); yalnız TÜFE girdisi geçerliyken.
    pub f1r_raw: Option<f64>,
    /// Kullanılan TÜFE endeksi (`str(Decimal)`); yalnız TÜFE girdisi geçerliyken.
    pub tufe_index_used: Option<String>,
    /// Yalnız rejim adımı geçildiyse.
    pub regime_value_used: Option<u8>,
    /// "LIVE_VALUE" | "ALLOC_REGIME_INPUT"
    pub regime_source: Option<&'static str>,
}

/// hazard / km.
#[derive(Debug, Clone, PartialEq)]
pub struct HazardOutput {
    pub model_id: Option<String>,
    pub hazard: Option<Vec<f64>>,
    pub s: Option<Vec<f64>>,
    pub p_l: Option<Vec<f64>>,
    pub p_close_ceiling: Option<Vec<f64>>,
    pub clipped: Option<bool>,
    pub warnings: Vec<Warning>,
    pub refused: Option<Refusal>,
    /// Yalnız `ceiling_hazard_v1` ailesinde `Some` (v0/PB/KM çıktıları bayt-eşit kalır).
    pub v1: Option<V1Out>,
}

/// `ceiling_path`: `limit_path` bloğunun metin alanları birebir sınanır (SPEC_APP EK 2 §3.3).
#[derive(Debug, Clone, PartialEq)]
pub struct LimitPathOut {
    pub ipo_price: String,
    pub snapped_ipo_price: String,
    pub tick: String,
    pub c: Vec<String>,
    pub rho: Vec<f64>,
}

impl LimitPathOut {
    pub fn to_json(&self) -> Value {
        json!({
            "ipo_price": self.ipo_price,
            "snapped_ipo_price": self.snapped_ipo_price,
            "tick": self.tick,
            "C": self.c,
            "rho": self.rho.iter().copied().map(jnum).collect::<Vec<_>>(),
        })
    }
}

/// `ceiling_path` (tavan yolu): seri alanları + limit yolu + D1..D10 karışım özetleri.
#[derive(Debug, Clone, PartialEq)]
pub struct PathOutput {
    pub model_id: Option<String>,
    pub refused: Option<Refusal>,
    pub warnings: Vec<Warning>,
    pub clipped: Option<bool>,
    pub hazard: Option<Vec<f64>>,
    pub s: Option<Vec<f64>>,
    pub p_l: Option<Vec<f64>>,
    pub p_close_ceiling: Option<Vec<f64>>,
    pub limit_path: Option<LimitPathOut>,
    /// D1..D10 (10 öğe).
    pub horizons: Vec<Option<Horizon>>,
}

/// `post_d1_hazard_v0` kapsam dışı (ret değil): `{code, reason}` (alan yok; Python `D1NotApplicable`).
#[derive(Debug, Clone, PartialEq)]
pub struct NotApplicable {
    pub code: String,
    pub reason: String,
}

/// j = 1 koşullu görünüm (`predict_post_d1.curves`): S_cond k = 2..10, P_L_cond l = 1..10 (metin anahtarlı sözlükler).
#[derive(Debug, Clone, PartialEq)]
pub struct ConditionalJ1 {
    /// k = 2..10 sırasıyla.
    pub s_cond: Vec<f64>,
    pub p_break_next: f64,
    /// l = 1..10 sırasıyla.
    pub p_l_cond: Vec<f64>,
}

impl ConditionalJ1 {
    pub fn to_json(&self) -> Value {
        let s: Map<String, Value> = self.s_cond.iter().enumerate().map(|(i, x)| ((i + 2).to_string(), jnum(*x))).collect();
        let pl: Map<String, Value> = self.p_l_cond.iter().enumerate().map(|(i, x)| ((i + 1).to_string(), jnum(*x))).collect();
        json!({"S_cond": Value::Object(s), "p_break_next": jnum(self.p_break_next), "P_L_cond": Value::Object(pl)})
    }
}

/// `d1_features` (Python sözlük sırası).
#[derive(Debug, Clone, PartialEq)]
pub struct D1Features {
    pub d1_lock: u8,
    /// `str(Decimal)`: hacim / arz edilen pay (60 hane).
    pub d1_turnover_ratio: String,
    pub d1_turnover_ln: f64,
    pub clipped: bool,
    pub d1_turnover_used: f64,
    /// u (z-skor), `d1_preprocessing.columns` sırasıyla.
    pub z: Vec<(String, f64)>,
    pub ceiling_close_d1: u8,
    /// `open_at_U`, `high_at_U`, `close_at_U`.
    pub lock_consistency: Vec<(String, bool)>,
}

impl D1Features {
    pub fn to_json(&self) -> Value {
        let z: Map<String, Value> = self.z.iter().map(|(k, v)| (k.clone(), jnum(*v))).collect();
        let lc: Map<String, Value> = self.lock_consistency.iter().map(|(k, v)| (k.clone(), Value::Bool(*v))).collect();
        let mut m = Map::new();
        m.insert("d1_lock".into(), json!(self.d1_lock));
        m.insert("d1_turnover_ratio".into(), Value::String(self.d1_turnover_ratio.clone()));
        m.insert("d1_turnover_ln".into(), jnum(self.d1_turnover_ln));
        m.insert("clipped".into(), Value::Bool(self.clipped));
        m.insert("d1_turnover_used".into(), jnum(self.d1_turnover_used));
        m.insert("z".into(), Value::Object(z));
        m.insert("ceiling_close_D1".into(), json!(self.ceiling_close_d1));
        m.insert("lock_consistency".into(), Value::Object(lc));
        Value::Object(m)
    }
}

/// `post_d1_hazard_v0` (`borsai/predict_post_d1.py: predict_post_d1`; EK 3 §6.2).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct PostD1Output {
    pub model_id: Option<String>,
    pub refused: Option<Refusal>,
    pub not_applicable: Option<NotApplicable>,
    pub warnings: Vec<Warning>,
    /// f3 kırpma bayrağı (ana modelden).
    pub clipped: Option<bool>,
    pub hazard: Option<Vec<f64>>,
    pub s: Option<Vec<f64>>,
    pub p_l: Option<Vec<f64>>,
    pub p_close_ceiling: Option<Vec<f64>>,
    pub conditional_j1: Option<ConditionalJ1>,
    /// `predict_path.conditional(ceiling_path_v0, çıktı ⊕ bu modelin S'i, 1, [kapanış(D_1)])` JSON'u aynen.
    pub path_conditional: Option<Value>,
    pub d1_features: Option<D1Features>,
}

pub const STAGE_POST_D1: &str = "POST_D1";

impl PostD1Output {
    pub fn to_json(&self) -> Value {
        let mut m = Map::new();
        m.insert("model_id".into(), jstr(&self.model_id));
        m.insert("stage".into(), Value::String(STAGE_POST_D1.into()));
        m.insert("refused".into(), jrefusal(&self.refused));
        m.insert(
            "not_applicable".into(),
            self.not_applicable.as_ref().map(|n| json!({"code": n.code, "reason": n.reason})).unwrap_or(Value::Null),
        );
        m.insert("warnings".into(), Value::Array(self.warnings.iter().map(Warning::to_json).collect()));
        m.insert("clipped".into(), self.clipped.map(Value::Bool).unwrap_or(Value::Null));
        m.insert("hazard".into(), jvec(&self.hazard));
        m.insert("S".into(), jvec(&self.s));
        m.insert("P_L".into(), jvec(&self.p_l));
        m.insert("P_close_ceiling".into(), jvec(&self.p_close_ceiling));
        m.insert("conditional_j1".into(), self.conditional_j1.as_ref().map(ConditionalJ1::to_json).unwrap_or(Value::Null));
        m.insert("path_conditional".into(), self.path_conditional.clone().unwrap_or(Value::Null));
        m.insert("d1_features".into(), self.d1_features.as_ref().map(D1Features::to_json).unwrap_or(Value::Null));
        Value::Object(m)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Output {
    Linear(LinearOutput),
    Hazard(HazardOutput),
    Path(PathOutput),
    /// Yalnız `post_d1::run_post_d1` üretir (`predict` dağıtımı bu türü çalıştırmaz).
    PostD1(PostD1Output),
}

impl Output {
    pub fn refused(&self) -> Option<&Refusal> {
        match self {
            Output::Linear(o) => o.refused.as_ref(),
            Output::Hazard(o) => o.refused.as_ref(),
            Output::Path(o) => o.refused.as_ref(),
            Output::PostD1(o) => o.refused.as_ref(),
        }
    }

    pub fn warnings(&self) -> &[Warning] {
        match self {
            Output::Linear(o) => &o.warnings,
            Output::Hazard(o) => &o.warnings,
            Output::Path(o) => &o.warnings,
            Output::PostD1(o) => &o.warnings,
        }
    }

    pub fn to_json(&self) -> Value {
        let mut m = Map::new();
        match self {
            Output::PostD1(o) => return o.to_json(),
            Output::Linear(o) => {
                m.insert("model_id".into(), jstr(&o.model_id));
                for (h, cell) in &o.horizons {
                    let v = match cell {
                        Some(c) => json!({
                            "return": jopt(c.ret),
                            "return_unclipped": jopt(c.return_unclipped),
                            "return_clipped": jstr(&c.return_clipped),
                            "price": jopt(c.price),
                            "p_up": jopt(c.p_up),
                            "direction": jstr(&c.direction),
                        }),
                        None => Value::Null,
                    };
                    m.insert(h.clone(), v);
                }
                m.insert("warnings".into(), Value::Array(o.warnings.iter().map(Warning::to_json).collect()));
                m.insert("refused".into(), jrefusal(&o.refused));
                if let Some(f) = &o.features {
                    let v = match f {
                        Some(f) => json!({"pb1": jnum(f.pb1), "pb2": jnum(f.pb2), "pb3": jnum(f.pb3), "pb4": jnum(f.pb4)}),
                        None => Value::Null,
                    };
                    m.insert("features".into(), v);
                }
                if let Some(f6) = &o.f6_market20 {
                    m.insert("f6_market20".into(), jopt(*f6));
                }
                if let Some(f) = &o.fall {
                    m.insert("clipped".into(), f.clipped.map(Value::Bool).unwrap_or(Value::Null));
                    m.insert("clipped_features".into(), f.clipped_features.as_ref().map(|c| json!(c)).unwrap_or(Value::Null));
                    m.insert("f1r_raw".into(), jopt(f.f1r_raw));
                    m.insert("tufe_index_used".into(), jstr(&f.tufe_index_used));
                    m.insert("add_sale_used".into(), f.add_sale_used.map(|x| json!(x)).unwrap_or(Value::Null));
                }
            }
            Output::Hazard(o) => {
                m.insert("model_id".into(), jstr(&o.model_id));
                m.insert("hazard".into(), jvec(&o.hazard));
                m.insert("S".into(), jvec(&o.s));
                m.insert("P_L".into(), jvec(&o.p_l));
                m.insert("P_close_ceiling".into(), jvec(&o.p_close_ceiling));
                m.insert("clipped".into(), o.clipped.map(Value::Bool).unwrap_or(Value::Null));
                m.insert("warnings".into(), Value::Array(o.warnings.iter().map(Warning::to_json).collect()));
                m.insert("refused".into(), jrefusal(&o.refused));
                if let Some(v) = &o.v1 {
                    m.insert(
                        "clipped_features".into(),
                        v.clipped_features.as_ref().map(|c| json!(c)).unwrap_or(Value::Null),
                    );
                    if let Some(x) = v.f1r_raw {
                        m.insert("f1r_raw".into(), jnum(x));
                    }
                    if let Some(t) = &v.tufe_index_used {
                        m.insert("tufe_index_used".into(), Value::String(t.clone()));
                    }
                    if let Some(r) = v.regime_value_used {
                        m.insert("regime_value_used".into(), json!(r));
                    }
                    if let Some(src) = v.regime_source {
                        m.insert("regime_source".into(), Value::String(src.into()));
                    }
                }
            }
            // Python `predict_path.predict` sözlük sırası
            Output::Path(o) => {
                m.insert("model_id".into(), jstr(&o.model_id));
                m.insert("refused".into(), jrefusal(&o.refused));
                m.insert("warnings".into(), Value::Array(o.warnings.iter().map(Warning::to_json).collect()));
                m.insert("clipped".into(), o.clipped.map(Value::Bool).unwrap_or(Value::Null));
                m.insert("hazard".into(), jvec(&o.hazard));
                m.insert("S".into(), jvec(&o.s));
                m.insert("P_L".into(), jvec(&o.p_l));
                m.insert("P_close_ceiling".into(), jvec(&o.p_close_ceiling));
                m.insert("limit_path".into(), o.limit_path.as_ref().map(LimitPathOut::to_json).unwrap_or(Value::Null));
                for (i, h) in o.horizons.iter().enumerate() {
                    let v = match h {
                        Some(h) => Value::Object(h.to_map()),
                        None => Value::Null,
                    };
                    m.insert(format!("D{}", i + 1), v);
                }
            }
        }
        Value::Object(m)
    }
}

impl Conditional {
    pub fn to_json(&self) -> Value {
        json!({
            "j": self.j,
            "S_cond": self.s_cond.iter().map(|x| jopt(*x)).collect::<Vec<_>>(),
            "P_L_cond": self.p_l_cond.iter().map(|x| jopt(*x)).collect::<Vec<_>>(),
            "p_break_next": jnum(self.p_break_next),
        })
    }
}
