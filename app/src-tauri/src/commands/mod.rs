//! Tauri komutları (SPEC_APP §6 sözleşmesi). Hepsi `Result<T, AppError>` döner.
pub mod ceiling;
pub mod config;
pub mod fall;
pub mod form;
pub mod freeze;
pub mod git;
pub mod inputs_doc;
pub mod market20;
pub mod models;
pub mod parity;
pub mod path;
pub mod post_d1;
pub mod predict;
pub mod registry;
pub mod registry_snapshot;
pub mod sade;
pub mod sade_break;
pub mod scenario;
pub mod scores;
pub mod scores_oot;
pub mod snapshot;
pub mod source_docs;

use serde::Serialize;

/// Ön uç `code`'u `tr.ts`'ten çevirir; `message` geliştirici içindir; `detail` ham çıktıdır (stderr).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct AppError {
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
}

impl AppError {
    pub fn new(code: &str, message: impl Into<String>) -> Self {
        AppError { code: code.to_string(), message: message.into(), detail: None }
    }

    pub fn with_detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = Some(detail.into());
        self
    }
}

pub const IO_ERROR: &str = "IO_ERROR";
pub const REPO_MODE_REQUIRED: &str = "REPO_MODE_REQUIRED";
pub const INVALID_ARGUMENT: &str = "INVALID_ARGUMENT";

pub fn io_error(what: &str, e: impl std::fmt::Display) -> AppError {
    AppError::new(IO_ERROR, format!("{what}: {e}"))
}
