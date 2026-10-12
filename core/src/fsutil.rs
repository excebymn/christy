//! Small filesystem helpers shared by the cache and the setup stamps.

use std::fs;
use std::io;
use std::path::Path;

/// Writes to a temp file next to the target, then renames, so a crash or a
/// parallel run never leaves a half-written file behind.
pub fn write_atomic(path: &Path, contents: &[u8]) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut tmp_name = path
        .file_name()
        .map(|name| name.to_os_string())
        .unwrap_or_default();
    tmp_name.push(format!(".tmp{}", std::process::id()));
    let tmp = path.with_file_name(tmp_name);

    fs::write(&tmp, contents)?;
    let renamed = fs::rename(&tmp, path);
    if renamed.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    renamed
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writes_and_replaces_without_leaving_temp_files() {
        let dir = std::env::temp_dir().join(format!("christy-fsutil-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        let file = dir.join("nested").join("data.json");

        write_atomic(&file, b"one").unwrap();
        write_atomic(&file, b"two").unwrap();

        assert_eq!(fs::read_to_string(&file).unwrap(), "two");
        let leftovers: Vec<_> = fs::read_dir(file.parent().unwrap()).unwrap().collect();
        assert_eq!(leftovers.len(), 1);
    }
}
