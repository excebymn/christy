//! Checks what a tool needs before it can run. Pure inspection: nothing is
//! installed here. Fixing what's missing is the tool's own setup script's job.

use std::env;
use std::path::PathBuf;

use crate::manifest::{Manifest, Runtime};
use crate::paths::Paths;
use crate::setup::stamps;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Requirement {
    /// A command that must be found in PATH.
    Command(String),
    /// A python tool's venv interpreter.
    Environment(PathBuf),
    /// A `binary` tool's executable, normally built by its setup script.
    Executable(PathBuf),
    /// A path from `requires.paths` that doesn't exist yet.
    Path(PathBuf),
    /// The setup script or a watched file changed since the last setup.
    SetupChanged,
}

/// Everything that stands between the tool and a successful launch. Empty
/// means ready.
pub fn check(paths: &Paths, manifest: &Manifest) -> Vec<Requirement> {
    let mut missing = Vec::new();
    let tool_dir = paths.tools_dir.join(&manifest.name);

    match manifest.runtime {
        Runtime::Python => {
            let python = paths.tool_env_dir(&manifest.name).join("bin").join("python");
            if !python.is_file() {
                missing.push(Requirement::Environment(python));
            }
        }
        Runtime::Node => require_command("node", &mut missing),
        Runtime::Bash => require_command("bash", &mut missing),
        Runtime::Binary => {
            let entry = tool_dir.join(&manifest.entry);
            if !entry.is_file() {
                missing.push(Requirement::Executable(entry));
            }
        }
    }

    for bin in &manifest.requires.bins {
        require_command(bin, &mut missing);
    }

    for relative in &manifest.requires.paths {
        let path = tool_dir.join(relative);
        if !path.exists() {
            missing.push(Requirement::Path(path));
        }
    }

    // Only worth reporting on its own: if something else is missing, running
    // setup fixes this too.
    if missing.is_empty() && stamps::is_outdated(paths, manifest) {
        missing.push(Requirement::SetupChanged);
    }
    missing
}

fn require_command(name: &str, missing: &mut Vec<Requirement>) {
    let requirement = Requirement::Command(name.to_string());
    if find_in_path(name).is_none() && !missing.contains(&requirement) {
        missing.push(requirement);
    }
}

/// First executable called `name` on PATH.
pub fn find_in_path(name: &str) -> Option<PathBuf> {
    let paths = env::var_os("PATH")?;
    env::split_paths(&paths)
        .map(|dir| dir.join(name))
        .find(|candidate| is_executable_file(candidate))
}

#[cfg(unix)]
fn is_executable_file(path: &std::path::Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    std::fs::metadata(path)
        .map(|meta| meta.is_file() && meta.permissions().mode() & 0o111 != 0)
        .unwrap_or(false)
}

#[cfg(not(unix))]
fn is_executable_file(path: &std::path::Path) -> bool {
    path.is_file()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse;
    use crate::paths::RepoSource;
    use std::fs;

    fn paths(label: &str) -> Paths {
        let root = env::temp_dir().join(format!("christy-deps-{}-{label}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let repo = root.join("repo");
        fs::create_dir_all(repo.join("tools")).unwrap();
        Paths {
            tools_dir: repo.join("tools"),
            repo,
            repo_source: RepoSource::EnvVar,
            config_dir: root.join("config"),
            state_dir: root.join("state"),
        }
    }

    fn manifest(runtime: &str, extra: &str) -> Manifest {
        parse(&format!(
            "schema = 1\nname = \"demo\"\ndescription = \"d\"\nruntime = \"{runtime}\"\nentry = \"bin/demo\"\n{extra}"
        ))
        .unwrap()
    }

    #[test]
    fn finds_real_commands_and_rejects_fake_ones() {
        assert!(find_in_path("sh").is_some());
        assert!(find_in_path("definitely-not-a-real-command-xyz").is_none());
    }

    #[test]
    fn python_needs_its_venv() {
        let paths = paths("python");
        let missing = check(&paths, &manifest("python", ""));
        assert!(matches!(missing.as_slice(), [Requirement::Environment(_)]));

        let python = paths.tool_env_dir("demo").join("bin/python");
        fs::create_dir_all(python.parent().unwrap()).unwrap();
        fs::write(&python, "").unwrap();
        assert!(check(&paths, &manifest("python", "")).is_empty());
    }

    #[test]
    fn declared_bins_are_checked_without_duplicates() {
        let paths = paths("bins");
        let m = manifest("bash", "[requires]\nbins = [\"bash\", \"nope-xyz\", \"nope-xyz\"]\n");
        assert_eq!(check(&paths, &m), vec![Requirement::Command("nope-xyz".into())]);
    }

    #[test]
    fn required_paths_must_exist() {
        let paths = paths("paths");
        let m = manifest("bash", "[requires]\npaths = [\"node_modules\"]\n");
        let missing = check(&paths, &m);
        assert!(matches!(missing.as_slice(), [Requirement::Path(p)] if p.ends_with("demo/node_modules")));

        fs::create_dir_all(paths.tools_dir.join("demo/node_modules")).unwrap();
        assert!(check(&paths, &m).is_empty());
    }

    #[test]
    fn binary_needs_its_executable() {
        let paths = paths("binary");
        let missing = check(&paths, &manifest("binary", ""));
        assert!(matches!(missing.as_slice(), [Requirement::Executable(_)]));
    }
}
