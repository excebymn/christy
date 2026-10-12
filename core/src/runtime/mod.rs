//! Turns a validated manifest into a concrete launch plan (program, args,
//! environment), then replaces the core process with it.
//!
//! The core never captures or wraps a tool's I/O: it `exec`s, so the tool
//! owns the TTY, signals, and exit code. The cwd is left alone on purpose;
//! tools work relative to wherever the user called `christy` from.

mod launch;

use std::env;
use std::ffi::OsString;

use crate::error::CoreError;
use crate::manifest::{Manifest, Runtime};
use crate::paths::{self, Paths};

pub use launch::exec;

pub const ENV_TOOL_DIR: &str = "CHRISTY_TOOL_DIR";
pub const ENV_VERSION: &str = "CHRISTY_VERSION";

/// Convention: every tool answers this flag with its own help. `christy help
/// <tool>` is shorthand for `christy <tool> --help`.
pub const HELP_FLAG: &str = "--help";

#[derive(Debug)]
pub struct LaunchPlan {
    pub program: OsString,
    pub args: Vec<OsString>,
    pub env: Vec<(&'static str, OsString)>,
}

pub fn plan(
    paths: &Paths,
    manifest: &Manifest,
    user_args: Vec<OsString>,
) -> Result<LaunchPlan, CoreError> {
    check_platform(manifest)?;

    let tool_dir = paths.tools_dir.join(&manifest.name);
    let entry = tool_dir.join(&manifest.entry);

    let (program, mut args): (OsString, Vec<OsString>) = match manifest.runtime {
        Runtime::Python => {
            // Always the tool's own venv, never the system python.
            let env_dir = paths.tool_env_dir(&manifest.name);
            let python = env_dir.join("bin").join("python");
            if !python.is_file() {
                return Err(CoreError::EnvMissing {
                    tool: manifest.name.clone(),
                    expected: python,
                    setup_script: manifest
                        .setup
                        .as_ref()
                        .map(|setup| tool_dir.join(&setup.script)),
                });
            }
            (python.into_os_string(), vec![entry.into_os_string()])
        }
        Runtime::Node => ("node".into(), vec![entry.into_os_string()]),
        Runtime::Bash => ("bash".into(), vec![entry.into_os_string()]),
        Runtime::Binary => {
            if !entry.is_file() {
                return Err(CoreError::BinaryMissing {
                    tool: manifest.name.clone(),
                    expected: entry,
                });
            }
            (entry.into_os_string(), Vec::new())
        }
    };
    args.extend(user_args);

    Ok(LaunchPlan {
        program,
        args,
        env: tool_env(paths, manifest),
    })
}

/// The environment every tool (and every setup script) is given.
pub fn tool_env(paths: &Paths, manifest: &Manifest) -> Vec<(&'static str, OsString)> {
    vec![
        (paths::ENV_HOME, paths.repo.clone().into_os_string()),
        (
            ENV_TOOL_DIR,
            paths.tools_dir.join(&manifest.name).into_os_string(),
        ),
        (paths::ENV_STATE_DIR, paths.state_dir.clone().into_os_string()),
        (ENV_VERSION, OsString::from(env!("CARGO_PKG_VERSION"))),
    ]
}

/// An empty `platforms` list means "runs anywhere".
pub fn check_platform(manifest: &Manifest) -> Result<(), CoreError> {
    let current = env::consts::OS;
    if manifest.platforms.is_empty() || manifest.platforms.iter().any(|p| p == current) {
        return Ok(());
    }
    Err(CoreError::PlatformUnsupported {
        tool: manifest.name.clone(),
        platforms: manifest.platforms.clone(),
        current: current.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse;
    use std::fs;
    use std::path::PathBuf;

    struct Fixture {
        paths: Paths,
    }

    fn fixture(label: &str) -> Fixture {
        let root = env::temp_dir().join(format!("christy-runtime-{}-{label}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let repo = root.join("repo");
        fs::create_dir_all(repo.join("tools")).unwrap();
        Fixture {
            paths: Paths {
                tools_dir: repo.join("tools"),
                repo,
                repo_source: crate::paths::RepoSource::EnvVar,
                config_dir: root.join("config"),
                state_dir: root.join("state"),
            },
        }
    }

    fn manifest(runtime: &str, entry: &str, extra: &str) -> Manifest {
        parse(&format!(
            "schema = 1\nname = \"demo\"\ndescription = \"d\"\nruntime = \"{runtime}\"\nentry = \"{entry}\"\n{extra}"
        ))
        .unwrap()
    }

    fn touch(path: PathBuf) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, "").unwrap();
    }

    fn os(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn python_runs_through_the_tools_own_venv() {
        let fx = fixture("python");
        touch(fx.paths.tool_env_dir("demo").join("bin/python"));
        let plan = plan(&fx.paths, &manifest("python", "main.py", ""), os(&["-h", "x y"])).unwrap();

        assert_eq!(plan.program, fx.paths.tool_env_dir("demo").join("bin/python").into_os_string());
        assert_eq!(plan.args[0], fx.paths.tools_dir.join("demo/main.py").into_os_string());
        assert_eq!(&plan.args[1..], os(&["-h", "x y"]).as_slice());
    }

    #[test]
    fn missing_venv_points_at_the_setup_script() {
        let fx = fixture("noenv");
        let m = manifest("python", "main.py", "[setup]\nscript = \"setup.sh\"\n");
        match plan(&fx.paths, &m, vec![]) {
            Err(CoreError::EnvMissing { setup_script, .. }) => {
                assert_eq!(setup_script, Some(fx.paths.tools_dir.join("demo/setup.sh")));
            }
            other => panic!("expected EnvMissing, got {other:?}"),
        }
    }

    #[test]
    fn bash_and_node_use_the_interpreter_from_path() {
        let fx = fixture("interp");
        let bash = plan(&fx.paths, &manifest("bash", "run.sh", ""), vec![]).unwrap();
        assert_eq!(bash.program, OsString::from("bash"));
        let node = plan(&fx.paths, &manifest("node", "index.js", ""), vec![]).unwrap();
        assert_eq!(node.program, OsString::from("node"));
    }

    #[test]
    fn binary_runs_the_entry_directly_once_built() {
        let fx = fixture("binary");
        let m = manifest("binary", "bin/demo", "");
        assert!(matches!(plan(&fx.paths, &m, vec![]), Err(CoreError::BinaryMissing { .. })));

        touch(fx.paths.tools_dir.join("demo/bin/demo"));
        let plan = plan(&fx.paths, &m, os(&["a"])).unwrap();
        assert_eq!(plan.program, fx.paths.tools_dir.join("demo/bin/demo").into_os_string());
        assert_eq!(plan.args, os(&["a"]));
    }

    #[test]
    fn platform_list_is_enforced() {
        let fx = fixture("platform");
        let other = if env::consts::OS == "linux" { "macos" } else { "linux" };
        let m = manifest("bash", "run.sh", &format!("platforms = [\"{other}\"]\n"));
        assert!(matches!(plan(&fx.paths, &m, vec![]), Err(CoreError::PlatformUnsupported { .. })));

        let here = manifest("bash", "run.sh", &format!("platforms = [\"{}\"]\n", env::consts::OS));
        assert!(plan(&fx.paths, &here, vec![]).is_ok());
    }

    #[test]
    fn env_vars_are_absolute_and_complete() {
        let fx = fixture("env");
        let plan = plan(&fx.paths, &manifest("bash", "run.sh", ""), vec![]).unwrap();
        let keys: Vec<&str> = plan.env.iter().map(|(k, _)| *k).collect();
        assert_eq!(
            keys,
            ["CHRISTY_HOME", "CHRISTY_TOOL_DIR", "CHRISTY_STATE_DIR", "CHRISTY_VERSION"]
        );
    }
}
