//! Sade görünüm (FAZ9_APP_UI) Rust tarafı: yeni salt okuma komutları GERÇEK repo dosyalarıyla, görev dosyasındaki
//! beklenen sayılarla (orkestratörün dosyalardan hesapladığı; 4 ondalık). `ui_view` ayarının geriye uyumu.
//! Vitest'in sade render fixture'ları bu komutların gerçek çıktısıdır:
//!
//!   BORSAI_UPDATE_UI_FIXTURES=1 cargo test --test sade   # app/tests/fixtures/ui/sade_*.json yeniden yazılır
//!
//! Fixture'lar repo dosyalarıyla değişir (skor, kayıt, sonuç); içerikleri vitest'te aynı beklenen sayılarla sınanır.
use borsai_app_lib::commands::ceiling::{
    attach_calc, calc_view_value, ceiling_display_value, ceiling_summary_value, record_summary_in, streak_view_in, SVector,
    SummaryModel, CALC_RULE_ID,
};
use borsai_app_lib::commands::config::{load_config, set_config_value, set_ui_view_value, AppConfig, UI_AYRINTILI, UI_SADE};
use borsai_app_lib::commands::predict::{predict_all_value, F6Arg};
use borsai_app_lib::commands::registry::record_ceiling_in;
use borsai_app_lib::commands::sade::{
    arz_view_in, headline_gate_value, load_repo, monitor_view_in, perf_view_value, read_days, GateEntry, HeadlineGate, MonitorView,
    PerfView,
};
use borsai_app_lib::commands::sade_break::break_view_in;
use borsai_app_lib::commands::scenario::pretty;
use borsai_app_lib::state::AppState;
use serde_json::{json, Map, Value};
use std::path::PathBuf;

const NETGL_RECORD: &str = "20260922T121936Z_65a39d7392dd.json";
const CITAS_RECORD: &str = "20260922T121935Z_6356b36ec865.json";
const TOL: f64 = 5e-5;

fn app_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").canonicalize().unwrap()
}

fn repo_dir() -> PathBuf {
    app_dir().join("..").canonicalize().unwrap()
}

fn tmp_dir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("borsai_sade_{name}_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d.canonicalize().unwrap()
}

/// Gerçek dosyadan üretilmiş anlık görüntü: yalnız BORSAI_UPDATE_UI_FIXTURES=1 ile yazılır.
fn snapshot(name: &str, v: &impl serde::Serialize) {
    if std::env::var("BORSAI_UPDATE_UI_FIXTURES").as_deref() == Ok("1") {
        let path = app_dir().join("tests").join("fixtures").join("ui").join(name);
        std::fs::write(path, pretty(&serde_json::to_value(v).unwrap())).unwrap();
    }
}

fn close(a: f64, b: f64) -> bool {
    (a - b).abs() <= TOL
}

fn assert_close(a: Option<f64>, b: f64, what: &str) {
    let a = a.unwrap_or_else(|| panic!("{what}: değer yok"));
    assert!(close(a, b), "{what}: {a} ≠ {b} (±{TOL})");
}

/// Görevdeki "beklenen L ≈ 3.2813" 4 ondalığa yuvarlanmış S_k'ların toplamıdır; tam değer Σ S_k = Σ l·P(L = l) =
/// 3.28115 (Python ile aynı). Bu değer ve "P(10 | ≥3) ≈ 0.0592" (tam S_10/S_3 = 0.059132) için tolerans yuvarlama
/// farkını kapsar; ikisinin tam değeri ayrıca ±5e-5 ile sınanır (rapor §7 notu).
const EXPECTED_L_NETGL: f64 = 3.2813;
const EXPECTED_L_TOL: f64 = 3e-4;

fn assert_rounded(a: Option<f64>, task: f64, exact: f64, what: &str) {
    let a = a.unwrap_or_else(|| panic!("{what}: değer yok"));
    assert!((a - task).abs() <= EXPECTED_L_TOL, "{what}: {a} ≠ {task} (±{EXPECTED_L_TOL})");
    assert!((a - exact).abs() <= TOL, "{what}: tam değer {a} ≠ {exact}");
}

fn assert_expected_l(a: Option<f64>, what: &str) {
    let a = a.unwrap_or_else(|| panic!("{what}: değer yok"));
    assert!((a - EXPECTED_L_NETGL).abs() <= EXPECTED_L_TOL, "{what}: {a} ≠ {EXPECTED_L_NETGL} (±{EXPECTED_L_TOL})");
    assert!((a - 3.28115).abs() <= TOL, "{what}: tam değer {a}");
}

fn supported() -> Vec<String> {
    AppState::from_embedded().models.as_ref().unwrap().models.iter().map(|m| m.model_id.clone()).collect()
}

fn embedded_pairs() -> Vec<(String, String)> {
    AppState::from_embedded().models.as_ref().unwrap().models.iter().map(|m| (m.model_id.clone(), m.params_sha256.clone())).collect()
}

/// Gömülü model dosyaları (`ModelRef.params`): hesaplayıcı eki n ve `day_groups`'u bunlardan okur.
fn embedded_models() -> Vec<borsai_predict::ModelRef> {
    AppState::from_embedded().models.as_ref().unwrap().models.clone()
}

/// Bülten adı kalıbı (th[bm] + 8 hane) çıktıda yok (hijyen).
fn no_bulletin_names(v: &impl serde::Serialize, what: &str) {
    let text = serde_json::to_string(v).unwrap();
    let bytes = text.as_bytes();
    for i in 0..bytes.len().saturating_sub(11) {
        let w = &bytes[i..i + 11];
        if w[0] == b't' && w[1] == b'h' && (w[2] == b'b' || w[2] == b'm') && w[3..11].iter().all(u8::is_ascii_digit) {
            panic!("{what}: bülten adı kalıbı çıktıda");
        }
    }
}

// ---------------------------------------------------------------- K-UI-1: ui_view ayarı

