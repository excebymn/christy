//! Every user-facing string of the core lives here and nowhere else.
//!
//! Logic only calls these functions, so wording can change without touching
//! behavior. Plain text only: styling is applied by the caller.

use std::io;
use std::path::Path;

use crate::deps::Requirement;
use crate::error::UnmetContext;
use crate::paths::RepoSource;

// --- version ---

pub fn version_line() -> String {
    format!("christy {}", env!("CARGO_PKG_VERSION"))
}

// --- help ---

pub const HELP_TAGLINE: &str = "personal CLI ecosystem, one entry point for all your tools";

pub const HELP_SECTION_USAGE: &str = "USAGE";
pub const HELP_USAGE_LINES: [&str; 2] = ["christy <tool> [args...]", "christy <command>"];

pub const HELP_SECTION_COMMANDS: &str = "COMMANDS";
pub const HELP_COMMANDS: [(&str, &str); 5] = [
    ("list", "show available tools"),
    ("doctor", "check the environment and every tool"),
    ("setup [tool]", "set up a tool (all tools that need it if omitted)"),
    ("update", "pull the latest tools and refresh the registry"),
    ("help [tool]", "show this help, or a tool's own help"),
];

pub const HELP_SECTION_OPTIONS: &str = "OPTIONS";
pub const HELP_OPTIONS: [(&str, &str); 2] = [
    ("-h, --help", "show this help"),
    ("-V, --version", "print the version"),
];

pub const HELP_SECTION_TOOLS: &str = "TOOLS";
pub const HELP_NO_TOOLS: &str = "no tools found yet";

pub fn help_tools_unavailable(reason: &str) -> String {
    format!("couldn't load the tool list ({reason})")
}

// --- list ---

pub const LIST_COL_NAME: &str = "NAME";
pub const LIST_COL_VERSION: &str = "VERSION";
pub const LIST_COL_RUNTIME: &str = "RUNTIME";
pub const LIST_COL_DESCRIPTION: &str = "DESCRIPTION";
pub const LIST_NO_VERSION: &str = "-";

pub fn list_no_tools(tools_dir: &Path) -> String {
    format!("No tools found in {}.", tools_dir.display())
}

pub fn list_problems(count: usize) -> String {
    let (noun, verb) = if count == 1 {
        ("tool has", "a problem")
    } else {
        ("tools have", "problems")
    };
    format!("{count} {noun} {verb}. Run `christy doctor` for details.")
}

// --- usage errors ---

pub fn usage_unknown_option(option: &str) -> String {
    format!("unknown option '{option}'. Try `christy --help`.")
}

pub fn usage_no_arguments(command: &str) -> String {
    format!("`{command}` doesn't take any arguments.")
}

pub fn usage_setup_too_many() -> String {
    "`setup` takes at most one tool name.".to_string()
}

pub fn usage_not_utf8() -> String {
    "the command name must be valid UTF-8.".to_string()
}

// --- repo / config ---

pub fn repo_not_found() -> String {
    "couldn't find the christy repo. Set CHRISTY_HOME, or run scripts/setup.sh \
     so it can write ~/.config/christy/config.toml."
        .to_string()
}

pub fn repo_invalid(path: &Path) -> String {
    format!(
        "{} doesn't look like a christy repo (no tools/ folder in it).",
        path.display()
    )
}

pub fn config_error(path: &Path, detail: &str) -> String {
    format!("couldn't read config at {}: {detail}", path.display())
}

// --- tools ---

pub fn unknown_tool(name: &str, suggestions: &[String]) -> String {
    let mut text = format!("unknown tool or command '{name}'.");
    match suggestions {
        [] => text.push_str(" Run `christy list` to see what's available."),
        [one] => text.push_str(&format!(" Did you mean '{one}'?")),
        many => text.push_str(&format!(" Did you mean one of: {}?", many.join(", "))),
    }
    text
}

pub fn invalid_tool(name: &str, reasons: &[String]) -> String {
    let mut text = format!("tool '{name}' can't run because its manifest has problems:");
    for reason in reasons {
        text.push_str(&format!("\n  - {reason}"));
    }
    text
}

