//! `christy <tool> [args...]` and `christy help <tool>`.

use std::ffi::OsString;

use super::find_valid_tool;
use crate::error::CoreError;
use crate::paths::Paths;
use crate::registry;
use crate::runtime;
use crate::setup;

/// Resolves the tool, makes sure it's ready (offering its setup if not), builds
/// the launch plan, and hands the process over. Only returns on failure: on
/// success the tool replaces the core.
pub fn run(name: &str, args: Vec<OsString>) -> Result<i32, CoreError> {
    let paths = Paths::resolve()?;
    let registry = registry::load_or_build(&paths)?;
    let manifest = find_valid_tool(&registry, name)?;
    // Platform first: there's no point offering to install things for a tool
    // that can't run here at all.
    runtime::check_platform(manifest)?;
    setup::ensure_ready(&paths, manifest)?;
    let plan = runtime::plan(&paths, manifest, args)?;
    Err(runtime::exec(plan))
}

/// `christy help <tool>` is shorthand for `christy <tool> --help`.
pub fn help(name: &str) -> Result<i32, CoreError> {
    run(name, vec![OsString::from(runtime::HELP_FLAG)])
}
