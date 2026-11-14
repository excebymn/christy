"""Plain data containers and tiny helpers shared across treeignore modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# How the tree decides what to leave out.
MODE_GITIGNORE = "gitignore"  # follow the folder's .gitignore files
MODE_PICK = "pick"            # leave out what the user picked
MODE_ALL = "all"              # nothing is left out

# Why something was left out.
REASON_GITIGNORE = "gitignore"
REASON_PICKED = "picked"

# Names of the yes/no options, in the order they are offered.
EXTRA_KEYS = (
    "dirs_only",
    "hidden",
    "sizes",
    "dates",
    "perms",
    "paths",
    "counts",
    "show_ignored",
    "ascii",
    "largest_first",
    "mixed",
)


@dataclass
class Options:
    depth: Optional[int] = None  # None = as deep as it goes
    dirs_only: bool = False
    hidden: bool = False
    sizes: bool = False
    dates: bool = False
    perms: bool = False
    paths: bool = False
    counts: bool = False
    show_ignored: bool = False
    ascii: bool = False
    largest_first: bool = False
    mixed: bool = False

    @property
    def need_stat(self) -> bool:
        return self.sizes or self.dates or self.perms or self.largest_first

    @property
    def need_totals(self) -> bool:
        return self.sizes or self.largest_first


@dataclass
class Node:
    name: str
    rel: str            # posix-style path relative to the picked folder
    kind: str           # "dir" | "file" | "link"
    size: int = 0       # files: own size, folders: total of everything inside
    mtime: Optional[float] = None
    mode: Optional[int] = None
    target: str = ""    # links only
    ignored: str = ""   # reason, for left-out folders that are shown as markers
    item_count: Optional[int] = None
    children: list["Node"] = field(default_factory=list)


@dataclass
class Tree:
    root: Node
    shown_dirs: int = 0
    shown_files: int = 0
    left_out: int = 0
    gitignore_files: int = 0
    unreadable: int = 0


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
