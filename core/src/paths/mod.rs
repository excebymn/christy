//! Resolves where the repo, config, and state live.
//!
//! Repo lookup order:
//!   1. `CHRISTY_HOME` env var (must be a valid repo, no silent fallthrough)
//!   2. `repo_path` in `<config dir>/config.toml` (written by scripts/setup.sh)
//!   3. dev fallback: walk up from the running binary looking for a checkout
//!      that has both `core/Cargo.toml` and `tools/`

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::error::CoreError;

pub const ENV_HOME: &str = "CHRISTY_HOME";
pub const ENV_CONFIG_DIR: &str = "CHRISTY_CONFIG_DIR";
pub const ENV_STATE_DIR: &str = "CHRISTY_STATE_DIR";

/// How the repo was located, shown by `doctor`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RepoSource {
    EnvVar,
    ConfigFile,
    NextToBinary,
}

#[derive(Debug, Clone)]
pub struct Paths {
    pub repo: PathBuf,
    pub repo_source: RepoSource,
    pub tools_dir: PathBuf,
    pub config_dir: PathBuf,
    pub state_dir: PathBuf,
}

#[derive(Debug, Deserialize)]
struct ConfigFile {
    repo_path: Option<PathBuf>,
}

impl Paths {
    pub fn resolve() -> Result<Self, CoreError> {
        let config_dir = absolutize(config_dir()?);
        let state_dir = absolutize(state_dir()?);
        let (repo, repo_source) = find_repo(&config_dir)?;
        let repo = absolutize(repo);
        Ok(Self {
            tools_dir: repo.join("tools"),
            repo,
            repo_source,
            config_dir,
            state_dir,
        })
    }

    #[allow(dead_code)] // used by `setup` in M3
    pub fn config_file(&self) -> PathBuf {
        self.config_dir.join("config.toml")
    }

    pub fn registry_file(&self) -> PathBuf {
        self.state_dir.join("registry.json")
    }

    /// Where a tool's isolated environment lives (python venv, node_modules
    /// cache, ...). Created by the tool's own setup script.
    pub fn tool_env_dir(&self, tool: &str) -> PathBuf {
        self.state_dir.join("envs").join(tool)
    }
}

/// Tools run with the caller's cwd and may change it, so every path handed
/// to them (via env vars) must be absolute.
fn absolutize(path: PathBuf) -> PathBuf {
    if path.is_absolute() {
        return path;
    }
    match env::current_dir() {
        Ok(cwd) => cwd.join(path),
        Err(_) => path,
    }
}

fn config_dir() -> Result<PathBuf, CoreError> {
    base_dir(ENV_CONFIG_DIR, "XDG_CONFIG_HOME", ".config")
}

fn state_dir() -> Result<PathBuf, CoreError> {
    base_dir(ENV_STATE_DIR, "XDG_DATA_HOME", ".local/share")
}

/// Explicit override first, then the XDG variable, then `$HOME/<fallback>`.
fn base_dir(override_var: &str, xdg_var: &str, home_fallback: &str) -> Result<PathBuf, CoreError> {
    if let Some(dir) = non_empty_env(override_var) {
        return Ok(PathBuf::from(dir));
    }
    if let Some(dir) = non_empty_env(xdg_var) {
        return Ok(PathBuf::from(dir).join("christy"));
    }
    match non_empty_env("HOME") {
        Some(home) => Ok(PathBuf::from(home).join(home_fallback).join("christy")),
        None => Err(CoreError::Config {
            path: PathBuf::from("$HOME"),
            detail: "HOME is not set, can't locate the config and state folders".to_string(),
        }),
    }
}

fn non_empty_env(name: &str) -> Option<std::ffi::OsString> {
    env::var_os(name).filter(|value| !value.is_empty())
}

fn find_repo(config_dir: &Path) -> Result<(PathBuf, RepoSource), CoreError> {
    if let Some(dir) = non_empty_env(ENV_HOME) {
        return checked(PathBuf::from(dir), RepoSource::EnvVar);
    }

    if let Some(path) = repo_from_config(&config_dir.join("config.toml"))? {
        return checked(path, RepoSource::ConfigFile);
    }

    repo_from_exe()
        .map(|path| (path, RepoSource::NextToBinary))
        .ok_or(CoreError::RepoNotFound)
}

/// An explicitly configured repo must be valid; no silent fallthrough.
fn checked(path: PathBuf, source: RepoSource) -> Result<(PathBuf, RepoSource), CoreError> {
    if is_repo(&path) {
        Ok((path, source))
    } else {
        Err(CoreError::RepoInvalid(path))
    }
}

fn repo_from_config(config_file: &Path) -> Result<Option<PathBuf>, CoreError> {
    let text = match fs::read_to_string(config_file) {
        Ok(text) => text,
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(err) => {
            return Err(CoreError::Config {
                path: config_file.to_path_buf(),
                detail: err.to_string(),
            })
        }
    };
    let parsed: ConfigFile = toml::from_str(&text).map_err(|err| CoreError::Config {
        path: config_file.to_path_buf(),
        detail: err.message().to_string(),
    })?;
    Ok(parsed.repo_path)
}

fn repo_from_exe() -> Option<PathBuf> {
    let exe = env::current_exe().ok()?;
    exe.ancestors()
        .skip(1)
        .find(|dir| is_repo(dir) && dir.join("core").join("Cargo.toml").is_file())
        .map(Path::to_path_buf)
}

fn is_repo(path: &Path) -> bool {
    path.join("tools").is_dir()
}
