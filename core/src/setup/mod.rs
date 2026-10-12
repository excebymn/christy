//! On-demand setup.
//!
//! Nothing is installed up front. When a tool is launched and something is
//! missing, the core offers to run *that tool's own* setup script, then checks
//! again. Dependency logic stays inside the tool; the core only orchestrates.
//!
//! The script runs with the terminal attached, so anything it needs (a `sudo`
//! password, a confirmation from the package manager) works normally.

pub mod stamps;

use std::fs;
use std::process::Command;

use crate::deps::{self, Requirement};
use crate::error::{CoreError, UnmetContext};
use crate::manifest::Manifest;
use crate::messages as msg;
use crate::paths::Paths;
use crate::prompt;
use crate::runtime;

/// Called right before a tool launches. Returns once the tool is ready, or
/// explains why it can't be.
pub fn ensure_ready(paths: &Paths, manifest: &Manifest) -> Result<(), CoreError> {
    let missing = deps::check(paths, manifest);
    if missing.is_empty() {
        return Ok(());
    }

    if manifest.setup.is_none() {
        return Err(unmet(manifest, missing, UnmetContext::NoSetupScript));
    }
    if !prompt::is_interactive() {
        return Err(unmet(manifest, missing, UnmetContext::NeedsSetup));
    }

    eprintln!("{}", msg::needs_setup(&manifest.name, &missing));
    if !prompt::confirm(msg::ASK_RUN_SETUP, true) {
        return Err(CoreError::SetupDeclined {
            tool: manifest.name.clone(),
        });
    }

    run_and_verify(paths, manifest)
}

/// Runs the setup script, then checks that it really delivered: a script can
/// exit 0 and still leave something missing.
pub fn run_and_verify(paths: &Paths, manifest: &Manifest) -> Result<(), CoreError> {
    run_setup(paths, manifest)?;
    let still_missing = deps::check(paths, manifest);
    if still_missing.is_empty() {
        Ok(())
    } else {
        Err(unmet(manifest, still_missing, UnmetContext::AfterSetup))
    }
}

/// Runs the tool's setup script and records a stamp on success. Used both by
/// the on-demand flow and by `christy setup`.
pub fn run_setup(paths: &Paths, manifest: &Manifest) -> Result<(), CoreError> {
    let Some(spec) = &manifest.setup else {
        return Err(CoreError::NoSetupScript {
            tool: manifest.name.clone(),
        });
    };

    let tool_dir = paths.tools_dir.join(&manifest.name);
    let script = tool_dir.join(&spec.script);
    // Scripts are free to create what they need, but the base folder should
    // exist so they don't each have to think about it.
    let _ = fs::create_dir_all(&paths.state_dir);

    eprintln!("{}", msg::running_setup(&manifest.name));

    // `.sh` scripts go through bash so they need no executable bit; anything
    // else is run directly.
    let mut command = if script.extension().is_some_and(|ext| ext == "sh") {
        let mut command = Command::new("bash");
        command.arg(&script);
        command
    } else {
        Command::new(&script)
    };
    command.current_dir(&tool_dir);
    for (key, value) in runtime::tool_env(paths, manifest) {
        command.env(key, value);
    }

    let status = command.status().map_err(|source| CoreError::LaunchFailed {
        program: script.display().to_string(),
        source,
    })?;
    if !status.success() {
        return Err(CoreError::SetupFailed {
            tool: manifest.name.clone(),
            code: status.code(),
        });
    }

    // Best effort: failing to record only means no staleness detection.
    let _ = stamps::record(paths, manifest);
    eprintln!("{}", msg::setup_done(&manifest.name));
    Ok(())
}

fn unmet(manifest: &Manifest, missing: Vec<Requirement>, context: UnmetContext) -> CoreError {
    CoreError::Unmet {
        tool: manifest.name.clone(),
        missing,
        context,
    }
}
