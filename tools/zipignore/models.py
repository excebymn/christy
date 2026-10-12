"""Plain data containers and tiny helpers shared across zipignore modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# How the file list is decided.
MODE_GITIGNORE = "gitignore"  # follow the folder's .gitignore files
MODE_PICK = "pick"            # leave out what the user picked
MODE_ALL = "all"              # everything

# Why something was left out.
REASON_GITIGNORE = "gitignore"
REASON_PICKED = "picked"
REASON_BUILTIN = "builtin"
REASON_SYMLINK = "symlink"


@dataclass(frozen=True)
class FileEntry:
    path: Path
    rel: str  # posix-style path relative to the zipped folder
    size: int


@dataclass(frozen=True)
class Skipped:
    rel: str
    is_dir: bool
    reason: str


@dataclass
class ScanResult:
    files: list[FileEntry] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)
    gitignore_files: int = 0

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)


@dataclass
class ArchiveReport:
    out_path: Path
    added: int = 0
    added_bytes: int = 0
    zip_size: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
