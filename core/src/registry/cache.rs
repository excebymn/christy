//! Reads and writes `registry.json`. The cache is disposable: anything wrong
//! with it just means a rebuild, never an error.

use std::fs;
use std::io;
use std::path::Path;

use super::types::{Registry, REGISTRY_SCHEMA};
use crate::fsutil;

/// `None` when the file is missing, unreadable, corrupt, or from another schema.
pub fn load(path: &Path) -> Option<Registry> {
    let text = fs::read_to_string(path).ok()?;
    let registry: Registry = serde_json::from_str(&text).ok()?;
    (registry.schema == REGISTRY_SCHEMA).then_some(registry)
}

pub fn save(path: &Path, registry: &Registry) -> io::Result<()> {
    let json = serde_json::to_string_pretty(registry).map_err(io::Error::other)?;
    fsutil::write_atomic(path, json.as_bytes())
}
