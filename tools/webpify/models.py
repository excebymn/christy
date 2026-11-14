"""Plain data containers shared across webpify modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif"}
WEBP_EXT = ".webp"

# Where the results go.
DEST_FOLDER = "folder"    # a new 'webp' folder, originals untouched
DEST_BESIDE = "beside"    # next to each original, originals untouched
DEST_CUSTOM = "custom"    # a folder the user names, originals untouched
DEST_REPLACE = "replace"  # WebP replaces the original (always confirmed)
OUTPUT_DIR_NAME = "webp"

STATUS_CONVERTED = "converted"
STATUS_KEPT = "kept"        # the WebP wasn't smaller, the original stays
STATUS_SKIPPED = "skipped"  # not touched on purpose (output exists, ...)
STATUS_ERROR = "error"

# The yes/no options of the checklist, in the order they are offered.
EXTRA_KEYS = ("recursive", "keep_metadata", "overwrite", "include_webp")

QUALITY_PRESETS = {
    "balanced": 80,
    "smaller": 70,
    "high": 90,
}


@dataclass
class Settings:
    quality: int = 80
    lossless: bool = False
    max_width: Optional[int] = None  # None = keep the original size
    destination: str = DEST_FOLDER
    custom_dir: Optional[Path] = None
    recursive: bool = True
    keep_metadata: bool = False
    overwrite: bool = False
    include_webp: bool = False


@dataclass
class Job:
    src: Path
    dst: Path
    src_size: int
    skip_reason: str = ""  # non-empty = don't convert, report why


@dataclass
class Result:
    src: Path
    dst: Optional[Path]
    status: str
    src_size: int = 0
    new_size: int = 0
    detail: str = ""

    @property
    def saved(self) -> int:
        return self.src_size - self.new_size if self.status == STATUS_CONVERTED else 0


@dataclass
class Stats:
    results: list[Result] = field(default_factory=list)

    def add(self, result: Result) -> None:
        self.results.append(result)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def total_before(self) -> int:
        return sum(r.src_size for r in self.results if r.status == STATUS_CONVERTED)

    @property
    def total_after(self) -> int:
        return sum(r.new_size for r in self.results if r.status == STATUS_CONVERTED)


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
