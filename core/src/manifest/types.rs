//! Shape of a tool's `manifest.toml` (schema 1).
//!
//! Unknown fields are rejected so typos surface in `doctor` instead of being
//! silently ignored. New fields come with a new `schema` number.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema: u32,
    pub name: String,
    pub version: Option<String>,
    pub description: String,
    pub runtime: Runtime,
    pub entry: String,
    #[serde(default)]
    pub platforms: Vec<String>,
    #[serde(default)]
    pub requires: Requires,
    pub setup: Option<SetupSpec>,
}

/// How the core launches the entry. A Rust or Go tool is just `binary`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Runtime {
    Python,
    Node,
    Bash,
    Binary,
}

impl Runtime {
    pub fn as_str(&self) -> &'static str {
        match self {
            Runtime::Python => "python",
            Runtime::Node => "node",
            Runtime::Bash => "bash",
            Runtime::Binary => "binary",
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Requires {
    /// Commands that must be found in PATH.
    #[serde(default)]
    pub bins: Vec<String>,
    /// Paths (relative to the tool folder) that must exist, e.g.
    /// `node_modules` or a built artifact. Missing ones trigger setup.
    #[serde(default)]
    pub paths: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SetupSpec {
    pub script: String,
    /// Files (relative to the tool folder, e.g. `requirements.txt`) whose
    /// changes mean setup should run again. The script itself is always watched.
    #[serde(default)]
    pub watch: Vec<String>,
}
