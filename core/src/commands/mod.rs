//! Built-in commands and the shared tool lookup.

pub mod doctor;
pub mod help;
pub mod list;
pub mod run;
pub mod setup;
pub mod update;

use crate::error::CoreError;
use crate::manifest::{Manifest, RESERVED_NAMES};
use crate::registry::{Registry, ToolState};
use crate::suggest;

/// Finds a runnable tool by name, or explains why it can't be used:
/// unknown (with suggestions) or present but with a broken manifest.
pub fn find_valid_tool<'a>(registry: &'a Registry, name: &str) -> Result<&'a Manifest, CoreError> {
    match registry.find(name) {
        Some(entry) => match &entry.state {
            ToolState::Valid { manifest } => Ok(manifest),
            ToolState::Invalid { reasons } => Err(CoreError::InvalidTool {
                name: name.to_string(),
                reasons: reasons.clone(),
            }),
        },
        None => {
            let known = registry
                .valid_tools()
                .map(|manifest| manifest.name.as_str())
                .chain(RESERVED_NAMES.iter().copied());
            Err(CoreError::UnknownTool {
                name: name.to_string(),
                suggestions: suggest::closest(name, known),
            })
        }
    }
}
