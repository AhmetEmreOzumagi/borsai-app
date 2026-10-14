//! BorsAi masaüstü uygulaması, Rust arka uç (SPEC_APP §1.1).
pub mod clock;
pub mod commands;
pub mod embedded;
pub mod json_out;
pub mod python;
pub mod state;

use tauri::Manager;

/// Varsayılan pencere (FAZ9_UI_FIX K-FIX-6): 1440 × 900 mantıksal piksel, ortada (tauri.conf.json ile aynı; cargo testi
/// eşitliği sınar). Ekranın çalışma alanı bundan küçükse pencere büyütülmüş açılır.
pub const DEFAULT_WINDOW: (f64, f64) = (1440.0, 900.0);
/// En küçük pencere (K-FIX-6): bu sınırlarda hiçbir sade ekranda yatay kaydırma çubuğu çıkmaz.
pub const MIN_WINDOW: (f64, f64) = (1024.0, 680.0);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(state::AppState::from_embedded())
        .setup(|app| {
            // Yalnız debug derlemede: BORSAI_DATA_DIR uygulama verisini başka dizine yönlendirir
            // (ekran görüntüsü/demo koşuları sahibinin gerçek uygulama verisine yazmasın diye).
            let dir = match std::env::var_os("BORSAI_DATA_DIR") {
                Some(d) if cfg!(debug_assertions) => std::path::PathBuf::from(d),
                _ => app.path().app_data_dir()?,
            };
            app.state::<state::AppState>().attach_data_dir(&dir);
            // Kişisel modda gömülü sicil anlık görüntüsü açılışta yazılır ve doğrulanır (FAZ9_SNAPSHOT K-SNAP-2)
            app.state::<state::AppState>().prepare_snapshot();
            // Pencere (K-FIX-6): çalışma alanı 1440 × 900'den küçükse büyütülmüş aç (monitör okunamazsa olduğu gibi kalır).
            if let Some(w) = app.get_webview_window("main") {
                if let Ok(Some(m)) = w.current_monitor() {
                    let area = m.work_area().size.to_logical::<f64>(m.scale_factor());
                    if area.width < DEFAULT_WINDOW.0 || area.height < DEFAULT_WINDOW.1 {
                        let _ = w.maximize();
                    }
                }
            }
            // Yalnız ekran görüntüsü koşusu: pencere önde kalsın (arkada kalan WebView zamanlayıcıları askıya alınır).
            #[cfg(feature = "snapshot")]
            if std::env::var_os("BORSAI_SNAPSHOT_DIR").is_some() {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.set_always_on_top(true);
                    let _ = w.set_focus();
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::models::app_info,
            commands::predict::predict_all,
            commands::config::get_config,
            commands::config::set_config,
            commands::config::validate_repo,
            commands::config::set_ui_view,
            commands::market20::market20_via_python,
            commands::form::check_form,
            commands::inputs_doc::list_input_documents,
            commands::inputs_doc::read_input_document,
            commands::inputs_doc::preview_inputs_doc,
            commands::inputs_doc::write_inputs_doc,
            commands::source_docs::copy_source_docs,
            commands::source_docs::read_source_manifest,
            commands::freeze::freeze_preflight,
            commands::freeze::inputs_pit_check,
            commands::freeze::freeze_record,
            commands::freeze::cancel_record,
            commands::freeze::freeze_todo,
            commands::registry::registry_view,
            commands::registry::record_ceiling,
            commands::registry::read_record_json,
            commands::ceiling::ceiling_display,
            commands::ceiling::streak_view,
            commands::ceiling::ceiling_summary,
            commands::ceiling::record_summary,
            commands::path::path_display,
            commands::path::path_conditional,
            commands::path::path_params,
            commands::post_d1::post_d1_records,
            commands::post_d1::post_d1_view,
            commands::post_d1::post_d1_preflight,
            commands::post_d1::post_d1_freeze,
            commands::post_d1::post_d1_cancel,
            commands::post_d1::post_d1_todo,
            commands::scenario::save_scenario,
            commands::scenario::list_scenarios,
            commands::scenario::load_scenario,
            commands::scenario::delete_scenario,
            commands::scenario::export_scenario,
            commands::scenario::export_all_scenarios,
            commands::scores::score_hints,
            commands::scores::scores_view,
            commands::scores::scores_post_d1_view,
            commands::scores_oot::scores_oot_view,
            commands::scores_oot::scores_oot_model,
            commands::sade::monitor_view,
            commands::sade::arz_view,
            commands::sade::arz_streak,
            commands::sade::perf_view,
            commands::sade::headline_gate,
            commands::sade_break::break_view,
            commands::snapshot::dev_snapshot,
            commands::snapshot::dev_scores_fixture,
            commands::snapshot::dev_snapshot_done,
            commands::snapshot::dev_window_size,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri uygulaması başlatılamadı");
}
