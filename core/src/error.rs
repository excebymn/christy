//! Core error type. Each variant maps to an exit code the shell can rely on.

use std::fmt;
use std::io;
use std::path::PathBuf;

use crate::deps::Requirement;
use crate::messages as msg;
use crate::term::Painter;

/// Exit codes owned by the core. A tool's own exit code is passed through
/// untouched once it is running, so these never overlap with normal tool use.
pub const EXIT_USAGE: i32 = 2;
pub const EXIT_CANNOT_RUN: i32 = 126;
pub const EXIT_UNKNOWN_TOOL: i32 = 127;

/// Why a tool's requirements are still unmet, which decides the advice shown.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnmetContext {
    /// Setup would fix it, but there's no terminal to ask on.
    NeedsSetup,
    /// The manifest has no setup script, so only the user can fix it.
    NoSetupScript,
    /// Setup ran and finished, yet something is still missing.
    AfterSetup,
}

#[derive(Debug)]
pub enum CoreError {
    /// Bad arguments to a built-in command.
    Usage(String),
    /// No repo found via CHRISTY_HOME, config.toml, or the dev fallback.
    RepoNotFound,
    /// A repo path was given explicitly but does not look like a repo.
    RepoInvalid(PathBuf),
    /// config.toml exists but cannot be read or parsed.
    Config { path: PathBuf, detail: String },
    Io { context: String, source: io::Error },
    UnknownTool { name: String, suggestions: Vec<String> },
    InvalidTool { name: String, reasons: Vec<String> },
    /// The manifest's `platforms` list doesn't include the current OS.
    PlatformUnsupported {
        tool: String,
        platforms: Vec<String>,
        current: String,
    },
    /// A python tool's venv doesn't exist yet.
    EnvMissing {
        tool: String,
        expected: PathBuf,
        setup_script: Option<PathBuf>,
    },
    /// A `binary` tool's executable hasn't been built yet.
    BinaryMissing { tool: String, expected: PathBuf },
    /// `exec` itself failed (command not found, not executable, ...).
    LaunchFailed { program: String, source: io::Error },
    /// Requirements are missing and weren't (or couldn't be) fixed.
    Unmet {
        tool: String,
        missing: Vec<Requirement>,
        context: UnmetContext,
    },
    /// The user answered "no" to running setup.
    SetupDeclined { tool: String },
    /// The tool's setup script exited with an error (`None` = killed by signal).
    SetupFailed { tool: String, code: Option<i32> },
    /// `christy setup <tool>` on a tool whose manifest has no `[setup]`.
    NoSetupScript { tool: String },
    /// A helper command (git, cargo) ran and failed.
    CommandFailed { what: String, code: Option<i32> },
}

impl CoreError {
    pub fn exit_code(&self) -> i32 {
        match self {
            CoreError::Usage(_) => EXIT_USAGE,
            CoreError::UnknownTool { .. } => EXIT_UNKNOWN_TOOL,
            CoreError::InvalidTool { .. }
            | CoreError::PlatformUnsupported { .. }
            | CoreError::EnvMissing { .. }
            | CoreError::BinaryMissing { .. }
            | CoreError::LaunchFailed { .. }
            | CoreError::Unmet { .. }
            | CoreError::SetupDeclined { .. } => EXIT_CANNOT_RUN,
            _ => 1,
        }
    }

    /// Prints `error: ...` on stderr.
    pub fn report(&self) {
        let painter = Painter::stderr();
        eprintln!("{} {self}", painter.red(&painter.bold("error:")));
    }

    pub fn io(context: impl Into<String>, source: io::Error) -> Self {
        CoreError::Io {
            context: context.into(),
            source,
        }
    }
}

impl fmt::Display for CoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CoreError::Usage(detail) => write!(f, "{detail}"),
            CoreError::RepoNotFound => write!(f, "{}", msg::repo_not_found()),
            CoreError::RepoInvalid(path) => write!(f, "{}", msg::repo_invalid(path)),
            CoreError::Config { path, detail } => write!(f, "{}", msg::config_error(path, detail)),
            CoreError::Io { context, source } => write!(f, "{context}: {source}"),
            CoreError::UnknownTool { name, suggestions } => {
                write!(f, "{}", msg::unknown_tool(name, suggestions))
            }
            CoreError::InvalidTool { name, reasons } => {
                write!(f, "{}", msg::invalid_tool(name, reasons))
            }
            CoreError::PlatformUnsupported {
                tool,
                platforms,
                current,
            } => write!(f, "{}", msg::platform_unsupported(tool, platforms, current)),
            CoreError::EnvMissing {
                tool,
                expected,
                setup_script,
            } => write!(
                f,
                "{}",
                msg::env_missing(tool, expected, setup_script.as_deref())
            ),
            CoreError::BinaryMissing { tool, expected } => {
                write!(f, "{}", msg::binary_missing(tool, expected))
            }
            CoreError::LaunchFailed { program, source } => {
                write!(f, "{}", msg::launch_failed(program, source))
            }
            CoreError::Unmet {
                tool,
                missing,
                context,
            } => write!(f, "{}", msg::unmet(tool, missing, *context)),
            CoreError::SetupDeclined { tool } => write!(f, "{}", msg::setup_declined(tool)),
            CoreError::SetupFailed { tool, code } => {
                write!(f, "{}", msg::setup_failed(tool, *code))
            }
            CoreError::NoSetupScript { tool } => write!(f, "{}", msg::no_setup_script(tool)),
            CoreError::CommandFailed { what, code } => {
                write!(f, "{}", msg::command_failed(what, *code))
            }
        }
    }
}

impl std::error::Error for CoreError {}
