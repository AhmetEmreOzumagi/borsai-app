//! Sade görünümün kırılma akşamı kartı (FAZ9_APP_UI K-UI-3 `break_view`): makine kaydı (`registry/post_break/<T>/`),
//! `scores/scores_break.json` kartı ve sha denetimli katsayılar (`models/break_floor_v0.json`). Model çalıştırılmaz,
//! tahmin üretilmez (EK 5 portu ayrı görev): olasılıklar yalnız makine kaydından okunur.
//!
//! - Katsayılar yalnız `sha256(models/break_floor_v0.json)` makine kaydındaki `params_sha256`'ya eşitken döner; değilse
//!   kart kapanır (`status = SHA_MISMATCH` ya da `NO_MODEL_FILE`) ve hiçbir değer dönmez.
//! - Bülten dosya adları (`streak.sessions[].thb/thm`) ve eğitim arz listeleri dönmez (hijyen).
//! - Hesap yok: katkı (katsayı × z) hesaplanmaz; karşılaştırıcı oranları donmuş karttan anahtarla okunur.
use serde::Serialize;
use serde_json::Value;
use std::path::Path;

use super::inputs_doc::valid_ticker;
use super::models::sha256_hex;
use super::sade::{machine_files, read_machine, scores_break_in, BREAK_MODEL, BREAK_ZERO};
use super::{AppError, INVALID_ARGUMENT};
use crate::state::AppState;

pub const BREAK_MODEL_FILE: &str = "break_floor_v0.json";

fn st(v: &Value, ptr: &str) -> Option<String> {
    v.pointer(ptr).and_then(Value::as_str).map(str::to_string)
}

fn num(v: &Value, ptr: &str) -> Option<f64> {
    v.pointer(ptr).and_then(Value::as_f64)
}

fn uint(v: &Value, ptr: &str) -> Option<u64> {
    v.pointer(ptr).and_then(Value::as_u64)
}

