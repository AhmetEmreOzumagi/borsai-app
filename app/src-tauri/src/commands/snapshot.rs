//! YALNIZ GELİŞTİRME: ekran görüntüsü (WKWebView `takeSnapshot`), `app/docs/screens/` için.
//! `--features snapshot` olmadan derlenmez (komut `SNAPSHOT_UNAVAILABLE` döner). Hedef dizin
//! `BORSAI_SNAPSHOT_DIR` ortam değişkeninden; dosya adı `[a-z0-9_]+`; başka hiçbir yere yazmaz.
use super::AppError;
use crate::state::AppState;

pub const SNAPSHOT_UNAVAILABLE: &str = "SNAPSHOT_UNAVAILABLE";

fn snapshot_run() -> bool {
    cfg!(feature = "snapshot") && std::env::var_os("BORSAI_SNAPSHOT_DIR").is_some()
}

#[tauri::command]
pub fn dev_snapshot(window: tauri::WebviewWindow, name: String) -> Result<(), AppError> {
    imp::snapshot(window, name)
}

/// YALNIZ ekran görüntüsü koşusu: doğruluk panelini `BORSAI_SCORES_FIXTURES/<ad>.json` sentetik
/// dosyasına bağlar (SPEC_APP §5.3 fixture'ları; boş ad ayarı kaldırır). Dosya salt okunur ve
/// `synthetic: true` taşır; panel başlığında kaynak "FIXTURE" ve kurgusal uyarısı görünür.
#[tauri::command]
pub fn dev_scores_fixture(state: tauri::State<'_, AppState>, name: String) -> Result<(), AppError> {
    if !snapshot_run() {
        return Err(AppError::new(SNAPSHOT_UNAVAILABLE, "yalnız --features snapshot ile"));
    }
    if name.is_empty() {
        state.set_scores_fixture(None);
        return Ok(());
    }
    if !name.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_') {
        return Err(AppError::new(SNAPSHOT_UNAVAILABLE, format!("ad {name:?}")));
    }
    let dir = std::env::var("BORSAI_SCORES_FIXTURES")
        .map_err(|_| AppError::new(SNAPSHOT_UNAVAILABLE, "BORSAI_SCORES_FIXTURES yok"))?;
    state.set_scores_fixture(Some(std::path::PathBuf::from(dir).join(format!("{name}.json"))));
    Ok(())
}

/// YALNIZ ekran görüntüsü koşusu: pencereyi verilen mantıksal boyuta getirir (büyütme kapanır, ortalanır). FAZ9_UI_FIX
/// K-FIX-6 görüntüleri (1200 px Sicil) ve 1024 × 680 yatay kaydırma denetimi için; üretimde `SNAPSHOT_UNAVAILABLE`.
#[tauri::command]
pub fn dev_window_size(window: tauri::WebviewWindow, width: f64, height: f64) -> Result<(), AppError> {
    if !snapshot_run() {
        return Err(AppError::new(SNAPSHOT_UNAVAILABLE, "yalnız --features snapshot ile"));
    }
    let err = |e: tauri::Error| AppError::new(SNAPSHOT_UNAVAILABLE, e.to_string());
    window.unmaximize().map_err(err)?;
    window.set_size(tauri::LogicalSize::new(width, height)).map_err(err)?;
    window.center().map_err(err)?;
    Ok(())
}

/// Ekran görüntüsü koşusunun sonu: uygulama kapanır (yalnız snapshot özelliği ve BORSAI_SNAPSHOT_DIR ile).
#[tauri::command]
pub fn dev_snapshot_done(app: tauri::AppHandle) -> Result<(), AppError> {
    if snapshot_run() {
        app.exit(0);
        return Ok(());
    }
    Err(AppError::new(SNAPSHOT_UNAVAILABLE, "yalnız --features snapshot ile"))
}

#[cfg(not(all(feature = "snapshot", target_os = "macos")))]
mod imp {
    use super::{AppError, SNAPSHOT_UNAVAILABLE};

    pub fn snapshot(_window: tauri::WebviewWindow, _name: String) -> Result<(), AppError> {
        Err(AppError::new(SNAPSHOT_UNAVAILABLE, "yalnız --features snapshot ile"))
    }
}

#[cfg(all(feature = "snapshot", target_os = "macos"))]
mod imp {
    use super::{AppError, SNAPSHOT_UNAVAILABLE};
    use block2::RcBlock;
    use objc2::runtime::AnyObject;
    use objc2_app_kit::{NSBitmapImageFileType, NSBitmapImageRep, NSImage};
    use objc2_foundation::{NSDictionary, NSError, NSString};
    use objc2_web_kit::WKWebView;
    use std::path::PathBuf;

    pub fn snapshot(window: tauri::WebviewWindow, name: String) -> Result<(), AppError> {
        let dir = std::env::var("BORSAI_SNAPSHOT_DIR").map_err(|_| AppError::new(SNAPSHOT_UNAVAILABLE, "BORSAI_SNAPSHOT_DIR yok"))?;
        if name.is_empty() || !name.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_') {
            return Err(AppError::new(SNAPSHOT_UNAVAILABLE, format!("ad {name:?}")));
        }
        let path = PathBuf::from(dir).join(format!("{name}.png"));
        window
            .with_webview(move |pw| unsafe {
                let wk: &WKWebView = &*(pw.inner() as *const WKWebView);
                let block = RcBlock::new(move |img: *mut NSImage, _err: *mut NSError| {
                    let Some(img) = img.as_ref() else { return };
                    let Some(tiff) = img.TIFFRepresentation() else { return };
                    let Some(rep) = NSBitmapImageRep::imageRepWithData(&tiff) else { return };
                    let props: objc2::rc::Retained<NSDictionary<NSString, AnyObject>> = NSDictionary::new();
                    if let Some(png) = rep.representationUsingType_properties(NSBitmapImageFileType::PNG, &props) {
                        let _ = std::fs::write(&path, png.to_vec());
                    }
                });
                wk.takeSnapshotWithConfiguration_completionHandler(None, &block);
            })
            .map_err(|e| AppError::new(SNAPSHOT_UNAVAILABLE, e.to_string()))
    }
}
