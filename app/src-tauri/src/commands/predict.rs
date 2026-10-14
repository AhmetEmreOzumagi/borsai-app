//! `predict_all(inputs, f6, t)`: bütün gömülü modeller aynı girdiyle, INDEX sırasıyla (SPEC_APP §3b, U5).
//!
//! TÜFE girdisi (SPEC_APP EK 3 §3.3): Python'da `predict_hazard` saftır, girdiyi `freeze.tufe_for_record` hazırlar.
//! Uygulamada aynı ayrım: `predict_all` çağrılmadan önce `tufe_for_inputs` girdi sözlüğüne `tufe_index` ve
//! `tufe_refusal` anahtarlarını (kayıt biçimi) ANCAK gömülü kümede deflatörlü model varsa ekler. Kaynak (§3.1):
//! repo modunda `<repo>/data/raw/tuik/tufe_genel_2025_100.csv` her tahminde yeniden okunur (yeni ay yeniden derleme
//! istemez); bağımsız modda derlemeye gömülü kopya. Kullanıcı TÜFE değerini elle giremez (imputasyon yok): ay ilk
//! işlem gününden (T) türetilir.
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use borsai_predict::error::{TUFE_FILE_MISMATCH, TUFE_MISSING, TUFE_NOT_PIT};
use borsai_predict::tufe::{self, DeflatorPin, TufeTable};

use super::AppError;
use crate::embedded;
use crate::state::AppState;

/// f6: hazır değer (metin/sayı) ya da market20 neden kodu (SPEC_APP §3a.2).
#[derive(Debug, Clone, Default, Deserialize)]
pub struct F6Arg {
    pub value: Option<Value>,
    pub refusal: Option<String>,
}

// ---------------------------------------------------------------- TÜFE kaynağı (EK 3 §3.1–§3.5)

pub const TUFE_SOURCE_REPO: &str = "REPO";
pub const TUFE_SOURCE_EMBEDDED: &str = "EMBEDDED";
/// Ret nedenleri (TufeInfo.reason; ekrandaki açıklama `tr.ts`'tedir).
pub const TUFE_REASON_T_UNKNOWN: &str = "T_UNKNOWN";
pub const TUFE_REASON_TABLE_INVALID: &str = "TABLE_INVALID";
pub const TUFE_REASON_MONTH_MISSING: &str = "MONTH_MISSING";
pub const TUFE_REASON_NOT_PIT: &str = "NOT_PIT";
pub const TUFE_REASON_PIN_MISMATCH: &str = "PIN_MISMATCH";

/// Okunmuş tablo ve nereden geldiği.
#[derive(Debug, Clone)]
pub struct TufeSource {
    /// REPO | EMBEDDED
    pub source: &'static str,
    pub path: Option<PathBuf>,
    /// Ayrıştırılamadıysa neden (tablo geçersiz: deflatörlü modeller TUFE_FILE_MISMATCH).
    pub table: Result<TufeTable, String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct TufePinStatus {
    pub model_id: String,
    pub through_month: String,
    pub ok: bool,
}

/// Tablonun durumu (Ayarlar ve Hakkında satırı; EK 3 §3.5).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct TufeStatus {
    pub source: &'static str,
    pub path: Option<String>,
    pub valid: bool,
    pub error: Option<String>,
    /// Dosyanın son ayı.
    pub through_month: Option<String>,
    pub file_sha256: Option<String>,
    pub pins: Vec<TufePinStatus>,
}

/// Bir T için TÜFE girdisinin durumu (sonuç ekranı, kart ve dondur ön koşulu; §3.3).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct TufeInfo {
    pub source: &'static str,
    pub path: Option<String>,
    pub file_sha256: Option<String>,
    /// Dosyanın son ayı.
    pub through_month: Option<String>,
    pub t: Option<String>,
    /// T'nin ayı − 2.
    pub month: Option<String>,
    pub index: Option<String>,
    pub release_date: Option<String>,
    pub bulletin_id: Option<String>,
    /// TUFE_MISSING | TUFE_NOT_PIT | TUFE_FILE_MISMATCH | null
    pub refusal: Option<&'static str>,
    /// T_UNKNOWN | TABLE_INVALID | MONTH_MISSING | NOT_PIT | PIN_MISMATCH | null
    pub reason: Option<&'static str>,
    pub detail: Option<String>,
    /// Ay eksikse aylık ekleme komutu (Python `tufe.APPEND_COMMAND`; uygulama çalıştırmaz).
    pub append_command: Option<String>,
    /// Bütün deflatörlü modellerin önek pini tuttu mu (tablo geçerliyse).
    pub pin_ok: Option<bool>,
}

