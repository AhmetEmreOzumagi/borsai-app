//! `predict`'in uygulamadaki tek gerçeklemesi (SPEC_APP §1.2). Tauri'siz, saf crate.
//!
//! Tanım Python'dakidir: `borsai/predict.py`, `predict_hazard.py` (Faz 7 `ceiling_hazard_v1` dahil),
//! `predict_pb.py`, `predict_market20.py`, `features.py`, `horizons.py`, `survival.py`, `predict_path.py`,
//! `tufe.py`'nin okuma/denetim kısmı (SPEC_APP EK 3 §2–§3), `predict_post_d1.py` (EK 3 §6) ve `predict_fall.py`
//! (Faz 7C düşen arz; EK 3 §8). Bu crate bir porttur;
//! parite `app/parity/golden/*.jsonl` altın vektörleriyle `cargo test -p borsai_predict --test golden`
//! ile sınanır. fit, backtest, market20 (f6 hesabı), registry, freeze ve skorlama port edilmez.
pub mod dec;
pub mod error;
pub mod fall;
pub mod features;
pub mod hazard;
pub mod horizons;
pub mod linear;
pub mod market20;
pub mod output;
pub mod params;
pub mod path;
pub mod pb_features;
pub mod post_d1;
pub mod sum;
pub mod survival;
pub mod tufe;

use serde_json::{json, Map, Value};

pub use error::{PredictError, Refusal};
pub use output::Output;
pub use params::{check_params, model_kind, Kind};

/// Düz girdi sözlüğü (`borsai.registry.model_inputs` + isteğe bağlı f6 alanları); değerler metin.
pub type Inputs = Map<String, Value>;

/// `borsai/freeze.py: run_model` dağıtımı: tür → Python fonksiyonu.
pub fn predict(params: &Value, inputs: &Inputs) -> Result<Output, PredictError> {
    match model_kind(params) {
        Kind::Hazard | Kind::Km => {
            let p = params::parse_hazard(params)?;
            hazard::predict_hazard(&p, inputs).map(Output::Hazard)
        }
        Kind::CeilingPath => {
            let p = params::parse_path(params)?;
            path::predict_path(&p, inputs).map(Output::Path)
        }
        Kind::Market20 => market20::predict_market20(params, inputs).map(Output::Linear),
        Kind::Pb => {
            let p = params::parse_pb(params)?;
            linear::predict_pb(&p, inputs).map(Output::Linear)
        }
        Kind::Linear | Kind::Rule => {
            let p = params::parse_linear(params)?;
            linear::predict_core(&p, inputs, &[]).map(Output::Linear)
        }
        Kind::Fall => {
            let p = params::parse_fall(params)?;
            fall::predict_fall(&p, inputs).map(Output::Linear)
        }
        // Python `run_model`: D1 bülteni ister; listeleme öncesi akışta ERROR (giriş: `post_d1::run_post_d1`)
        Kind::PostD1 => Err(PredictError::params(params::POST_D1_NOT_PRE_LISTING)),
    }
}

/// `borsai/predict.py: predict` doğrudan (market20 sarmalayıcısı olmadan; FEATURE_NOT_PROVIDED yolu).
pub fn predict_core_only(params: &Value, inputs: &Inputs) -> Result<Output, PredictError> {
    let p = params::parse_linear(params)?;
    linear::predict_core(&p, inputs, &[]).map(Output::Linear)
}

pub const STATUS_PREDICTED: &str = "PREDICTED";
pub const STATUS_REFUSED: &str = "REFUSED";
pub const STATUS_ERROR: &str = "ERROR";

/// Tek model sonucu: `freeze.run_model` ile aynı alanlar.
#[derive(Debug, Clone, PartialEq)]
pub struct RunResult {
    pub kind: Kind,
    pub status: &'static str,
    pub refusal: Option<Refusal>,
    pub output: Option<Output>,
}

impl RunResult {
    pub fn to_json(&self) -> Value {
        json!({
            "kind": self.kind.as_str(),
            "status": self.status,
            "refusal": self.refusal.as_ref().map(|r| json!({"code": r.code, "field": r.field, "reason": r.reason})),
            "output": self.output.as_ref().map(Output::to_json),
        })
    }
}

pub fn run_model(params: &Value, inputs: &Inputs) -> RunResult {
    let kind = model_kind(params);
    match predict(params, inputs) {
        Ok(out) => {
            let refusal = out.refused().cloned();
            let status = if refusal.is_some() { STATUS_REFUSED } else { STATUS_PREDICTED };
            RunResult { kind, status, refusal, output: Some(out) }
        }
        Err(e) => RunResult {
            kind,
            status: STATUS_ERROR,
            refusal: Some(Refusal { code: e.code.clone(), field: None, reason: e.message.clone() }),
            output: None,
        },
    }
}

/// f6 (XU100 20 seans getirisi): hazır değer ya da neden kodu (SPEC_APP §3a.2).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct F6 {
    pub value: Option<Value>,
    pub refusal: Option<String>,
}

/// `inputs["f6_market20"]`, `inputs["f6_market20_refusal"]` (freeze.build_record gibi).
pub fn with_f6(inputs: &Inputs, f6: &F6) -> Inputs {
    let mut m = inputs.clone();
    m.insert("f6_market20".into(), f6.value.clone().unwrap_or(Value::Null));
    m.insert("f6_market20_refusal".into(), f6.refusal.clone().map(Value::String).unwrap_or(Value::Null));
    m
}

/// Gömülü bir model: kimlik, parametre dosyası sha256'sı, ayrıştırılmış JSON.
#[derive(Debug, Clone)]
pub struct ModelRef {
    pub model_id: String,
    pub params_sha256: String,
    pub params: Value,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ModelRun {
    pub model_id: String,
    pub params_sha256: String,
    pub result: RunResult,
}

impl ModelRun {
    pub fn to_json(&self) -> Value {
        let mut v = self.result.to_json();
        v["model_id"] = json!(self.model_id);
        v["params_sha256"] = json!(self.params_sha256);
        v
    }
}

/// Bütün modeller aynı girdiyle, verilen (INDEX) sırada (SPEC_APP §3b, U5).
pub fn predict_all(models: &[ModelRef], inputs: &Inputs, f6: &F6) -> Vec<ModelRun> {
    let full = with_f6(inputs, f6);
    models
        .iter()
        .map(|m| ModelRun { model_id: m.model_id.clone(), params_sha256: m.params_sha256.clone(), result: run_model(&m.params, &full) })
        .collect()
}
