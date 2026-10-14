//! Salt okuma git çağrıları (SPEC_APP §5.4 U32). Uygulama `commit`, `push`, `add`, `tag` ÇALIŞTIRMAZ:
//! `Command::new("git")` yalnız bu dosyada ve alt komut beyaz listesiyle çağrılır. Her çağrı
//! `GIT_OPTIONAL_LOCKS=0` taşır (paralel commit sırasında index.lock bırakılmaz).
use std::path::Path;
use std::process::Command;

use super::AppError;

pub const GIT_READONLY_SUBCOMMANDS: [&str; 4] = ["rev-parse", "status", "log", "ls-files"];
pub const GIT_NOT_ALLOWED: &str = "GIT_NOT_ALLOWED";
pub const GIT_FAILED: &str = "GIT_FAILED";

/// Beyaz liste dışı alt komut `GIT_NOT_ALLOWED`. `-c`, `--exec-path` gibi seçenekler de reddedilir
/// (ilk argüman alt komut olmak zorunda).
pub fn git_command(repo: &Path, args: &[&str]) -> Result<Command, AppError> {
    let sub = args.first().copied().unwrap_or("");
    if !GIT_READONLY_SUBCOMMANDS.contains(&sub) {
        return Err(AppError::new(GIT_NOT_ALLOWED, format!("git {sub:?}: yalnız salt okuma alt komutları")));
    }
    let mut cmd = Command::new("git");
    // Windows: verbatim önekli yolu (`\\?\C:\…`) her araç tanımaz; git'e öneksiz yazım gider (unix'te yol aynen; FAZ9_WINDOWS K-WIN-3)
    cmd.env("GIT_OPTIONAL_LOCKS", "0").arg("-C").arg(super::config::plain_path(repo.to_path_buf())).args(args);
    Ok(cmd)
}

pub fn git_readonly(repo: &Path, args: &[&str]) -> Result<String, AppError> {
    let out = git_command(repo, args)?
        .output()
        .map_err(|e| AppError::new(GIT_FAILED, format!("git çalıştırılamadı: {e}")))?;
    if !out.status.success() {
        return Err(AppError::new(GIT_FAILED, format!("git {} başarısız", args.join(" ")))
            .with_detail(String::from_utf8_lossy(&out.stderr).to_string()));
    }
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}
