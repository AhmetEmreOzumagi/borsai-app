// Windows'ta sürüm derlemesinde ek konsol penceresi açılmasın (create-tauri-app düzeni).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    borsai_app_lib::run()
}
