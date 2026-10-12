"""Finds the files to clean and decides where the results go."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
OOXML_EXTS = {".docx", ".xlsx", ".pptx"}
ODF_EXTS = {".odt", ".ods", ".odp"}
DOCUMENT_EXTS = {".pdf"} | OOXML_EXTS | ODF_EXTS
CODE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".c", ".h", ".cpp",
    ".hpp", ".cc", ".java", ".kt", ".swift", ".rb", ".php", ".cs", ".sh",
    ".lua", ".dart", ".vue", ".html", ".css", ".json", ".yaml", ".yml",
    ".toml", ".md", ".sql",
}
CATEGORY_EXTS = {"image": IMAGE_EXTS, "document": DOCUMENT_EXTS, "code": CODE_EXTS}

OUTPUT_DIR_NAME = "metadata_cleaned"

# Never descend into these: our own output (so reruns don't nest copies),
# VCS internals, and dependency/cache folders.
SKIP_DIRS = {OUTPUT_DIR_NAME, ".git", "node_modules", "__pycache__", ".venv", "venv"}


def detect_category(path: Path, active_types: set[str]) -> Optional[str]:
    ext = path.suffix.lower()
    for category in active_types:
        if ext in CATEGORY_EXTS[category]:
            return category
    return None


def gather_files(root: Path, active_types: set[str]) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            category = detect_category(path, active_types)
            if category:
                found.append((path, category))
    return found


def root_of(target: Path) -> Path:
    return target if target.is_dir() else target.parent


def output_dir(target: Path, mode: str) -> Optional[Path]:
    return root_of(target) / OUTPUT_DIR_NAME if mode == "copy" else None


def resolve_destination(root: Path, src: Path, mode: str, out_dir: Optional[Path]) -> Path:
    if mode == "overwrite":
        return src
    return out_dir / src.relative_to(root)
