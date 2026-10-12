"""Walks a folder and decides what goes into the zip."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Optional

from pathspec import GitIgnoreSpec

from models import (
    MODE_GITIGNORE,
    REASON_BUILTIN,
    REASON_GITIGNORE,
    REASON_PICKED,
    REASON_SYMLINK,
    FileEntry,
    ScanResult,
    Skipped,
)

# Never part of a zip, whatever the mode.
ALWAYS_SKIP = {".git"}

# Pre-checked in the manual picker: heavy, regenerable folders.
SUGGESTED_EXCLUDES = (
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    "target",
    "dist",
    "build",
)

# File names that usually hold secrets (matched case-insensitively on the
# base name). Only checked when no .gitignore is protecting the zip.
SENSITIVE_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "credentials.json",
)
SENSITIVE_SAFE = {".env.example", ".env.sample", ".env.template", ".env.dist"}


def read_gitignore(path: Path) -> Optional[GitIgnoreSpec]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return GitIgnoreSpec.from_lines(lines)


def count_rules(path: Path) -> int:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0
    return sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))


def list_top_level_dirs(root: Path) -> list[Path]:
    """Real (non-symlink) subfolders of root, hidden ones included, minus .git."""
    try:
        entries = [
            p for p in root.iterdir()
            if p.name not in ALWAYS_SKIP and p.is_dir() and not p.is_symlink()
        ]
    except OSError:
        return []
    return sorted(entries, key=lambda p: p.name.lower())


def dir_size(path: Path) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


def find_sensitive(files: list[FileEntry]) -> list[FileEntry]:
    hits = []
    for entry in files:
        name = Path(entry.rel).name.lower()
        if name in SENSITIVE_SAFE:
            continue
        if any(fnmatch.fnmatch(name, pattern) for pattern in SENSITIVE_PATTERNS):
            hits.append(entry)
    return hits


class _Walker:
    def __init__(self, root: Path, use_gitignore: bool, picked: set[str], skip_paths: set[str]):
        self.root = root
        self.use_gitignore = use_gitignore
        self.picked = picked
        self.skip_paths = skip_paths
        self.result = ScanResult()

    def run(self) -> ScanResult:
        stack: list[tuple[str, GitIgnoreSpec]] = []
        if self.use_gitignore:
            spec = read_gitignore(self.root / ".gitignore")
            if spec is not None:
                stack.append(("", spec))
                self.result.gitignore_files += 1
        self._walk(self.root, "", stack)
        return self.result

    def _skip(self, rel: str, is_dir: bool, reason: str) -> None:
        self.result.skipped.append(Skipped(rel, is_dir, reason))

    @staticmethod
    def _ignored(rel: str, is_dir: bool, stack: list[tuple[str, GitIgnoreSpec]]) -> bool:
        """Git semantics: the last matching pattern wins, deeper files override."""
        verdict = False
        for prefix, spec in stack:
            sub = rel[len(prefix):]
            if is_dir:
                sub += "/"  # lets dir-only patterns like `build/` match
            include = spec.check_file(sub).include
            if include is not None:
                verdict = include
        return verdict

    def _walk(self, directory: Path, prefix: str, stack: list[tuple[str, GitIgnoreSpec]]) -> None:
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except OSError:
            self.result.unreadable.append(prefix.rstrip("/") or ".")
            return

        for entry in entries:
            rel = prefix + entry.name
            try:
                is_symlink = entry.is_symlink()
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue

            if entry.name in ALWAYS_SKIP:
                self._skip(rel, is_dir, REASON_BUILTIN)
                continue
            if entry.path in self.skip_paths:
                continue  # the zip we are about to write
            if is_symlink:
                self._skip(rel, False, REASON_SYMLINK)
                continue
            if not (is_dir or is_file):
                continue  # sockets, fifos, devices
            if rel in self.picked:
                self._skip(rel, is_dir, REASON_PICKED)
                continue
            if self.use_gitignore and self._ignored(rel, is_dir, stack):
                self._skip(rel, is_dir, REASON_GITIGNORE)
                continue

            if is_dir:
                child_stack = stack
                if self.use_gitignore:
                    spec = read_gitignore(Path(entry.path) / ".gitignore")
                    if spec is not None:
                        child_stack = stack + [(rel + "/", spec)]
                        self.result.gitignore_files += 1
                self._walk(Path(entry.path), rel + "/", child_stack)
            else:
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    size = 0
                self.result.files.append(FileEntry(Path(entry.path), rel, size))


def scan_folder(root: Path, mode: str, picked: set[str], skip_paths: set[str]) -> ScanResult:
    """List what would go into the zip.

    `picked` holds paths relative to root (folders or single files) to leave
    out. `skip_paths` are absolute paths that must never be zipped (the output
    zip and its temp file, which may live inside root).
    """
    return _Walker(root, mode == MODE_GITIGNORE, picked, skip_paths).run()
