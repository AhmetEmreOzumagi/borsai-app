//! FAZ3_FABLE_APP_AUDIT adım 5: kişisel kayıt yol bekçisi sondaları (büyük/küçük harf, `..`, sembolik bağ).
use borsai_app_lib::commands::config::is_within;
use borsai_app_lib::commands::scenario::{export_scenario_in, save_scenario_in, scenarios_dir, F6Doc, SaveScenarioReq};
use borsai_app_lib::state::AppState;
use serde_json::{json, Map};
use std::path::{Path, PathBuf};

#[test]
fn probe_paths() {
    let repo = PathBuf::from("/tmp/borsai_app_audit/clone").canonicalize().unwrap();
    println!("PROBE repo canonical = {}", repo.display());
    println!("PROBE canonicalize(UPPER) = {:?}", std::fs::canonicalize("/TMP/BORSAI_APP_AUDIT/CLONE"));
    let cases = [
        ("exact", "/tmp/borsai_app_audit/clone/registry/records/x.json"),
        ("upper_case", "/TMP/BORSAI_APP_AUDIT/CLONE/registry/records/x.json"),
        ("mixed_case", "/tmp/Borsai_App_Audit/Clone/Registry/Records/x.json"),
        ("dotdot_existing", "/tmp/borsai_app_audit/other/../clone/registry/records/x.json"),
        ("dotdot_nonexistent_mid", "/tmp/borsai_app_audit/clone/registry/nonexist/../records/x.json"),
        ("dotdot_from_outside_nonexistent", "/tmp/borsai_app_audit/nodir/../clone/registry/records/x.json"),
        ("outside", "/tmp/borsai_app_audit/elsewhere/x.json"),
    ];
    let _ = std::fs::create_dir_all("/tmp/borsai_app_audit/other");
    let _ = std::fs::remove_file("/tmp/borsai_app_audit/link");
    std::os::unix::fs::symlink(&repo, "/tmp/borsai_app_audit/link").unwrap();
    for (name, p) in cases {
        println!("PROBE is_within[{name}] {p} -> {}", is_within(Path::new(p), &repo));
    }
    println!("PROBE is_within[symlink_dir] -> {}", is_within(Path::new("/tmp/borsai_app_audit/link/registry/records/x.json"), &repo));
    // file-level symlink: target path itself is a symlink pointing into the repo
    let _ = std::fs::remove_file("/tmp/borsai_app_audit/filelink.json");
    std::os::unix::fs::symlink(repo.join("registry/records/kacak_probe.json"), "/tmp/borsai_app_audit/filelink.json").unwrap();
    println!("PROBE is_within[symlink_file] -> {}", is_within(Path::new("/tmp/borsai_app_audit/filelink.json"), &repo));
    // gerçek komut yolu: export hedefi bu varyantlarla
    let data = PathBuf::from("/tmp/borsai_app_audit/probe_data");
    let _ = std::fs::remove_dir_all(&data);
    std::fs::create_dir_all(&data).unwrap();
    let state = AppState::from_embedded();
    let mut inputs = Map::new();
    for (k, v) in [("ipo_price_tl", "25.52"), ("shares_offered", "87500000"), ("post_ipo_share_capital", "312500000"),
        ("capital_increase_shares", "62500000"), ("existing_share_sale_shares", "25000000"), ("additional_sale_shares", "0"),
        ("total_demand_multiple", "2.84"), ("total_demand_filter_status", "NOT_SPECIFIED"), ("ipo_size_tl", "2233000000"),
        ("ipo_price_try", "25.52"), ("planned_pre_ipo_capital", "250000000"), ("planned_post_ipo_capital", "312500000"),
        ("planned_capital_increase_shares", "62500000"), ("planned_existing_share_sale", "25000000"),
        ("planned_base_offer_shares", "87500000"), ("planned_additional_sale_ceiling", "0"), ("planned_max_offer_shares", "87500000")] {
        inputs.insert(k.into(), json!(v));
    }
    let req = SaveScenarioReq { title: "probe".into(), stage: "POST_BOOKBUILD_PRE_LISTING".into(), ticker_label: None, inputs,
        input_dates: Map::new(), f6: F6Doc { origin: "NONE".into(), ..Default::default() }, observed_streak_user: None };
    let saved = save_scenario_in(&state, &data, &[repo.clone()], &req).unwrap();
    for (name, p) in [
        ("upper_case", "/TMP/BORSAI_APP_AUDIT/CLONE/registry/records/kacak_probe.json"),
        ("dotdot_nonexistent_mid", "/tmp/borsai_app_audit/clone/registry/nonexist/../records/kacak_probe.json"),
        ("symlink_dir", "/tmp/borsai_app_audit/link/registry/records/kacak_probe.json"),
        ("symlink_file", "/tmp/borsai_app_audit/filelink.json"),
    ] {
        let r = export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, Path::new(p));
        let written = repo.join("registry/records/kacak_probe.json").exists();
        println!("PROBE export[{name}] -> {:?} ; repo'da dosya oluştu mu: {written}", r.as_ref().map(|_| "OK").map_err(|e| e.code.clone()));
        let _ = std::fs::remove_file(repo.join("registry/records/kacak_probe.json"));
    }
    // app_data_dir repo altına: scenarios_dir bekçisi
    for (name, d) in [("upper_case_datadir", "/TMP/BORSAI_APP_AUDIT/CLONE/appdata"), ("symlink_datadir", "/tmp/borsai_app_audit/link/appdata")] {
        println!("PROBE scenarios_dir[{name}] -> {:?}", scenarios_dir(Path::new(d), &[repo.clone()]).map(|p| p.display().to_string()).map_err(|e| e.code));
    }
    let _ = std::fs::remove_file("/tmp/borsai_app_audit/link");
    let _ = std::fs::remove_file("/tmp/borsai_app_audit/filelink.json");
}
