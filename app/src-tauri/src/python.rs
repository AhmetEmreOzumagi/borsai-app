//! Repo içi Python çağrısı (SPEC_APP §1.1; yalnız repo modunda). cwd = repo_root; ağ yok;
//! `PYTHONDONTWRITEBYTECODE=1`: çağrı repo ağacına `__pycache__` bile yazmaz.
use std::path::Path;
use std::process::Command;

use crate::commands::AppError;

pub const PYTHON_NOT_FOUND: &str = "PYTHON_NOT_FOUND";
pub const PYTHON_FAILED: &str = "PYTHON_FAILED";

pub fn python_command(python: &Path, repo: &Path, args: &[&str]) -> Command {
    let mut cmd = Command::new(python);
    cmd.current_dir(repo).env("PYTHONDONTWRITEBYTECODE", "1").env("PYTHONNOUSERSITE", "1").args(args);
    cmd
}

/// Başarıda stdout; çıkış kodu ≠ 0 ise `PYTHON_FAILED` (stderr `detail`'de, aynen).
pub fn run_python(python: &Path, repo: &Path, args: &[&str]) -> Result<String, AppError> {
    let out = python_command(python, repo, args).output().map_err(|e| {
        AppError::new(PYTHON_NOT_FOUND, format!("Python çalıştırılamadı: {}", python.display())).with_detail(e.to_string())
    })?;
    if !out.status.success() {
        return Err(AppError::new(PYTHON_FAILED, format!("Python çıkış kodu {}", out.status.code().unwrap_or(-1)))
            .with_detail(String::from_utf8_lossy(&out.stderr).to_string()));
    }
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}