/// Model kümesindeki deflatörlü modellerin TÜFE pinleri (Python `freeze.deflator_pins`: JSON'da `deflator` sözlüğü olan her
/// model; Faz 7 v1 real/pooled ve Faz 7C h99/pooled).
pub fn deflator_pins(models: &[borsai_predict::ModelRef]) -> Vec<(String, DeflatorPin)> {
    models
        .iter()
        .filter_map(|m| {
            let d = m.params.get("deflator").filter(|d| d.is_object())?;
            let t = |k: &str| d.get(k).and_then(Value::as_str).map(str::to_string);
            Some((m.model_id.clone(), DeflatorPin { through_month: t("through_month")?, prefix_sha256: t("file_sha256")? }))
        })
        .collect()
}

/// Derlemeye gömülü modellerin pinleri (bütünlükten bağımsız; dondur ön koşulu ve ayar denetimi kullanır).
pub fn embedded_deflator_pins() -> &'static [(String, DeflatorPin)] {
    static PINS: OnceLock<Vec<(String, DeflatorPin)>> = OnceLock::new();
    PINS.get_or_init(|| {
        let refs: Vec<borsai_predict::ModelRef> = embedded::EMBEDDED_MODELS
            .iter()
            .filter_map(|m| {
                Some(borsai_predict::ModelRef {
                    model_id: m.model_id.to_string(),
                    params_sha256: String::new(),
                    params: serde_json::from_str(m.json).ok()?,
                })
            })
            .collect();
        deflator_pins(&refs)
    })
}

/// Repo içi TÜFE yolu (bileşenlerle kurulur).
pub fn tufe_path_in(repo: &Path) -> PathBuf {
    repo.join("data").join("raw").join("tuik").join("tufe_genel_2025_100.csv")
}

/// Repo dosyasından (her çağrıda yeniden okunur).
pub fn tufe_source_repo(repo: &Path) -> TufeSource {
    let path = tufe_path_in(repo);
    let table = std::fs::read(&path)
        .map_err(|e| format!("{} okunamadı: {e}", path.display()))
        .and_then(|raw| tufe::parse(&raw).map_err(|e| e.0));
    TufeSource { source: TUFE_SOURCE_REPO, path: Some(path), table }
}

/// Derlemeye gömülü kopya (bağımsız mod). Gömülü tablo yoksa `None` (deflatörlü model de yok demektir).
pub fn tufe_source_embedded() -> Option<TufeSource> {
    let text = embedded::TUFE_CSV?;
    Some(TufeSource { source: TUFE_SOURCE_EMBEDDED, path: None, table: tufe::parse(text.as_bytes()).map_err(|e| e.0) })
}

/// Kaynak seçimi §3.1: doğrulanmış repo modu → repo dosyası; değilse gömülü.
pub fn tufe_source(state: &AppState) -> Option<TufeSource> {
    match state.repo() {
        Some(r) => Some(tufe_source_repo(&r.root)),
        None => tufe_source_embedded(),
    }
}

pub fn tufe_status(src: &TufeSource, pins: &[(String, DeflatorPin)]) -> TufeStatus {
    let (valid, error, through, sha) = match &src.table {
        Ok(t) => (true, None, Some(t.last_month().to_string()), Some(t.file_sha256.clone())),
        Err(e) => (false, Some(e.clone()), None, None),
    };
    let pins = pins
        .iter()
        .map(|(id, pin)| TufePinStatus {
            model_id: id.clone(),
            through_month: pin.through_month.clone(),
            ok: src.table.as_ref().is_ok_and(|t| tufe::verify_pin(t, pin).is_ok()),
        })
        .collect();
    TufeStatus { source: src.source, path: src.path.as_ref().map(|p| p.display().to_string()), valid, error, through_month: through, file_sha256: sha, pins }
}

