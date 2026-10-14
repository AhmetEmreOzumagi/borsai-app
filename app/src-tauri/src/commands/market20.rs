//! f6 (XU100 20 seans getirisi) repo modunda Python'dan (SPEC_APP §3a.2). Uygulama ağa çıkmaz,
//! XU100 indirmez, güncellemez; pinli dosyalar ve takvim `borsai.market20.load_live_sources`'tan.
use serde::Serialize;
use serde_json::Value;

use super::{AppError, INVALID_ARGUMENT};
use crate::clock::{is_iso_date, today_istanbul};
use crate::python::run_python;
use crate::state::AppState;

/// Şartnamedeki komut, birebir.
pub const PY_MARKET20: &str = "import json,sys; from borsai import market20 as m; cal,recs,sha=m.load_live_sources(); \
t=sys.argv[2] or None; r=m.market20(sys.argv[1],cal,recs,xu100_sha256=sha,live=bool(t),first_trading_date=t); \
print(json.dumps(r.as_record()))";

pub const MARKET20_OUTPUT_INVALID: &str = "MARKET20_OUTPUT_INVALID";

#[derive(Debug, Clone, Serialize)]
pub struct Market20View {
    /// `Market20Result.as_record()` aynen: ref_date, f6 (metin | null), refusal, S0_date, S20_date,
    /// close_S0, close_S20, calendar_sha256, xu100_sha256.
    pub record: Value,
    /// T verilmedi: `live=False`, kural 5 denetlenemedi.
    pub t_unknown: bool,
}

pub fn market20_value(state: &AppState, ref_date: Option<String>, t: Option<String>) -> Result<Market20View, AppError> {
    let repo = state.require_repo()?;
    let ref_date = ref_date.filter(|s| !s.is_empty()).unwrap_or_else(today_istanbul);
    let t = t.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    for d in std::iter::once(&ref_date).chain(t.iter()) {
        if !is_iso_date(d) {
            return Err(AppError::new(INVALID_ARGUMENT, format!("ISO tarih değil: {d:?}")));
        }
    }
    let out = run_python(&repo.python, &repo.root, &["-c", PY_MARKET20, &ref_date, t.as_deref().unwrap_or("")])?;
    let record: Value = serde_json::from_str(out.trim())
        .map_err(|e| AppError::new(MARKET20_OUTPUT_INVALID, format!("Python çıktısı JSON değil: {e}")).with_detail(out.clone()))?;
    let f6_ok = matches!(record.get("f6"), Some(Value::String(_)) | Some(Value::Null));
    let refusal_ok = matches!(record.get("refusal"), Some(Value::String(_)) | Some(Value::Null));
    if !f6_ok || !refusal_ok {
        return Err(AppError::new(MARKET20_OUTPUT_INVALID, "f6/refusal alanı beklenen biçimde değil").with_detail(out));
    }
    Ok(Market20View { record, t_unknown: t.is_none() })
}

#[tauri::command]
pub async fn market20_via_python(
    state: tauri::State<'_, AppState>,
    ref_date: Option<String>,
    t: Option<String>,
) -> Result<Market20View, AppError> {
    market20_value(&state, ref_date, t)
}
