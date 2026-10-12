//! Checks that go beyond parsing: naming rules, safe relative paths, and that
//! the files the manifest points at actually exist.

use std::path::{Component, Path};

use super::types::{Manifest, Runtime};
use crate::messages as msg;

/// Names a tool may not take, because they are built-in commands.
pub const RESERVED_NAMES: &[&str] = &["list", "help", "doctor", "setup", "update", "version"];

const KNOWN_PLATFORMS: &[&str] = &["linux", "macos"];

/// Returns every problem found, so `doctor` can show them all at once.
pub fn validate(manifest: &Manifest, dir_name: &str, tool_dir: &Path) -> Vec<String> {
    let mut problems = Vec::new();

    if !is_valid_name(&manifest.name) {
        problems.push(msg::name_invalid(&manifest.name));
    } else if manifest.name != dir_name {
        problems.push(msg::name_mismatch(&manifest.name, dir_name));
    }
    if RESERVED_NAMES.contains(&manifest.name.as_str()) {
        problems.push(msg::name_reserved(&manifest.name));
    }

    if manifest.description.trim().is_empty() {
        problems.push(msg::description_empty());
    }

    check_entry(manifest, tool_dir, &mut problems);

    if let Some(setup) = &manifest.setup {
        if !is_safe_relative(&setup.script) {
            problems.push(msg::path_not_relative("setup.script", &setup.script));
        } else if !tool_dir.join(&setup.script).is_file() {
            problems.push(msg::setup_script_missing(&setup.script));
        }
        for watched in &setup.watch {
            if !is_safe_relative(watched) {
                problems.push(msg::path_not_relative("setup.watch", watched));
            } else if !tool_dir.join(watched).is_file() {
                problems.push(msg::watch_file_missing(watched));
            }
        }
    }

    for platform in &manifest.platforms {
        if !KNOWN_PLATFORMS.contains(&platform.as_str()) {
            problems.push(msg::platform_unknown(platform));
        }
    }

    for path in &manifest.requires.paths {
        if !is_safe_relative(path) {
            problems.push(msg::path_not_relative("requires.paths", path));
        }
    }

    for bin in &manifest.requires.bins {
        if bin.is_empty() || bin.contains('/') || bin.chars().any(char::is_whitespace) {
            problems.push(msg::bin_invalid(bin));
        }
    }

    problems
}

fn check_entry(manifest: &Manifest, tool_dir: &Path, problems: &mut Vec<String>) {
    if manifest.entry.trim().is_empty() {
        problems.push(msg::entry_empty());
        return;
    }
    if !is_safe_relative(&manifest.entry) {
        problems.push(msg::path_not_relative("entry", &manifest.entry));
        return;
    }
    // A `binary` entry is typically produced by the tool's setup script
    // (cargo build, go build), so it may legitimately not exist yet.
    if manifest.runtime != Runtime::Binary && !tool_dir.join(&manifest.entry).is_file() {
        problems.push(msg::entry_missing(&manifest.entry));
    }
}

fn is_valid_name(name: &str) -> bool {
    let mut chars = name.chars();
    match chars.next() {
        Some(first) if first.is_ascii_lowercase() || first.is_ascii_digit() => {}
        _ => return false,
    }
    chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_')
}

/// Relative, no `..`, no root: the path can't escape the tool folder.
fn is_safe_relative(value: &str) -> bool {
    let path = Path::new(value);
    !value.is_empty()
        && path.is_relative()
        && path
            .components()
            .all(|c| matches!(c, Component::Normal(_) | Component::CurDir))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse::parse;
    use std::fs;

    fn sample(extra: &str) -> Manifest {
        let text = format!(
            "schema = 1\nname = \"demo\"\ndescription = \"A demo\"\nruntime = \"bash\"\nentry = \"run.sh\"\n{extra}"
        );
        parse(&text).expect("sample manifest must parse")
    }

    fn tool_dir_with(files: &[&str]) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "christy-validate-{}-{}",
            std::process::id(),
            files.join("_").replace('/', "-")
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        for file in files {
            let path = dir.join(file);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, "").unwrap();
        }
        dir
    }

    #[test]
    fn a_good_manifest_has_no_problems() {
        let dir = tool_dir_with(&["run.sh"]);
        assert!(validate(&sample(""), "demo", &dir).is_empty());
    }

    #[test]
    fn name_must_match_the_folder() {
        let dir = tool_dir_with(&["run.sh", "other"]);
        let problems = validate(&sample(""), "other", &dir);
        assert!(problems.iter().any(|p| p.contains("doesn't match")));
    }

    #[test]
    fn reserved_names_are_rejected() {
        let dir = tool_dir_with(&["run.sh", "list"]);
        let text = "schema = 1\nname = \"list\"\ndescription = \"x\"\nruntime = \"bash\"\nentry = \"run.sh\"\n";
        let problems = validate(&parse(text).unwrap(), "list", &dir);
        assert!(problems.iter().any(|p| p.contains("reserved")));
    }

    #[test]
    fn entry_must_exist_unless_binary() {
        let dir = tool_dir_with(&["something-else"]);
        assert!(validate(&sample(""), "demo", &dir)
            .iter()
            .any(|p| p.contains("doesn't exist")));

        let text = "schema = 1\nname = \"demo\"\ndescription = \"x\"\nruntime = \"binary\"\nentry = \"bin/demo\"\n";
        assert!(validate(&parse(text).unwrap(), "demo", &dir).is_empty());
    }

    #[test]
    fn watched_files_must_exist_and_stay_inside() {
        let dir = tool_dir_with(&["run.sh", "setup.sh", "requirements.txt"]);
        let ok = sample("[setup]\nscript = \"setup.sh\"\nwatch = [\"requirements.txt\"]\n");
        assert!(validate(&ok, "demo", &dir).is_empty());

        let missing = sample("[setup]\nscript = \"setup.sh\"\nwatch = [\"nope.txt\"]\n");
        assert!(validate(&missing, "demo", &dir).iter().any(|p| p.contains("nope.txt")));

        let escaping = sample("[setup]\nscript = \"setup.sh\"\nwatch = [\"../x\"]\n");
        assert!(validate(&escaping, "demo", &dir).iter().any(|p| p.contains("relative")));
    }

    #[test]
    fn paths_cannot_escape_the_tool_folder() {
        assert!(!is_safe_relative("../evil.sh"));
        assert!(!is_safe_relative("/etc/passwd"));
        assert!(!is_safe_relative(""));
        assert!(is_safe_relative("bin/run.sh"));
        assert!(is_safe_relative("./run.sh"));
    }

    #[test]
    fn name_rules() {
        assert!(is_valid_name("cleanmeta"));
        assert!(is_valid_name("video-convert_2"));
        assert!(!is_valid_name("Clean"));
        assert!(!is_valid_name("-x"));
        assert!(!is_valid_name(""));
        assert!(!is_valid_name("a b"));
    }
}