/// `freeze.tufe_for_record` sırası (EK 3 §3.3): (tufe_index, tufe_refusal, bilgi).
/// 1. T boş → TUFE_MISSING (T_UNKNOWN) · 2. tablo geçersiz → TUFE_FILE_MISMATCH · 3. `index_for(T)`: ay yok →
/// TUFE_MISSING (ay adı ve ekleme komutu), yayım T'den önce değil → TUFE_NOT_PIT · 4. deflatörlü modellerin önek
/// pini tutmuyorsa TUFE_FILE_MISMATCH (tek kod bütün deflatörlü hücreler için) · 5. aksi hâlde `tufe_index` = kaynak
/// metni. `python`: ekleme komutunda gösterilecek yorumlayıcı (repo modunda ayardaki; yoksa Python metni aynen).
pub fn tufe_for_inputs(
    t: Option<&str>,
    src: &TufeSource,
    pins: &[(String, DeflatorPin)],
    python: Option<&str>,
) -> (Option<String>, Option<&'static str>, TufeInfo) {
    let t = t.map(str::trim).filter(|s| !s.is_empty());
    let mut info = TufeInfo {
        source: src.source,
        path: src.path.as_ref().map(|p| p.display().to_string()),
        file_sha256: src.table.as_ref().ok().map(|x| x.file_sha256.clone()),
        through_month: src.table.as_ref().ok().map(|x| x.last_month().to_string()),
        t: t.map(str::to_string),
        month: t.and_then(tufe::month_for),
        index: None,
        release_date: None,
        bulletin_id: None,
        refusal: None,
        reason: None,
        detail: None,
        append_command: None,
        pin_ok: None,
    };
    let refuse = |mut info: TufeInfo, code: &'static str, reason: &'static str, detail: String| {
        info.refusal = Some(code);
        info.reason = Some(reason);
        info.detail = Some(detail);
        (None, Some(code), info)
    };
    let Some(t) = t.filter(|t| tufe::month_for(t).is_some()) else {
        return refuse(info, TUFE_MISSING, TUFE_REASON_T_UNKNOWN, "ilk işlem günü bilinmiyor; T'nin ayı − 2 belirlenemez".into());
    };
    let table = match &src.table {
        Ok(tb) => tb,
        Err(e) => return refuse(info, TUFE_FILE_MISMATCH, TUFE_REASON_TABLE_INVALID, e.clone()),
    };
    let row = match tufe::index_for(t, table) {
        Ok(r) => r,
        Err(r) if r.code == TUFE_MISSING => {
            let month = r.month.clone().unwrap_or_default();
            info.append_command = Some(tufe::append_command(&month, python));
            return refuse(info, TUFE_MISSING, TUFE_REASON_MONTH_MISSING, r.message);
        }
        Err(r) => return refuse(info, TUFE_NOT_PIT, TUFE_REASON_NOT_PIT, r.message),
    };
    info.index = Some(row.index.clone());
    info.release_date = Some(row.release_date.clone());
    info.bulletin_id = Some(row.bulletin_id.clone());
    for (id, pin) in pins {
        if let Err(r) = tufe::verify_pin(table, pin) {
            info.pin_ok = Some(false);
            info.index = None;
            return refuse(info, TUFE_FILE_MISMATCH, TUFE_REASON_PIN_MISMATCH, format!("{id}: {}", r.message));
        }
    }
    info.pin_ok = Some(true);
    (Some(row.index.clone()), None, info)
}

/// Girdi sözlüğüne kayıt biçimindeki TÜFE anahtarlarını ekler (deflatörlü model yoksa hiçbir şey eklenmez).
pub fn with_tufe(inputs: &Map<String, Value>, idx: Option<String>, refusal: Option<&'static str>) -> Map<String, Value> {
    let mut m = inputs.clone();
    m.insert("tufe_index".into(), idx.map(Value::String).unwrap_or(Value::Null));
    m.insert("tufe_refusal".into(), refusal.map(|c| Value::String(c.into())).unwrap_or(Value::Null));
    m
}

