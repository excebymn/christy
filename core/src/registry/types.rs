//! What the registry cache holds.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::manifest::Manifest;

/// Bump when the on-disk shape changes; an older cache is simply rebuilt.
pub const REGISTRY_SCHEMA: u32 = 1;

/// Modification time + size of a file, enough to notice edits cheaply.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileStamp {
    pub mtime_ns: u64,
    pub size: u64,
}

/// A tool folder's cheap identity. If this is unchanged, the cached parse of
/// its manifest is still good.
///
/// `dir_mtime_ns` changes when files are added, removed, or renamed directly
/// inside the folder (entry file, setup script). `christy update` and
/// `doctor` always rescan, which covers deeper changes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Fingerprint {
    pub dir_name: String,
    pub dir_mtime_ns: u64,
    pub manifest: Option<FileStamp>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "lowercase")]
pub enum ToolState {
    Valid { manifest: Manifest },
    Invalid { reasons: Vec<String> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolEntry {
    pub fingerprint: Fingerprint,
    #[serde(flatten)]
    pub state: ToolState,
}

impl ToolEntry {
    pub fn dir_name(&self) -> &str {
        &self.fingerprint.dir_name
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Registry {
    pub schema: u32,
    pub repo: PathBuf,
    /// Sorted by folder name.
    pub tools: Vec<ToolEntry>,
}

impl Registry {
    /// Valid tools in name order.
    pub fn valid_tools(&self) -> impl Iterator<Item = &Manifest> {
        self.tools.iter().filter_map(|entry| match &entry.state {
            ToolState::Valid { manifest } => Some(manifest),
            ToolState::Invalid { .. } => None,
        })
    }

    pub fn invalid_count(&self) -> usize {
        self.tools
            .iter()
            .filter(|entry| matches!(entry.state, ToolState::Invalid { .. }))
            .count()
    }

    /// Finds a tool by folder name, valid or not. For valid tools the folder
    /// name equals the manifest name (validation enforces it).
    pub fn find(&self, name: &str) -> Option<&ToolEntry> {
        self.tools.iter().find(|entry| entry.dir_name() == name)
    }

    pub fn is_fresh(&self, current: &[Fingerprint]) -> bool {
        self.tools.iter().map(|entry| &entry.fingerprint).eq(current.iter())
    }
}
