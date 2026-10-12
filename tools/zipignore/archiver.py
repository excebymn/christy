"""Writes the zip. Output goes to a temp file first, then an atomic replace."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Callable, Optional

from models import ArchiveReport, FileEntry


def archive_root_name(root: Path) -> str:
    return root.name or "archive"


def temp_path_for(out_path: Path) -> Path:
    return out_path.with_name(f".{out_path.name}.zipignore-tmp")


def resolve_output(cli_output: Optional[str], root: Path) -> Path:
    default_name = f"{archive_root_name(root)}.zip"
    if not cli_output:
        return (Path.cwd() / default_name).resolve()
    target = Path(cli_output).expanduser()
    if target.is_dir():
        target = target / default_name
    return target.resolve()


def build_zip(
    root: Path,
    files: list[FileEntry],
    out_path: Path,
    flat: bool,
    on_file: Optional[Callable[[FileEntry], None]] = None,
) -> ArchiveReport:
    """Zip `files` (paths under root). Per-file problems are collected, not raised.

    Raises OSError only when the zip itself can't be created or finalised.
    """
    report = ArchiveReport(out_path=out_path)
    prefix = "" if flat else f"{archive_root_name(root)}/"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = temp_path_for(out_path)

    try:
        # strict_timestamps=False clamps pre-1980 mtimes instead of raising.
        with zipfile.ZipFile(
            tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6, strict_timestamps=False
        ) as zout:
            for entry in files:
                try:
                    zout.write(entry.path, prefix + entry.rel)
                except OSError as exc:
                    report.errors.append((entry.rel, exc.strerror or str(exc)))
                else:
                    report.added += 1
                    report.added_bytes += entry.size
                if on_file is not None:
                    on_file(entry)

        if report.added:
            os.replace(tmp, out_path)
            report.zip_size = out_path.stat().st_size
    finally:
        tmp.unlink(missing_ok=True)

    return report
