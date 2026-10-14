//! build.rs gömme planı ve git kuralları (SPEC_APP §1.4; FAZ3_APP_STAGE01 adım 4, K3).
#[path = "../build_embed.rs"]
mod build_embed;

use build_embed::build_embed_impl::*;
use std::path::{Path, PathBuf};

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

fn tmp_dir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("borsai_build_embed_{name}_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(d.join("models")).unwrap();
    d
}

#[test]
fn plan_pins_first_27_index_entries() {
    let plan = plan_embedding(&repo(), &PINNED_MODEL_IDS).expect("gerçek repo planı");
    let ids: Vec<&str> = plan.models.iter().map(|m| m.model_id.as_str()).collect();
    assert_eq!(ids, PINNED_MODEL_IDS.to_vec());
    assert_eq!(PINNED_MODEL_IDS.len(), 27, "Faz 4 tavan-yolu, Faz 7 v1 ve Faz 7C modelleri gömülü kümede (EK 2 §3.5, EK 3 §4.1)");
    assert_eq!(&PINNED_MODEL_IDS[16..19], ["ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0"]);
    assert_eq!(
        &PINNED_MODEL_IDS[19..23],
        ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"]
    );
    // EK 3 P4 (U58/U80): dört düşen arz kaydı gömülü; INDEX'in gömülmeyen kaydı yok
    assert_eq!(&PINNED_MODEL_IDS[23..], ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"]);
    assert_eq!(plan.ignored_model_ids, Vec::<String>::new(), "INDEX'in gömülmeyen kaydı yok (EK 3 §4.4, P4 sonrası)");
    assert_eq!(plan.index_sha256.len(), 64);
    // deflatörlü model gömüldüğü için TÜFE tablosu da gömülür (EK 3 §3.5)
    assert_eq!(plan.tufe_path.as_deref(), Some(tufe_path(&repo()).as_path()));
}

/// EK 3 §3.5: deflatörlü model varken TÜFE tablosu yoksa derleme kırılır; yoksa tablo gömülmez.
#[test]
fn tufe_table_required_only_with_deflator() {
    let d = tmp_dir("tufe");
    let index = serde_json::json!({
        "schema_version": "borsai.model_index/1",
        "models": [{"model_id": "a", "file": "a.json"}]
    });
    std::fs::write(d.join("models/INDEX.json"), serde_json::to_vec(&index).unwrap()).unwrap();
    std::fs::write(d.join("models/a.json"), br#"{"features": ["f1", "f2", "f3"]}"#).unwrap();
    assert!(plan_embedding(&d, &["a"]).unwrap().tufe_path.is_none(), "deflatörsüz: tablo gömülmez");
    std::fs::write(d.join("models/a.json"), br#"{"features": ["f1r", "f2", "f3"], "deflator": {"through_month": "2026-08"}}"#)
        .unwrap();
    let err = plan_embedding(&d, &["a"]).unwrap_err();
    assert!(err.contains("TÜFE tablosu yok"), "{err}");
    let p = tufe_path(&d);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(&p, b"month,index\n").unwrap();
    assert_eq!(plan_embedding(&d, &["a"]).unwrap().tufe_path, Some(p));
    let _ = std::fs::remove_dir_all(&d);
}

#[test]
fn missing_model_file_breaks_the_build() {
    let d = tmp_dir("missing");
    let index = serde_json::json!({
        "schema_version": "borsai.model_index/1",
        "models": [{"model_id": "a", "file": "a.json"}, {"model_id": "b", "file": "b.json"}]
    });
    std::fs::write(d.join("models/INDEX.json"), serde_json::to_vec(&index).unwrap()).unwrap();
    std::fs::write(d.join("models/a.json"), b"{}").unwrap();
    let err = plan_embedding(&d, &["a", "b"]).unwrap_err();
    assert!(err.contains("diskte yok"), "{err}");
    std::fs::write(d.join("models/b.json"), b"{}").unwrap();
    assert!(plan_embedding(&d, &["a", "b"]).is_ok());
    let err = plan_embedding(&d, &["b", "a"]).unwrap_err();
    assert!(err.contains("sıra"), "{err}");
    let _ = std::fs::remove_dir_all(&d);
}

#[test]
fn extra_index_entries_are_listed_but_not_embedded() {
    let d = tmp_dir("extra");
    let index = serde_json::json!({
        "schema_version": "borsai.model_index/1",
        "models": [{"model_id": "a", "file": "a.json"}, {"model_id": "later", "file": "later.json"}]
    });
    std::fs::write(d.join("models/INDEX.json"), serde_json::to_vec(&index).unwrap()).unwrap();
    std::fs::write(d.join("models/a.json"), b"{}").unwrap();
    let plan = plan_embedding(&d, &["a"]).unwrap();
    assert_eq!(plan.models.len(), 1);
    assert_eq!(plan.ignored_model_ids, vec!["later".to_string()]);
    let _ = std::fs::remove_dir_all(&d);
}

#[test]
fn git_calls_are_lock_free_and_read_only() {
    let cmd = git_command(&repo(), &["status", "--porcelain", "--", "models", "scores"]);
    let envs: Vec<_> = cmd.get_envs().collect();
    assert!(envs.iter().any(|(k, v)| *k == "GIT_OPTIONAL_LOCKS" && v.map(|v| v == "0").unwrap_or(false)));
    assert_eq!(GIT_READONLY_SUBCOMMANDS, ["rev-parse", "status", "ls-files", "log"]);
    for forbidden in ["commit", "add", "push", "tag", "reset", "checkout", "stash", "gc"] {
        let r = std::panic::catch_unwind(|| git_command(&repo(), &[forbidden]));
        assert!(r.is_err(), "{forbidden} beyaz listede olmamalı");
    }
}

#[test]
fn build_rs_runs_git_only_through_the_whitelist() {
    let src = std::fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("build.rs")).unwrap();
    assert!(!src.contains("Command::new"), "build.rs git'i yalnız build_embed.rs üzerinden çağırır");
    let embed = std::fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("build_embed.rs")).unwrap();
    assert_eq!(embed.matches("Command::new(").count(), 1, "tek git çağrı noktası: git_command");
}


/// EK 3 §4.1 P2: ikinci dizin (models/INDEX_POST_D1.json) sabit listeyle sırasıyla aynı; fazla ya da eksik kayıt ve diskte
/// olmayan dosya derlemeyi kırar.
#[test]
fn plan_pins_post_d1_index() {
    let plan = plan_post_d1(&repo(), &PINNED_POST_D1_MODEL_IDS).expect("gerçek repo ikinci dizin planı");
    assert_eq!(PINNED_POST_D1_MODEL_IDS, ["post_d1_hazard_v0"]);
    assert_eq!(plan.models.iter().map(|m| m.model_id.as_str()).collect::<Vec<_>>(), ["post_d1_hazard_v0"]);
    assert_eq!(plan.index_sha256.len(), 64);
    let d = tmp_dir("post");
    let write = |models: serde_json::Value| {
        let idx = serde_json::json!({"schema_version": "borsai.model_index/1", "models": models});
        std::fs::write(d.join("models").join(INDEX_POST_D1_FILE), serde_json::to_vec(&idx).unwrap()).unwrap();
    };
    write(serde_json::json!([{"model_id": "p", "file": "p.json"}]));
    let err = plan_post_d1(&d, &["p"]).unwrap_err();
    assert!(err.contains("diskte yok"), "{err}");
    std::fs::write(d.join("models/p.json"), b"{}").unwrap();
    assert!(plan_post_d1(&d, &["p"]).is_ok());
    write(serde_json::json!([{"model_id": "p", "file": "p.json"}, {"model_id": "q", "file": "p.json"}]));
    let err = plan_post_d1(&d, &["p"]).unwrap_err();
    assert!(err.contains("sabit listede"), "fazla kayıt: {err}");
    let _ = std::fs::remove_dir_all(&d);
}

// ---------------------------------------------------------------- FAZ9_SNAPSHOT K-SNAP-1: sicil anlık görüntüsü

/// Anlık görüntünün kapsamı sabittir; plan gerçek repodaki dosyaları aynen (yol, sha256, bayt) ve yol sırasıyla taşır;
/// izlenen her dosya plandadır; ham bülten, PDF, `registry/source_docs/`, `registry/oot/` girmez; `data/outcomes/`'tan yalnız
/// kayıtlı arzların `<T>.csv`'si (B2: `COMPLETENESS.csv` girmez); gömülü manifest planla aynı.
#[test]
fn plan_snapshot_pins_spec_and_mirrors_repo() {
    assert_eq!(
        SNAPSHOT_SPEC.iter().map(|(p, s)| (spec_rel(p), *s)).collect::<Vec<_>>(),
        vec![
            ("registry/ipos.csv".to_string(), SnapshotScope::File),
            ("registry/records".to_string(), SnapshotScope::Tree),
            ("registry/inputs".to_string(), SnapshotScope::Tree),
            ("registry/post_break".to_string(), SnapshotScope::Tree),
            ("registry/push_proofs".to_string(), SnapshotScope::Tree),
            ("data/outcomes".to_string(), SnapshotScope::PerRecord("csv")),
            ("scores/scores_break.json".to_string(), SnapshotScope::File),
            ("scores/scores_post_d1.json".to_string(), SnapshotScope::File),
            ("models/break_floor_v0.json".to_string(), SnapshotScope::File),
        ]
    );
    let r = repo();
    let plan = plan_snapshot(&r).expect("gerçek repo anlık görüntü planı");
    let rels: Vec<&str> = plan.files.iter().map(|f| f.rel.as_str()).collect();
    let mut sorted = rels.clone();
    sorted.sort();
    sorted.dedup();
    assert_eq!(rels, sorted, "yol sırası, tekil");
    for f in &plan.files {
        let disk = f.rel.split('/').fold(r.clone(), |p, c| p.join(c));
        let bytes = std::fs::read(&disk).unwrap();
        assert_eq!((f.sha256.as_str(), f.bytes), (sha256_hex(&bytes).as_str(), bytes.len() as u64), "{}", f.rel);
        assert!(f.rel.split('/').all(portable_name), "{}", f.rel);
        for bad in ["registry/oot/", "registry/source_docs/", "registry/legacy_frozen/", "data/raw/"] {
            assert!(!f.rel.starts_with(bad), "{} gömülmemeli", f.rel);
        }
        assert!(!f.rel.ends_with(".pdf") && !f.rel.ends_with(".zip"), "{}", f.rel);
    }
    for must in ["registry/ipos.csv", "scores/scores_break.json", "scores/scores_post_d1.json", "models/break_floor_v0.json"] {
        assert!(rels.contains(&must), "{must}");
    }
    for root in ["registry/records/", "registry/inputs/", "registry/post_break/", "registry/push_proofs/", "data/outcomes/"] {
        assert!(rels.iter().any(|x| x.starts_with(root)), "{root} boş");
    }
    // data/outcomes: kayıt dizini olan her arz için <T>.csv, başka dosya yok
    let tickers = record_tickers(&r).unwrap();
    assert_eq!(tickers.len(), 7, "kayıtlı 7 arz");
    let outcomes: Vec<&str> = rels.iter().copied().filter(|x| x.starts_with("data/outcomes/")).collect();
    assert_eq!(outcomes, tickers.iter().map(|t| format!("data/outcomes/{t}.csv")).collect::<Vec<_>>());
    assert!(r.join("data").join("outcomes").join("COMPLETENESS.csv").is_file() && !rels.contains(&"data/outcomes/COMPLETENESS.csv"));
    // izlenen her dosya planda (izlenmeyen fazlası olabilir: plan çalışma ağacından)
    let paths: Vec<String> = SNAPSHOT_SPEC.iter().map(|(p, _)| spec_rel(p)).collect();
    let mut args = vec!["ls-files", "--"];
    args.extend(paths.iter().map(String::as_str));
    let tracked = git_readonly(&r, &args).expect("git ls-files");
    for t in tracked.lines().filter(|t| !t.rsplit('/').next().unwrap_or("").starts_with('.')) {
        if t.starts_with("data/outcomes/") && !outcomes.contains(&t) {
            continue;
        }
        assert!(rels.contains(&t), "izlenen {t} planda yok");
    }
    assert_eq!(plan.manifest, snapshot_manifest(&plan.files));
    assert_eq!(plan.manifest_sha256, sha256_hex(plan.manifest.as_bytes()));
    // derlemeye gömülen = bugünkü plan (build.rs bu yollar değişince yeniden koşar)
    let b = borsai_app_lib::embedded::BUILD_INFO;
    assert_eq!(b.snapshot_manifest, plan.manifest);
    assert_eq!(b.snapshot_manifest_sha256, plan.manifest_sha256);
    let embedded: Vec<&str> = borsai_app_lib::embedded::SNAPSHOT_FILES.iter().map(|f| f.rel).collect();
    assert_eq!(embedded, rels);
}

/// Kapsam kuralları (geçici dizinde): gizli ad atlanır; `PerRecord` yalnız kayıt dizini olan arzın `<T>.csv`'sini alır (tamlık
/// listesi, kaydı olmayan arz, başka uzantı ve alt dizin girmez); `Tree` iner; olmayan yol gömülmez; taşınabilir olmayan ad ve
/// sembolik bağ derlemeyi kırar.
#[test]
fn plan_snapshot_scope_rules() {
    let d = tmp_dir("snap");
    assert!(plan_snapshot(&d).unwrap().files.is_empty(), "hiçbiri yok: boş plan, derleme kırılmaz");
    let put = |rel: &str, body: &[u8]| {
        let p = rel.split('/').fold(d.clone(), |p, c| p.join(c));
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, body).unwrap();
    };
    put("registry/ipos.csv", b"ticker\n");
    put("registry/records/AAAA/r1.json", b"{}");
    put("registry/records/AAAA/.DS_Store", b"x");
    put("registry/records/AAAA/sub/r2.json", b"{}");
    put("data/outcomes/AAAA.csv", b"h,session_date\n1,2026-10-01\n");
    put("data/outcomes/notes.txt", b"x");
    put("data/outcomes/sub/BBBB.csv", b"x");
    put("data/outcomes/COMPLETENESS.csv", b"first_seen,code\n");
    put("data/outcomes/ZZZZ.csv", b"h,session_date\n");
    put("data/outcomes/AAAA.txt", b"x");
    put("registry/oot/records/x.json", b"{}");
    let plan = plan_snapshot(&d).unwrap();
    let rels: Vec<&str> = plan.files.iter().map(|f| f.rel.as_str()).collect();
    assert_eq!(rels, ["data/outcomes/AAAA.csv", "registry/ipos.csv", "registry/records/AAAA/r1.json", "registry/records/AAAA/sub/r2.json"]);
    assert_eq!(plan.manifest.lines().count(), 4);
    put("registry/inputs/bad name.json", b"{}");
    let err = plan_snapshot(&d).unwrap_err();
    assert!(err.contains("taşınabilir"), "{err}");
    std::fs::remove_file(d.join("registry").join("inputs").join("bad name.json")).unwrap();
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(d.join("registry").join("ipos.csv"), d.join("registry").join("records").join("AAAA").join("l.json")).unwrap();
        let err = plan_snapshot(&d).unwrap_err();
        assert!(err.contains("sembolik bağ"), "{err}");
    }
    let _ = std::fs::remove_dir_all(&d);
}

