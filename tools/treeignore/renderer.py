"""Turns a Tree into printable lines.

Pure Python on purpose: a line is a list of (text, style) segments, so the
same lines can be coloured on a terminal (ui.py) or joined into plain text for
a .txt file. Styles are rich style names; "" means no style.
"""

from __future__ import annotations

import stat
import time
from typing import Iterator

import messages as msg
from models import REASON_GITIGNORE, Node, Options, Tree, human_size

Segment = tuple[str, str]
Line = list[Segment]

STYLE_ROOT = "bold"
STYLE_DIR = "bold blue"
STYLE_LINK = "cyan"
STYLE_DIM = "dim"
STYLE_TAG = "yellow"

# (middle branch, last branch, vertical continuation, blank continuation)
UNICODE_PARTS = ("├── ", "└── ", "│   ", "    ")
ASCII_PARTS = ("|-- ", "`-- ", "|   ", "    ")

DATE_FORMAT = "%Y-%m-%d %H:%M"
DATE_WIDTH = 16
PERMS_WIDTH = 10


def plain(line: Line) -> str:
    return "".join(text for text, _style in line)


def _nodes(node: Node) -> Iterator[Node]:
    for child in node.children:
        yield child
        yield from _nodes(child)


def _size_text(node: Node) -> str:
    if node.kind == "link" or node.ignored:
        return "-"
    return human_size(node.size)


def _meta(node: Node, opts: Options, size_width: int) -> str:
    parts = []
    if opts.perms:
        parts.append(stat.filemode(node.mode) if node.mode is not None else "-" * PERMS_WIDTH)
    if opts.sizes:
        parts.append(_size_text(node).rjust(size_width))
    if opts.dates:
        if node.mtime is None:
            parts.append("-".ljust(DATE_WIDTH))
        else:
            parts.append(time.strftime(DATE_FORMAT, time.localtime(node.mtime)))
    return "[" + "  ".join(parts) + "]  " if parts else ""


def _label(node: Node, opts: Options) -> Line:
    text = node.rel if opts.paths else node.name
    if node.kind == "dir":
        segments: Line = [(text + "/", STYLE_DIR)]
    elif node.kind == "link":
        segments = [(text, STYLE_LINK), (" -> ", STYLE_DIM), (node.target, "")]
    else:
        segments = [(text, "")]

    if node.ignored:
        tag = msg.TAG_IGNORED if node.ignored == REASON_GITIGNORE else msg.TAG_EXCLUDED
        segments.append(("  " + tag, STYLE_TAG))
    elif opts.counts and node.kind == "dir" and node.item_count is not None:
        count = node.item_count
        label = msg.ITEM_ONE if count == 1 else msg.ITEM_MANY.format(count=count)
        segments.append((f"  ({label})", STYLE_DIM))
    return segments


def summary_text(tree: Tree, opts: Options) -> str:
    dirs = tree.shown_dirs
    parts = [msg.SUMMARY_DIR_ONE if dirs == 1 else msg.SUMMARY_DIR_MANY.format(count=dirs)]
    if not opts.dirs_only:
        files = tree.shown_files
        parts.append(msg.SUMMARY_FILE_ONE if files == 1 else msg.SUMMARY_FILE_MANY.format(count=files))
    if tree.left_out:
        parts.append(msg.SUMMARY_LEFT_OUT.format(count=tree.left_out))
    if opts.sizes:
        parts.append(msg.SUMMARY_TOTAL_SIZE.format(size=human_size(tree.root.size)))
    text = ", ".join(parts)
    if opts.depth is not None:
        text += msg.SUMMARY_DEPTH.format(depth=opts.depth)
    return text


def render(tree: Tree, opts: Options) -> list[Line]:
    """The whole output: the tree, a blank line and the summary."""
    middle, last, vertical, blank = ASCII_PARTS if opts.ascii else UNICODE_PARTS
    size_width = max((len(_size_text(n)) for n in _nodes(tree.root)), default=1) if opts.sizes else 0

    lines: list[Line] = [[((tree.root.name + "/") if tree.root.name else "/", STYLE_ROOT)]]

    def walk(node: Node, prefix: str) -> None:
        count = len(node.children)
        for index, child in enumerate(node.children):
            is_last = index == count - 1
            line: Line = [(prefix + (last if is_last else middle), STYLE_DIM)]
            meta = _meta(child, opts, size_width)
            if meta:
                line.append((meta, STYLE_DIM))
            line.extend(_label(child, opts))
            lines.append(line)
            if child.children:
                walk(child, prefix + (blank if is_last else vertical))

    walk(tree.root, "")
    lines.append([])
    lines.append([(summary_text(tree, opts), "")])
    return lines