/// Ekleme komutunda gösterilecek yorumlayıcı: repo modunda ayardaki Python (repo içindeyse göreli).
pub fn python_display(state: &AppState) -> Option<String> {
    state.repo().map(|r| r.python.strip_prefix(&r.root).map(|p| p.display().to_string()).unwrap_or_else(|_| r.python.display().to_string()))
}

/// Tahminde kullanılan TÜFE bilgisi (sonuç ekranı ve kart satırı); gömülü kümede deflatörlü model yoksa `None`.
pub fn tufe_info_value(state: &AppState, t: Option<&str>) -> Option<TufeInfo> {
    let models = state.models.as_ref().ok()?;
    let pins = deflator_pins(&models.models);
    if pins.is_empty() {
        return None;
    }
    let src = tufe_source(state)?;
    Some(tufe_for_inputs(t, &src, &pins, python_display(state).as_deref()).2)
}

// ---------------------------------------------------------------- predict_all

pub fn predict_all_value(state: &AppState, inputs: &Map<String, Value>, f6: &F6Arg, t: Option<&str>) -> Result<Vec<Value>, AppError> {
    let models = state.models.as_ref().map_err(|e| e.to_app_error())?;
    let f6 = borsai_predict::F6 { value: f6.value.clone(), refusal: f6.refusal.clone() };
    let pins = deflator_pins(&models.models);
    let inputs = match (pins.is_empty(), tufe_source(state)) {
        (false, Some(src)) => {
            let (idx, refusal, _) = tufe_for_inputs(t, &src, &pins, None);
            with_tufe(inputs, idx, refusal)
        }
        // deflatörlü model var ama tablo gömülü değil (derleme bunu engeller): fail-closed
        (false, None) => with_tufe(inputs, None, Some(TUFE_FILE_MISMATCH)),
        (true, _) => inputs.clone(),
    };
    Ok(borsai_predict::predict_all(&models.models, &inputs, &f6).iter().map(|r| r.to_json()).collect())
}

#[tauri::command]
pub fn predict_all(
    state: tauri::State<'_, AppState>,
    inputs: Map<String, Value>,
    f6: Option<F6Arg>,
    t: Option<String>,
) -> Result<Vec<Value>, AppError> {
    predict_all_value(&state, &inputs, &f6.unwrap_or_default(), t.as_deref())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn src(csv: &str) -> TufeSource {
        TufeSource { source: TUFE_SOURCE_EMBEDDED, path: None, table: tufe::parse(csv.as_bytes()).map_err(|e| e.0) }
    }

    #[test]
    fn tufe_rules_order() {
        let s = tufe_source_embedded().expect("gömülü TÜFE tablosu");
        let pins = embedded_deflator_pins();
        assert_eq!(pins.len(), 4, "v1 real/pooled ve (C) h99/pooled");
        let (idx, r, info) = tufe_for_inputs(Some("2026-09-17"), &s, pins, None);
        assert_eq!((idx.as_deref(), r, info.month.as_deref(), info.pin_ok), (Some("132.31"), None, Some("2026-07"), Some(true)));
        let (_, r, info) = tufe_for_inputs(None, &s, pins, None);
        assert_eq!((r, info.reason), (Some(TUFE_MISSING), Some(TUFE_REASON_T_UNKNOWN)));
        let (_, r, info) = tufe_for_inputs(Some("2099-11-10"), &s, pins, None);
        assert_eq!((r, info.reason, info.month.as_deref()), (Some(TUFE_MISSING), Some(TUFE_REASON_MONTH_MISSING), Some("2099-09")));
        assert!(info.append_command.unwrap().contains("--append-month 2099-09 "));
        let (_, r, info) = tufe_for_inputs(Some("2026-09-17"), &src("bozuk\n"), pins, None);
        assert_eq!((r, info.reason), (Some(TUFE_FILE_MISMATCH), Some(TUFE_REASON_TABLE_INVALID)));
    }
}