/// Eski config dosyası (alan yok) aynen okunur → SADE; `set_ui_view` yalnız görünümü değiştirir ve kalıcıdır;
/// tanınmayan değer ayarı sıfırlamaz; `set_config` geçersiz değeri reddeder; eski ayar ekranının yükü (alan yok) kabul edilir.
#[test]
fn ui_view_config_backward_compatible() {
    let data = tmp_dir("cfg");
    let old = r#"{"schema_version":"borsai.app_config/1","repo_root":null,"python_path":null,"scores_source":"EMBEDDED"}"#;
    std::fs::write(data.join("config.json"), old).unwrap();
    let (cfg, note) = load_config(&data);
    assert_eq!(note, None, "eski dosya sıfırlanmaz");
    assert_eq!((cfg.ui_view.as_str(), cfg.scores_source.as_str()), (UI_SADE, "EMBEDDED"));
    assert_eq!(AppConfig::default().ui_view, UI_SADE);

    let state = AppState::from_embedded();
    state.attach_data_dir(&data);
    let v = set_ui_view_value(&state, UI_AYRINTILI).unwrap();
    assert_eq!((v.config.ui_view.as_str(), v.config.scores_source.as_str()), (UI_AYRINTILI, "EMBEDDED"));
    assert_eq!(load_config(&data).0.ui_view, UI_AYRINTILI, "kalıcı");
    assert_eq!(set_ui_view_value(&state, "X").unwrap_err().code, "INVALID_ARGUMENT");
    assert_eq!(load_config(&data).0.ui_view, UI_AYRINTILI, "reddedilen değer yazılmaz");
    let back = set_ui_view_value(&state, UI_SADE).unwrap();
    assert_eq!(back.config.ui_view, UI_SADE);

    // tanınmayan değer: ayar sıfırlanmaz, görünüm varsayılana döner
    std::fs::write(data.join("config.json"), old.replace("}", r#","ui_view":"BASKA"}"#)).unwrap();
    let (cfg, note) = load_config(&data);
    assert_eq!((cfg.ui_view.as_str(), note), (UI_SADE, None));
    assert!(!data.join("config.json.bak").exists());

    // eski ayar ekranının yükü (ui_view yok) serde varsayılanıyla kabul edilir; geçersiz değer reddedilir
    let legacy: AppConfig = serde_json::from_str(old).unwrap();
    assert_eq!(legacy.ui_view, UI_SADE);
    assert!(set_config_value(&state, legacy).is_ok());
    let bad = AppConfig { ui_view: "X".into(), ..AppConfig::default() };
    assert_eq!(set_config_value(&state, bad).unwrap_err().code, "INVALID_ARGUMENT");
    let _ = std::fs::remove_dir_all(&data);
}

// ---------------------------------------------------------------- K-UI-8: hesaplayıcı (NETGL, beklenen sayılar)

fn record_doc(ticker: &str, file: &str) -> Value {
    serde_json::from_slice(&std::fs::read(repo_dir().join("registry/records").join(ticker).join(file)).unwrap()).unwrap()
}

fn record_s(rec: &Value, model_id: &str) -> Vec<f64> {
    let c = rec["models"].as_array().unwrap().iter().find(|m| m["model_id"] == json!(model_id)).unwrap();
    serde_json::from_value(c["output"]["S"].clone()).unwrap()
}

fn netgl_inputs() -> (Map<String, Value>, F6Arg, String) {
    let doc: Value = serde_json::from_slice(&std::fs::read(repo_dir().join("registry/inputs/NETGL.json")).unwrap()).unwrap();
    let inputs = borsai_app_lib::commands::form::model_input_fields()
        .map(|f| (f.to_string(), doc["fields"][f]["value"].clone()))
        .collect();
    let rec = record_doc("NETGL", NETGL_RECORD);
    let t = doc["fields"]["first_trading_date"]["value"].as_str().unwrap().to_string();
    (inputs, F6Arg { value: Some(rec["market20"]["f6"].clone()), refusal: None }, t)
}

/// Görev "Beklenen sayılar": S₁…S₁₀, beklenen L 3.2813, medyan 3, P(L = l) tepesi l = 3 (≈ 0.2022, D4'te bozulma);
/// j = 0 yarın tavan 0.8176; j = 3: yarın bozulma 0.3324, beklenen kalan 1.890, P(≥5 | ≥3) 0.4458, P(10 | ≥3) 0.0592;
/// `base_km_last10` S = 0.5, 0.4, 0.32, 0.256, 0.2048, beklenen L 2.2127. Resmi görünüm (record_summary/record_ceiling)
/// ve senaryo (predict_all → ceiling_display/ceiling_summary) aynı sayıları verir.
#[test]
fn calculator_netgl_expected_numbers() {
    let rec = record_doc("NETGL", NETGL_RECORD);
    let s = record_s(&rec, "ceiling_hazard_v0");
    let expected_s = [0.8176, 0.7053, 0.6084, 0.4062, 0.2712, 0.1811, 0.1209, 0.0807, 0.0539, 0.0360];
    for (k, (a, b)) in s.iter().zip(expected_s).enumerate() {
        assert!(close(*a, b), "S_{} = {a} ≠ {b}", k + 1);
    }
    let km = record_s(&rec, "base_km_last10");
    for (a, b) in km.iter().zip([0.5, 0.4, 0.32, 0.256, 0.2048]) {
        assert!(close(*a, b), "base_km_last10 S {a} ≠ {b}");
    }
    let repo = repo_dir();
    let ids = supported();
    let emb = embedded_pairs();
    let loaded = load_repo(&repo);
    let docs = loaded.docs();
    let sc = docs.scores.map(|d| (d, "REPO", "real"));

    // gözlenen seri: j = 3, D4'te bozuldu, L = 3
    let streak = streak_view_in(Some(&repo.join("data/outcomes")), Some("NETGL")).unwrap();
    assert_eq!((streak.j_observed, streak.broken, streak.unlabeled), (Some(3), true, false));
    snapshot("sade_streak_netgl.json", &streak);

    for j in [0usize, 3] {
        // resmi görünüm
        let summary = record_summary_in(&repo, "NETGL", NETGL_RECORD, j, Some(3), &emb, sc, None).unwrap();
        let mut ceiling = record_ceiling_in(&repo, "NETGL", NETGL_RECORD, j, &ids, &emb).unwrap();
        attach_calc(&mut ceiling.display, &embedded_models()); // `record_ceiling` komutu gibi (K-FIX-3)
        let f = summary.rows.iter().find(|r| r.role == "FEATURED").unwrap();
        assert_eq!(f.model_id, "ceiling_hazard_v0");
        assert_expected_l(f.expected_l, "beklenen L");
        assert_eq!((f.median_l, f.mode_l, f.mode_break_day), (Some(3), Some(3), Some(4)));
        assert_close(f.p_mode, 0.2022, "P(L = 3)");
        let rule = summary.rows.iter().find(|r| r.model_id == "base_km_last10").unwrap();
        assert_close(rule.expected_l, 2.2127, "base_km_last10 beklenen L");
        let row = ceiling.display.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap();
        let cond = row.cond.as_ref().unwrap();
        // "yarın da tavan" = P(L ≥ j+1 | L ≥ j) = S_cond[j] (Rust alanı)
        match j {
            0 => {
                assert_close(cond.s_cond[0], 0.8176, "j = 0 yarın tavan");
                assert_eq!(summary.j_source, "NONE");
            }
            _ => {
                let c = f.cond.as_ref().unwrap();
                assert_close(Some(c.p_break_next), 0.3324, "j = 3 yarın bozulma");
                assert_close(Some(c.expected_remaining), 1.890, "j = 3 beklenen kalan");
                assert_close(c.s_cond_5, 0.4458, "P(≥5 | ≥3)");
                assert_rounded(c.s_cond_10, 0.0592, 0.059132, "P(10 | ≥3)");
                assert_close(cond.s_cond[3], 1.0 - 0.3324, "j = 3 yarın tavan");
                assert_eq!(summary.j_source, "OFFICIAL");
            }
        }
        snapshot(&format!("sade_record_summary_netgl_j{j}.json"), &summary);
        snapshot(&format!("sade_record_ceiling_netgl_j{j}.json"), &ceiling);
    }

    // senaryo: predict_all (gömülü modeller) → aynı S; ceiling_display ve ceiling_summary aynı sayılar
    let (inputs, f6, t) = netgl_inputs();
    let runs = predict_all_value(&AppState::from_embedded(), &inputs, &f6, Some(&t)).unwrap();
    let models: Vec<SummaryModel> = runs.iter().map(|r| serde_json::from_value(r.clone()).unwrap()).collect();
    let sv: Vec<SVector> = runs
        .iter()
        .filter(|r| r["status"] == json!("PREDICTED") && (r["kind"] == json!("hazard") || r["kind"] == json!("km")))
        .map(|r| SVector { model_id: r["model_id"].as_str().unwrap().into(), s: serde_json::from_value(r["output"]["S"].clone()).unwrap() })
        .collect();
    snapshot("sade_runs_netgl.json", &runs);
    for j in [0usize, 3] {
        let mut disp = ceiling_display_value(&sv, j, Some("25.52")).unwrap();
        attach_calc(&mut disp, &embedded_models()); // `ceiling_display` komutu gibi (K-FIX-3)
        let row = disp.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap();
        assert_expected_l(Some(row.expected_l), "senaryo beklenen L");
        let c = row.cond.as_ref().unwrap();
        if j == 0 {
            assert_close(c.s_cond[0], 0.8176, "senaryo j = 0 yarın tavan");
        } else {
            assert_close(Some(c.p_break_next), 0.3324, "senaryo j = 3 bozulma");
            assert_close(Some(c.expected_remaining), 1.890, "senaryo beklenen kalan");
            assert_close(c.s_cond[4], 0.4458, "senaryo P(≥5 | ≥3)");
            assert_rounded(c.s_cond[9], 0.0592, 0.059132, "senaryo P(10 | ≥3)");
        }
        let summary = ceiling_summary_value(&models, j, None, false, None, &emb, sc, None, None);
        assert_eq!(summary.rows[0].model_id, "ceiling_hazard_v0");
        assert_eq!(summary.j_source, if j == 0 { "NONE" } else { "HYPOTHETICAL" });
        snapshot(&format!("sade_ceiling_netgl_j{j}.json"), &disp);
        snapshot(&format!("sade_summary_netgl_j{j}.json"), &summary);
    }
}

// ---------------------------------------------------------------- K-FIX-3: geçmiş arzlar ve gün grupları

/// FAZ9_UI_FIX "Beklenen sayılar": "yarın da tavan" (model `cond.S_cond[j]`) NETGL %82 %86 %86 %67×7 (j = 3 ham 0.6676) ve
/// CITAS %92 %94 %94 %85×7 (0.8459); "Geçmiş arzlarda" (base_km_expanding S_{j+1} / S_j, S_0 = 1) bütün kayıtlarda aynı:
/// 0.8182 0.8642 0.9429 0.8030 0.7736 0.8049 0.8182 0.7778 0.8095 0.8235; S × 99 tam sayı → sayımlar 99/81, 81/70, …;
/// `day_groups` g1 = [1], g2 = [2, 3], g3 = [4…10] yalnız gün grubu taşıyan modellerde. Saf display'de ek yok.
#[test]
fn calculator_history_and_day_groups_expected_numbers() {
    let repo = repo_dir();
    let ids = supported();
    let emb = embedded_pairs();
    let models = embedded_models();
    let hist = [0.8182, 0.8642, 0.9429, 0.8030, 0.7736, 0.8049, 0.8182, 0.7778, 0.8095, 0.8235];
    let hist_pct = [82, 86, 94, 80, 77, 80, 82, 78, 81, 82];
    let s99 = [81u64, 70, 66, 53, 41, 33, 27, 21, 17, 14];
    let cases = [
        ("NETGL", NETGL_RECORD, [82, 86, 86, 67, 67, 67, 67, 67, 67, 67], 0.6676),
        ("CITAS", CITAS_RECORD, [92, 94, 94, 85, 85, 85, 85, 85, 85, 85], 0.8459),
    ];
    for (t, file, pct, j3) in cases {
        for j in 0..10usize {
            let mut c = record_ceiling_in(&repo, t, file, j, &ids, &emb).unwrap();
            attach_calc(&mut c.display, &models);
            let row = c.display.rows.iter().find(|r| r.model_id == "ceiling_hazard_v0").unwrap();
            let p = row.cond.as_ref().unwrap().s_cond[j].unwrap();
            assert_eq!((p * 100.0).round() as i32, pct[j], "{t} j = {j} yarın da tavan");
            if j == 3 {
                assert!(close(p, j3), "{t} j = 3 ham {p} ≠ {j3}");
            }
            let calc = c.display.calc.as_ref().unwrap();
            assert_eq!(calc.j, j);
            let h = &calc.history;
            assert_eq!((h.rule_id.as_str(), h.in_rows), (CALC_RULE_ID, true));
            assert_close(h.p_next, hist[j], &format!("{t} j = {j} geçmiş arzlarda"));
            assert_eq!((h.p_next.unwrap() * 100.0).round() as i32, hist_pct[j], "{t} j = {j} ekranda");
            assert_eq!(h.n_train, Some(99));
            assert_eq!((h.n_at_j, h.n_next), (Some(if j == 0 { 99 } else { s99[j - 1] }), Some(s99[j])), "{t} j = {j} sayım");
            assert_eq!(h.s_cond.len(), 10);
            assert!(h.s_cond[..j].iter().all(Option::is_none));
            assert_close(h.s_cond[j], hist[j], "s_cond[j]");
            let g = calc.day_groups.iter().find(|g| g.model_id == "ceiling_hazard_v0").unwrap();
            assert_eq!(g.groups, vec![vec![1], vec![2, 3], vec![4, 5, 6, 7, 8, 9, 10]]);
            assert!(calc.day_groups.iter().all(|g| g.model_id != CALC_RULE_ID), "kuralda gün grubu yok");
            let text = serde_json::to_string(calc).unwrap();
            assert!(!text.contains("tickers"), "eğitim arz listesi dönmez");
            if t == "NETGL" && j == 6 {
                snapshot("sade_record_ceiling_netgl_j6.json", &c);
            }
        }
    }
    // senaryo yolu (predict_all → ceiling_display + ek): aynı sayılar, NETGL j = 3
    let (inputs, f6, t) = netgl_inputs();
    let runs = predict_all_value(&AppState::from_embedded(), &inputs, &f6, Some(&t)).unwrap();
    let sv: Vec<SVector> = runs
        .iter()
        .filter(|r| r["status"] == json!("PREDICTED") && (r["kind"] == json!("hazard") || r["kind"] == json!("km")))
        .map(|r| SVector { model_id: r["model_id"].as_str().unwrap().into(), s: serde_json::from_value(r["output"]["S"].clone()).unwrap() })
        .collect();
    let mut disp = ceiling_display_value(&sv, 3, Some("25.52")).unwrap();
    assert!(disp.calc.is_none() && serde_json::to_value(&disp).unwrap().get("calc").is_none(), "saf display'de ek yok");
    attach_calc(&mut disp, &models);
    let h = &disp.calc.as_ref().unwrap().history;
    assert_close(h.p_next, 0.8030, "senaryo j = 3 geçmiş arzlarda");
    assert_eq!((h.n_at_j, h.n_next), (Some(66), Some(53)));
    // kural satırı yoksa: in_rows false, değer ve sayım yok; gün grupları yine okunur
    let only = vec![sv.iter().find(|v| v.model_id == "ceiling_hazard_v0").unwrap().clone()];
    let d = ceiling_display_value(&only, 3, None).unwrap();
    let c = calc_view_value(&d.rows, 3, &models);
    assert!(!c.history.in_rows && c.history.p_next.is_none() && c.history.n_at_j.is_none() && c.history.s_cond.is_empty());
    assert_eq!(c.day_groups.len(), 1);
    // S × n tam sayı değilse (1e-9) yalnız oran, sayım null
    let bad = vec![SVector { model_id: CALC_RULE_ID.into(), s: vec![0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05] }];
    let d = ceiling_display_value(&bad, 0, None).unwrap();
    let c = calc_view_value(&d.rows, 0, &models);
    assert!(c.history.in_rows && c.history.n_train == Some(99) && c.history.n_at_j.is_none() && c.history.n_next.is_none());
    assert_close(c.history.p_next, 0.8, "oran yine var");
    // tanımsız j (S_j = 0 → cond yok): değer yok
    let zero = vec![SVector { model_id: CALC_RULE_ID.into(), s: vec![0.0; 10] }];
    let d = ceiling_display_value(&zero, 3, None).unwrap();
    let c = calc_view_value(&d.rows, 3, &models);
    assert!(c.history.in_rows && c.history.p_next.is_none() && c.history.n_at_j.is_none());
}

// ---------------------------------------------------------------- K-UI-4: headline_gate

fn gate(g: &HeadlineGate, m: &str, o: &str, h: Option<&str>) -> GateEntry {
    g.entries.iter().find(|e| e.model_id == m && e.output == o && e.horizon_or_k.as_deref() == h).cloned().unwrap()
}

/// Bugünkü dosyalarla K-UI-4 beklentisi: ceiling_hazard_v0 öne çıkar (iki birincil hücre de dosyada "geçiyor"); V1.5 D5
/// getirisi öne çıkar, D10 arz üstü olasılığı (birincil değil) çıkmaz; post_d1 birincil RPS hücresi n < 10 → çıkmaz;
/// break_floor_v0 F1 `promotion.promoted` → çıkar, etiket dosyadan. Ön uçta liste yok; kural Rust'ta.
#[test]
fn headline_gate_real_files() {
    let loaded = load_repo(&repo_dir());
    let g = headline_gate_value(&loaded.docs());
    let c = gate(&g, "ceiling_hazard_v0", "S", None);
    assert!(c.is_primary && c.featured && c.verdicts.len() == 2, "{c:?}");
    assert_eq!(c.primary_rules, ["base_km_last10", "base_km_expanding"]);
    let d5 = gate(&g, "v1_5_h99", "return", Some("D5"));
    assert!(d5.is_primary && d5.featured && d5.verdicts.len() == 1);
    for h in ["D1", "D3", "D10"] {
        let e = gate(&g, "v1_5_h99", "return", Some(h));
        assert!(!e.is_primary && !e.featured && e.verdicts.is_empty(), "{h}");
    }
    for h in ["D1", "D3", "D5", "D10"] {
        assert!(!gate(&g, "v1_5_h99", "p_up", Some(h)).featured, "p_up {h}");
    }
    let p = gate(&g, "post_d1_hazard_v0", "S_cond", None);
    assert!(p.is_primary && !p.featured && p.verdicts.is_empty() && p.status == "OK", "{p:?}");
    assert_eq!(p.live_n, Some(0));
    let b = gate(&g, "break_floor_v0", "p_floor", Some("F1"));
    assert!(b.is_primary && b.featured, "{b:?}");
    assert_eq!(b.label.as_deref(), Some("ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0"));
    assert!(!gate(&g, "break_floor_v0", "p_floor", Some("F2")).featured);
    assert_eq!(g.entries.iter().filter(|e| e.featured).count(), 3);

    // dosyalar yokken (bağımsız mod) hiçbir çıktı öne çıkmaz
    let empty = borsai_app_lib::commands::sade::Docs { scores: None, scores_source: None, post_d1: None, brk: None, oot: None };
    let g0 = headline_gate_value(&empty);
    assert!(g0.entries.iter().all(|e| !e.featured && e.status == "NO_FILE"));
    snapshot("sade_gate.json", &g);
}

/// Mutasyon: birincil hücrenin verdict'i "geçiyor" değilse ya da bir birincil kural satırı eksikse öne çıkmaz.
#[test]
fn headline_gate_follows_file_verdicts() {
    let loaded = load_repo(&repo_dir());
    let mut scores = loaded.scores.as_ref().unwrap().0.clone();
    let cells = scores["models"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|m| m["model_id"] == json!("ceiling_hazard_v0"))
        .unwrap()["backtest"]["cells"]
        .as_array_mut()
        .unwrap();
    let i = cells.iter().position(|c| c["label"] == json!("birincil") && c["rule_id"] == json!("base_km_last10")).unwrap();
    cells[i]["verdict"] = json!("ayırt edilemiyor");
    let docs = borsai_app_lib::commands::sade::Docs { scores: Some(&scores), scores_source: Some("REPO"), post_d1: None, brk: None, oot: None };
    let e = gate(&headline_gate_value(&docs), "ceiling_hazard_v0", "S", None);
    assert!(e.is_primary && !e.featured, "bir birincil satır geçmiyorsa öne çıkmaz");
    cells_remove(&mut scores, i);
    let docs = borsai_app_lib::commands::sade::Docs { scores: Some(&scores), scores_source: Some("REPO"), post_d1: None, brk: None, oot: None };
    let e = gate(&headline_gate_value(&docs), "ceiling_hazard_v0", "S", None);
    assert!(!e.featured && e.verdicts.len() == 1, "eksik birincil satır → öne çıkmaz");
}

fn cells_remove(scores: &mut Value, i: usize) {
    scores["models"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|m| m["model_id"] == json!("ceiling_hazard_v0"))
        .unwrap()["backtest"]["cells"]
        .as_array_mut()
        .unwrap()
        .remove(i);
}

// ---------------------------------------------------------------- monitor_view

/// Görev "Monitör sayımları" ve "Makine kayıtları" ve "Canlı sınıflar": 7 arz, seride 0; D10'da arz altında 2 (NETGL R_10
/// ≈ −0.3617, BKRGY); tabanda kırılma 3 (BKRGY b = 1, KPEKS b = 6, NETGL b = 4); F1 p_floor tablosu; TKNKA D10'da arz
/// altına inemez; NETGL kırpma uyarısı; sınıflar model başına (NETGL: tavan geç kayıt, getiri canlı).
#[test]
fn monitor_view_real_repo() {
    let repo = repo_dir();
    let loaded = load_repo(&repo);
    let v: MonitorView = monitor_view_in(&repo, &loaded.docs(), &supported()).unwrap();
    let c = &v.counts;
    assert_eq!((c.n_ipos, c.n_in_streak, c.n_d10_known, c.n_d10_below, c.n_break_known, c.n_break_floor), (7, 0, 7, 2, 7, 3));
    assert_eq!((c.n_impossible_d10, c.n_pre_listing_records, c.n_machine_records, c.n_post_d1_records), (1, 7, 7, 0));
    assert_eq!((c.first_d1.as_deref(), c.last_d1.as_deref()), (Some("2026-08-18"), Some("2026-09-17")));
    assert_eq!(c.n_frozen, 7);
    assert_eq!(c.n_payda, c.n_frozen + c.n_out_of_scope + c.n_skipped);
    assert_eq!(v.data_date.as_deref(), Some("2026-09-30"));
    let order: Vec<&str> = v.rows.iter().map(|r| r.ticker.as_str()).collect();
    assert_eq!(order, ["NETGL", "BKRGY", "INTET", "KPEKS", "TKNKA", "VEYAS", "CITAS"], "D1 azalan");
    let row = |t: &str| v.rows.iter().find(|r| r.ticker == t).unwrap();
    let below: Vec<&str> = v.rows.iter().filter(|r| r.r10_below == Some(true)).map(|r| r.ticker.as_str()).collect();
    assert_eq!(below, ["NETGL", "BKRGY"]);
    let netgl = row("NETGL");
    assert!(netgl.r10.as_deref().unwrap().starts_with("-0.3616771159"));
    assert_eq!((netgl.ipo_price.as_deref(), netgl.d10_close.as_deref()), (Some("25.52"), Some("16.29")));
    assert_eq!(netgl.shares_offered.as_deref(), Some("87500000"));
    assert_eq!((netgl.streak.j_observed, netgl.streak.realized_l, netgl.streak.in_streak), (Some(3), Some(3), false));
    let floor: Vec<(&str, u64)> = v
        .rows
        .iter()
        .filter(|r| r.break_info.as_ref().and_then(|b| b.b_floor) == Some(1))
        .map(|r| (r.ticker.as_str(), r.break_info.as_ref().unwrap().b.unwrap()))
        .collect();
    assert_eq!(floor, [("NETGL", 4), ("BKRGY", 1), ("KPEKS", 6)]);
    for (t, p) in [("BKRGY", 0.5433), ("KPEKS", 0.5389), ("NETGL", 0.4991), ("INTET", 0.1418), ("CITAS", 0.1383), ("TKNKA", 0.1382), ("VEYAS", 0.1376)] {
        assert_close(row(t).break_info.as_ref().unwrap().p_floor_f1, p, t);
    }
    assert_close(netgl.break_info.as_ref().unwrap().p_floor_f2, 0.3043, "NETGL F2");
    assert_eq!(netgl.break_info.as_ref().unwrap().warnings, ["B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"]);
    let impossible: Vec<&str> =
        v.rows.iter().filter(|r| r.break_info.as_ref().and_then(|b| b.impossible_d10) == Some(true)).map(|r| r.ticker.as_str()).collect();
    assert_eq!(impossible, ["TKNKA"]);
    // kayıttan beklenen ve medyan seri, P(≥ 5)
    let ce = netgl.ceiling.as_ref().unwrap();
    assert_expected_l(ce.expected_l, "NETGL beklenen");
    assert_eq!(ce.median_l, Some(3));
    assert_close(ce.p_ge5, 0.2712, "NETGL P(≥5)");
    let veyas = row("VEYAS").ceiling.as_ref().unwrap();
    assert_eq!((veyas.status.as_deref(), veyas.refusal_code.as_deref(), veyas.expected_l), (Some("REFUSED"), Some("F3_MISSING"), None));
    // sınıflar (scores.json canlı satırları)
    let class = |t: &str, m: &str| row(t).classes.iter().find(|c| c.model_id == m).unwrap().clone();
    let count = |m: &str, cls: &str, status: &str| {
        v.rows.iter().filter(|r| r.classes.iter().any(|c| c.model_id == m && c.class.as_deref() == Some(cls) && c.status.as_deref() == Some(status))).count()
    };
    assert_eq!((count("ceiling_hazard_v0", "LATE_RECORD", "SCORED"), count("ceiling_hazard_v0", "LATE_RECORD", "REFUSED")), (6, 1));
    assert_eq!(count("ceiling_hazard_v0", "LIVE", "SCORED"), 0);
    assert_eq!((count("v1_5_h99", "LIVE", "SCORED"), count("v1_5_h99", "LATE_RECORD", "SCORED"), count("v1_5_h99", "LATE_RECORD", "REFUSED")), (1, 5, 1));
    assert_eq!(class("NETGL", "v1_5_h99").class.as_deref(), Some("LIVE"));
    assert_eq!(class("NETGL", "v1_5_h99").record_push_proof_created_at.as_deref(), Some("2026-09-16T11:32:27Z"));
    assert_eq!(class("NETGL", "ceiling_hazard_v0").class.as_deref(), Some("LATE_RECORD"));
    assert_eq!(class("VEYAS", "ceiling_hazard_v0").status.as_deref(), Some("REFUSED"));
    assert!(v.rows.iter().all(|r| class(&r.ticker, "break_floor_v0").class.as_deref() == Some("RETRO")));
    // rejim (C4: D_1 ≥ 2026-09-16)
    assert_eq!(v.regime.as_ref().map(|r| (r.tag.as_str(), r.start_d1.as_deref())), Some(("FON_KRIZI_2026", Some("2026-09-16"))));
    let tagged: Vec<&str> = v.rows.iter().filter(|r| !r.regime_tags.is_empty()).map(|r| r.ticker.as_str()).collect();
    assert_eq!(tagged, ["NETGL"]);
    // olay akışı: yeni olan üstte; kırılma ve D10 olayları dosyalardan
    assert!(v.events.windows(2).all(|w| w[0].at >= w[1].at));
    assert!(v.events.iter().any(|e| e.kind == "BREAK" && e.ticker.as_deref() == Some("NETGL") && e.at == "2026-09-22"));
    let machine = v.events.iter().find(|e| e.kind == "MACHINE").unwrap();
    assert_eq!((machine.tickers.len(), machine.ticker.clone(), machine.class.as_deref()), (7, None, Some("RETRO")), "aynı gün tek satır");
    assert!(v.events.iter().any(|e| e.kind == "MODEL_FROZEN" && e.model_id.as_deref() == Some("break_floor_v0")));
    assert!(v.events.iter().any(|e| e.kind == "REGIME" && e.at == "2026-09-16"));
    assert!(v.events.iter().any(|e| e.kind == "D10" && e.ticker.as_deref() == Some("NETGL") && e.close_raw.as_deref() == Some("16.29")));
    no_bulletin_names(&v, "monitor_view");
    snapshot("sade_monitor.json", &v);
}

/// arz_view (NETGL): koridor, kayıttaki P_close_ceiling ve V1.5 fiyatları, getiri satırları (gerçekleşen R_h metni), günlük.
#[test]
fn arz_view_real_repo() {
    let repo = repo_dir();
    let loaded = load_repo(&repo);
    let a = arz_view_in(&repo, "NETGL", &loaded.docs(), &supported()).unwrap();
    assert_eq!(a.row.record_file.as_deref(), Some(NETGL_RECORD));
    assert_close(a.p_close_ceiling[0], 0.8176, "P_close_ceiling D1");
    let closes: Vec<&str> = a.row.days.iter().filter_map(|d| d.close_raw.as_deref()).collect();
    assert_eq!(closes, ["28.06", "30.86", "33.94", "30.56", "27.52", "24.78", "22.32", "20.1", "18.09", "16.29"]);
    let ceil: Vec<Option<u8>> = a.row.days.iter().map(|d| d.ceiling_close).collect();
    assert_eq!(ceil, [Some(1), Some(1), Some(1), Some(0), Some(0), Some(0), Some(0), Some(0), Some(0), Some(0)]);
    let r = a.row.returns.as_ref().unwrap();
    let d5 = r.rows.iter().find(|x| x.horizon == "D5").unwrap();
    assert_close(d5.ret, 0.2552, "D5 getiri");
    assert_close(d5.price, 32.0315, "D5 fiyat");
    assert!(d5.realized.as_deref().unwrap().starts_with("0.0783699059"));
    let d10 = r.rows.iter().find(|x| x.horizon == "D10").unwrap();
    assert_close(d10.p_up, 0.6023, "D10 arz üstü");
    assert!(a.post_d1_files.is_empty());
    assert!(a.log.windows(2).all(|w| w[0].at <= w[1].at), "günlük eskiden yeniye");
    let kinds: Vec<&str> = a.log.iter().map(|e| e.kind).collect();
    for k in ["LEGACY_RECORD", "STREAK", "RECORD", "BREAK", "D10", "MODEL_FROZEN", "MACHINE"] {
        assert!(kinds.contains(&k), "{k} yok: {kinds:?}");
    }
    assert!(arz_view_in(&repo, "../x", &loaded.docs(), &supported()).is_err());
    // K-FIX-4: işlem sayısı metni aynen (D1 17885, D2 28445), göreli yükseklik = gün / on günün en büyüğü (D9 241603 → 1)
    let tc: Vec<&str> = a.row.days.iter().filter_map(|d| d.trade_count_raw.as_deref()).collect();
    assert_eq!(tc, ["17885", "28445", "54010", "42067", "3205", "56449", "5119", "3261", "241603", "47414"]);
    let rel: Vec<f64> = a.row.days.iter().map(|d| d.trade_count_rel.unwrap()).collect();
    assert_eq!(rel[8], 1.0, "en büyük gün 1");
    assert_close(Some(rel[0]), 17885.0 / 241603.0, "D1 oranı");
    assert!(rel.iter().all(|r| (0.0..=1.0).contains(r)));
    no_bulletin_names(&a, "arz_view");
    snapshot("sade_arz_netgl.json", &a);
}

/// `read_days` (K-FIX-4): sütun yoksa ya da sayı yoksa alanlar null (çubuk çizilmez, tire); OK olmayan günün sayısı okunmaz.
#[test]
fn read_days_trade_counts_optional() {
    let dir = tmp_dir("days");
    std::fs::create_dir_all(dir.join("data/outcomes")).unwrap();
    let head = "h,session_date,close_raw,upper_limit_raw,reference_raw,ceiling_close,R_h,status";
    std::fs::write(dir.join("data/outcomes/AAAA.csv"), format!("{head}\n1,2026-01-05,11,11,10,1,0.1,OK\n")).unwrap();
    let (days, _) = read_days(&dir, "AAAA").unwrap().unwrap();
    assert!(days.iter().all(|d| d.trade_count_raw.is_none() && d.trade_count_rel.is_none()));
    let head2 = "h,session_date,close_raw,upper_limit_raw,reference_raw,trade_count_raw,ceiling_close,R_h,status";
    std::fs::write(
        dir.join("data/outcomes/BBBB.csv"),
        format!("{head2}\n1,2026-01-05,11,11,10,400,1,0.1,OK\n2,2026-01-06,12,12.1,11,100,0,,OK\n3,2026-01-07,,,,900,,,PENDING\n"),
    )
    .unwrap();
    let (days, _) = read_days(&dir, "BBBB").unwrap().unwrap();
    assert_eq!((days[0].trade_count_raw.as_deref(), days[0].trade_count_rel), (Some("400"), Some(1.0)));
    assert_eq!((days[1].trade_count_raw.as_deref(), days[1].trade_count_rel), (Some("100"), Some(0.25)));
    assert_eq!((days[2].trade_count_raw.as_deref(), days[2].trade_count_rel), (None, None), "OK olmayan gün");
    assert_eq!(days[3].trade_count_rel, None);
    let _ = std::fs::remove_dir_all(&dir);
}

/// K-FIX-6: pencere ayarı (tauri.conf.json) lib sabitleriyle aynı: 1440 × 900 ortada, en küçük 1024 × 680.
#[test]
fn window_config_k_fix_6() {
    let conf: Value = serde_json::from_str(&std::fs::read_to_string(app_dir().join("src-tauri/tauri.conf.json")).unwrap()).unwrap();
    let w = &conf["app"]["windows"][0];
    assert_eq!((w["width"].as_f64(), w["height"].as_f64()), (Some(borsai_app_lib::DEFAULT_WINDOW.0), Some(borsai_app_lib::DEFAULT_WINDOW.1)));
    assert_eq!((w["minWidth"].as_f64(), w["minHeight"].as_f64()), (Some(borsai_app_lib::MIN_WINDOW.0), Some(borsai_app_lib::MIN_WINDOW.1)));
    assert_eq!(w["center"], json!(true));
    assert_eq!((borsai_app_lib::DEFAULT_WINDOW, borsai_app_lib::MIN_WINDOW), ((1440.0, 900.0), (1024.0, 680.0)));
}

// ---------------------------------------------------------------- break_view

/// NETGL: F1 0.4991, F2 0.3043; karşılaştırıcılar (taban kırılması sınıfı 0.5429, `@ZERO` 0.3049, ürün NOT_AVAILABLE);
/// katsayılar sha denetimli (b_floor +0.987, b_turnover +0.063, sabit −1.001, C = 1); b_turnover kırpıldı (kullanılan
/// −2.179, ham −2.267); D10 yapısal sıfır yok. TKNKA: D10'da arz altına inemez. Kart: backtest_info ve promotion.
#[test]
fn break_view_real_files() {
    let repo = repo_dir();
    let loaded = load_repo(&repo);
    let b = break_view_in(&repo, "NETGL", loaded.brk.as_ref()).unwrap();
    assert_eq!(b.status, "OK");
    assert_eq!((b.b, b.l, b.b_floor, b.break_date.as_deref()), (Some(4), Some(3), Some(1), Some("2026-09-22")));
    assert_close(b.p_f1, 0.4991, "F1");
    assert_close(b.p_f2, 0.3043, "F2");
    assert_close(b.zero_f1, 0.3049, "@ZERO F1");
    assert_close(b.by_type_f1, 0.5429, "taban kırılması sınıf oranı");
    assert_eq!(b.product_status.as_deref(), Some("NOT_AVAILABLE"));
    let f = |n: &str| b.features.iter().find(|x| x.name == n).unwrap().clone();
    let fl = f("b_floor");
    assert_eq!((fl.close_raw.as_deref(), fl.lower_limit_raw.as_deref(), fl.value_f1), (Some("30.56"), Some("30.56"), Some(1.0)));
    assert_close(fl.coef_f1, 0.9867, "b_floor katsayı");
    let tu = f("b_turnover");
    assert_close(tu.coef_f1, 0.0629, "b_turnover katsayı");
    assert_close(tu.value_f1, -2.1789, "kırpılmış değer");
    assert_close(tu.ln_value, -2.2666, "ham ln");
    assert_eq!(tu.clipped_f1, Some(true));
    assert!(tu.ratio_raw.as_deref().unwrap().starts_with("0.1036686"));
    let h1 = b.heads.iter().find(|h| h.head == "F1").unwrap();
    assert_close(h1.intercept, -1.0007, "sabit");
    assert_eq!((h1.c.clone(), h1.training_n, h1.training_events), (Some(json!(1.0)), Some(82), Some(25)));
    assert_eq!((b.structural_min10.as_deref(), b.structural_p.as_deref(), b.impossible_d10), (Some("16.29"), Some("25.52"), Some(false)));
    assert_eq!(b.warnings, ["B_TURNOVER_CLIPPED_TO_TRAINING_P05_P95"]);
    assert_eq!((b.class.as_deref(), b.live_n_scored, b.live_n_retro), (Some("RETRO"), Some(0), Some(7)));
    let card = b.card.as_ref().unwrap();
    assert_eq!((card.promoted, card.promotion_stage), (Some(true), Some(1)));
    let info = card.backtest_info.as_ref().unwrap();
    assert_close(info["F1_product"]["diff"].as_f64(), -0.19038, "F1 − ürün");
    assert_close(info["F1_product"]["ci95"][0].as_f64(), -0.25203, "F1 − ürün alt");
    assert_close(info["F1_product"]["ci95"][1].as_f64(), -0.12470, "F1 − ürün üst");
    assert_eq!((info["F1_product"]["n"].as_u64(), info["F1_product"]["n_months"].as_u64()), (Some(69), Some(21)));
    assert_close(info["F1_zero"]["diff"].as_f64(), -0.02808, "F1 − @ZERO");
    assert_close(info["F1_zero"]["ci95"][0].as_f64(), -0.04528, "F1 − @ZERO alt");
    assert_close(info["F1_zero"]["ci95"][1].as_f64(), -0.00740, "F1 − @ZERO üst");
    no_bulletin_names(&b, "break_view");
    snapshot("sade_break_netgl.json", &b);
    let t = break_view_in(&repo, "TKNKA", loaded.brk.as_ref()).unwrap();
    assert_eq!((t.impossible_d10, t.b_floor), (Some(true), Some(0)));
    assert_close(t.by_type_f1, 0.1277, "taban üstü sınıf oranı");
    snapshot("sade_break_tknka.json", &t);
}

/// Katsayı dosyasının sha'sı makine kaydındakiyle tutmazsa kart kapanır (hiçbir değer dönmez); dosya yoksa da.
#[test]
fn break_view_closes_on_sha_mismatch() {
    let repo = repo_dir();
    let tmp = tmp_dir("brk");
    let copy = |rel: &str| {
        let dst = tmp.join(rel);
        std::fs::create_dir_all(dst.parent().unwrap()).unwrap();
        std::fs::copy(repo.join(rel), &dst).unwrap();
    };
    let machine = std::fs::read_dir(repo.join("registry/post_break/NETGL")).unwrap().flatten().next().unwrap().file_name();
    copy(&format!("registry/post_break/NETGL/{}", machine.to_string_lossy()));
    let none = break_view_in(&tmp, "NETGL", None).unwrap();
    assert_eq!(none.status, "NO_MODEL_FILE");
    assert!(none.p_f1.is_none() && none.features.is_empty());
    copy("models/break_floor_v0.json");
    assert_eq!(break_view_in(&tmp, "NETGL", None).unwrap().status, "OK");
    let p = tmp.join("models/break_floor_v0.json");
    let mut text = std::fs::read_to_string(&p).unwrap();
    text.push('\n');
    std::fs::write(&p, text).unwrap();
    let bad = break_view_in(&tmp, "NETGL", None).unwrap();
    assert_eq!(bad.status, "SHA_MISMATCH");
    assert!(bad.p_f1.is_none() && bad.features.is_empty() && bad.heads.is_empty() && bad.card.is_none());
    assert_eq!(break_view_in(&tmp, "BKRGY", None).unwrap().status, "NO_RECORD");
    let _ = std::fs::remove_dir_all(&tmp);
}

// ---------------------------------------------------------------- perf_view

/// Görev "Model performansı satırları": dört satır dosyadaki gibi (fark, aralık, n, kazanç/kayıp/eşit, verdict aynen) +
/// kırılma backtest_info iki satırı (hükümsüz, etiket dosyadan). Üç terazi model başına; canlı satırlar 7 arz.
#[test]
fn perf_view_real_files() {
    let repo = repo_dir();
    let loaded = load_repo(&repo);
    let p: PerfView = perf_view_value(&loaded.docs());
    let expected = [
        ("ceiling_hazard_v0", "RPS", "base_km_last10", -0.04956, [-0.07515, -0.02186], 87, (52, 35, 0), "geçiyor", true),
        ("ceiling_hazard_v0", "RPS", "base_km_expanding", -0.05686, [-0.08326, -0.02865], 87, (59, 28, 0), "geçiyor", true),
        ("v1_5_h99", "MAE", "base_train_median", -0.08387, [-0.13432, -0.03211], 87, (58, 29, 0), "geçiyor", true),
        ("v1_5_h99", "Brier", "base_rate", -0.03910, [-0.07562, 0.00234], 81, (52, 29, 0), "ayırt edilemiyor", false),
    ];
    assert_eq!(p.rows.len(), 6);
    for (i, (m, metric, rule, diff, ci, n, wlt, verdict, featured)) in expected.iter().enumerate() {
        let r = &p.rows[i];
        assert_eq!((r.model_id.as_str(), r.metric.as_deref(), r.rule_id.as_deref()), (*m, Some(*metric), Some(*rule)), "satır {i}");
        assert_close(r.diff.as_ref().and_then(Value::as_f64), *diff, "fark");
        assert_close(r.ci95.as_ref().and_then(|c| c[0].as_f64()), ci[0], "aralık alt");
        assert_close(r.ci95.as_ref().and_then(|c| c[1].as_f64()), ci[1], "aralık üst");
        assert_eq!((r.n, r.wins, r.losses, r.ties), (Some(*n), Some(wlt.0), Some(wlt.1), Some(wlt.2)));
        assert_eq!(r.verdict.as_deref(), Some(*verdict));
        assert_eq!(r.featured, *featured, "satır {i}");
    }
    assert_eq!(p.rows[3].label.as_deref(), Some("keşif"));
    let (b1, b2) = (&p.rows[4], &p.rows[5]);
    assert_eq!((b1.rule_id.as_deref(), b2.rule_id.as_deref()), (Some("PRODUCT_BREAK_FLOOR"), Some("break_floor_v0@ZERO")));
    assert_close(b1.diff.as_ref().and_then(Value::as_f64), -0.19038, "F1 − ürün");
    assert_close(b2.diff.as_ref().and_then(Value::as_f64), -0.02808, "F1 − @ZERO");
    assert_eq!((b1.n, b1.n_months, b1.verdict.clone()), (Some(69), Some(21), None));
    assert_eq!(b1.file_label.as_deref(), Some("backtest'te geçiyor (tasarıma maruz)"));
    // K-FIX-5: "ayırt edilemiyor" (v1_5_h99 D10 Brier) ile "geçemiyor" ayrı; hükümsüz 2 (ürün ve @ZERO)
    let c = &p.counts;
    assert_eq!((c.n_rows, c.n_pass, c.n_undecided, c.n_fail, c.n_other, c.n_no_verdict), (6, 3, 1, 0, 0, 2));
    assert_eq!(c.n_pass + c.n_undecided + c.n_fail + c.n_other + c.n_no_verdict, c.n_rows);
    // üç terazi (asla toplanmaz): model başına ayrı alanlar
    let sc = |m: &str| p.scales.iter().find(|s| s.model_id == m).unwrap().clone();
    assert_eq!(p.scales.iter().map(|s| s.model_id.as_str()).collect::<Vec<_>>(), ["ceiling_hazard_v0", "v1_5_h99", "post_d1_hazard_v0", "break_floor_v0"]);
    assert_eq!(sc("ceiling_hazard_v0").live.n_live, Some(0));
    assert_eq!((sc("v1_5_h99").live.n_live, sc("v1_5_h99").live.n_late, sc("v1_5_h99").live.n_refused), (Some(1), Some(5), Some(1)));
    assert_eq!(sc("ceiling_hazard_v0").oot.block.as_deref(), Some("oot_pre_h99_all"));
    assert_eq!(sc("ceiling_hazard_v0").oot.status, "OK");
    assert_eq!(sc("post_d1_hazard_v0").oot.n, Some(104));
    assert_eq!(sc("break_floor_v0").oot.status, "NO_TEST");
    assert_eq!(sc("break_floor_v0").backtest_label.as_deref(), Some("backtest'te geçiyor (tasarıma maruz)"));
    assert_eq!((sc("break_floor_v0").live.n_scored, sc("break_floor_v0").live.n_retro), (Some(0), Some(7)));
    // canlı satırlar: 7 arz; NETGL getiri canlı, tavan geç kayıt, gerçekleşen L = 3
    assert_eq!(p.live_rows.len(), 7);
    let n = p.live_rows.iter().find(|r| r.ticker == "NETGL").unwrap();
    assert_eq!(n.d5.as_ref().unwrap().class.as_deref(), Some("LIVE"));
    assert_eq!(n.ceiling.as_ref().unwrap().class.as_deref(), Some("LATE_RECORD"));
    assert_eq!(n.ceiling.as_ref().unwrap().realized, Some(json!(3)));
    assert_expected_l(n.ceiling.as_ref().unwrap().predicted, "canlı satır beklenen L");
    assert_eq!(n.break_class.as_deref(), Some("RETRO"));
    assert_eq!((p.min_n_metric, p.min_n_verdict, p.n_production), (10, 30, 4));
    snapshot("sade_perf.json", &p);
}

/// Bağımsız mod: yalnız gömülü scores.json ile geçmiş test satırları ve kapı çalışır; öbür bölümler boş (repo modu ister).
#[test]
fn perf_view_embedded_only() {
    let scores: Value = serde_json::from_str(borsai_app_lib::embedded::SCORES_JSON.expect("gömülü scores.json")).unwrap();
    let docs = borsai_app_lib::commands::sade::Docs { scores: Some(&scores), scores_source: Some("EMBEDDED"), post_d1: None, brk: None, oot: None };
    let p = perf_view_value(&docs);
    assert_eq!(p.rows.len(), 4, "kırılma satırları repo modu ister");
    assert!(!p.has_break && !p.has_post_d1 && !p.has_oot);
    assert_eq!(p.scales.iter().find(|s| s.model_id == "break_floor_v0").unwrap().backtest_status, "NO_FILE");
}


// ---------------------------------------------------------------- FAZ9_SNAPSHOT: kişisel modda gömülü sicil anlık görüntüsü

/// K-SNAP-2/3: kişisel modda Monitör, Analiz (arz, seri, kayıt kartı, koşullu görünüm, ham kayıt), kırılma kartı, Sicil ve
/// Performans gömülü anlık görüntüden okunur ve repo modundaki görünümlerle aynıdır; yalnız `repo_root`, künye (`snapshot`)
/// ve `git status` (anlık görüntüde derleme anınınki, git çağrılmaz) ayrıdır. Kayıt kanıtı (kaydı ekleyen commit, push
/// kanıtı) anlık görüntüde de dolu. Skor kaynağı iki tarafta da gömülü (`EMBEDDED`).
#[test]
fn snapshot_mode_views_equal_repo_views() {
    use borsai_app_lib::commands::ceiling::record_summary_value;
    use borsai_app_lib::commands::registry::{read_record_json_value, record_ceiling_value, registry_view_value};
    use borsai_app_lib::commands::registry_snapshot::frozen_git;
    use borsai_app_lib::commands::sade::{arz_streak_value, arz_view_value, load, monitor_view_value};
    use borsai_app_lib::commands::sade_break::break_view_value;

    let personal = AppState::from_embedded();
    personal.attach_data_dir(&tmp_dir("snapmode"));
    personal.prepare_snapshot();
    let root = personal.read_root().expect("anlık görüntü");
    assert_eq!(root.snapshot.as_ref().map(|s| s.status), Some("READY"));
    let frozen = frozen_git(&root.root).expect("anlık görüntü kökü tanınır");
    assert!(frozen_git(&repo_dir()).is_none(), "repo anlık görüntü sayılmaz");
    let repo = AppState::from_embedded().with_repo_for_tests(&tmp_dir("snapmode_repo"), &repo_dir());
    repo.runtime.lock().unwrap().config.scores_source = "EMBEDDED".into();

    // Monitör (K-SNAP-3: künye, derleme ve son sonuç)
    let mut ms = monitor_view_value(&personal).unwrap();
    let mr = monitor_view_value(&repo).unwrap();
    let info = ms.snapshot.take().expect("monitör künyesi");
    assert_eq!((info.status, info.n_files, info.build_sha7.len()), ("READY", borsai_app_lib::embedded::SNAPSHOT_FILES.len(), 7));
    assert_eq!(info.last_session, mr.data_date, "son sonuç = data/outcomes'taki en geç seans");
    assert!(mr.snapshot.is_none());
    assert_eq!(ms.git_status, frozen.status(&["registry", "data"]));
    ms.git_status = mr.git_status.clone();
    assert_eq!(ms, mr);
    assert_eq!(mr.rows.len(), 7, "takipteki 7 arz");

    // Sicil
    let mut rs = registry_view_value(&personal).unwrap();
    let rr = registry_view_value(&repo).unwrap();
    assert!(rs.snapshot.take().is_some() && rr.snapshot.is_none());
    assert_eq!(rs.git_status_registry, frozen.status(&["registry"]));
    rs.git_status_registry = rr.git_status_registry.clone();
    rs.repo_root = rr.repo_root.clone();
    assert_eq!(rs, rr);
    let rec = rs.tickers.iter().flat_map(|t| &t.records).filter(|r| r.record_type.as_deref() == Some("PREDICTION")).collect::<Vec<_>>();
    assert_eq!(rec.len(), 7);
    assert!(rec.iter().all(|r| r.tracked && r.added_commit.is_some() && r.push_proof.is_some()), "kayıt kanıtı anlık görüntüde dolu");

    // Analiz, kırılma kartı, kayıt kartı, koşullu görünüm, ham kayıt
    for row in &mr.rows {
        let t = row.ticker.as_str();
        assert_eq!(arz_view_value(&personal, t).unwrap(), arz_view_value(&repo, t).unwrap(), "{t}");
        assert_eq!(break_view_value(&personal, t).unwrap(), break_view_value(&repo, t).unwrap(), "{t}");
        assert_eq!(break_view_value(&personal, t).unwrap().status, "OK", "{t}: katsayı sha'sı tutar");
        let st = arz_streak_value(&personal, t).unwrap();
        assert_eq!(st, arz_streak_value(&repo, t).unwrap(), "{t}");
        let file = row.record_file.as_deref().expect("kayıt");
        let j = st.j_observed.unwrap_or(0);
        assert_eq!(record_ceiling_value(&personal, t, file, j).unwrap(), record_ceiling_value(&repo, t, file, j).unwrap(), "{t}");
        assert_eq!(
            serde_json::to_value(record_summary_value(&personal, t, file, j, st.j_observed).unwrap()).unwrap(),
            serde_json::to_value(record_summary_value(&repo, t, file, j, st.j_observed).unwrap()).unwrap(),
            "{t}"
        );
        assert_eq!(read_record_json_value(&personal, t, file).unwrap(), read_record_json_value(&repo, t, file).unwrap(), "{t}");
    }

    // Performans ve öne çıkarma kapısı: D1 sonrası ve kırılma bölümleri anlık görüntüden
    let (lp, lr) = (load(&personal), load(&repo));
    let (pp, pr) = (perf_view_value(&lp.docs()), perf_view_value(&lr.docs()));
    assert!(pp.has_post_d1 && pp.has_break && pp.has_oot);
    assert_eq!(pp, pr);
    assert_eq!(headline_gate_value(&lp.docs()), headline_gate_value(&lr.docs()));

    // veri dizini yoksa (uygulama verisi bağlanmamış) eskisi gibi repo modu ister
    let bare = AppState::from_embedded();
    assert_eq!(monitor_view_value(&bare).unwrap_err().code, "REPO_MODE_REQUIRED");

    // künye sözleşmesi (ön uç `SnapshotInfo`): alanlar ve sıra; Ayarlar görünümünde yalnız kişisel modda
    let keys: Vec<String> = serde_json::to_value(&info).unwrap().as_object().unwrap().keys().cloned().collect();
    assert_eq!(keys, ["status", "code", "detail", "build_sha7", "build_dirty", "manifest_sha256", "n_files", "bytes", "last_session"]);
    let cv = |st: &AppState| serde_json::to_value(borsai_app_lib::commands::config::config_view(st)).unwrap();
    assert_eq!(cv(&personal)["snapshot"]["status"], json!("READY"));
    assert!(cv(&repo).get("snapshot").is_none(), "repo modunda alan yok");
    let fresh = AppState::from_embedded();
    fresh.attach_data_dir(&tmp_dir("snapmode_pending"));
    assert_eq!(cv(&fresh)["snapshot"]["status"], json!("PENDING"), "henüz yazılmadı; ilk okumada yazılır");
}