pub fn platform_unsupported(tool: &str, platforms: &[String], current: &str) -> String {
    format!(
        "tool '{tool}' only supports {} (this is {current}).",
        platforms.join(", ")
    )
}

pub fn env_missing(tool: &str, expected: &Path, setup_script: Option<&Path>) -> String {
    let mut text = format!(
        "the environment for '{tool}' isn't set up yet (expected {}).",
        expected.display()
    );
    match setup_script {
        Some(script) => text.push_str(&format!(" Run its setup script: {}", script.display())),
        None => text.push_str(" Its manifest doesn't declare a setup script."),
    }
    text
}

pub fn binary_missing(tool: &str, expected: &Path) -> String {
    format!(
        "the executable for '{tool}' doesn't exist yet (expected {}). \
         It is normally built by the tool's setup script.",
        expected.display()
    )
}

pub fn launch_failed(program: &str, source: &io::Error) -> String {
    match source.kind() {
        io::ErrorKind::NotFound => {
            format!("couldn't start '{program}': command not found.")
        }
        io::ErrorKind::PermissionDenied => {
            format!("couldn't start '{program}': permission denied (is it executable?).")
        }
        _ => format!("couldn't start '{program}': {source}"),
    }
}

pub fn plural(count: usize, singular: &str) -> String {
    if count == 1 {
        format!("{count} {singular}")
    } else {
        format!("{count} {singular}s")
    }
}

// --- manifest parsing ---

pub fn manifest_not_found() -> String {
    "manifest.toml not found".to_string()
}

pub fn manifest_unreadable(detail: &str) -> String {
    format!("couldn't read manifest.toml: {detail}")
}

pub fn manifest_syntax(detail: &str) -> String {
    format!("manifest.toml isn't valid TOML: {detail}")
}

pub fn manifest_schema_missing() -> String {
    "manifest.toml is missing the `schema` field (expected an integer such as `schema = 1`)"
        .to_string()
}

pub fn manifest_schema_unsupported(found: i64, supported: u32) -> String {
    if found > supported as i64 {
        format!(
            "manifest uses schema {found}, but this christy only understands up to schema \
             {supported}. Rebuild the core after updating."
        )
    } else {
        format!("manifest schema {found} is not valid (expected {supported}).")
    }
}

pub fn manifest_invalid(detail: &str) -> String {
    format!("manifest.toml has an invalid field: {}", detail.trim())
}

// --- manifest validation ---

pub fn name_invalid(name: &str) -> String {
    format!(
        "name '{name}' is invalid (use lowercase letters, digits, '-' or '_', \
         starting with a letter or digit)"
    )
}

pub fn name_mismatch(name: &str, dir_name: &str) -> String {
    format!("name '{name}' doesn't match its folder name '{dir_name}'")
}

pub fn name_reserved(name: &str) -> String {
    format!("name '{name}' is reserved for a built-in command")
}

pub fn description_empty() -> String {
    "description is empty".to_string()
}

pub fn entry_empty() -> String {
    "entry is empty".to_string()
}

pub fn path_not_relative(field: &str, value: &str) -> String {
    format!("{field} '{value}' must be a relative path inside the tool folder")
}

pub fn entry_missing(entry: &str) -> String {
    format!("entry file '{entry}' doesn't exist")
}

pub fn setup_script_missing(script: &str) -> String {
    format!("setup script '{script}' doesn't exist")
}

pub fn platform_unknown(platform: &str) -> String {
    format!("unknown platform '{platform}' (expected 'linux' or 'macos')")
}

pub fn bin_invalid(bin: &str) -> String {
    format!("requires.bins entry '{bin}' must be a plain command name")
}

pub fn watch_file_missing(path: &str) -> String {
    format!("watched file '{path}' (setup.watch) doesn't exist")
}

// --- requirements and setup ---

pub const PROMPT_UNCLEAR: &str = "Please answer y or n.";
pub const ASK_RUN_SETUP: &str = "Run its setup script now?";

