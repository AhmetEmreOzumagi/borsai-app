//! Tavan yolu (Faz 4) gösterim türevleri ve koşullu getiri (SPEC_APP EK 2 §4.1–§4.3).
//!
//! - `path_display`: Grup A/C fiyat satırı. Medyan getiri limit atomuysa kayıttaki `C_h` METNİ
//!   gösterilir; değilse `≈ P × (1 + medyan)` burada hesaplanır (görüntüleme türevi, kayda yazılmaz).
//!   Ön uç hiçbir çarpma yapmaz (U25 taraması).
//! - `path_conditional`: SPEC_CEILING_PATH_V0 §7 durum 1/2. Gözlenen kapanışları KENDİSİ okur
//!   (`<repo>/data/outcomes/<T>.csv` `close_raw`, salt okuma); hangi h'nin dosyadan, hangisinin
//!   limit yolu varsayımı olduğunu döner. Resmi görünümde yalnız dondurulmuş kayıttaki `output` ve
//!   gömülü `post_break.cells` kullanılır: tahmin yolu (`predict_all`) çağrılmaz ve kayıttaki
//!   `params_sha256` gömülü sha ile eşit değilse hesap yapılmaz (U38, U49).
//! - Kullanıcı beyanı bu modülde YOKTUR: imzalarda parametresi yoktur, hiçbir hesaba girmez
//!   (SPEC_APP §3g, U52; proje sahibi kararı 2026-09-23).
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;

use borsai_predict::dec;
use borsai_predict::features::parse_decimal;
use borsai_predict::params::parse_path;
use borsai_predict::path;
use borsai_predict::survival::DAYS;

use super::ceiling::read_closes_in;
use super::freeze::read_record;
use super::inputs_doc::valid_ticker;
use super::registry::RECORD_PREDICTION;
use super::{AppError, INVALID_ARGUMENT};
use crate::state::AppState;

pub const PATH_MODEL_UNKNOWN: &str = "PATH_MODEL_UNKNOWN";
pub const PATH_MODEL_NOT_IN_RECORD: &str = "PATH_MODEL_NOT_IN_RECORD";
pub const PATH_PARAMS_SHA_MISMATCH: &str = "PATH_PARAMS_SHA_MISMATCH";
pub const PATH_CLOSE_MISSING: &str = "PATH_CLOSE_MISSING";
pub const PATH_CONDITIONAL_FAILED: &str = "PATH_CONDITIONAL_FAILED";

/// Kaynak türü: dondurulmuş kayıt (resmi görünüm) ya da elde olan çıktı (canlı sonuç / senaryo).
pub const SOURCE_RECORD: &str = "RECORD";
pub const SOURCE_OUTPUT: &str = "OUTPUT";

pub const STATE_STREAK_ONGOING: &str = path::STATE_STREAK_ONGOING;
pub const STATE_AFTER_BREAK: &str = path::STATE_AFTER_BREAK;

/// Kapanış kaynağı: dosyadaki resmi kapanış ya da limit yolu varsayımı (yalnız varsayımsal j).
pub const ORIGIN_FILE: &str = "FILE";
pub const ORIGIN_LIMIT_PATH: &str = "LIMIT_PATH";

// ---------------------------------------------------------------- §4.1 fiyat satırı

