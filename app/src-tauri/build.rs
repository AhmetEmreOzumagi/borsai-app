// Modelleri, INDEX'i ve sicil anlık görüntüsünü derlemeye gömer (SPEC_APP §1.4; FAZ9_SNAPSHOT K-SNAP-1); ardından tauri-build.
include!("build_embed.rs");

use build_embed_impl::*;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let repo = manifest_dir
        .join("..")
        .join("..")
        .canonicalize()
        .expect("repo kökü (app/src-tauri/../..) çözülemedi");

    let plan = plan_embedding(&repo, &PINNED_MODEL_IDS).unwrap_or_else(|e| panic!("model gömme: {e}"));
    let post = plan_post_d1(&repo, &PINNED_POST_D1_MODEL_IDS).unwrap_or_else(|e| panic!("ikinci dizin gömme: {e}"));
    let snap = plan_snapshot(&repo).unwrap_or_else(|e| panic!("anlık görüntü gömme: {e}"));
    let snap_git = snapshot_git(&repo, &snap);
    let head = git_readonly(&repo, &["rev-parse", "HEAD"]).unwrap_or_else(|| "UNKNOWN".into());
    let status =
        git_readonly(&repo, &["status", "--porcelain", "--", "models", "scores"]).unwrap_or_else(|| "UNKNOWN".into());

    let out_dir = PathBuf::from(std::env::var("OUT_DIR").expect("OUT_DIR"));
    // scores_oot.json: bağımsız mod için satırsız süzülmüş kopya (K-P1-3 eki)
    let oot = plan.scores_oot_path.as_ref().map(|p| {
        let raw = std::fs::read(p).unwrap_or_else(|e| panic!("{} okunamadı: {e}", p.display()));
        let filtered = filter_scores_oot(&raw).unwrap_or_else(|e| panic!("scores_oot süzgeci: {e}"));
        let path = out_dir.join("scores_oot_embedded.json");
        std::fs::write(&path, serde_json::to_string(&filtered).expect("serde")).expect("scores_oot_embedded.json yazılamadı");
        path
    });
    let out = out_dir.join("embedded.rs");
    std::fs::write(&out, render_embedded_rs(&plan, &post, &head, &status, oot.as_deref(), &snap, &snap_git))
        .expect("embedded.rs yazılamadı");

    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=build_embed.rs");
    println!("cargo:rerun-if-changed={}", repo.join("models").display());
    println!("cargo:rerun-if-changed={}", repo.join("scores").display());
    println!("cargo:rerun-if-changed={}", tufe_path(&repo).display());
    // anlık görüntü yolları (var olanlar; olmayan yol her derlemede betiği yeniden koşturur)
    for (parts, _) in SNAPSHOT_SPEC.iter() {
        let p = parts.iter().fold(repo.clone(), |p, c| p.join(c));
        if p.exists() {
            println!("cargo:rerun-if-changed={}", p.display());
        }
    }
    if let Some(git_dir) = git_readonly(&repo, &["rev-parse", "--absolute-git-dir"]) {
        let git_dir = PathBuf::from(git_dir.trim());
        for rel in ["HEAD", "packed-refs", "refs/heads"] {
            let p = git_dir.join(rel);
            if p.exists() {
                println!("cargo:rerun-if-changed={}", p.display());
            }
        }
    }

    tauri_build::build()
}
