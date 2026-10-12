//! Replaces the core process with the tool.

use super::LaunchPlan;
use crate::error::CoreError;

/// Never returns on success: the tool takes over this process, keeping its
/// PID, TTY, signal handling, and exit code. Only a failed launch comes back.
#[cfg(unix)]
pub fn exec(plan: LaunchPlan) -> CoreError {
    use std::os::unix::process::CommandExt;
    use std::process::Command;

    let mut command = Command::new(&plan.program);
    command.args(&plan.args);
    for (key, value) in &plan.env {
        command.env(key, value);
    }
    let source = command.exec();
    CoreError::LaunchFailed {
        program: plan.program.to_string_lossy().into_owned(),
        source,
    }
}

#[cfg(not(unix))]
pub fn exec(plan: LaunchPlan) -> CoreError {
    CoreError::LaunchFailed {
        program: plan.program.to_string_lossy().into_owned(),
        source: std::io::Error::other("running tools isn't supported on this platform"),
    }
}