#[derive(Debug, Clone, Deserialize)]
pub struct PathOutputArg {
    pub model_id: String,
    /// `predict_all` / kayıt / senaryo çıktısı, OLDUĞU GİBİ.
    pub output: Value,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PathPriceCell {
    pub h: usize,
    /// `return == limit_path_return` (bit-eşit): fiyat kesin `C_h` metnidir.
    pub on_limit_path: bool,
    /// Yalnız limit atomunda: kayıttaki `limit_path.C[h−1]` metni (aynen).
    pub c_text: Option<String>,
    /// Limit atomunda DEĞİLKEN: `P × (1 + medyan)` (görüntüleme türevi; kayıtta yoktur).
    pub approx_price: Option<f64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PathDisplayRow {
    pub model_id: String,
    /// `limit_path` metin alanları (aynen); ret eden modelde null.
    pub ipo_price: Option<String>,
    pub snapped_ipo_price: Option<String>,
    pub tick: Option<String>,
    pub c: Vec<String>,
    pub cells: Vec<PathPriceCell>,
}

fn f64_of(v: Option<&Value>) -> Option<f64> {
    match v? {
        Value::Number(n) => n.as_f64(),
        Value::String(s) => match s.as_str() {
            "NaN" => Some(f64::NAN),
            "Infinity" => Some(f64::INFINITY),
            "-Infinity" => Some(f64::NEG_INFINITY),
            _ => None,
        },
        _ => None,
    }
}

fn text_of(v: Option<&Value>) -> Option<String> {
    v.and_then(Value::as_str).map(str::to_string)
}

fn price_f64(text: &str) -> Option<f64> {
    parse_decimal(Some(&Value::String(text.to_string())), "ipo_price", false)
        .ok()
        .flatten()
        .map(|d| d.to_f64())
}

pub fn path_display_row(model_id: &str, output: &Value) -> PathDisplayRow {
    let lp = output.get("limit_path").filter(|v| !v.is_null());
    let c: Vec<String> = lp
        .and_then(|l| l.get("C"))
        .and_then(Value::as_array)
        .map(|a| a.iter().filter_map(|x| x.as_str().map(str::to_string)).collect())
        .unwrap_or_default();
    let ipo_price = lp.and_then(|l| text_of(l.get("ipo_price")));
    let p = ipo_price.as_deref().and_then(price_f64);
    let mut cells = Vec::with_capacity(DAYS);
    for h in 1..=DAYS {
        let cell = output.get(format!("D{h}")).filter(|v| !v.is_null());
        let ret = cell.and_then(|d| f64_of(d.get("return")));
        let lpr = cell.and_then(|d| f64_of(d.get("limit_path_return")));
        // "bit-eşit": NaN dahil ham gösterim karşılaştırması.
        let on_limit_path = match (ret, lpr) {
            (Some(a), Some(b)) => a.to_bits() == b.to_bits(),
            _ => false,
        };
        let c_text = if on_limit_path { c.get(h - 1).cloned() } else { None };
        let approx_price = match (on_limit_path, p, ret) {
            (false, Some(p), Some(r)) => Some(p * (1.0 + r)),
            _ => None,
        };
        cells.push(PathPriceCell { h, on_limit_path, c_text, approx_price });
    }
    PathDisplayRow {
        model_id: model_id.to_string(),
        snapped_ipo_price: lp.and_then(|l| text_of(l.get("snapped_ipo_price"))),
        tick: lp.and_then(|l| text_of(l.get("tick"))),
        ipo_price,
        c,
        cells,
    }
}

pub fn path_display_value(models: &[PathOutputArg]) -> Vec<PathDisplayRow> {
    models.iter().map(|m| path_display_row(&m.model_id, &m.output)).collect()
}

#[tauri::command]
pub fn path_display(models: Vec<PathOutputArg>) -> Result<Vec<PathDisplayRow>, AppError> {
    Ok(path_display_value(&models))
}

// ---------------------------------------------------------------- §4.3 koşullu getiri

#[derive(Debug, Clone, Deserialize)]
pub struct PathSource {
    /// RECORD (dondurulmuş kayıt) | OUTPUT (canlı sonuç ya da senaryo çıktısı)
    pub kind: String,
    /// Gözlenen kapanışların okunacağı arz kodu; yoksa yalnız j = 0 hesaplanabilir.
    pub ticker: Option<String>,
    /// RECORD: `registry/records/<ticker>/<file>`
    pub file: Option<String>,
    /// OUTPUT: çıktı olduğu gibi.
    pub output: Option<Value>,
    /// OUTPUT: çıktının yazıldığı parametre sha'sı; ZORUNLU (yoksa `INVALID_ARGUMENT`, gömülü sha
    /// varsayılmaz) ve gömülüyle eşit değilse hesap yok.
    pub params_sha256: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct CloseRow {
    pub h: usize,
    /// FILE (resmi kapanış) | LIMIT_PATH (varsayım; yalnız varsayımsal j)
    pub origin: &'static str,
    pub close: String,
    pub session_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Mismatch {
    pub t: usize,
    pub close: String,
    pub c: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PathConditional {
    pub model_id: String,
    /// STREAK_ONGOING (durum 1) | AFTER_BREAK (durum 2)
    pub state: &'static str,
    pub j_or_t: usize,
    /// RECORD | OUTPUT
    pub source_kind: String,
    pub source_file: Option<String>,
    pub params_sha256: String,
    pub closes: Vec<CloseRow>,
    /// En az bir kapanış limit yolu varsayımı (varsayımsal j).
    pub assumed: bool,
    /// `limit_path_mismatch` (kayda ve dosyaya YAZILMAZ; yalnız ekran uyarısı).
    pub limit_path_mismatch: i64,
    pub mismatch: Option<Mismatch>,
    /// `predict_path.conditional` / `conditional_after_break` çıktısı, olduğu gibi.
    pub result: Value,
}

fn embedded_model<'a>(state: &'a AppState, model_id: &str) -> Result<(&'a Value, &'a str), AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    let m = models
        .models
        .iter()
        .zip(&models.kinds)
        .find(|(m, k)| m.model_id == model_id && **k == borsai_predict::Kind::CeilingPath)
        .map(|(m, _)| m)
        .ok_or_else(|| AppError::new(PATH_MODEL_UNKNOWN, format!("tavan yolu modeli değil ya da gömülü değil: {model_id}")))?;
    Ok((&m.params, &m.params_sha256))
}

/// Kayıttaki çıktı ve sha (resmi görünüm; model YENİDEN ÇALIŞTIRILMAZ).
fn record_output(repo: &Path, ticker: &str, file: &str, model_id: &str) -> Result<(Value, String), AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let rel = format!("registry/records/{ticker}/{file}");
    let doc = read_record(repo, &rel)?;
    if doc["record_type"].as_str() != Some(RECORD_PREDICTION) {
        return Err(AppError::new(super::registry::RECORD_NOT_ACTIVE, format!("{file}: tahmin kaydı değil")));
    }
    let cell = doc["models"]
        .as_array()
        .into_iter()
        .flatten()
        .find(|c| c["model_id"].as_str() == Some(model_id))
        .ok_or_else(|| {
            AppError::new(PATH_MODEL_NOT_IN_RECORD, format!("{file}: kayıtta {model_id} yok (kayıt INDEX'ten eski)"))
        })?;
    let sha = cell["params_sha256"].as_str().unwrap_or_default().to_string();
    Ok((cell["output"].clone(), sha))
}

/// `data/outcomes/<T>.csv`'deki resmi kapanışlar (h = 1..10; `status = OK` ve `close_raw` dolu).
fn official_closes(state: &AppState, ticker: Option<&str>) -> Result<Vec<Option<(String, Option<String>)>>, AppError> {
    let dir = state.repo().map(|r| r.root.join("data").join("outcomes"));
    match (dir, ticker) {
        (Some(d), Some(t)) => read_closes_in(&d, t),
        _ => Ok((0..DAYS).map(|_| None).collect()),
    }
}

fn limit_c(output: &Value) -> Vec<String> {
    output
        .pointer("/limit_path/C")
        .and_then(Value::as_array)
        .map(|a| a.iter().filter_map(|x| x.as_str().map(str::to_string)).collect())
        .unwrap_or_default()
}

fn first_mismatch(closes: &[CloseRow], c: &[String]) -> Option<Mismatch> {
    for row in closes {
        let (Some(a), Some(b)) = (dec_of(&row.close), c.get(row.h - 1).and_then(|x| dec_of(x))) else { continue };
        if !dec::eq(&a, &b) {
            return Some(Mismatch { t: row.h, close: row.close.clone(), c: c[row.h - 1].clone() });
        }
    }
    None
}

fn dec_of(text: &str) -> Option<dec::Dec> {
    match dec::parse(text) {
        Some(dec::Parsed::Finite(d)) => Some(d),
        _ => None,
    }
}

pub fn path_conditional_value(
    state: &AppState,
    model_id: &str,
    source: &PathSource,
    j_or_t: usize,
    state_name: &str,
) -> Result<PathConditional, AppError> {
    let (params, embedded_sha) = embedded_model(state, model_id)?;
    let (output, sha, source_file) = match source.kind.as_str() {
        SOURCE_RECORD => {
            let repo = state.require_repo()?;
            let (t, f) = (source.ticker.as_deref(), source.file.as_deref());
            let (t, f) = match (t, f) {
                (Some(t), Some(f)) => (t, f),
                _ => return Err(AppError::new(INVALID_ARGUMENT, "kayıt kaynağı arz kodu ve dosya ister")),
            };
            let (o, sha) = record_output(&repo.root, t, f, model_id)?;
            (o, sha, Some(f.to_string()))
        }
        // Çıktıyı üreten parametrenin sha'sı zorunlu: verilmezse gömülü sha VARSAYILMAZ (B8).
        SOURCE_OUTPUT => match &source.params_sha256 {
            Some(sha) => (source.output.clone().unwrap_or(Value::Null), sha.clone(), None),
            None => return Err(AppError::new(INVALID_ARGUMENT, "çıktı kaynağı params_sha256 ister")),
        },
        other => return Err(AppError::new(INVALID_ARGUMENT, format!("kaynak türü {other:?}"))),
    };
    if sha != embedded_sha {
        return Err(AppError::new(
            PATH_PARAMS_SHA_MISMATCH,
            format!("{model_id}: kayıt farklı parametreyle yazılmış; koşullu getiri hesaplanmaz"),
        )
        .with_detail(format!("kayıt sha {sha} ≠ gömülü sha {embedded_sha}")));
    }
    let p = parse_path(params).map_err(|e| AppError::new(&e.code, e.message))?;
    let c = limit_c(&output);
    let file_closes = official_closes(state, source.ticker.as_deref())?;
    let state_name = match state_name {
        STATE_STREAK_ONGOING => STATE_STREAK_ONGOING,
        STATE_AFTER_BREAK => STATE_AFTER_BREAK,
        other => return Err(AppError::new(INVALID_ARGUMENT, format!("durum {other:?}"))),
    };
    // Durum 1: h = 1..j; durum 2: h = 1..t+1 (kırılma günü kapanışı dağılımın ölçeğidir).
    let need = if state_name == STATE_STREAK_ONGOING { j_or_t } else { j_or_t + 1 };
    let mut closes: Vec<CloseRow> = Vec::with_capacity(need);
    for h in 1..=need {
        match file_closes.get(h - 1).and_then(Option::as_ref) {
            Some((close, date)) => {
                closes.push(CloseRow { h, origin: ORIGIN_FILE, close: close.clone(), session_date: date.clone() })
            }
            // Durum 2'de varsayım YOKTUR: gözlenen kapanış dağılımın ölçeğidir, uydurulmaz.
            None if state_name == STATE_AFTER_BREAK => {
                return Err(AppError::new(
                    PATH_CLOSE_MISSING,
                    format!("D{h} kapanışı dosyada yok; kırılma sonrası dağılım için resmi kapanış gerekir"),
                ))
            }
            // Durum 1'de eksik kapanış yalnız varsayımsal j > resmi j'de olur: limit yolu varsayımı.
            None => match c.get(h - 1) {
                Some(x) => closes.push(CloseRow { h, origin: ORIGIN_LIMIT_PATH, close: x.clone(), session_date: None }),
                None => {
                    return Err(AppError::new(
                        PATH_CLOSE_MISSING,
                        format!("D{h} kapanışı yok ve limit yolu varsayımı kurulamadı"),
                    ))
                }
            },
        }
    }
    let texts: Vec<String> = closes.iter().map(|r| r.close.clone()).collect();
    let result = match state_name {
        STATE_STREAK_ONGOING => path::conditional(&p, &output, j_or_t, &texts),
        _ => path::conditional_after_break(&p, &output, j_or_t, &texts),
    }
    .map_err(|e| AppError::new(PATH_CONDITIONAL_FAILED, e.message).with_detail(e.code))?;
    let mismatch = first_mismatch(&closes, &c);
    Ok(PathConditional {
        model_id: model_id.to_string(),
        state: state_name,
        j_or_t,
        source_kind: source.kind.clone(),
        source_file,
        params_sha256: embedded_sha.to_string(),
        assumed: closes.iter().any(|r| r.origin == ORIGIN_LIMIT_PATH),
        limit_path_mismatch: result.get("limit_path_mismatch").and_then(Value::as_i64).unwrap_or(0),
        mismatch,
        closes,
        result,
    })
}

#[tauri::command]
pub fn path_conditional(
    state: tauri::State<'_, AppState>,
    model_id: String,
    source: PathSource,
    j_or_t: usize,
    state_name: String,
) -> Result<PathConditional, AppError> {
    path_conditional_value(&state, &model_id, &source, j_or_t, &state_name)
}

/// D1 sonrası kaydın ikincil çıktısı (EK 3 §6.5 "Getiri (koşullu)" ek kartı "D1 sonrası S ile tavan yolu"): kayıttaki
/// `models[post_d1_hazard_v0].output.path_conditional` (Python `predict_path.conditional(ceiling_path_v0, …, j = 1,
/// [kapanış(D_1)])`) OLDUĞU GİBİ sarılır; HESAP YOK. Kapanış kaydın `d1.fields_raw.close` metnidir (resmi D_1).
pub const SOURCE_RECORD_POST_D1: &str = "RECORD_POST_D1";

pub fn post_d1_path_card(
    record_file: &str,
    params_sha256: &str,
    d1_close: &str,
    d1_date: Option<&str>,
    result: Value,
) -> PathConditional {
    PathConditional {
        model_id: super::post_d1::POST_D1_MODEL_ID.to_string(),
        state: STATE_STREAK_ONGOING,
        j_or_t: 1,
        source_kind: SOURCE_RECORD_POST_D1.to_string(),
        source_file: Some(record_file.to_string()),
        params_sha256: params_sha256.to_string(),
        closes: vec![CloseRow { h: 1, origin: ORIGIN_FILE, close: d1_close.to_string(), session_date: d1_date.map(str::to_string) }],
        assumed: false,
        limit_path_mismatch: result.get("limit_path_mismatch").and_then(Value::as_i64).unwrap_or(0),
        mismatch: None,
        result,
    }
}

/// Grup C'nin hücre notu ve kartın "seri modeli" satırı için gömülü parametre özeti (sayı yok).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PathParamsInfo {
    pub model_id: String,
    pub survival_model_id: Option<String>,
    pub survival_model_sha256: Option<String>,
    pub n_min: usize,
    /// `post_break`: hücreleri kuran arz sayısı, gözlem sayısı ve kesim tarihi.
    pub n_ipo: Option<u64>,
    pub n_obs: Option<u64>,
    pub cutoff_date: Option<String>,
}

fn params_info(model_id: &str, params: &Value) -> PathParamsInfo {
    PathParamsInfo {
        model_id: model_id.to_string(),
        survival_model_id: params.get("survival_model_id").and_then(Value::as_str).map(str::to_string),
        survival_model_sha256: params.get("survival_model_sha256").and_then(Value::as_str).map(str::to_string),
        n_min: path::N_MIN,
        n_ipo: params.pointer("/post_break/n_ipo").and_then(Value::as_u64),
        n_obs: params.pointer("/post_break/n_obs").and_then(Value::as_u64),
        cutoff_date: params.pointer("/post_break/cutoff_date").and_then(Value::as_str).map(str::to_string),
    }
}

/// Gömülü bütün `ceiling_path` modelleri (INDEX sırası): Grup C hücre notu, sütun başlığı ve kart.
pub fn path_params_value(state: &AppState) -> Result<Vec<PathParamsInfo>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    Ok(models
        .models
        .iter()
        .zip(&models.kinds)
        .filter(|(_, k)| **k == borsai_predict::Kind::CeilingPath)
        .map(|(m, _)| params_info(&m.model_id, &m.params))
        .collect())
}

