//! FAZ3_FABLE_APP_AUDIT_CLOSE adım 2: `resolve_path` / `is_within` / dışa aktarma ve kaydetme bekçisi
//! sondaları. Yalnız klonda koşar (`/tmp/borsai_app_audit_close/clone`); asıl `app/`'e yazılmaz.
//! Her vaka: bekçi sonucu (is_within), tekli + toplu dışa aktarma sonucu, repo altında dosya oluştu mu.
use borsai_app_lib::commands::config::{is_within, resolve_path};
use borsai_app_lib::commands::scenario::{
    export_all_scenarios_in, export_scenario_in, save_scenario_in, scenarios_dir, F6Doc, SaveScenarioReq,
};
use borsai_app_lib::state::AppState;
use serde_json::{json, Map};
use std::path::{Path, PathBuf};

const BASE: &str = "/tmp/borsai_app_audit_close";

fn ln(target: impl AsRef<Path>, link: impl AsRef<Path>) {
    let _ = std::fs::remove_file(link.as_ref());
    std::os::unix::fs::symlink(target.as_ref(), link.as_ref()).unwrap();
}

fn repo_tree(repo: &Path) -> Vec<String> {
    let out = std::process::Command::new("git")
        .current_dir(repo)
        .env("GIT_OPTIONAL_LOCKS", "0")
        .args(["status", "--porcelain", "--untracked-files=all", "--", "registry", "data", "scores", "app/parity"])
        .output()
        .unwrap();
    String::from_utf8_lossy(&out.stdout).lines().map(str::to_string).collect()
}

fn req() -> SaveScenarioReq {
    let mut inputs = Map::new();
    for (k, v) in [
        ("ipo_price_tl", "25.52"), ("shares_offered", "87500000"), ("post_ipo_share_capital", "312500000"),
        ("capital_increase_shares", "62500000"), ("existing_share_sale_shares", "25000000"), ("additional_sale_shares", "0"),
        ("total_demand_multiple", "2.84"), ("total_demand_filter_status", "NOT_SPECIFIED"), ("ipo_size_tl", "2233000000"),
        ("ipo_price_try", "25.52"), ("planned_pre_ipo_capital", "250000000"), ("planned_post_ipo_capital", "312500000"),
        ("planned_capital_increase_shares", "62500000"), ("planned_existing_share_sale", "25000000"),
        ("planned_base_offer_shares", "87500000"), ("planned_additional_sale_ceiling", "0"), ("planned_max_offer_shares", "87500000"),
    ] {
        inputs.insert(k.into(), json!(v));
    }
    SaveScenarioReq {
        title: "probe".into(), stage: "POST_BOOKBUILD_PRE_LISTING".into(), ticker_label: None, inputs,
        input_dates: Map::new(), f6: F6Doc { origin: "NONE".into(), ..Default::default() }, observed_streak_user: None,
    }
}

