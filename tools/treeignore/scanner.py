"""Walks a folder and builds the tree that will be printed."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pathspec import GitIgnoreSpec

from models import (
    MODE_GITIGNORE,
    REASON_GITIGNORE,
    REASON_PICKED,
    Node,
    Options,
    Tree,
)

# Never shown, whatever the options.
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

Stack = list[tuple[str, GitIgnoreSpec]]


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


class _Walker:
    def __init__(self, root: Path, mode: str, picked: set[str], skip_paths: set[str], opts: Options):
        self.root = root
        self.use_gitignore = mode == MODE_GITIGNORE
        self.picked = picked
        self.skip_paths = skip_paths
        self.opts = opts
        self.tree = Tree(root=Node(name=root.name, rel="", kind="dir"))

    def run(self) -> Tree:
        stack: Stack = []
        if self.use_gitignore:
            spec = read_gitignore(self.root / ".gitignore")
            if spec is not None:
                stack.append(("", spec))
                self.tree.gitignore_files += 1
        node = self.tree.root
        node.size = self._fill(node, self.root, "", stack, level=1, recurse=True)
        return self.tree

    # -- helpers --------------------------------------------------------

    def _reason(self, rel: str, is_dir: bool, stack: Stack) -> str:
        if rel in self.picked:
            return REASON_PICKED
        if self.use_gitignore and stack:
            verdict = False
            for prefix, spec in stack:  # root first, deeper files override
                sub = rel[len(prefix):]
                if is_dir:
                    sub += "/"  # lets dir-only patterns like `build/` match
                include = spec.check_file(sub).include
                if include is not None:
                    verdict = include
            if verdict:
                return REASON_GITIGNORE
        return ""

    def _stat(self, entry: os.DirEntry, node: Node) -> None:
        if not self.opts.need_stat:
            return
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            return
        node.mtime = st.st_mtime
        node.mode = st.st_mode
        if node.kind == "file":
            node.size = st.st_size

    def _sort(self, nodes: list[Node]) -> None:
        mixed = self.opts.mixed
        largest = self.opts.largest_first

        def key(node: Node):
            group = 0 if (mixed or node.kind == "dir") else 1
            return (group, -node.size if largest else 0, node.name.lower(), node.name)

        nodes.sort(key=key)

    # -- the walk -------------------------------------------------------

    def _fill(self, node: Node, directory: Path, prefix: str, stack: Stack, level: int, recurse: bool) -> int:
        """Fill node.children with what is shown at this level and return the
        total size of everything inside (when the options need totals).

        `level` is the depth of this folder's children (1 = directly inside
        the picked folder). Past the depth limit nothing is added to the tree;
        the folder is only walked when totals are needed, or counted shallowly
        (recurse=False) when only the item count is needed.
        """
        opts = self.opts
        expand = opts.depth is None or level <= opts.depth
        total = 0
        included = 0

        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except OSError:
            self.tree.unreadable += 1
            return 0

        for entry in entries:
            name = entry.name
            if name in ALWAYS_SKIP:
                continue
            if not opts.hidden and name.startswith("."):
                continue
            if entry.path in self.skip_paths:
                continue  # e.g. the .txt we are about to write
            rel = prefix + name
            try:
                is_symlink = entry.is_symlink()
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue

            if is_symlink:
                if opts.dirs_only:
                    continue
                included += 1
                if expand:
                    try:
                        target = os.readlink(entry.path)
                    except OSError:
                        target = "?"
                    link = Node(name=name, rel=rel, kind="link", target=target)
                    self._stat(entry, link)
                    node.children.append(link)
                    self.tree.shown_files += 1
                continue
            if not (is_dir or is_file):
                continue  # sockets, fifos, devices

            reason = self._reason(rel, is_dir, stack)
            if reason:
                if expand:
                    if is_dir or not opts.dirs_only:
                        self.tree.left_out += 1  # files aren't shown in folders-only mode
                    if is_dir and opts.show_ignored:
                        marker = Node(name=name, rel=rel, kind="dir", ignored=reason)
                        self._stat(entry, marker)
                        node.children.append(marker)
                continue

            if is_dir:
                included += 1
                child = Node(name=name, rel=rel, kind="dir")
                self._stat(entry, child)
                shown_below = opts.depth is None or level + 1 <= opts.depth
                if recurse and (shown_below or opts.need_totals):
                    child_stack = stack
                    if self.use_gitignore:
                        spec = read_gitignore(Path(entry.path) / ".gitignore")
                        if spec is not None:
                            child_stack = stack + [(rel + "/", spec)]
                            self.tree.gitignore_files += 1
                    child.size = self._fill(child, Path(entry.path), rel + "/", child_stack, level + 1, True)
                elif recurse and opts.counts:
                    # Past the depth limit, only the item count is wanted.
                    child_stack = stack
                    if self.use_gitignore:
                        spec = read_gitignore(Path(entry.path) / ".gitignore")
                        if spec is not None:
                            child_stack = stack + [(rel + "/", spec)]
                    self._fill(child, Path(entry.path), rel + "/", child_stack, level + 1, False)
                total += child.size
                if expand:
                    node.children.append(child)
                    self.tree.shown_dirs += 1
            else:
                if not opts.dirs_only:
                    included += 1
                leaf = Node(name=name, rel=rel, kind="file")
                self._stat(entry, leaf)
                total += leaf.size
                if expand and not opts.dirs_only:
                    node.children.append(leaf)
                    self.tree.shown_files += 1

        node.item_count = included
        if expand:
            self._sort(node.children)
        return total


def build_tree(root: Path, mode: str, picked: set[str], skip_paths: set[str], opts: Options) -> Tree:
    """Scan root into a Tree.

    `picked` holds paths relative to root (folders or single files) to leave
    out. `skip_paths` are absolute paths that must never appear (a file we are
    about to write inside root).
    """
    return _Walker(root, mode, picked, skip_paths, opts).run()
