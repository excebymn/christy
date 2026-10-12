//! `christy doctor`: a full health check of the environment and every tool.
//!
//! A tool that merely needs setup is normal (dependencies are installed on
//! demand), so it's a warning, not a failure. Only real breakage makes
//! `doctor` exit non-zero: an unusable repo or state folder, or a tool with
//! an invalid manifest.

use std::fs;
use std::path::Path;

use crate::deps;
use crate::error::CoreError;
use crate::manifest::Manifest;
use crate::messages as msg;
use crate::paths::Paths;
use crate::registry::{self, Registry, ToolState};
use crate::runtime;
use crate::term::Painter;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Level {
    Ok,
    Note,
    Warn,
    Fail,
}

#[derive(Debug)]
struct Row {
    level: Level,
    tag: &'static str,
    label: String,
    detail: String,
    /// Extra lines shown under the row, aligned with the detail column.
    extra: Vec<String>,
}

impl Row {
    fn new(level: Level, tag: &'static str, label: &str, detail: String) -> Self {
        Self {
            level,
            tag,
            label: label.to_string(),
            detail,
            extra: Vec::new(),
        }
    }

    fn with_extra(mut self, extra: Vec<String>) -> Self {
        self.extra = extra;
        self
    }
}

pub fn run() -> Result<i32, CoreError> {
    let painter = Painter::stdout();
    println!("{}\n", painter.bold(&msg::doctor_title()));

    let paths = match Paths::resolve() {
        Ok(paths) => paths,
        Err(err) => {
            let rows = vec![Row::new(Level::Fail, msg::TAG_FAIL, msg::DOCTOR_LABEL_REPO, err.to_string())];
            print_section(&painter, msg::DOCTOR_SECTION_ENV, &rows);
            return Ok(1);
        }
    };

    let mut env_rows = vec![
        Row::new(
            Level::Ok,
            msg::TAG_OK,
            msg::DOCTOR_LABEL_REPO,
            msg::doctor_repo_ok(&paths.repo, paths.repo_source),
        ),
        Row::new(
            Level::Ok,
            msg::TAG_OK,
            msg::DOCTOR_LABEL_TOOLS_DIR,
            msg::doctor_tools_dir(&paths.tools_dir),
        ),
        config_row(&paths),
        state_row(&paths),
    ];

    let mut tool_rows = Vec::new();
    let mut summary = None;
    match registry::refresh(&paths) {
        Ok(build) => {
            env_rows.push(cache_row(build.saved));
            let (rows, counts) = tool_rows_for(&paths, &build.registry);
            tool_rows = rows;
            summary = Some(counts);
        }
        Err(err) => env_rows.push(Row::new(
            Level::Fail,
            msg::TAG_FAIL,
            msg::DOCTOR_LABEL_CACHE,
            err.to_string(),
        )),
    }
    env_rows.push(bash_row());
    env_rows.push(git_row(&paths));

    print_section(&painter, msg::DOCTOR_SECTION_ENV, &env_rows);
    println!();
    if tool_rows.is_empty() {
        println!("{}", painter.bold(msg::DOCTOR_SECTION_TOOLS));
        println!("  {}", painter.dim(msg::DOCTOR_NO_TOOLS));
    } else {
        print_section(&painter, msg::DOCTOR_SECTION_TOOLS, &tool_rows);
    }
    if let Some(counts) = summary {
        println!("\n{}", msg::doctor_summary(counts.ready, counts.setup, counts.invalid, counts.skipped));
    }

    let failed = env_rows.iter().chain(&tool_rows).any(|row| row.level == Level::Fail);
    Ok(i32::from(failed))
}

fn config_row(paths: &Paths) -> Row {
    let file = paths.config_file();
    if file.is_file() {
        Row::new(Level::Ok, msg::TAG_OK, msg::DOCTOR_LABEL_CONFIG, msg::doctor_config_present(&file))
    } else {
        Row::new(Level::Note, msg::TAG_NOTE, msg::DOCTOR_LABEL_CONFIG, msg::doctor_config_absent(&file))
    }
}

