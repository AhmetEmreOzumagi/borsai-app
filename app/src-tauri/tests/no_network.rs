//! U34: ağ bağımlılığı yok (SPEC_APP §3a.2, §5.5).
//!
//! Sapma (rapora yazıldı): Tauri 2 `reqwest` (→ `hyper`) bağımlılığını yalnız Android/iOS hedefleri
//! için bildirir; `Cargo.lock` platformdan bağımsız olduğundan bu paketler dosyada GEÇER ama macOS
//! derlemesine girmez. Bu yüzden `reqwest`/`hyper` denetimi macOS'a çözülmüş bağımlılık grafiğinde
//! (`cargo metadata --filter-platform aarch64-apple-darwin`) yapılır; `ureq` ve `tauri-plugin-http`
//! `Cargo.lock`'ta hiç yoktur.
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::Command;

const NETWORK_CRATES: [&str; 4] = ["reqwest", "ureq", "hyper", "tauri-plugin-http"];

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| panic!("{}: {e}", p.display()))
}

#[test]
fn no_network_deps() {
    // 1. macOS için çözülmüş grafik: ağ istemcisi yok
    let out = Command::new(env!("CARGO"))
        .current_dir(manifest_dir())
        .args(["metadata", "--format-version", "1", "--locked", "--offline", "--filter-platform", "aarch64-apple-darwin"])
        .output()
        .expect("cargo metadata");
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let meta: Value = serde_json::from_slice(&out.stdout).unwrap();
    let names: std::collections::BTreeMap<&str, &str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["id"].as_str().unwrap(), p["name"].as_str().unwrap()))
        .collect();
    let resolved: Vec<&str> =
        meta["resolve"]["nodes"].as_array().unwrap().iter().map(|n| names[n["id"].as_str().unwrap()]).collect();
    for c in NETWORK_CRATES {
        assert!(!resolved.contains(&c), "macOS derlemesinde ağ paketi: {c}");
    }
    // 2. Cargo.lock: ureq ve tauri-plugin-http hiç yok; reqwest/hyper yalnız mobil hedef (yukarıda sınandı)
    let lock = read(&manifest_dir().join("Cargo.lock"));
    for c in ["ureq", "tauri-plugin-http"] {
        assert!(!lock.contains(&format!("name = \"{c}\"")), "Cargo.lock'ta {c}");
    }
    // 3. doğrudan bağımlılıklar
    let cargo_toml = read(&manifest_dir().join("Cargo.toml"));
    for c in NETWORK_CRATES {
        assert!(!cargo_toml.contains(c), "Cargo.toml'da {c}");
    }
    // 4. package-lock.json: axios / node-fetch yok
    let pkg_lock = read(&manifest_dir().join("../package-lock.json"));
    for c in ["axios", "node-fetch", "@tauri-apps/plugin-http"] {
        assert!(!pkg_lock.contains(&format!("\"node_modules/{c}\"")), "package-lock.json'da {c}");
    }
    // 5. CSP connect-src yalnız 'self' ipc: http://ipc.localhost
    let conf: Value = serde_json::from_str(&read(&manifest_dir().join("tauri.conf.json"))).unwrap();
    let csp = conf["app"]["security"]["csp"].as_str().expect("CSP tanımlı olmalı");
    let connect = csp
        .split(';')
        .map(str::trim)
        .find(|d| d.starts_with("connect-src"))
        .expect("connect-src yönergesi");
    assert_eq!(connect, "connect-src 'self' ipc: http://ipc.localhost");
    assert!(csp.split(';').map(str::trim).any(|d| d == "default-src 'self'"));
    // 6. yetenekler: yalnız core:default ve dialog:default
    let cap: Value = serde_json::from_str(&read(&manifest_dir().join("capabilities/default.json"))).unwrap();
    assert_eq!(cap["permissions"], serde_json::json!(["core:default", "dialog:default"]));
}
