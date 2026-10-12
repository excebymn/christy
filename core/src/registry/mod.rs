//! The registry: every tool the core knows about, cached on disk.
//!
//! Each run takes a cheap fingerprint of `tools/` and compares it to the
//! cache. Same fingerprint, reuse the cache; different, rebuild and save.

mod cache;
mod scan;
mod types;

use crate::error::CoreError;
use crate::paths::Paths;

pub use scan::stamp_file;
pub use types::{FileStamp, Registry, ToolState};
use types::{Fingerprint, REGISTRY_SCHEMA};

/// A registry plus whether the cache file could be written.
pub struct Build {
    pub registry: Registry,
    pub saved: bool,
}

/// The cache as last saved, without checking that it is still fresh. Used by
/// `update` to see what changed.
pub fn cached(paths: &Paths) -> Option<Registry> {
    cache::load(&paths.registry_file())
}

/// The normal path for every command: cached when fresh, rebuilt when stale.
pub fn load_or_build(paths: &Paths) -> Result<Registry, CoreError> {
    let current = scan::fingerprints(&paths.tools_dir)?;
    if let Some(cached) = cache::load(&paths.registry_file()) {
        if cached.repo == paths.repo && cached.is_fresh(&current) {
            return Ok(cached);
        }
    }
    Ok(build_and_save(paths, current).registry)
}

/// Always rescans, ignoring the cache. For `update`, `setup`, and `doctor`.
pub fn refresh(paths: &Paths) -> Result<Build, CoreError> {
    let current = scan::fingerprints(&paths.tools_dir)?;
    Ok(build_and_save(paths, current))
}

fn build_and_save(paths: &Paths, current: Vec<Fingerprint>) -> Build {
    let registry = Registry {
        schema: REGISTRY_SCHEMA,
        repo: paths.repo.clone(),
        tools: current
            .into_iter()
            .map(|fingerprint| scan::build_entry(&paths.tools_dir, fingerprint))
            .collect(),
    };
    // Best effort: a read-only state dir only costs speed, never correctness.
    // `doctor` reports whether the cache could be saved.
    let saved = cache::save(&paths.registry_file(), &registry).is_ok();
    Build { registry, saved }
}