fn cell<'a>(rec: &'a Value, model_id: &str) -> Option<&'a Value> {
    rec.get("models")?.as_array()?.iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(model_id))
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BreakFeature {
    /// `b_floor` | `b_turnover`
    pub name: String,
    /// b_floor: kapanış ve alt limit metni (D_b, aynen); b_turnover: oran metni ve ln değeri (kayıttan).
    pub close_raw: Option<String>,
    pub lower_limit_raw: Option<String>,
    pub ratio_raw: Option<String>,
    pub ln_value: Option<f64>,
    /// b_floor: 0/1; b_turnover: modelin kullandığı (kırpılmışsa sınırdaki) değer, F1 başlığı (uyarıdaki `used.F1`).
    pub value_f1: Option<f64>,
    pub clipped_f1: Option<bool>,
    pub z_f1: Option<f64>,
    pub z_f2: Option<f64>,
    pub coef_f1: Option<f64>,
    pub coef_f2: Option<f64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BreakHead {
    pub head: &'static str,
    pub c: Option<Value>,
    pub intercept: Option<f64>,
    pub training_n: Option<u64>,
    pub training_events: Option<u64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BreakCard {
    /// `backtest_info` aynen (F1_product, F1_zero: diff, ci95, n, n_months; k1; label; scale; subset).
    pub backtest_info: Option<Value>,
    pub promotion_label: Option<String>,
    pub promoted: Option<bool>,
    pub promotion_stage: Option<u64>,
    pub regime_tag: Option<String>,
    pub regime_start_d1: Option<String>,
    pub regime_text: Option<String>,
    pub frozen_at: Option<String>,
    pub model_commit: Option<String>,
    pub model_push_proof_created_at: Option<String>,
    pub n_variants_same_data: Option<u64>,
    pub training_n_f1: Option<u64>,
    pub training_n_f2: Option<u64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct BreakView {
    pub ticker: String,
    /// OK | NO_RECORD | NO_MODEL_FILE | SHA_MISMATCH (son ikisinde kart kapalı: aşağıdaki alanlar boş)
    pub status: &'static str,
    pub record_file: Option<String>,
    pub record_params_sha256: Option<String>,
    pub model_file_sha256: Option<String>,
    pub produced_at_utc: Option<String>,
    pub b: Option<u64>,
    pub l: Option<u64>,
    pub break_date: Option<String>,
    pub b_floor: Option<u64>,
    pub model_status: Option<String>,
    pub p_f1: Option<f64>,
    pub p_f2: Option<f64>,
    /// Donmuş `@ZERO` (kayıttaki çıktı; = eğitim oranı).
    pub zero_f1: Option<f64>,
    pub zero_f2: Option<f64>,
    /// Donmuş kart `comparators_frozen.by_type_F1[b_floor]` (bu arzın kırılma türündeki eğitim oranı).
    pub by_type_f1: Option<f64>,
    /// `PRODUCT_BREAK_FLOOR` (kayıt): durum ve F1.
    pub product_status: Option<String>,
    pub product_f1: Option<f64>,
    pub features: Vec<BreakFeature>,
    pub heads: Vec<BreakHead>,
    /// `structural_zero_D10`: arz fiyatı, D10'un en düşük mümkün kapanışı, imkânsızlık.
    pub structural_p: Option<String>,
    pub structural_min10: Option<String>,
    pub impossible_d10: Option<bool>,
    pub warnings: Vec<String>,
    pub exposure_class: Option<String>,
    pub t_open: Option<String>,
    /// `scores_break.json` payda satırı (sınıf) ve canlı sayılar.
    pub class: Option<String>,
    pub live_n_scored: Option<u64>,
    pub live_n_retro: Option<u64>,
    pub card: Option<BreakCard>,
}

fn closed(ticker: &str, status: &'static str) -> BreakView {
    BreakView {
        ticker: ticker.into(),
        status,
        record_file: None,
        record_params_sha256: None,
        model_file_sha256: None,
        produced_at_utc: None,
        b: None,
        l: None,
        break_date: None,
        b_floor: None,
        model_status: None,
        p_f1: None,
        p_f2: None,
        zero_f1: None,
        zero_f2: None,
        by_type_f1: None,
        product_status: None,
        product_f1: None,
        features: Vec::new(),
        heads: Vec::new(),
        structural_p: None,
        structural_min10: None,
        impossible_d10: None,
        warnings: Vec::new(),
        exposure_class: None,
        t_open: None,
        class: None,
        live_n_scored: None,
        live_n_retro: None,
        card: None,
    }
}

fn card_of(m: &Value) -> Option<BreakCard> {
    let c = m.get("card")?;
    Some(BreakCard {
        backtest_info: c.get("backtest_info").cloned(),
        promotion_label: st(c, "/promotion/label"),
        promoted: c.pointer("/promotion/promoted").and_then(Value::as_bool),
        promotion_stage: uint(c, "/promotion/stage"),
        regime_tag: st(c, "/regime_warning/tag"),
        regime_start_d1: st(c, "/regime_warning/start_d1"),
        regime_text: st(c, "/regime_warning/text"),
        frozen_at: st(c, "/frozen_at"),
        model_commit: st(c, "/model_commit"),
        model_push_proof_created_at: st(c, "/model_push_proof_created_at"),
        n_variants_same_data: uint(c, "/n_variants_same_data"),
        training_n_f1: uint(c, "/training_n_F1"),
        training_n_f2: uint(c, "/training_n_F2"),
    })
}

/// Kırılma kartı. `scores_break`: `scores/scores_break.json` (yoksa kart alanları ve sınıf boş kalır).
pub fn break_view_in(repo: &Path, ticker: &str, scores_break: Option<&Value>) -> Result<BreakView, AppError> {
    if !valid_ticker(ticker) {
        return Err(AppError::new(INVALID_ARGUMENT, format!("arz kodu {ticker:?}")));
    }
    let Some(file) = machine_files(repo, ticker).into_iter().next() else { return Ok(closed(ticker, "NO_RECORD")) };
    let rec = read_machine(repo, ticker, &file)?;
    let mcell = cell(&rec, BREAK_MODEL);
    let rec_sha = mcell.and_then(|c| st(c, "/params_sha256"));
    let model_bytes = std::fs::read(repo.join("models").join(BREAK_MODEL_FILE)).ok();
    let model_sha = model_bytes.as_deref().map(sha256_hex);
    let mut view = closed(ticker, "OK");
    view.record_file = Some(file);
    view.record_params_sha256 = rec_sha.clone();
    view.model_file_sha256 = model_sha.clone();
    let Some(bytes) = model_bytes else {
        view.status = "NO_MODEL_FILE";
        return Ok(view);
    };
    if rec_sha.is_none() || rec_sha != model_sha {
        view.status = "SHA_MISMATCH";
        return Ok(view);
    }
    let params: Value = serde_json::from_slice(&bytes).map_err(|e| super::io_error(BREAK_MODEL_FILE, e))?;
    let b_floor = uint(&rec, "/break_day/b_floor");
    let smodel = scores_break.and_then(|d| {
        d.get("models")?.as_array()?.iter().find(|m| m.get("model_id").and_then(Value::as_str) == Some(BREAK_MODEL))
    });
    let card = smodel.and_then(card_of);
    let denom = smodel
        .and_then(|m| m.pointer("/live_break/denominator"))
        .and_then(Value::as_array)
        .and_then(|rows| rows.iter().find(|r| r.get("ticker").and_then(Value::as_str) == Some(ticker)));
    // Model kullandığı değer: kırpma uyarısının `used` alanı (yalnız kırpıldıysa); değilse kayıttaki ln değeri.
    let warn = mcell
        .and_then(|c| c.pointer("/output/warnings"))
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let used_f1 = warn
        .iter()
        .find(|w| w.get("feature").and_then(Value::as_str) == Some("b_turnover"))
        .and_then(|w| num(w, "/used/F1"));
    let coef = |head: &str, i: usize| num(&params, &format!("/horizons/{head}/p_floor/coef/{i}"));
    let columns: Vec<String> = params
        .pointer("/horizons/F1/p_floor/columns")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|c| c.as_str().map(str::to_string))
        .collect();
    view.features = columns
        .iter()
        .enumerate()
        .map(|(i, name)| {
            let is_floor = name == "b_floor";
            BreakFeature {
                name: name.clone(),
                close_raw: is_floor.then(|| st(&rec, "/break_day/fields_raw/close")).flatten(),
                lower_limit_raw: is_floor.then(|| st(&rec, "/break_day/fields_raw/lower_limit")).flatten(),
                ratio_raw: (!is_floor).then(|| st(&rec, "/features/b_turnover_ratio")).flatten(),
                ln_value: (!is_floor).then(|| num(&rec, "/features/b_turnover_ln")).flatten(),
                value_f1: if is_floor { b_floor.map(|b| b as f64) } else { used_f1.or_else(|| num(&rec, "/features/b_turnover_ln")) },
                clipped_f1: (!is_floor).then(|| rec.pointer("/features/clipped/F1").and_then(Value::as_bool)).flatten(),
                z_f1: num(&rec, &format!("/features/z/F1/{name}")),
                z_f2: num(&rec, &format!("/features/z/F2/{name}")),
                coef_f1: coef("F1", i),
                coef_f2: coef("F2", i),
            }
        })
        .collect();
    view.heads = [("F1", "n_F1", "events_F1"), ("F2", "n_F2", "events_F2")]
        .iter()
        .map(|&(head, n, ev)| BreakHead {
            head,
            c: params.pointer(&format!("/horizons/{head}/p_floor/C")).cloned(),
            intercept: num(&params, &format!("/horizons/{head}/p_floor/intercept")),
            training_n: uint(&params, &format!("/training/{n}")),
            training_events: uint(&params, &format!("/training/{ev}")),
        })
        .collect();
    let zcell = cell(&rec, BREAK_ZERO);
    view.produced_at_utc = st(&rec, "/produced_at_utc");
    view.b = uint(&rec, "/streak/b");
    view.l = uint(&rec, "/streak/L");
    view.break_date = st(&rec, "/streak/break_date");
    view.b_floor = b_floor;
    view.model_status = mcell.and_then(|c| st(c, "/status"));
    view.p_f1 = mcell.and_then(|c| num(c, "/output/F1/p_floor"));
    view.p_f2 = mcell.and_then(|c| num(c, "/output/F2/p_floor"));
    view.zero_f1 = zcell.and_then(|c| num(c, "/output/F1/p_floor"));
    view.zero_f2 = zcell.and_then(|c| num(c, "/output/F2/p_floor"));
    view.by_type_f1 = b_floor.and_then(|b| {
        smodel.and_then(|m| m.pointer(&format!("/card/comparators_frozen/by_type_F1/{b}"))).and_then(Value::as_f64)
    });
    view.product_status = st(&rec, "/comparators/PRODUCT_BREAK_FLOOR/status");
    view.product_f1 = num(&rec, "/comparators/PRODUCT_BREAK_FLOOR/F1");
    view.structural_p = st(&rec, "/structural_zero_D10/P");
    view.structural_min10 = st(&rec, "/structural_zero_D10/min10");
    view.impossible_d10 = rec.pointer("/structural_zero_D10/impossible").and_then(Value::as_bool);
    view.warnings = warn.iter().filter_map(|w| st(w, "/code")).collect();
    view.exposure_class = st(&rec, "/exposure_class");
    view.t_open = st(&rec, "/t_open");
    view.class = denom.and_then(|r| st(r, "/class").or_else(|| st(r, "/stage_status")));
    view.live_n_scored = smodel.and_then(|m| uint(m, "/live_break/n_scored"));
    view.live_n_retro = smodel.and_then(|m| uint(m, "/live_break/n_retro"));
    view.card = card;
    Ok(view)
}

/// Kırılma kartı: repo ya da kişisel modda gömülü anlık görüntü (FAZ9_SNAPSHOT K-SNAP-2; katsayılar anlık görüntüdeki
/// `models/break_floor_v0.json`'dan, sha denetimi aynen).
pub fn break_view_value(state: &AppState, ticker: &str) -> Result<BreakView, AppError> {
    let root = state.read_root()?;
    let sb = scores_break_in(&root.root);
    break_view_in(&root.root, ticker, sb.as_ref())
}

#[tauri::command]
pub fn break_view(state: tauri::State<'_, AppState>, ticker: String) -> Result<BreakView, AppError> {
    break_view_value(&state, &ticker)
}