fn state_row(paths: &Paths) -> Row {
    match check_writable(&paths.state_dir) {
        Ok(()) => Row::new(Level::Ok, msg::TAG_OK, msg::DOCTOR_LABEL_STATE, msg::doctor_state_ok(&paths.state_dir)),
        Err(detail) => Row::new(
            Level::Fail,
            msg::TAG_FAIL,
            msg::DOCTOR_LABEL_STATE,
            msg::doctor_state_fail(&paths.state_dir, &detail),
        ),
    }
}

fn cache_row(saved: bool) -> Row {
    if saved {
        Row::new(Level::Ok, msg::TAG_OK, msg::DOCTOR_LABEL_CACHE, msg::DOCTOR_CACHE_OK.to_string())
    } else {
        Row::new(Level::Warn, msg::TAG_WARN, msg::DOCTOR_LABEL_CACHE, msg::DOCTOR_CACHE_UNSAVED.to_string())
    }
}

fn bash_row() -> Row {
    match deps::find_in_path("bash") {
        Some(path) => Row::new(Level::Ok, msg::TAG_OK, msg::DOCTOR_LABEL_BASH, msg::doctor_bash_ok(&path)),
        None => Row::new(Level::Warn, msg::TAG_WARN, msg::DOCTOR_LABEL_BASH, msg::DOCTOR_BASH_MISSING.to_string()),
    }
}

fn git_row(paths: &Paths) -> Row {
    if paths.repo.join(".git").exists() {
        Row::new(Level::Ok, msg::TAG_OK, msg::DOCTOR_LABEL_GIT, msg::DOCTOR_GIT_OK.to_string())
    } else {
        Row::new(Level::Note, msg::TAG_NOTE, msg::DOCTOR_LABEL_GIT, msg::DOCTOR_GIT_NONE.to_string())
    }
}

/// Creates the folder if needed and writes then removes a probe file.
fn check_writable(dir: &Path) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|err| err.to_string())?;
    let probe = dir.join(format!(".doctor-probe-{}", std::process::id()));
    fs::write(&probe, b"").map_err(|err| err.to_string())?;
    let _ = fs::remove_file(&probe);
    Ok(())
}

#[derive(Debug, Default, PartialEq, Eq)]
struct Counts {
    ready: usize,
    setup: usize,
    invalid: usize,
    skipped: usize,
}

fn tool_rows_for(paths: &Paths, registry: &Registry) -> (Vec<Row>, Counts) {
    let mut rows = Vec::new();
    let mut counts = Counts::default();

    for entry in &registry.tools {
        match &entry.state {
            ToolState::Invalid { reasons } => {
                counts.invalid += 1;
                let extra = reasons.iter().map(|reason| format!("- {reason}")).collect();
                rows.push(
                    Row::new(Level::Fail, msg::TAG_INVALID, entry.dir_name(), msg::DOCTOR_TOOL_INVALID.to_string())
                        .with_extra(extra),
                );
            }
            ToolState::Valid { manifest } => rows.push(valid_tool_row(paths, manifest, &mut counts)),
        }
    }
    (rows, counts)
}

fn valid_tool_row(paths: &Paths, manifest: &Manifest, counts: &mut Counts) -> Row {
    if runtime::check_platform(manifest).is_err() {
        counts.skipped += 1;
        return Row::new(
            Level::Note,
            msg::TAG_SKIPPED,
            &manifest.name,
            msg::doctor_tool_skipped(&manifest.platforms, std::env::consts::OS),
        );
    }

    let missing = deps::check(paths, manifest);
    if missing.is_empty() {
        counts.ready += 1;
        return Row::new(
            Level::Ok,
            msg::TAG_READY,
            &manifest.name,
            msg::doctor_tool_ready(manifest.runtime.as_str(), manifest.version.as_deref()),
        );
    }

    counts.setup += 1;
    let extra = missing.iter().map(|item| format!("- {}", msg::requirement(item))).collect();
    Row::new(
        Level::Warn,
        msg::TAG_SETUP,
        &manifest.name,
        msg::doctor_tool_needs_setup(manifest.setup.is_some()).to_string(),
    )
    .with_extra(extra)
}

