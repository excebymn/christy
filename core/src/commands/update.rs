//! `christy update`: pull the repo, rescan the tools, rebuild the core if its
//! sources changed, and say what's different.
//!
//! New tools need nothing else: dropping a folder in (or pulling one) is
//! enough, and any setup they need is offered on first run.

use std::path::Path;
use std::process::{Command, Stdio};

use crate::deps;
use crate::error::CoreError;
use crate::messages as msg;
use crate::paths::Paths;
use crate::registry::{self, Registry, ToolState};
use crate::runtime;

pub fn run() -> Result<i32, CoreError> {
    let paths = Paths::resolve()?;
    // What we knew at the last run, to compare against after the pull.
    let before = registry::cached(&paths);

    let core_changed = pull(&paths.repo)?;

    let build = registry::refresh(&paths)?;
    if core_changed {
        rebuild_core(&paths.repo)?;
    }

    report_tool_changes(before.as_ref(), &build.registry);
    report_needs_setup(&paths, &build.registry);
    if build.registry.invalid_count() > 0 {
        println!("\n{}", msg::list_problems(build.registry.invalid_count()));
    }
    Ok(0)
}

/// Returns whether anything under `core/` changed in the pull.
fn pull(repo: &Path) -> Result<bool, CoreError> {
    if !repo.join(".git").exists() {
        println!("{}", msg::UPDATE_NOT_GIT);
        return Ok(false);
    }

    let head_before = git_output(repo, &["rev-parse", "HEAD"])?;
    println!("{}", msg::UPDATE_PULLING);
    git_run(repo, &["pull", "--ff-only"])?;
    let head_after = git_output(repo, &["rev-parse", "HEAD"])?;

    // git already says "Already up to date." when nothing came in.
    if head_before == head_after {
        return Ok(false);
    }
    let changed = git_output(
        repo,
        &["diff", "--name-only", &head_before, &head_after, "--", "core"],
    )?;
    Ok(!changed.is_empty())
}

fn rebuild_core(repo: &Path) -> Result<(), CoreError> {
    println!("{}", msg::UPDATE_CORE_CHANGED);
    let manifest = repo.join("core").join("Cargo.toml");
    let status = Command::new("cargo")
        .args(["build", "--release", "--manifest-path"])
        .arg(&manifest)
        .status()
        .map_err(|source| CoreError::LaunchFailed {
            program: "cargo".to_string(),
            source,
        })?;
    if !status.success() {
        return Err(CoreError::CommandFailed {
            what: "cargo build".to_string(),
            code: status.code(),
        });
    }
    println!(
        "{}",
        msg::update_core_rebuilt(&repo.join("core/target/release/christy"))
    );
    Ok(())
}

/// Runs git with the terminal attached, so progress and prompts show.
fn git_run(repo: &Path, args: &[&str]) -> Result<(), CoreError> {
    let status = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(args)
        .status()
        .map_err(git_launch_error)?;
    if status.success() {
        Ok(())
    } else {
        Err(CoreError::CommandFailed {
            what: format!("git {}", args.join(" ")),
            code: status.code(),
        })
    }
}

/// Runs git and returns its trimmed stdout.
fn git_output(repo: &Path, args: &[&str]) -> Result<String, CoreError> {
    let output = Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(args)
        .stderr(Stdio::inherit())
        .output()
        .map_err(git_launch_error)?;
    if !output.status.success() {
        return Err(CoreError::CommandFailed {
            what: format!("git {}", args.join(" ")),
            code: output.status.code(),
        });
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn git_launch_error(source: std::io::Error) -> CoreError {
    CoreError::LaunchFailed {
        program: "git".to_string(),
        source,
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
struct Diff {
    added: Vec<String>,
    removed: Vec<String>,
    changed: Vec<String>,
}

impl Diff {
    fn is_empty(&self) -> bool {
        self.added.is_empty() && self.removed.is_empty() && self.changed.is_empty()
    }
}

fn diff(before: &Registry, after: &Registry) -> Diff {
    let mut result = Diff::default();
    for entry in &after.tools {
        match before.find(entry.dir_name()) {
            None => result.added.push(entry.dir_name().to_string()),
            Some(old) if old.fingerprint.manifest != entry.fingerprint.manifest => {
                result.changed.push(entry.dir_name().to_string());
            }
            Some(_) => {}
        }
    }
    for entry in &before.tools {
        if after.find(entry.dir_name()).is_none() {
            result.removed.push(entry.dir_name().to_string());
        }
    }
    result
}

fn report_tool_changes(before: Option<&Registry>, after: &Registry) {
    let Some(before) = before else {
        println!("{}", msg::update_tools_found(after.tools.len()));
        return;
    };
    let changes = diff(before, after);
    if changes.is_empty() {
        println!("{}", msg::UPDATE_NO_TOOL_CHANGES);
        return;
    }
    for (label, names) in [
        ("added:", &changes.added),
        ("changed:", &changes.changed),
        ("removed:", &changes.removed),
    ] {
        if !names.is_empty() {
            println!("{}", msg::update_diff_line(label, names));
        }
    }
}

fn report_needs_setup(paths: &Paths, registry: &Registry) {
    let names: Vec<String> = registry
        .tools
        .iter()
        .filter_map(|entry| match &entry.state {
            ToolState::Valid { manifest } => Some(manifest),
            ToolState::Invalid { .. } => None,
        })
        .filter(|manifest| runtime::check_platform(manifest).is_ok())
        .filter(|manifest| !deps::check(paths, manifest).is_empty())
        .map(|manifest| manifest.name.clone())
        .collect();
    if !names.is_empty() {
        println!("\n{}", msg::update_needs_setup(&names));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn registry_with(tools: &[(&str, u64)]) -> Registry {
        let json = serde_json::json!({
            "schema": 1,
            "repo": "/r",
            "tools": tools.iter().map(|(name, mtime)| serde_json::json!({
                "fingerprint": {
                    "dir_name": name,
                    "dir_mtime_ns": 0,
                    "manifest": { "mtime_ns": mtime, "size": 1 }
                },
                "status": "invalid",
                "reasons": []
            })).collect::<Vec<_>>()
        });
        serde_json::from_value(json).unwrap()
    }

    #[test]
    fn diff_finds_added_removed_and_changed_tools() {
        let before = registry_with(&[("a", 1), ("b", 1), ("c", 1)]);
        let after = registry_with(&[("a", 1), ("b", 2), ("d", 1)]);
        let changes = diff(&before, &after);
        assert_eq!(changes.added, vec!["d"]);
        assert_eq!(changes.removed, vec!["c"]);
        assert_eq!(changes.changed, vec!["b"]);
    }

    #[test]
    fn identical_registries_have_no_diff() {
        let registry = registry_with(&[("a", 1)]);
        assert!(diff(&registry, &registry).is_empty());
    }
}