/// Derleme anının git bilgisi: izlenen her tahmin kaydı için kaydı ekleyen commit (40 hane). Anlık görüntü yolları temizken
/// gömülen bilgi bugünküyle aynıdır (kirli ağaçta `git add` derleme betiğini yeniden koşturmaz; eşitlik orada aranmaz).
#[test]
fn snapshot_git_facts_match_embedded() {
    let r = repo();
    let plan = plan_snapshot(&r).unwrap();
    let g = snapshot_git(&r, &plan);
    assert!(!g.records.is_empty(), "izlenen tahmin kaydı yok");
    for (rel, c) in &g.records {
        assert!(rel.starts_with("registry/records/") && plan.files.iter().any(|f| &f.rel == rel), "{rel}");
        assert!(c.len() == 40 && c.bytes().all(|b| b.is_ascii_hexdigit()), "{rel}: {c:?}");
    }
    if g.status.is_empty() {
        let embedded: Vec<(String, String)> =
            borsai_app_lib::embedded::SNAPSHOT_RECORD_COMMITS.iter().map(|(a, b)| (a.to_string(), b.to_string())).collect();
        assert_eq!(embedded, g.records);
        assert_eq!(borsai_app_lib::embedded::BUILD_INFO.git_status_snapshot, "");
    } else {
        eprintln!("anlık görüntü yolları kirli; gömülü git bilgisiyle eşitlik aranmadı:\n{}", g.status);
    }
}
