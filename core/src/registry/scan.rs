//! Looks at `tools/` on disk: cheap fingerprints first, full parse + validation
//! only when needed.

use std::fs::{self, Metadata};
use std::path::Path;
use std::time::UNIX_EPOCH;

use super::types::{FileStamp, Fingerprint, ToolEntry, ToolState};
use crate::error::CoreError;
use crate::manifest;
use crate::messages as msg;

pub const MANIFEST_FILE: &str = "manifest.toml";

/// One fingerprint per tool folder, sorted by folder name. Loose files are
/// ignored, and so are folders starting with `.` (hidden) or `_` (templates,
/// work in progress, or tools switched off by renaming).
pub fn fingerprints(tools_dir: &Path) -> Result<Vec<Fingerprint>, CoreError> {
    let read = fs::read_dir(tools_dir)
        .map_err(|err| CoreError::io(format!("couldn't read {}", tools_dir.display()), err))?;

    let mut result = Vec::new();
    for entry in read {
        let entry = entry
            .map_err(|err| CoreError::io(format!("couldn't read {}", tools_dir.display()), err))?;
        let dir_name = match entry.file_name().into_string() {
            Ok(name) if !name.starts_with('.') && !name.starts_with('_') => name,
            _ => continue,
        };
        let path = entry.path();
        // `metadata` follows symlinks, so a symlinked tool folder works.
        let Ok(dir_meta) = fs::metadata(&path) else {
            continue;
        };
        if !dir_meta.is_dir() {
            continue;
        }
        let manifest = fs::metadata(path.join(MANIFEST_FILE))
            .ok()
            .filter(Metadata::is_file)
            .map(|meta| stamp(&meta));
        result.push(Fingerprint {
            dir_name,
            dir_mtime_ns: mtime_ns(&dir_meta),
            manifest,
        });
    }
    result.sort_by(|a, b| a.dir_name.cmp(&b.dir_name));
    Ok(result)
}

/// Parses and validates the manifest behind a fingerprint.
pub fn build_entry(tools_dir: &Path, fingerprint: Fingerprint) -> ToolEntry {
    let tool_dir = tools_dir.join(&fingerprint.dir_name);
    let state = match load_manifest(&tool_dir, &fingerprint) {
        Ok(manifest) => ToolState::Valid { manifest },
        Err(reasons) => ToolState::Invalid { reasons },
    };
    ToolEntry { fingerprint, state }
}

fn load_manifest(
    tool_dir: &Path,
    fingerprint: &Fingerprint,
) -> Result<manifest::Manifest, Vec<String>> {
    if fingerprint.manifest.is_none() {
        return Err(vec![msg::manifest_not_found()]);
    }
    let text = fs::read_to_string(tool_dir.join(MANIFEST_FILE))
        .map_err(|err| vec![msg::manifest_unreadable(&err.to_string())])?;
    let parsed = manifest::parse(&text)?;

    let problems = manifest::validate(&parsed, &fingerprint.dir_name, tool_dir);
    if problems.is_empty() {
        Ok(parsed)
    } else {
        Err(problems)
    }
}

/// Stamp of a single file, or `None` if it doesn't exist.
pub fn stamp_file(path: &Path) -> Option<FileStamp> {
    fs::metadata(path)
        .ok()
        .filter(Metadata::is_file)
        .map(|meta| stamp(&meta))
}

fn stamp(meta: &Metadata) -> FileStamp {
    FileStamp {
        mtime_ns: mtime_ns(meta),
        size: meta.len(),
    }
}

fn mtime_ns(meta: &Metadata) -> u64 {
    meta.modified()
        .ok()
        .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
        .map_or(0, |elapsed| elapsed.as_nanos() as u64)
}