pub fn requirement(requirement: &Requirement) -> String {
    match requirement {
        Requirement::Command(name) => format!("command '{name}' was not found in PATH"),
        Requirement::Environment(path) => {
            format!("its environment is missing (expected {})", path.display())
        }
        Requirement::Executable(path) => {
            format!("its executable hasn't been built yet (expected {})", path.display())
        }
        Requirement::Path(path) => format!("{} doesn't exist yet", path.display()),
        Requirement::SetupChanged => "its setup files changed since the last setup".to_string(),
    }
}

fn requirement_list(missing: &[Requirement]) -> String {
    missing
        .iter()
        .map(|item| format!("\n  - {}", requirement(item)))
        .collect()
}

pub fn needs_setup(tool: &str, missing: &[Requirement]) -> String {
    format!(
        "'{tool}' needs a few things before it can run:{}",
        requirement_list(missing)
    )
}

pub fn running_setup(tool: &str) -> String {
    format!("Running setup for '{tool}'...")
}

pub fn setup_done(tool: &str) -> String {
    format!("Setup for '{tool}' finished.")
}

pub fn setup_failed(tool: &str, code: Option<i32>) -> String {
    match code {
        Some(code) => format!("setup for '{tool}' failed (the script exited with status {code})."),
        None => format!("setup for '{tool}' was interrupted."),
    }
}

pub fn setup_declined(tool: &str) -> String {
    format!("setup was cancelled, so '{tool}' can't run.")
}

pub fn no_setup_script(tool: &str) -> String {
    format!("tool '{tool}' has no setup script (add a [setup] section to its manifest).")
}

pub fn unmet(tool: &str, missing: &[Requirement], context: UnmetContext) -> String {
    let list = requirement_list(missing);
    match context {
        UnmetContext::NeedsSetup => format!(
            "'{tool}' can't run yet:{list}\nRun `christy setup {tool}` to fix this."
        ),
        UnmetContext::NoSetupScript => format!(
            "'{tool}' can't run yet:{list}\nIt has no setup script, so these have to be \
             installed by hand."
        ),
        UnmetContext::AfterSetup => format!(
            "setup for '{tool}' finished, but these are still missing:{list}"
        ),
    }
}

pub fn command_failed(what: &str, code: Option<i32>) -> String {
    match code {
        Some(code) => format!("{what} failed (exit status {code})."),
        None => format!("{what} was interrupted."),
    }
}

// --- `christy setup` ---

pub const SETUP_NOTHING_TO_DO: &str = "Everything is ready, nothing to set up.";

pub fn setup_manual(tool: &str, missing: &[Requirement]) -> String {
    format!(
        "'{tool}' has no setup script, so these have to be installed by hand:{}",
        requirement_list(missing)
    )
}

pub fn setup_summary(done: usize, failed: usize, manual: usize) -> String {
    let mut parts = vec![format!("{done} set up")];
    if failed > 0 {
        parts.push(format!("{failed} failed"));
    }
    if manual > 0 {
        parts.push(format!("{manual} need manual installs"));
    }
    parts.join(", ")
}

// --- `christy doctor` ---

pub fn doctor_title() -> String {
    format!("christy {} doctor", env!("CARGO_PKG_VERSION"))
}

pub const DOCTOR_SECTION_ENV: &str = "ENVIRONMENT";
pub const DOCTOR_SECTION_TOOLS: &str = "TOOLS";

pub const TAG_OK: &str = "ok";
pub const TAG_NOTE: &str = "note";
pub const TAG_WARN: &str = "warn";
pub const TAG_FAIL: &str = "fail";
pub const TAG_READY: &str = "ready";
pub const TAG_SETUP: &str = "setup";
pub const TAG_INVALID: &str = "invalid";
pub const TAG_SKIPPED: &str = "skipped";