fn print_section(painter: &Painter, title: &str, rows: &[Row]) {
    println!("{}", painter.bold(title));
    print!("{}", render_rows(painter, rows));
}

fn render_rows(painter: &Painter, rows: &[Row]) -> String {
    let tag_w = rows.iter().map(|row| row.tag.len()).max().unwrap_or(0);
    let label_w = rows.iter().map(|row| row.label.chars().count()).max().unwrap_or(0);
    let mut out = String::new();

    for row in rows {
        let tag = format!("{:<tag_w$}", row.tag);
        let tag = match row.level {
            Level::Ok => painter.green(&tag),
            Level::Note => painter.dim(&tag),
            Level::Warn => painter.yellow(&tag),
            Level::Fail => painter.red(&tag),
        };
        out.push_str(&format!("  {tag}  {:<label_w$}  {}\n", row.label, row.detail));
        for line in &row.extra {
            out.push_str(&format!("  {:<tag_w$}  {:<label_w$}  {line}\n", "", ""));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse;
    use crate::paths::RepoSource;

    fn fixture(label: &str) -> Paths {
        let root = std::env::temp_dir().join(format!("christy-doctor-{}-{label}", std::process::id()));
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

    fn manifest(extra: &str) -> Manifest {
        parse(&format!(
            "schema = 1\nname = \"demo\"\nversion = \"1.0\"\ndescription = \"d\"\nruntime = \"bash\"\nentry = \"run.sh\"\n{extra}"
        ))
        .unwrap()
    }

    #[test]
    fn ready_tools_are_counted_and_described() {
        let paths = fixture("ready");
        let mut counts = Counts::default();
        let row = valid_tool_row(&paths, &manifest(""), &mut counts);
        assert_eq!(row.tag, "ready");
        assert_eq!(row.detail, "bash, version 1.0");
        assert_eq!(counts.ready, 1);
    }

    #[test]
    fn missing_requirements_are_a_warning_with_details() {
        let paths = fixture("missing");
        let mut counts = Counts::default();
        let m = manifest("[requires]\nbins = [\"nope-xyz\"]\n");
        let row = valid_tool_row(&paths, &m, &mut counts);
        assert_eq!(row.level, Level::Warn);
        assert!(row.detail.contains("no setup script"));
        assert!(row.extra[0].contains("nope-xyz"));
        assert_eq!(counts.setup, 1);
    }

    #[test]
    fn wrong_platform_is_skipped_not_failed() {
        let paths = fixture("platform");
        let other = if std::env::consts::OS == "linux" { "macos" } else { "linux" };
        let mut counts = Counts::default();
        let row = valid_tool_row(&paths, &manifest(&format!("platforms = [\"{other}\"]\n")), &mut counts);
        assert_eq!(row.tag, "skipped");
        assert_eq!(row.level, Level::Note);
        assert_eq!(counts.skipped, 1);
    }

    #[test]
    fn rows_align_and_extras_hang_under_the_detail_column() {
        let rows = vec![
            Row::new(Level::Ok, "ready", "cleanmeta", "python".to_string()),
            Row::new(Level::Fail, "invalid", "x", "invalid manifest".to_string())
                .with_extra(vec!["- bad name".to_string()]),
        ];
        let text = render_rows(&Painter::plain(), &rows);
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(lines[0], "  ready    cleanmeta  python");
        assert_eq!(lines[1], "  invalid  x          invalid manifest");
        assert_eq!(lines[2], "                      - bad name");
    }

    #[test]
    fn writable_check_creates_the_folder() {
        let paths = fixture("writable");
        assert!(check_writable(&paths.state_dir).is_ok());
        assert!(paths.state_dir.is_dir());
    }
}
