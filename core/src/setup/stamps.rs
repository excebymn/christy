//! Remembers what a tool's setup files looked like when setup last succeeded.
//!
//! After a `git pull` changes `requirements.txt` or `setup.sh`, the tool's
//! environment is stale even though nothing is "missing". Comparing stamps
//! catches that. A tool with no recorded stamp (set up by hand, say) is never
//! flagged, so nobody gets nagged about something christy never ran.

use std::collections::BTreeMap;
use std::fs;
use std::io;

use serde::{Deserialize, Serialize};

use crate::fsutil;
use crate::manifest::Manifest;
use crate::paths::Paths;
use crate::registry::{stamp_file, FileStamp};

type Stamps = BTreeMap<String, FileStamp>;

#[derive(Debug, Default, Serialize, Deserialize)]
struct StampFile {
    /// tool name -> (watched file, stamp)
    #[serde(default)]
    tools: BTreeMap<String, Stamps>,
}

fn stamp_path(paths: &Paths) -> std::path::PathBuf {
    paths.state_dir.join("setup-stamps.json")
}

/// The setup script plus every watched file that currently exists.
fn current(paths: &Paths, manifest: &Manifest) -> Stamps {
    let mut stamps = Stamps::new();
    let Some(setup) = &manifest.setup else {
        return stamps;
    };
    let tool_dir = paths.tools_dir.join(&manifest.name);
    for relative in std::iter::once(&setup.script).chain(setup.watch.iter()) {
        if let Some(stamp) = stamp_file(&tool_dir.join(relative)) {
            stamps.insert(relative.clone(), stamp);
        }
    }
    stamps
}

/// Unreadable or corrupt stamp files count as "no stamps": never an error.
fn load(paths: &Paths) -> StampFile {
    fs::read_to_string(stamp_path(paths))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

/// Call after a setup script succeeded.
pub fn record(paths: &Paths, manifest: &Manifest) -> io::Result<()> {
    let mut file = load(paths);
    file.tools
        .insert(manifest.name.clone(), current(paths, manifest));
    let json = serde_json::to_string_pretty(&file).map_err(io::Error::other)?;
    fsutil::write_atomic(&stamp_path(paths), json.as_bytes())
}

/// True only when christy recorded a setup for this tool and its setup files
/// have changed since.
pub fn is_outdated(paths: &Paths, manifest: &Manifest) -> bool {
    match load(paths).tools.get(&manifest.name) {
        Some(recorded) => *recorded != current(paths, manifest),
        None => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse;
    use crate::paths::RepoSource;
    use std::time::Duration;

    fn setup_fixture(label: &str) -> (Paths, Manifest) {
        let root = std::env::temp_dir().join(format!("christy-stamps-{}-{label}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let tool = root.join("repo/tools/demo");
        fs::create_dir_all(&tool).unwrap();
        fs::write(tool.join("setup.sh"), "echo hi").unwrap();
        fs::write(tool.join("requirements.txt"), "rich").unwrap();
        let manifest = parse(
            "schema = 1\nname = \"demo\"\ndescription = \"d\"\nruntime = \"bash\"\nentry = \"run.sh\"\n\
             [setup]\nscript = \"setup.sh\"\nwatch = [\"requirements.txt\"]\n",
        )
        .unwrap();
        let paths = Paths {
            repo: root.join("repo"),
            repo_source: RepoSource::EnvVar,
            tools_dir: root.join("repo/tools"),
            config_dir: root.join("config"),
            state_dir: root.join("state"),
        };
        (paths, manifest)
    }

    #[test]
    fn never_set_up_means_never_outdated() {
        let (paths, manifest) = setup_fixture("never");
        assert!(!is_outdated(&paths, &manifest));
    }

    #[test]
    fn unchanged_files_stay_current() {
        let (paths, manifest) = setup_fixture("same");
        record(&paths, &manifest).unwrap();
        assert!(!is_outdated(&paths, &manifest));
    }

    #[test]
    fn editing_a_watched_file_marks_the_tool_outdated_until_setup_reruns() {
        let (paths, manifest) = setup_fixture("edit");
        record(&paths, &manifest).unwrap();

        std::thread::sleep(Duration::from_millis(20));
        fs::write(paths.tools_dir.join("demo/requirements.txt"), "rich\npillow").unwrap();
        assert!(is_outdated(&paths, &manifest));

        record(&paths, &manifest).unwrap();
        assert!(!is_outdated(&paths, &manifest));
    }

    #[test]
    fn corrupt_stamp_file_is_ignored() {
        let (paths, manifest) = setup_fixture("corrupt");
        fs::create_dir_all(&paths.state_dir).unwrap();
        fs::write(stamp_path(&paths), "{ nope").unwrap();
        assert!(!is_outdated(&paths, &manifest));
    }
}