pub const DOCTOR_LABEL_REPO: &str = "repo";
pub const DOCTOR_LABEL_TOOLS_DIR: &str = "tools folder";
pub const DOCTOR_LABEL_CONFIG: &str = "config file";
pub const DOCTOR_LABEL_STATE: &str = "state folder";
pub const DOCTOR_LABEL_CACHE: &str = "registry cache";
pub const DOCTOR_LABEL_BASH: &str = "bash";
pub const DOCTOR_LABEL_GIT: &str = "git";

pub fn repo_source_text(source: RepoSource) -> &'static str {
    match source {
        RepoSource::EnvVar => "via CHRISTY_HOME",
        RepoSource::ConfigFile => "via config.toml",
        RepoSource::NextToBinary => "found next to the binary",
    }
}

pub fn doctor_repo_ok(path: &Path, source: RepoSource) -> String {
    format!("{} ({})", path.display(), repo_source_text(source))
}

pub fn doctor_tools_dir(path: &Path) -> String {
    path.display().to_string()
}

pub fn doctor_config_present(path: &Path) -> String {
    path.display().to_string()
}

pub fn doctor_config_absent(path: &Path) -> String {
    format!("not present at {} (optional)", path.display())
}

pub fn doctor_state_ok(path: &Path) -> String {
    format!("{} (writable)", path.display())
}

pub fn doctor_state_fail(path: &Path, detail: &str) -> String {
    format!("can't write to {}: {detail}", path.display())
}

pub const DOCTOR_CACHE_OK: &str = "rebuilt and saved";
pub const DOCTOR_CACHE_UNSAVED: &str =
    "couldn't be saved; everything still works, but each run rescans tools/";

pub fn doctor_bash_ok(path: &Path) -> String {
    path.display().to_string()
}

pub const DOCTOR_BASH_MISSING: &str = "not found, setup scripts can't run";
pub const DOCTOR_GIT_OK: &str = "git checkout, `christy update` can pull";
pub const DOCTOR_GIT_NONE: &str = "not a git checkout, `christy update` can't pull";
pub const DOCTOR_NO_TOOLS: &str = "no tools found";

pub fn doctor_tool_ready(runtime: &str, version: Option<&str>) -> String {
    match version {
        Some(version) => format!("{runtime}, version {version}"),
        None => runtime.to_string(),
    }
}

pub fn doctor_tool_needs_setup(has_script: bool) -> &'static str {
    if has_script {
        "needs setup (offered on first run)"
    } else {
        "missing requirements, and no setup script"
    }
}

pub const DOCTOR_TOOL_INVALID: &str = "invalid manifest";

pub fn doctor_tool_skipped(platforms: &[String], current: &str) -> String {
    format!("only supports {} (this is {current})", platforms.join(", "))
}

pub fn doctor_summary(ready: usize, setup: usize, invalid: usize, skipped: usize) -> String {
    let mut parts = vec![format!("{ready} ready")];
    if setup > 0 {
        parts.push(format!("{setup} need setup"));
    }
    if invalid > 0 {
        parts.push(format!("{invalid} invalid"));
    }
    if skipped > 0 {
        parts.push(format!("{skipped} skipped"));
    }
    parts.join(", ")
}

// --- `christy update` ---

pub const UPDATE_PULLING: &str = "Pulling the latest changes...";
pub const UPDATE_NOT_GIT: &str = "This repo isn't a git checkout, skipping the pull.";
pub const UPDATE_CORE_CHANGED: &str = "The core changed, rebuilding it...";
pub const UPDATE_NO_TOOL_CHANGES: &str = "No tool changes.";

pub fn update_core_rebuilt(path: &Path) -> String {
    format!("Core rebuilt: {}", path.display())
}

pub fn update_tools_found(count: usize) -> String {
    format!("{} found.", plural(count, "tool"))
}

pub fn update_diff_line(label: &str, names: &[String]) -> String {
    format!("  {label:<8} {}", names.join(", "))
}

pub fn update_needs_setup(names: &[String]) -> String {
    format!(
        "These tools need setup before first use: {}. They'll offer it when you run \
         them, or run `christy setup`.",
        names.join(", ")
    )
}
