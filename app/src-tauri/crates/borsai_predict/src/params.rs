//! Model parametre dosyası (`borsai.model/1`) okuma ve denetim (SPEC_APP §2.1).
//! Denetimler Python `_check_params`'ın (predict.py, predict_hazard.py, predict_pb.py) sırası ve
//! kodlarıyla aynıdır. Python'un yalnız kullanırken KeyError verdiği eksik alanlar burada da
//! PARAMS_INVALID sayılır (açılışta bütünlük yolu; U33).
use serde::Serialize;
use serde_json::{json, Map, Value};

use crate::error::{PredictError, SCHEMA_UNSUPPORTED};
use crate::horizons::horizon_days;
use crate::path::{self, Cells, GROUPS};
use crate::survival::{DAYS, DAY_GROUPS};

pub const SUPPORTED_SCHEMA: &str = "borsai.model/1";
pub const HAZARD_ALGORITHM: &str = "discrete_time_hazard_logit_l2";
pub const KM_ALGORITHMS: [&str; 2] = ["KM_EXPANDING", "KM_LAST10"];
pub const RIDGE_LOGIT_ALGORITHM: &str = "V1_5_RIDGE_LOGIT";
pub const CEILING_FEATURES: [&str; 3] = ["f1", "f2", "f3"];
pub const PB_CEILING_FEATURES: [&str; 2] = ["pb1", "pb2"];
/// Faz 7 `ceiling_hazard_v1` (JSON `family`); gerçek büyüklüklü özellik listesi (SPEC_APP EK 3 §2.2).
pub const FAMILY_V1: &str = "ceiling_hazard_v1";
pub const CEILING_V1_REAL_FEATURES: [&str; 3] = ["f1r", "f2", "f3"];
/// D1 sonrası güncelleme modeli (`borsai/predict_post_d1.py`; SPEC_APP EK 3 §6.1).
pub const POST_D1_ALGORITHM: &str = "discrete_time_hazard_offset_logit_l2";
pub const POST_D1_STAGE: &str = "POST_D1";
pub const POST_D1_PARENT_ID: &str = "ceiling_hazard_v0";
pub const POST_D1_PATH_ID: &str = "ceiling_path_v0";
pub const D1_COLUMNS: [&str; 2] = ["d1_lock", "d1_turnover"];
/// `UPDATED_DAYS = 2..10`.
pub const POST_D1_UPDATED_DAYS: [u64; 9] = [2, 3, 4, 5, 6, 7, 8, 9, 10];
/// Faz 7C düşen arz ailesi (`borsai/predict_fall.py`; SPEC_APP EK 3 §8). Tür ayrımı Python `freeze.model_kind` gibi
/// `algorithm`'dendir (referans kilidi: EK 3'ün `family` önerisi yerine).
pub const FALL_ALGORITHM: &str = "l2_logit_v1_6_grid";
pub const FAMILY_FALL: &str = "fall_d10_v0";
/// `FALL_HORIZONS`: çıktı bu sırayla yazılır (dosya sırası D10, D5 değil).
pub const FALL_HORIZONS: [&str; 2] = ["D5", "D10"];
pub const FALL_FEATURES: [&str; 3] = ["f1r", "f3", "add_sale"];
pub const ADDSALE_FEATURES: [&str; 1] = ["add_sale"];
/// `WINSOR_LOG_FEATURES`: kırpma ve ln yalnız bu ikisine.
pub const FALL_WINSOR_LOG: [&str; 2] = ["f1r", "f3"];

/// `borsai/freeze.py: model_kind` ile aynı ayrım.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    Hazard,
    Km,
    #[serde(rename = "ceiling_path")]
    CeilingPath,
    Market20,
    Pb,
    Linear,
    Rule,
    /// D1 sonrası güncelleme: listeleme öncesi akışta (`predict_all`) ÇALIŞMAZ; ayrı giriş `post_d1::run_post_d1`.
    #[serde(rename = "post_d1")]
    PostD1,
    /// Faz 7C düşen arz (`fall_d10_v0`; `@ZERO` kural satırı dahil): yalnız D5/D10 `p_up`, getiri başlığı yok.
    Fall,
}

impl Kind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Kind::Hazard => "hazard",
            Kind::Km => "km",
            Kind::CeilingPath => "ceiling_path",
            Kind::Market20 => "market20",
            Kind::Pb => "pb",
            Kind::Linear => "linear",
            Kind::Rule => "rule",
            Kind::PostD1 => "post_d1",
            Kind::Fall => "fall",
        }
    }
}

/// `list(params.get("features") or [])` öğelerinin `str()` karşılığı.
fn feature_names(p: &Value) -> Vec<String> {
    match p.get("features") {
        Some(Value::Array(a)) => a
            .iter()
            .map(|v| match v {
                Value::String(s) => s.clone(),
                other => other.to_string(),
            })
            .collect(),
        _ => Vec::new(),
    }
}

pub fn model_kind(p: &Value) -> Kind {
    let algorithm = p.get("algorithm").and_then(Value::as_str).unwrap_or("");
    let features = feature_names(p);
    if algorithm == HAZARD_ALGORITHM {
        return Kind::Hazard;
    }
    if algorithm == POST_D1_ALGORITHM {
        return Kind::PostD1;
    }
    if algorithm == FALL_ALGORITHM {
        return Kind::Fall;
    }
    if algorithm == path::ALGORITHM {
        return Kind::CeilingPath;
    }
    if KM_ALGORITHMS.contains(&algorithm) {
        return Kind::Km;
    }
    if algorithm == RIDGE_LOGIT_ALGORITHM {
        if features.iter().any(|f| f == "f6") {
            return Kind::Market20;
        }
        if features.iter().any(|f| f.starts_with("pb")) {
            return Kind::Pb;
        }
        return Kind::Linear;
    }
    Kind::Rule
}

// ---------------------------------------------------------------- ortak yardımcılar

fn bad(msg: impl Into<String>) -> PredictError {
    PredictError::params(msg)
}

