"""Finds the images to convert and decides where each result goes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from models import (
    DEST_BESIDE,
    DEST_CUSTOM,
    DEST_FOLDER,
    DEST_REPLACE,
    IMAGE_EXTS,
    OUTPUT_DIR_NAME,
    WEBP_EXT,
    Job,
    Settings,
)

# Never descend into these: dependency and cache folders, and any hidden folder.
SKIP_DIR_NAMES = {"node_modules", "__pycache__", "venv"}


def is_image(path: Path, include_webp: bool) -> bool:
    ext = path.suffix.lower()
    return ext in IMAGE_EXTS or (include_webp and ext == WEBP_EXT)


def root_of(target: Path) -> Path:
    return target if target.is_dir() else target.parent


def output_root(target: Path, settings: Settings) -> Optional[Path]:
    """The folder results are written under (None when they go next to the originals)."""
    root = root_of(target)
    if settings.destination == DEST_FOLDER:
        return root / OUTPUT_DIR_NAME
    if settings.destination == DEST_CUSTOM and settings.custom_dir is not None:
        return settings.custom_dir
    return None


def gather(target: Path, settings: Settings) -> list[Path]:
    """Every image under target (just the file itself for a single file)."""
    if target.is_file():
        return [target] if is_image(target, True) else []

    skip_output = output_root(target, settings)
    skip_resolved = skip_output.resolve() if skip_output is not None and skip_output.exists() else None
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(target):
        here = Path(dirpath)
        kept = []
        for name in sorted(dirnames):
            child = here / name
            if name.startswith(".") or name in SKIP_DIR_NAMES:
                continue
            if skip_resolved is not None and child.resolve() == skip_resolved:
                continue  # our own output, so reruns don't convert the results again
            kept.append(name)
        dirnames[:] = kept if settings.recursive else []
        for name in sorted(filenames):
            path = here / name
            if path.is_symlink() or name.startswith("."):
                continue
            if is_image(path, settings.include_webp):
                found.append(path)
    return found


def _unique(path: Path, taken: set[Path]) -> Path:
    """a.webp, then a-2.webp, a-3.webp... for names that collide within a run."""
    if path not in taken:
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if candidate not in taken:
            return candidate
        counter += 1


def plan(files: list[Path], target: Path, settings: Settings) -> list[Job]:
    """Decide the output path of every file and which ones to leave alone."""
    root = root_of(target)
    out_root = output_root(target, settings)
    taken: set[Path] = set()
    jobs = []
    for src in files:
        relative = src.relative_to(root)
        base = (out_root / relative) if out_root is not None else src
        dst = base.with_suffix(WEBP_EXT)
        try:
            size = src.stat().st_size
        except OSError:
            size = 0

        reason = ""
        if dst == src:
            # A .webp being recompressed in place; only the replace mode means that.
            if settings.destination != DEST_REPLACE:
                reason = "already a WebP (pick 'replace' to recompress it in place)"
        else:
            dst = _unique(dst, taken)
            if dst.exists() and not settings.overwrite:
                reason = "the WebP already exists"
        taken.add(dst)
        jobs.append(Job(src=src, dst=dst, src_size=size, skip_reason=reason))
    return jobs