#[tauri::command]
pub fn path_params(state: tauri::State<'_, AppState>) -> Result<Vec<PathParamsInfo>, AppError> {
    path_params_value(&state)
}

/// Yalnız test yardımcısı: JSON'dan kaynak kurmak (ön uç `PathSource`'u aynen gönderir).
pub fn source_output(ticker: Option<&str>, output: Value, sha: Option<&str>) -> PathSource {
    PathSource {
        kind: SOURCE_OUTPUT.into(),
        ticker: ticker.map(str::to_string),
        file: None,
        output: Some(output),
        params_sha256: sha.map(str::to_string),
    }
}

pub fn source_record(ticker: &str, file: &str) -> PathSource {
    PathSource {
        kind: SOURCE_RECORD.into(),
        ticker: Some(ticker.to_string()),
        file: Some(file.to_string()),
        output: None,
        params_sha256: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn out() -> Value {
        json!({
            "limit_path": {"ipo_price": "10", "snapped_ipo_price": "10.00", "tick": "0.01",
                           "C": ["11.00", "12.10"], "rho": [0.1, 0.21]},
            "D1": {"return": 0.1, "limit_path_return": 0.1},
            "D2": {"return": 0.05, "limit_path_return": 0.21},
            "D3": Value::Null,
        })
    }

    #[test]
    fn display_price_rule() {
        let r = path_display_row("m", &out());
        assert!(r.cells[0].on_limit_path && r.cells[0].c_text.as_deref() == Some("11.00"));
        assert_eq!(r.cells[0].approx_price, None, "limit atomunda yaklaşık fiyat yok");
        assert!(!r.cells[1].on_limit_path && r.cells[1].c_text.is_none());
        assert_eq!(r.cells[1].approx_price, Some(10.0 * 1.05));
        assert_eq!((r.cells[2].on_limit_path, r.cells[2].approx_price), (false, None), "hücre yok");
        assert_eq!(r.tick.as_deref(), Some("0.01"));
        assert_eq!(r.cells.len(), DAYS);
    }

    #[test]
    fn mismatch_first_deviating_day() {
        let rows = vec![
            CloseRow { h: 1, origin: ORIGIN_FILE, close: "11.00".into(), session_date: None },
            CloseRow { h: 2, origin: ORIGIN_FILE, close: "12.00".into(), session_date: None },
        ];
        let c = vec!["11.000".to_string(), "12.10".to_string()];
        let m = first_mismatch(&rows, &c).expect("sapma");
        assert_eq!((m.t, m.close.as_str(), m.c.as_str()), (2, "12.00", "12.10"), "D1 sayısal olarak eşit");
    }
}