#[test]
fn close_probe() {
    let repo = PathBuf::from(format!("{BASE}/clone")).canonicalize().unwrap();
    let x = PathBuf::from(format!("{BASE}/probe"));
    let _ = std::fs::remove_dir_all(&x);
    std::fs::create_dir_all(&x).unwrap();
    let xc = x.canonicalize().unwrap();
    println!("PROBE repo canonical = {}", repo.display());
    println!("PROBE probe dir (outside) canonical = {}", xc.display());
    let tree0 = repo_tree(&repo);
    println!("PROBE klon git status (registry data scores app/parity) başlangıç: {tree0:?}");

    let records = repo.join("registry").join("records");
    let kacak = records.join("kacak_probe.json");
    let data = x.join("probe_data");
    std::fs::create_dir_all(&data).unwrap();
    let state = AppState::from_embedded();
    let saved = save_scenario_in(&state, &data, &[repo.clone()], &req()).unwrap();

    // ---- bağlar (hepsi repo DIŞINDA, /tmp/borsai_app_audit_close/probe altında)
    ln(&kacak, x.join("askida_dosya.json")); // askıda dosya bağı (denetimin symlink_file vakası)
    ln("../clone/registry/records", x.join("goreli_dizin")); // göreli hedefli dizin bağı
    ln("../clone/registry/records/kacak_probe.json", x.join("goreli_dosya.json")); // göreli hedefli askıda dosya bağı
    ln(x.join("zincir2"), x.join("zincir1")); // iki halkalı zincir: dış → dış → repo (dizin)
    ln(&records, x.join("zincir2"));
    ln(x.join("zincir_dosya2.json"), x.join("zincir_dosya1.json")); // iki halkalı, dosya, askıda
    ln(&kacak, x.join("zincir_dosya2.json"));
    ln(x.join("dongu_b"), x.join("dongu_a")); // döngü a → b → a (repo dışı)
    ln(x.join("dongu_a"), x.join("dongu_b"));
    ln(&records, x.join("dizin_bagi")); // dizin bağı → repo/registry/records
    std::fs::create_dir_all(x.join("dis_dizin").join("alt")).unwrap();
    ln(x.join("dis_dizin").join("alt"), x.join("dis_dizin_bagi")); // repo dışını gösteren dizin bağı
    ln(x.join("baska_yer.json"), x.join("dis_dosya_bagi.json")); // repo dışını gösteren (askıda) dosya bağı
    // uzun zincir: 45 halka (MAX_LINKS = 40, macOS MAXSYMLINKS = 32)
    for i in 0..45 {
        let tgt: PathBuf = if i == 44 { records.clone() } else { x.join(format!("uzun{}", i + 1)) };
        ln(tgt, x.join(format!("uzun{i}")));
    }
    // 33 halka: OS sınırının (32) hemen üstü, MAX_LINKS altında
    for i in 0..33 {
        let tgt: PathBuf = if i == 32 { records.clone() } else { x.join(format!("orta{}", i + 1)) };
        ln(tgt, x.join(format!("orta{i}")));
    }
    // klon İÇİNDE (registry/records) askıda bağlar; sonda sonunda silinir
    ln("/nonexistent/zzz/askida_dis.json", records.join("askida_dis.json")); // dizin bağının içinde, repo dışına askıda
    ln(&kacak, records.join("askida_ic.json")); // dizin bağının içinde, repo içine askıda
    ln(records.join("dongu_ic_b"), records.join("dongu_ic_a")); // repo içinde döngü
    ln(records.join("dongu_ic_a"), records.join("dongu_ic_b"));

    let up = |p: &Path| PathBuf::from(p.display().to_string().replace("/private/tmp/borsai_app_audit_close/clone", "/TMP/BORSAI_APP_AUDIT_CLOSE/CLONE"));
    let mixed = |p: &Path| PathBuf::from(p.display().to_string().replace("/private/tmp/borsai_app_audit_close/clone", "/tmp/Borsai_App_Audit_Close/Clone").replace("/registry/records", "/Registry/Records"));
    let tmp_form = |p: &Path| PathBuf::from(p.display().to_string().replace("/private/tmp/", "/tmp/"));

    // (ad, hedef yol, beklenen is_within, repo altında oluşabilecek dosya)
    let cases: Vec<(&str, PathBuf, bool, PathBuf)> = vec![
        ("askida_dosya_bagi (denetim symlink_file)", x.join("askida_dosya.json"), true, kacak.clone()),
        ("goreli_dizin_bagi", x.join("goreli_dizin").join("kacak_probe.json"), true, kacak.clone()),
        ("goreli_askida_dosya_bagi", x.join("goreli_dosya.json"), true, kacak.clone()),
        ("zincir2_dizin (dış→dış→repo)", x.join("zincir1").join("kacak_probe.json"), true, kacak.clone()),
        ("zincir2_dosya_askida", x.join("zincir_dosya1.json"), true, kacak.clone()),
        ("dongu_dosya (a→b→a, repo dışı)", x.join("dongu_a"), false, kacak.clone()),
        ("dongu_dizin_bileseni (a→b→a, repo dışı)", x.join("dongu_a").join("kacak_probe.json"), false, kacak.clone()),
        ("dongu_repo_icinde", records.join("dongu_ic_a"), true, kacak.clone()),
        ("tmp_yerine_private (hedef /tmp/…)", tmp_form(&kacak), true, kacak.clone()),
        ("buyuk_harf", up(&kacak), true, kacak.clone()),
        ("karisik_harf", mixed(&kacak), true, kacak.clone()),
        ("bagdan_sonra_dotdot (dizin bağı → records, ../)", x.join("dizin_bagi").join("..").join("kacak_probe.json"), true, repo.join("registry").join("kacak_probe.json")),
        ("dotdot_var_olmayan_ara_dizin (repo içi)", records.join("yok").join("..").join("kacak_probe.json"), true, kacak.clone()),
        ("dotdot_disaridan_var_olmayan", PathBuf::from(format!("{BASE}/nodir/../clone/registry/records/kacak_probe.json")), true, kacak.clone()),
        ("dizin_baginin_icinde_askida_bag (repo dışına)", x.join("dizin_bagi").join("askida_dis.json"), false, kacak.clone()),
        ("dizin_baginin_icinde_askida_bag (repo içine)", x.join("dizin_bagi").join("askida_ic.json"), true, kacak.clone()),
        ("goreli_yol (cwd = klon)", PathBuf::from("registry/records/kacak_probe.json"), true, kacak.clone()),
        ("kokte_dotdot", PathBuf::from(format!("/../..{}", kacak.display())), true, kacak.clone()),
        ("uzun_zincir_45 (MAX_LINKS aşımı)", x.join("uzun0").join("kacak_probe.json"), false, kacak.clone()),
        ("orta_zincir_33 (OS sınırı üstü, MAX_LINKS altı)", x.join("orta0").join("kacak_probe.json"), true, kacak.clone()),
        // repo DIŞINI gösterenler: kabul edilmeli
        ("dis_dizin_bagi (kabul beklenir)", x.join("dis_dizin_bagi").join("ok.json"), false, x.join("dis_dizin").join("alt").join("ok.json")),
        ("dis_dizin_bagi_dotdot (fiziksel üst; kabul beklenir)", x.join("dis_dizin_bagi").join("..").join("ok2.json"), false, x.join("dis_dizin").join("ok2.json")),
        ("dis_dosya_bagi (askıda, repo dışına)", x.join("dis_dosya_bagi.json"), false, x.join("baska_yer.json")),
        ("repo_icinden_dotdot_ile_disari", repo.join("registry").join("..").join("..").join("probe").join("cikis.json"), false, x.join("cikis.json")),
    ];
    std::env::set_current_dir(&repo).unwrap();
    let mut rows = Vec::new();
    let mut unexpected = Vec::new();
    for (name, t, expect_within, landing) in &cases {
        let rp = resolve_path(t);
        let w = is_within(t, &repo);
        let _ = std::fs::remove_file(landing);
        let one = export_scenario_in(&data, &[repo.clone()], &saved.scenario_id, t).map(|_| "OK".to_string()).unwrap_or_else(|e| e.code);
        let landed_one = std::fs::symlink_metadata(landing).is_ok();
        let _ = std::fs::remove_file(landing);
        let many = export_all_scenarios_in(&data, &[repo.clone()], t).map(|_| "OK".to_string()).unwrap_or_else(|e| e.code);
        let landed_many = std::fs::symlink_metadata(landing).is_ok();
        let _ = std::fs::remove_file(landing);
        let in_repo = landing.starts_with(&repo);
        let line = format!(
            "PROBE [{name}]\n  hedef      = {}\n  resolve    = {}\n  is_within  = {w} (beklenen {expect_within})\n  tekli      = {one} ; dosya oluştu ({}) = {landed_one}\n  toplu      = {many} ; dosya oluştu = {landed_many}",
            t.display(), rp.display(), if in_repo { "REPO ALTINDA" } else { "repo dışında" }
        );
        println!("{line}");
        rows.push(line);
        if w != *expect_within {
            unexpected.push(format!("[{name}] is_within {w} ≠ beklenen {expect_within}"));
        }
        if in_repo && (landed_one || landed_many || one == "OK" || many == "OK") {
            unexpected.push(format!("[{name}] REPO ALTINA YAZILDI ya da kabul edildi: tekli {one} toplu {many}"));
        }
    }

    // ---- kaydetme: scenarios/ dizininin kendisi bağ
    let mut save_rows = Vec::new();
    for (name, target) in [
        ("scenarios → repo/registry/records/SNTX (askıda, repo içi)", records.join("SNTX")),
        ("scenarios → repo/registry/records (var olan, repo içi)", records.clone()),
        ("scenarios → repo dışı var olan dizin", x.join("dis_scen")),
        ("scenarios → repo dışı askıda dizin", x.join("dis_scen_yok")),
    ] {
        let _ = std::fs::create_dir_all(x.join("dis_scen"));
        let d = x.join(format!("data_{}", save_rows.len()));
        std::fs::create_dir_all(&d).unwrap();
        ln(&target, d.join("scenarios"));
        let sd = scenarios_dir(&d, &[repo.clone()]).map(|p| p.display().to_string()).unwrap_or_else(|e| e.code);
        let sv = save_scenario_in(&state, &d, &[repo.clone()], &req()).map(|s| s.scenario_id).unwrap_or_else(|e| e.code);
        let in_repo_files = std::fs::read_dir(&target).map(|r| r.flatten().map(|e| e.file_name().to_string_lossy().to_string()).collect::<Vec<_>>()).unwrap_or_default();
        let line = format!("PROBE kaydetme [{name}]\n  scenarios_dir = {sd}\n  save          = {sv}\n  hedef dizin içeriği = {in_repo_files:?}");
        println!("{line}");
        save_rows.push(line);
        if target.starts_with(&repo) && sv.len() == 26 {
            unexpected.push(format!("kaydetme [{name}] REPO ALTINA YAZDI"));
        }
        // repo altına bir şey düştüyse temizle
        if target == records.join("SNTX") {
            let _ = std::fs::remove_dir_all(records.join("SNTX"));
        }
    }

    // ---- temizlik (klon içindeki sonda bağları) ve son durum
    for f in ["askida_dis.json", "askida_ic.json", "dongu_ic_a", "dongu_ic_b"] {
        let _ = std::fs::remove_file(records.join(f));
    }
    let _ = std::fs::remove_file(&kacak);
    let _ = std::fs::remove_file(repo.join("registry").join("kacak_probe.json"));
    let tree1 = repo_tree(&repo);
    println!("PROBE klon git status (registry data scores app/parity) sonda sonu: {tree1:?}");
    println!("PROBE beklenmeyen: {unexpected:?}");
    assert_eq!(tree0, tree1, "klonun sicil ağacı değişti");
    assert!(unexpected.is_empty(), "{unexpected:?}");
}