/// JSON sayı -> binary64 (Python `float(int)`/float ile aynı yuvarlama).
fn num(v: &Value) -> Option<f64> {
    match v {
        Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

fn req_num(obj: &Value, key: &str, ctx: &str) -> Result<f64, PredictError> {
    obj.get(key).and_then(num).ok_or_else(|| bad(format!("{ctx}.{key} sayı değil")))
}

fn num_map(v: Option<&Value>, ctx: &str) -> Result<Map<String, Value>, PredictError> {
    match v {
        Some(Value::Object(m)) => {
            for (k, x) in m {
                if num(x).is_none() {
                    return Err(bad(format!("{ctx}.{k} sayı değil")));
                }
            }
            Ok(m.clone())
        }
        _ => Err(bad(format!("{ctx} yok"))),
    }
}

fn str_list(v: Option<&Value>, ctx: &str) -> Result<Vec<String>, PredictError> {
    match v {
        Some(Value::Array(a)) => a
            .iter()
            .map(|x| x.as_str().map(str::to_string).ok_or_else(|| bad(format!("{ctx} metin listesi değil"))))
            .collect(),
        _ => Err(bad(format!("{ctx} yok"))),
    }
}

fn check_schema(p: &Value) -> Result<(), PredictError> {
    if !p.is_object() {
        return Err(bad("params bir sözlük değil"));
    }
    match p.get("schema_version").and_then(Value::as_str) {
        Some(SUPPORTED_SCHEMA) => Ok(()),
        _ => Err(PredictError::new(
            SCHEMA_UNSUPPORTED,
            format!("schema_version={}", p.get("schema_version").unwrap_or(&Value::Null)),
        )),
    }
}

fn model_id(p: &Value) -> Option<String> {
    p.get("model_id").and_then(Value::as_str).map(str::to_string)
}

// ---------------------------------------------------------------- ön işleme

#[derive(Debug, Clone, PartialEq)]
pub struct Winsor {
    pub p05: f64,
    pub p95: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Prep {
    pub columns: Vec<String>,
    pub medians: Map<String, Value>,
    pub winsor: Vec<(String, Winsor)>,
    pub log_transform: Vec<String>,
    pub mean: Map<String, Value>,
    pub std: Map<String, Value>,
    pub f3_filter_mode: Option<String>,
}

impl Prep {
    pub fn median(&self, col: &str) -> Option<f64> {
        self.medians.get(col).and_then(num)
    }
    pub fn winsor_of(&self, col: &str) -> Option<&Winsor> {
        self.winsor.iter().find(|(c, _)| c == col).map(|(_, w)| w)
    }
    pub fn mean_of(&self, col: &str) -> Option<f64> {
        self.mean.get(col).and_then(num)
    }
    pub fn std_of(&self, col: &str) -> Option<f64> {
        self.std.get(col).and_then(num)
    }
}

/// `params["preprocessing"]`: null/yok -> None; sözlükse bütün alanlar zorunlu.
fn parse_prep(p: &Value) -> Result<Option<Prep>, PredictError> {
    let v = match p.get("preprocessing") {
        None | Some(Value::Null) => return Ok(None),
        Some(v @ Value::Object(_)) => v,
        Some(_) => return Err(bad("preprocessing sözlük değil")),
    };
    let columns = str_list(v.get("columns"), "preprocessing.columns")?;
    let mean = num_map(v.get("mean"), "preprocessing.mean")?;
    let std = num_map(v.get("std"), "preprocessing.std")?;
    for c in &columns {
        if !mean.contains_key(c) || !std.contains_key(c) {
            return Err(bad(format!("preprocessing: {c} için mean/std yok")));
        }
    }
    let medians = num_map(v.get("medians"), "preprocessing.medians")?;
    let winsor = match v.get("winsor") {
        Some(Value::Object(m)) => m
            .iter()
            .map(|(k, w)| {
                Ok((
                    k.clone(),
                    Winsor {
                        p05: req_num(w, "p05", "preprocessing.winsor")?,
                        p95: req_num(w, "p95", "preprocessing.winsor")?,
                    },
                ))
            })
            .collect::<Result<Vec<_>, PredictError>>()?,
        _ => return Err(bad("preprocessing.winsor yok")),
    };
    let log_transform = str_list(v.get("log_transform"), "preprocessing.log_transform")?;
    let f3_filter_mode = v.get("f3_filter_mode").and_then(Value::as_str).map(str::to_string);
    Ok(Some(Prep { columns, medians, winsor, log_transform, mean, std, f3_filter_mode }))
}

#[derive(Debug, Clone, PartialEq)]
pub struct Range {
    pub feature: String,
    pub min: f64,
    pub max: f64,
}

/// `params.get("feature_ranges", {})`, dosyadaki sırayla.
fn parse_ranges(p: &Value) -> Result<Vec<Range>, PredictError> {
    match p.get("feature_ranges") {
        None => Ok(Vec::new()),
        Some(Value::Object(m)) => m
            .iter()
            .map(|(k, r)| {
                Ok(Range {
                    feature: k.clone(),
                    min: req_num(r, "min", "feature_ranges")?,
                    max: req_num(r, "max", "feature_ranges")?,
                })
            })
            .collect(),
        Some(_) => Err(bad("feature_ranges sözlük değil")),
    }
}

// ---------------------------------------------------------------- doğrusal (V1.5 ailesi, PB, kurallar)

#[derive(Debug, Clone, PartialEq)]
pub enum Head {
    Constant(f64),
    /// ridge (getiri) ya da logit (p_up): sabit + Σ katsayı·z
    Linear { coef: Vec<f64>, intercept: f64 },
}

#[derive(Debug, Clone, PartialEq)]
pub struct Heads {
    pub ret: Option<Head>,
    pub p_up: Option<Head>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct LinearParams {
    pub model_id: Option<String>,
    pub features: Vec<String>,
    /// JSON anahtar sırası (dosya sort_keys ile: D1, D10, D3, D5).
    pub horizons: Vec<(String, Heads)>,
    pub prep: Option<Prep>,
    pub f3_missing: Option<String>,
    pub f3_filter_status_conflict: Option<String>,
    pub feature_ranges: Vec<Range>,
}

impl LinearParams {
    pub fn range_min(&self, feature: &str) -> Option<f64> {
        self.feature_ranges.iter().find(|r| r.feature == feature).map(|r| r.min)
    }
}

fn parse_head(h: &str, name: &str, head: &Value, prep: Option<&Prep>) -> Result<Head, PredictError> {
    let kind = head.get("kind").and_then(Value::as_str).unwrap_or("");
    match kind {
        "constant" => match head.get("value") {
            Some(Value::Number(n)) => Ok(Head::Constant(n.as_f64().unwrap_or(f64::NAN))),
            // Python isinstance(True, (int, float)) doğrudur; float(True) = 1.0
            Some(Value::Bool(b)) => Ok(Head::Constant(if *b { 1.0 } else { 0.0 })),
            _ => Err(bad(format!("{h}.{name}: sabit değer yok"))),
        },
        "ridge" | "logit" => {
            let columns = str_list(head.get("columns"), &format!("{h}.{name}.columns"))?;
            let coef = match head.get("coef") {
                Some(Value::Array(a)) => a.iter().map(num).collect::<Option<Vec<f64>>>(),
                _ => None,
            };
            let Some(prep) = prep else {
                return Err(bad(format!("{h}.{name}: kolonlar ön işlemeyle uyuşmuyor")));
            };
            let coef = coef.ok_or_else(|| bad(format!("{h}.{name}: coef sayı listesi değil")))?;
            if columns != prep.columns || coef.len() != columns.len() {
                return Err(bad(format!("{h}.{name}: kolonlar ön işlemeyle uyuşmuyor")));
            }
            let intercept = req_num(head, "intercept", &format!("{h}.{name}"))?;
            Ok(Head::Linear { coef, intercept })
        }
        other => Err(bad(format!("{h}.{name}: bilinmeyen kind {other:?}"))),
    }
}

/// predict.py `_check_params` + okuma.
pub fn parse_linear(p: &Value) -> Result<LinearParams, PredictError> {
    check_schema(p)?;
    let horizons_v = match p.get("horizons") {
        Some(Value::Object(m)) if !m.is_empty() => m,
        _ => return Err(bad("horizons yok")),
    };
    let prep = parse_prep(p)?;
    let mut horizons = Vec::with_capacity(horizons_v.len());
    for (h, heads) in horizons_v {
        if !heads.is_object() {
            return Err(bad(format!("{h}: başlıklar sözlük değil")));
        }
        let mut parsed = Heads { ret: None, p_up: None };
        for name in ["return", "p_up"] {
            let head = match heads.get(name) {
                None | Some(Value::Null) => continue,
                Some(v) => v,
            };
            let hd = parse_head(h, name, head, prep.as_ref())?;
            if name == "return" {
                if horizon_days(h).is_none() {
                    return Err(bad(format!("{h}: bilinmeyen ufuk")));
                }
                parsed.ret = Some(hd);
            } else {
                parsed.p_up = Some(hd);
            }
        }
        horizons.push((h.clone(), parsed));
    }
    let policy = p.get("input_policy");
    let pol = |k: &str| policy.and_then(|x| x.get(k)).and_then(Value::as_str).map(str::to_string);
    Ok(LinearParams {
        model_id: model_id(p),
        features: feature_names(p),
        horizons,
        prep,
        f3_missing: pol("f3_missing"),
        f3_filter_status_conflict: pol("f3_filter_status_conflict"),
        feature_ranges: parse_ranges(p)?,
    })
}

/// predict_pb.py: `_check_params` + "PB modeli değil" denetimi.
pub fn parse_pb(p: &Value) -> Result<LinearParams, PredictError> {
    let lp = parse_linear(p)?;
    if !lp.features.iter().any(|f| f.starts_with("pb")) {
        return Err(bad("PB modeli değil (özellikler pb1..)"));
    }
    if lp.prep.is_none() {
        return Err(bad("PB modelinde preprocessing yok"));
    }
    Ok(lp)
}

// ---------------------------------------------------------------- tavan (hazard, KM)

/// Tahsis rejimi terimi (JSON `regime`; yalnız pooled ve pooled@INF): η_d = γ_{g(d)} + δ·r + β·z.
#[derive(Debug, Clone, PartialEq)]
pub struct Regime {
    pub delta: f64,
    /// `alloc_regime` girdisi yoksa (canlı tahmin) kullanılan r.
    pub live_value: u8,
}

/// `ceiling_hazard_v1` ailesinin okunan alanları (EK 3 §2.1). Başka v1 alanı okunmaz.
#[derive(Debug, Clone, PartialEq)]
pub struct V1Params {
    /// "clip" | "real" | "pooled" (JSON `variant`; bilgi).
    pub variant: Option<String>,
    /// Yalnız `f1r` özellikli modellerde: TÜFE önek pini (kayıt/tahmin girdisini hazırlayan çağıran kullanır).
    pub deflator: Option<crate::tufe::DeflatorPin>,
    pub regime: Option<Regime>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct HazardParams {
    pub model_id: Option<String>,
    pub km: bool,
    pub features: Vec<String>,
    pub gamma: [f64; 3],
    pub beta: Vec<(String, f64)>,
    pub prep: Option<Prep>,
    pub feature_ranges: Vec<Range>,
    pub r_a: f64,
    pub r_b: f64,
    /// KM: `survival.hazard` (10 değer).
    pub km_hazard: Vec<f64>,
    /// `family == "ceiling_hazard_v1"` ise dolu (v0/PB/KM'de `None`).
    pub v1: Option<V1Params>,
}

impl HazardParams {
    pub fn beta_of(&self, c: &str) -> Option<f64> {
        self.beta.iter().find(|(k, _)| k == c).map(|(_, v)| *v)
    }
}

fn reclose(p: &Value) -> Result<(f64, f64), PredictError> {
    let r = p.get("reclose_rates").ok_or_else(|| bad("reclose_rates yok"))?;
    let (Some(a), Some(b)) = (r.get("r_a").and_then(num), r.get("r_b").and_then(num)) else {
        return Err(bad("reclose_rates yok"));
    };
    Ok((a, b))
}

/// predict_hazard.py `_check_params` + okuma.
pub fn parse_hazard(p: &Value) -> Result<HazardParams, PredictError> {
    check_schema(p)?;
    let algorithm = p.get("algorithm").and_then(Value::as_str).unwrap_or("");
    if KM_ALGORITHMS.contains(&algorithm) {
        let curve = p.get("survival");
        let s_len = curve.and_then(|c| c.get("S")).and_then(Value::as_array).map(Vec::len);
        if s_len != Some(DAYS) {
            return Err(bad("survival.S 10 değer değil"));
        }
        let hz = curve
            .and_then(|c| c.get("hazard"))
            .and_then(Value::as_array)
            .and_then(|a| a.iter().map(num).collect::<Option<Vec<f64>>>())
            .filter(|h| h.len() == DAYS)
            .ok_or_else(|| bad("survival.hazard 10 sayı değil"))?;
        let (r_a, r_b) = reclose(p)?;
        return Ok(HazardParams {
            model_id: model_id(p),
            km: true,
            features: Vec::new(),
            gamma: [0.0; 3],
            beta: Vec::new(),
            prep: None,
            feature_ranges: Vec::new(),
            r_a,
            r_b,
            km_hazard: hz,
            v1: None,
        });
    }
    if algorithm != HAZARD_ALGORITHM {
        return Err(bad(format!("tavan modeli değil: {algorithm:?}")));
    }
    let features = feature_names(p);
    let is_v1 = p.get("family").and_then(Value::as_str) == Some(FAMILY_V1);
    let ok_features = features.is_empty()
        || features == CEILING_FEATURES
        || if is_v1 { features == CEILING_V1_REAL_FEATURES } else { features == PB_CEILING_FEATURES };
    if !ok_features {
        return Err(bad(format!("desteklenmeyen özellik listesi {features:?}")));
    }
    let v1 = if is_v1 { Some(parse_v1(p, &features)?) } else { None };
    let groups_ok = match p.get("day_groups") {
        Some(Value::Object(m)) => {
            m.len() == DAY_GROUPS.len()
                && DAY_GROUPS.iter().all(|(g, days)| {
                    m.get(*g).and_then(Value::as_array).is_some_and(|a| {
                        a.len() == days.len() && a.iter().zip(days.iter()).all(|(x, d)| x.as_u64() == Some(*d as u64))
                    })
                })
        }
        _ => false,
    };
    if !groups_ok {
        return Err(bad("gün grupları şartnameyle aynı değil"));
    }
    let gamma: Vec<f64> = match p.get("gamma") {
        Some(Value::Array(a)) => a.iter().map(num).collect::<Option<Vec<f64>>>().unwrap_or_default(),
        _ => Vec::new(),
    };
    let beta: Vec<(String, f64)> = match p.get("beta") {
        Some(Value::Object(m)) => m.iter().map(|(k, v)| (k.clone(), num(v).unwrap_or(f64::NAN))).collect(),
        _ => Vec::new(),
    };
    let beta_keys: std::collections::BTreeSet<&str> = beta.iter().map(|(k, _)| k.as_str()).collect();
    let feat_keys: std::collections::BTreeSet<&str> = features.iter().map(String::as_str).collect();
    if gamma.len() != 3 || beta_keys != feat_keys {
        return Err(bad("gamma/beta boyutu tutmuyor"));
    }
    if beta.iter().any(|(_, v)| v.is_nan()) {
        return Err(bad("beta sayı değil"));
    }
    let prep = parse_prep(p)?;
    if !features.is_empty() {
        let ok = prep.as_ref().is_some_and(|pr| pr.columns.iter().all(|c| feat_keys.contains(c.as_str())));
        if !ok {
            return Err(bad("ön işleme kolonları özelliklerle uyuşmuyor"));
        }
    }
    let (r_a, r_b) = reclose(p)?;
    Ok(HazardParams {
        model_id: model_id(p),
        km: false,
        features,
        gamma: [gamma[0], gamma[1], gamma[2]],
        beta,
        prep,
        feature_ranges: parse_ranges(p)?,
        r_a,
        r_b,
        km_hazard: Vec::new(),
        v1,
    })
}

/// `_check_params` v1 dalı (Python sırası: kırpma sınırları → deflator → regime); ardından okuma.
fn parse_v1(p: &Value, features: &[String]) -> Result<V1Params, PredictError> {
    if !features.is_empty() {
        let winsor: std::collections::BTreeSet<&str> = p
            .get("preprocessing")
            .and_then(|x| x.get("winsor"))
            .and_then(Value::as_object)
            .map(|m| m.keys().map(String::as_str).collect())
            .unwrap_or_default();
        let feats: std::collections::BTreeSet<&str> = features.iter().map(String::as_str).collect();
        if winsor != feats {
            return Err(bad("v1: kırpma sınırları üç özelliğin hepsi için değil"));
        }
    }
    let deflator = p.get("deflator").filter(|d| d.is_object());
    if features.iter().any(|f| f == "f1r") && deflator.is_none() {
        return Err(bad("v1: f1r var ama deflator bloğu yok"));
    }
    let regime = match p.get("regime") {
        None | Some(Value::Null) => None,
        Some(r) => {
            let invalid = || bad("v1: regime bloğu geçersiz (delta, penalized, live_value)");
            // Python: isinstance(delta, (int, float)) and not bool; penalized is False; live_value in (0, 1)
            let delta = r.get("delta").and_then(num).ok_or_else(invalid)?;
            if r.get("penalized") != Some(&Value::Bool(false)) {
                return Err(invalid());
            }
            let live_value = match r.get("live_value") {
                Some(Value::Bool(b)) => u8::from(*b),
                Some(Value::Number(n)) if n.as_f64() == Some(0.0) => 0,
                Some(Value::Number(n)) if n.as_f64() == Some(1.0) => 1,
                _ => return Err(invalid()),
            };
            Some(Regime { delta, live_value })
        }
    };
    let text = |d: &Value, k: &str| d.get(k).and_then(Value::as_str).map(str::to_string);
    let deflator = deflator.and_then(|d| {
        Some(crate::tufe::DeflatorPin { through_month: text(d, "through_month")?, prefix_sha256: text(d, "file_sha256")? })
    });
    Ok(V1Params { variant: text(p, "variant"), deflator, regime })
}

// ---------------------------------------------------------------- tavan yolu (ceiling_path)

#[derive(Debug, Clone, PartialEq)]
pub struct PathParams {
    pub model_id: Option<String>,
    /// Gömülü (dondurulmuş) seri modelinin ayrıştırılmış parametreleri.
    pub survival: HazardParams,
    /// Aynı modelin ham JSON'u (U41 bütünlük denetimi gömülü dosyayla bunu karşılaştırır).
    pub survival_raw: Value,
    /// `ipo_price_tl` | `ipo_price_try`
    pub price_field: String,
    pub cells: Cells,
}

/// `limit_path` sabitleri şartnamedekiyle JSON-eşit mi (`margin`, `tick_table`, `upper_rounding`,
/// `d1_base`); `lower_rounding` ve `rule_source` OKUNMAZ.
fn limit_path_constants_ok(lp: &Value) -> bool {
    let table: Vec<Value> = path::TICK_TABLE
        .iter()
        .map(|(below, tick)| json!({"below": below.map(Value::from).unwrap_or(Value::Null), "tick": tick}))
        .collect();
    lp.get("margin") == Some(&json!(path::MARGIN))
        && lp.get("tick_table") == Some(&Value::Array(table))
        && lp.get("upper_rounding") == Some(&json!(path::UPPER_ROUNDING))
        && lp.get("d1_base") == Some(&json!(path::D1_BASE))
}

/// `post_break.cells` → `Cells`. Anahtar kümeleri tam Z 1..10 / B 1..9 olmalı.
fn parse_cells(doc: &Value) -> Result<Cells, PredictError> {
    let Some(obj) = doc.as_object() else {
        return Err(bad("hücre anahtarları Z 1..10 / B 1..9 değil"));
    };
    let mut cells: Cells = Cells::new();
    for g in GROUPS {
        let inner = obj.get(g.as_str()).and_then(Value::as_object);
        let want: std::collections::BTreeSet<String> = (1..=g.m_max()).map(|m| m.to_string()).collect();
        let got: std::collections::BTreeSet<String> =
            inner.map(|m| m.keys().cloned().collect()).unwrap_or_default();
        if got != want {
            return Err(bad("hücre anahtarları Z 1..10 / B 1..9 değil"));
        }
        for (key, list) in inner.expect("anahtar kümesi eşit") {
            let m: i32 = key.parse().map_err(|_| bad(format!("hücre anahtarı {key:?}")))?;
            let rows = list.as_array().ok_or_else(|| bad(format!("hücre {key:?} liste değil")))?;
            let mut out = Vec::with_capacity(rows.len());
            for r in rows {
                // Python `cells_from_json`: float(v), str(tk); bozuk değer etiketsiz istisna verir.
                let pair = r.as_array().filter(|a| a.len() == 2).ok_or_else(|| bad("hücre gözlemi (değer, ticker) değil"))?;
                let v = num(&pair[0]).ok_or_else(|| bad("hücre değeri sayı değil"))?;
                let tk = pair[1].as_str().map(str::to_string).unwrap_or_else(|| pair[1].to_string());
                out.push((v, tk));
            }
            cells.insert((g, m), out);
        }
    }
    Ok(cells)
}

/// `predict_path._check_params` + okuma. Sıra: schema → algorithm → survival_model (yüzeysel) →
/// limit_path → post_break; gömülü seri modelinin kendi denetimleri Python'da `ph.predict`
/// içinde, yani en sonda koşar.
pub fn parse_path(p: &Value) -> Result<PathParams, PredictError> {
    check_schema(p)?;
    let algorithm = p.get("algorithm").and_then(Value::as_str).unwrap_or("");
    if algorithm != path::ALGORITHM {
        return Err(bad(format!("tavan yolu modeli değil: {algorithm:?}")));
    }
    let surv = p.get("survival_model");
    let id_ok = surv.and_then(|s| s.get("model_id")) == p.get("survival_model_id");
    let alg_ok = surv.and_then(|s| s.get("algorithm")).and_then(Value::as_str) == Some(HAZARD_ALGORITHM);
    if !surv.is_some_and(Value::is_object) || !id_ok || !alg_ok {
        return Err(bad("gömülü seri modeli yok ya da kimliği tutmuyor"));
    }
    let surv = surv.expect("sözlük");
    let lp = p.get("limit_path").cloned().unwrap_or(Value::Object(Map::new()));
    let field = lp.get("price_field").and_then(Value::as_str).unwrap_or("");
    if !limit_path_constants_ok(&lp) || !path::PRICE_FIELDS.contains(&field) {
        return Err(bad("limit yolu sabitleri şartnameyle aynı değil"));
    }
    let pbk = p.get("post_break").cloned().unwrap_or(Value::Object(Map::new()));
    let groups: Vec<&str> = GROUPS.iter().map(|g| g.as_str()).collect();
    if pbk.get("N_MIN") != Some(&json!(path::N_MIN))
        || pbk.get("groups").and_then(Value::as_array).map(|a| a.iter().filter_map(Value::as_str).collect::<Vec<_>>())
            != Some(groups)
    {
        return Err(bad("kırılma sonrası sabitleri şartnameyle aynı değil"));
    }
    let cells = parse_cells(pbk.get("cells").unwrap_or(&Value::Null))?;
    Ok(PathParams {
        model_id: model_id(p),
        survival: parse_hazard(surv)?,
        survival_raw: surv.clone(),
        price_field: field.to_string(),
        cells,
    })
}

// ---------------------------------------------------------------- düşen arz (fall_d10_v0)

/// `predict_fall` ailesinin okunan alanları (EK 3 §8.1; referans kilidi `predict_fall._check_params`).
#[derive(Debug, Clone, PartialEq)]
pub struct FallParams {
    pub model_id: Option<String>,
    /// `[]` (`@ZERO`) | `[f1r, f3, add_sale]` (h99, pooled) | `[add_sale]` (addsale).
    pub features: Vec<String>,
    /// `p_up` başlıkları `FALL_HORIZONS` sırasıyla (D5, D10).
    pub horizons: Vec<(String, Head)>,
    pub prep: Option<Prep>,
    pub f3_filter_status_conflict: Option<String>,
    pub feature_ranges: Vec<Range>,
    /// f1r'li modellerde TÜFE önek pini (kayıt/tahmin girdisini hazırlayan çağıran kullanır).
    pub deflator: Option<crate::tufe::DeflatorPin>,
    /// JSON `variant` (bilgi): h99 | pooled | addsale | pooled@ZERO.
    pub variant: Option<String>,
}

impl FallParams {
    pub fn uses(&self, feature: &str) -> bool {
        self.features.iter().any(|f| f == feature)
    }
}

/// `predict_fall._check_params` birebir sırada (sözlük → şema → aile/algoritma → özellik listesi → ufuklar {D5, D10} →
/// ön işleme kolonları ⊆ özellikler → kırpma/log kümeleri `[f1r, f3] ∩ özellikler` → f1r varsa deflator → her ufukta
/// getiri başlığı yok ve `p_up` sabit (bool değil) ya da kolonları ön işlemeyle aynı logit); ardından okuma. Python'un
/// yalnız kullanırken KeyError verdiği eksik alanlar (mean/std, intercept) burada da PARAMS_INVALID sayılır.
pub fn parse_fall(p: &Value) -> Result<FallParams, PredictError> {
    check_schema(p)?;
    let text = |k: &str| p.get(k).and_then(Value::as_str);
    if text("family") != Some(FAMILY_FALL) || text("algorithm") != Some(FALL_ALGORITHM) {
        return Err(bad(format!(
            "düşen arz modeli değil: {} / {}",
            p.get("family").unwrap_or(&Value::Null),
            p.get("algorithm").unwrap_or(&Value::Null)
        )));
    }
    let features = match p.get("features") {
        None => Vec::new(),
        Some(Value::Array(_)) => feature_names(p),
        Some(other) => return Err(bad(format!("desteklenmeyen özellik listesi {other}"))),
    };
    if !(features.is_empty() || features == FALL_FEATURES || features == ADDSALE_FEATURES) {
        return Err(bad(format!("desteklenmeyen özellik listesi {features:?}")));
    }
    let horizons_v = match p.get("horizons") {
        Some(Value::Object(m)) => m,
        _ => return Err(bad(format!("ufuklar {FALL_HORIZONS:?} değil"))),
    };
    let mut keys: Vec<&str> = horizons_v.keys().map(String::as_str).collect();
    keys.sort_unstable();
    let mut want: Vec<&str> = FALL_HORIZONS.to_vec();
    want.sort_unstable();
    if keys != want {
        return Err(bad(format!("ufuklar {FALL_HORIZONS:?} değil")));
    }
    let raw_prep = p.get("preprocessing");
    if !features.is_empty() {
        let Some(Value::Object(pr)) = raw_prep else {
            return Err(bad("ön işleme kolonları özelliklerle uyuşmuyor"));
        };
        let cols_ok = match pr.get("columns") {
            None => true,
            Some(Value::Array(a)) => a.iter().all(|c| c.as_str().is_some_and(|c| features.iter().any(|f| f == c))),
            Some(_) => false,
        };
        if !cols_ok {
            return Err(bad("ön işleme kolonları özelliklerle uyuşmuyor"));
        }
        let mut expect: Vec<&str> = FALL_WINSOR_LOG.iter().copied().filter(|f| features.iter().any(|x| x == f)).collect();
        expect.sort_unstable();
        let mut winsor: Vec<&str> = pr.get("winsor").and_then(Value::as_object).map(|m| m.keys().map(String::as_str).collect()).unwrap_or_default();
        winsor.sort_unstable();
        let mut log: Vec<String> = match pr.get("log_transform") {
            None => Vec::new(),
            Some(Value::Array(a)) => a.iter().map(|x| x.as_str().map(str::to_string).unwrap_or_else(|| x.to_string())).collect(),
            Some(_) => return Err(bad(format!("kırpma/log özellikleri {expect:?} değil"))),
        };
        log.sort_unstable();
        if winsor != expect || log.iter().map(String::as_str).ne(expect.iter().copied()) {
            return Err(bad(format!("kırpma/log özellikleri {expect:?} değil")));
        }
        if features.iter().any(|f| f == "f1r") && !p.get("deflator").is_some_and(Value::is_object) {
            return Err(bad("f1r var ama deflator bloğu yok"));
        }
    }
    let prep = if features.is_empty() { None } else { parse_prep(p)? };
    for (h, heads) in horizons_v {
        if !heads.is_object() || !heads.get("return").map_or(true, Value::is_null) {
            return Err(bad(format!("{h}: getiri başlığı olmamalı")));
        }
        let head = heads.get("p_up").unwrap_or(&Value::Null);
        match head.get("kind").and_then(Value::as_str) {
            // Python: isinstance(value, (int, float)) and not bool
            Some("constant") if matches!(head.get("value"), Some(Value::Number(_))) => {}
            Some("constant") => return Err(bad(format!("{h}.p_up: sabit değer yok"))),
            Some("logit") if !features.is_empty() => {}
            Some("logit") => return Err(bad(format!("{h}.p_up: kolonlar ön işlemeyle uyuşmuyor"))),
            other => return Err(bad(format!("{h}.p_up: bilinmeyen kind {other:?}"))),
        }
    }
    let mut horizons = Vec::with_capacity(FALL_HORIZONS.len());
    for h in FALL_HORIZONS {
        let head = &horizons_v[h]["p_up"];
        horizons.push((h.to_string(), parse_head(h, "p_up", head, prep.as_ref())?));
    }
    let policy = p.get("input_policy");
    let deflator = p.get("deflator").filter(|d| d.is_object()).and_then(|d| {
        let t = |k: &str| d.get(k).and_then(Value::as_str).map(str::to_string);
        Some(crate::tufe::DeflatorPin { through_month: t("through_month")?, prefix_sha256: t("file_sha256")? })
    });
    Ok(FallParams {
        model_id: model_id(p),
        features,
        horizons,
        prep,
        f3_filter_status_conflict: policy.and_then(|x| x.get("f3_filter_status_conflict")).and_then(Value::as_str).map(str::to_string),
        feature_ranges: parse_ranges(p)?,
        deflator,
        variant: text("variant").map(str::to_string),
    })
}

/// Açılış bütünlüğü (U33): tahmin yolunun yapacağı parametre denetimi.
pub fn check_params(p: &Value) -> Result<Kind, PredictError> {
    let kind = model_kind(p);
    match kind {
        Kind::Hazard | Kind::Km => parse_hazard(p).map(|_| kind),
        Kind::CeilingPath => parse_path(p).map(|_| kind),
        Kind::Pb => parse_pb(p).map(|_| kind),
        Kind::Market20 | Kind::Linear | Kind::Rule => parse_linear(p).map(|_| kind),
        Kind::Fall => parse_fall(p).map(|_| kind),
        // ebeveynsiz denetlenemez: `parse_post_d1(p, parent, path)` (EK 3 §6.1); INDEX.json'da POST_D1 modeli olamaz
        Kind::PostD1 => Err(bad(POST_D1_NOT_PRE_LISTING)),
    }
}

/// Python `run_model`: POST_D1 modeli listeleme öncesi kayıtta çalışmaz (ERROR, PARAMS_INVALID).
pub const POST_D1_NOT_PRE_LISTING: &str = "POST_D1 modeli listeleme öncesi kayıtta çalışmaz";

// ---------------------------------------------------------------- D1 sonrası (post_d1_hazard_v0)

/// `predict_post_d1.check_params`'ın okuduğu alanlar (JSON sırası korunur).
#[derive(Debug, Clone, PartialEq)]
pub struct PostD1Params {
    pub model_id: Option<String>,
    /// δ, `D1_COLUMNS` sırasıyla (iki anahtar; sonlu).
    pub delta: Vec<(String, f64)>,
    /// `d1_preprocessing.columns` (D1_COLUMNS'un sıralı alt kümesi).
    pub columns: Vec<String>,
    /// `d1_preprocessing.clip.d1_turnover`.
    pub clip: Winsor,
    /// Aktif kolonların ortalama ve std'si (`columns` sırasıyla).
    pub mean: Vec<(String, f64)>,
    pub std: Vec<(String, f64)>,
    /// `feature_ranges` (dosyadaki sırayla; D1 kolonları ve miras f1..).
    pub feature_ranges: Vec<Range>,
    /// `parent.sha256` (kopya).
    pub parent_sha256: Option<String>,
}

impl PostD1Params {
    fn get(v: &[(String, f64)], k: &str) -> Option<f64> {
        v.iter().find(|(c, _)| c == k).map(|(_, x)| *x)
    }
    pub fn delta_of(&self, c: &str) -> Option<f64> {
        Self::get(&self.delta, c)
    }
    pub fn mean_of(&self, c: &str) -> Option<f64> {
        Self::get(&self.mean, c)
    }
    pub fn std_of(&self, c: &str) -> Option<f64> {
        Self::get(&self.std, c)
    }
    pub fn range_of(&self, feature: &str) -> Option<&Range> {
        self.feature_ranges.iter().find(|r| r.feature == feature)
    }
}

/// Python eşitliği (`!=`) JSON değerleri için: eksik anahtar = None = null; sayılar (ve bool: True == 1) değerce;
/// liste ve sözlükler öğe öğe. Tamsayı ↔ tamsayı kesin, karışık durumda binary64 karşılaştırması.
pub fn py_json_eq(a: Option<&Value>, b: Option<&Value>) -> bool {
    let a = a.unwrap_or(&Value::Null);
    let b = b.unwrap_or(&Value::Null);
    let as_num = |v: &Value| -> Option<(Option<i128>, f64)> {
        match v {
            Value::Bool(x) => Some((Some(i128::from(*x)), f64::from(u8::from(*x)))),
            Value::Number(n) => {
                let int = n.as_i64().map(i128::from).or_else(|| n.as_u64().map(i128::from));
                Some((int, n.as_f64().unwrap_or(f64::NAN)))
            }
            _ => None,
        }
    };
    match (a, b) {
        (Value::Null, Value::Null) => true,
        (Value::String(x), Value::String(y)) => x == y,
        (Value::Array(x), Value::Array(y)) => x.len() == y.len() && x.iter().zip(y).all(|(p, q)| py_json_eq(Some(p), Some(q))),
        (Value::Object(x), Value::Object(y)) => {
            x.len() == y.len() && x.iter().all(|(k, v)| y.contains_key(k) && py_json_eq(Some(v), y.get(k)))
        }
        _ => match (as_num(a), as_num(b)) {
            (Some((Some(i), _)), Some((Some(j), _))) => i == j,
            (Some((_, x)), Some((_, y))) => x == y,
            _ => false,
        },
    }
}

fn finite(v: Option<&Value>) -> Option<f64> {
    v.and_then(num).filter(|x| x.is_finite())
}

/// `predict_post_d1.check_params(params, parent, path_params)` birebir sırada (EK 3 §6.1); ardından okuma. `parent` ve
/// `path` ham JSON'dur (kopya alanların JSON eşitliği). Ebeveynin kendi parametre denetimi (`parse_hazard`) Python'da
/// `linear_predictor` içinde, bu denetimden SONRA koşar; çağıran o sırayla çağırır.
pub fn parse_post_d1(p: &Value, parent: &Value, path: Option<&Value>) -> Result<PostD1Params, PredictError> {
    if !p.is_object() || !parent.is_object() {
        return Err(bad("params/parent bir sözlük değil"));
    }
    check_schema(p)?;
    let text = |v: &Value, k: &str| v.get(k).and_then(Value::as_str).map(str::to_string);
    if text(p, "algorithm").as_deref() != Some(POST_D1_ALGORITHM) || text(p, "stage").as_deref() != Some(POST_D1_STAGE) {
        return Err(bad(format!(
            "D1 sonrası model değil: {} / {}",
            p.get("algorithm").unwrap_or(&Value::Null),
            p.get("stage").unwrap_or(&Value::Null)
        )));
    }
    let empty = Value::Object(Map::new());
    // `params.get("parent") or {}`: boş/null/false → {}
    let copy = match p.get("parent") {
        Some(v @ Value::Object(m)) if !m.is_empty() => v,
        _ => &empty,
    };
    if text(copy, "model_id").as_deref() != Some(POST_D1_PARENT_ID)
        || text(parent, "model_id").as_deref() != Some(POST_D1_PARENT_ID)
        || text(parent, "algorithm").as_deref() != Some(HAZARD_ALGORITHM)
    {
        return Err(bad("parent ceiling_hazard_v0 değil"));
    }
    let parent_prep_id = parent.get("preprocessing").filter(|v| v.is_object()).and_then(|v| v.get("preprocessing_id"));
    if !py_json_eq(copy.get("gamma"), parent.get("gamma"))
        || !py_json_eq(copy.get("beta"), parent.get("beta"))
        || !py_json_eq(copy.get("preprocessing_id"), parent_prep_id)
    {
        return Err(bad("parent kopya alanları (gamma, beta, preprocessing_id) verilen parent'la aynı değil"));
    }
    let ranges = p.get("feature_ranges").filter(|v| v.is_object());
    if let Some(Value::Object(pr)) = parent.get("feature_ranges") {
        for (f, r) in pr {
            if !py_json_eq(ranges.and_then(|x| x.get(f)), Some(r)) {
                return Err(bad("miras feature_ranges parent'ınkiyle aynı değil"));
            }
        }
    }
    let days_ok = match p.get("updated_days") {
        Some(Value::Array(a)) => {
            a.len() == POST_D1_UPDATED_DAYS.len()
                && a.iter().zip(POST_D1_UPDATED_DAYS).all(|(x, d)| py_json_eq(Some(x), Some(&Value::from(d))))
        }
        _ => false,
    };
    if !days_ok {
        return Err(bad("güncellenen günler 2..10 değil"));
    }
    let delta_v = p.get("delta").and_then(Value::as_object).cloned().unwrap_or_default();
    let prep = p.get("d1_preprocessing").filter(|v| v.is_object()).unwrap_or(&empty);
    let columns: Vec<String> = match prep.get("columns") {
        None => Vec::new(),
        Some(Value::Array(a)) => a
            .iter()
            .map(|x| x.as_str().map(str::to_string))
            .collect::<Option<Vec<_>>>()
            .ok_or_else(|| bad("d1_preprocessing.columns D1 özelliklerinin sıralı alt kümesi değil"))?,
        Some(_) => return Err(bad("d1_preprocessing.columns D1 özelliklerinin sıralı alt kümesi değil")),
    };
    let keys: std::collections::BTreeSet<&str> = delta_v.keys().map(String::as_str).collect();
    let want: std::collections::BTreeSet<&str> = D1_COLUMNS.iter().copied().collect();
    if keys != want || !delta_v.values().all(|v| finite(Some(v)).is_some()) {
        return Err(bad("delta iki D1 katsayısı değil"));
    }
    let ordered: Vec<&str> = D1_COLUMNS.iter().copied().filter(|c| columns.iter().any(|x| x == c)).collect();
    if !columns.iter().all(|c| want.contains(c.as_str())) || columns.iter().map(String::as_str).ne(ordered.iter().copied()) {
        return Err(bad("d1_preprocessing.columns D1 özelliklerinin sıralı alt kümesi değil"));
    }
    let delta: Vec<(String, f64)> =
        D1_COLUMNS.iter().map(|c| (c.to_string(), finite(delta_v.get(*c)).expect("sonlu"))).collect();
    if delta.iter().any(|(c, d)| !columns.contains(c) && *d != 0.0) {
        return Err(bad("düşen özelliğin katsayısı 0 değil"));
    }
    let clip_v = prep.get("clip").and_then(|c| c.get("d1_turnover"));
    let (p05, p95) = (finite(clip_v.and_then(|c| c.get("p05"))), finite(clip_v.and_then(|c| c.get("p95"))));
    let clip = match (p05, p95) {
        (Some(a), Some(b)) if a <= b => Winsor { p05: a, p95: b },
        _ => return Err(bad("d1_turnover kırpma sınırları yok")),
    };
    let mut mean = Vec::new();
    let mut std = Vec::new();
    for c in &columns {
        let m = finite(prep.get("mean").and_then(|x| x.get(c)));
        let s = finite(prep.get("std").and_then(|x| x.get(c))).filter(|s| *s > 0.0);
        let (Some(m), Some(s)) = (m, s) else {
            return Err(bad("aktif D1 kolonunun ortalama/std'si yok ya da std ≤ 0"));
        };
        mean.push((c.clone(), m));
        std.push((c.clone(), s));
    }
    if let Some(path) = path {
        let sec = p.get("path_secondary").filter(|v| v.is_object()).unwrap_or(&empty);
        if text(path, "algorithm").as_deref() != Some(path::ALGORITHM)
            || text(path, "model_id").as_deref() != Some(POST_D1_PATH_ID)
            || text(sec, "model_id").as_deref() != Some(POST_D1_PATH_ID)
            || !py_json_eq(path.get("survival_model_sha256"), copy.get("sha256"))
        {
            return Err(bad("path_conditional kaynağı ceiling_path_v0 değil ya da gömülü seri modeli parent değil"));
        }
    }
    Ok(PostD1Params {
        model_id: model_id(p),
        delta,
        columns,
        clip,
        mean,
        std,
        feature_ranges: parse_ranges(p)?,
        parent_sha256: text(copy, "sha256"),
    })
}
