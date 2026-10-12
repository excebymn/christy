"""Rich-based output helpers. No text lives here, it all comes from messages.

Everything goes to stderr so that `christy zipignore -n | other` only pipes
the file list.
"""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

import messages as msg
from models import (
    MODE_ALL,
    MODE_GITIGNORE,
    MODE_PICK,
    REASON_BUILTIN,
    REASON_GITIGNORE,
    REASON_PICKED,
    REASON_SYMLINK,
    ArchiveReport,
    FileEntry,
    ScanResult,
    human_size,
)

console = Console(stderr=True)

REASON_LABELS = {
    REASON_GITIGNORE: msg.REASON_GITIGNORE_LABEL,
    REASON_PICKED: msg.REASON_PICKED_LABEL,
    REASON_BUILTIN: msg.REASON_BUILTIN_LABEL,
    REASON_SYMLINK: msg.REASON_SYMLINK_LABEL,
}

MAX_LEFT_OUT_ROWS = 12
MAX_SENSITIVE_LISTED = 8
MAX_ERRORS_LISTED = 15
CURRENT_FILE_WIDTH = 40


def esc(value: object) -> str:
    """Escape user-provided text (paths, file names) for rich markup."""
    return escape(str(value))


def shorten(text: str, width: int = CURRENT_FILE_WIDTH) -> str:
    if len(text) <= width:
        return text
    return "..." + text[-(width - 3):]


def print_header() -> None:
    console.print()
    console.print(
        Panel.fit(
            f"{msg.HEADER_TITLE}\n{msg.HEADER_SUBTITLE}",
            border_style="cyan",
            padding=(1, 4),
        )
    )


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        TextColumn("[dim]{task.fields[current]}"),
        console=console,
    )


def print_sensitive(flagged: list[FileEntry]) -> None:
    console.print(msg.SENSITIVE_WARNING)
    for entry in flagged[:MAX_SENSITIVE_LISTED]:
        console.print(f"  [yellow]{esc(entry.rel)}[/yellow]")
    if len(flagged) > MAX_SENSITIVE_LISTED:
        console.print(msg.SENSITIVE_MORE.format(count=len(flagged) - MAX_SENSITIVE_LISTED))
    console.print()


def _rules_label(mode: str, scan: ScanResult, extra_count: int) -> str:
    if mode == MODE_GITIGNORE:
        label = msg.RULES_GITIGNORE.format(count=scan.gitignore_files)
    elif mode == MODE_PICK:
        label = msg.RULES_PICK
    else:
        label = msg.RULES_ALL
    if extra_count and mode != MODE_PICK:
        label += msg.RULES_EXTRA.format(count=extra_count)
    return label


def _print_left_out(scan: ScanResult) -> None:
    # Group repeats (40 x __pycache__) so the table stays readable.
    groups: dict[tuple[str, bool, str], list[str]] = {}
    for item in scan.skipped:
        if item.reason == REASON_SYMLINK:
            continue
        key = (Path(item.rel).name, item.is_dir, item.reason)
        groups.setdefault(key, []).append(item.rel)
    symlinks = sum(1 for item in scan.skipped if item.reason == REASON_SYMLINK)
    if not groups and not symlinks:
        return

    rows = sorted(groups.items(), key=lambda kv: (not kv[0][1], -len(kv[1]), kv[0][0].lower()))
    table = Table(title=msg.LEFT_OUT_TITLE, box=box.ROUNDED)
    table.add_column(msg.COL_ITEM, style="cyan", overflow="fold")
    table.add_column(msg.COL_WHY)

    for (name, is_dir, reason), rels in rows[:MAX_LEFT_OUT_ROWS]:
        suffix = "/" if is_dir else ""
        if len(rels) == 1:
            label = esc(rels[0] + suffix)
        else:
            label = msg.GROUP_COUNT.format(name=esc(name + suffix), count=len(rels))
        table.add_row(label, REASON_LABELS[reason])
    if len(rows) > MAX_LEFT_OUT_ROWS:
        table.add_row(msg.LEFT_OUT_MORE.format(count=len(rows) - MAX_LEFT_OUT_ROWS), "")
    if symlinks:
        table.add_row(msg.GROUP_COUNT.format(name="symlinks", count=symlinks), msg.REASON_SYMLINK_LABEL)

    console.print()
    console.print(table)


def print_preview(root: Path, scan: ScanResult, mode: str, extra_count: int, out_path: Path) -> None:
    table = Table(title=msg.PREVIEW_TITLE, box=box.ROUNDED, show_header=False)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    table.add_row(msg.ROW_SOURCE, esc(root))
    table.add_row(msg.ROW_RULES, _rules_label(mode, scan, extra_count))
    table.add_row(msg.ROW_FILES, str(len(scan.files)))
    table.add_row(msg.ROW_SIZE, human_size(scan.total_size))
    table.add_row(msg.ROW_OUTPUT, esc(out_path))

    console.print()
    console.print(table)
    _print_left_out(scan)
    if scan.unreadable:
        console.print(msg.UNREADABLE.format(count=len(scan.unreadable)))
    console.print()


def print_summary(report: ArchiveReport) -> None:
    table = Table(title=msg.SUMMARY_TITLE, box=box.ROUNDED, show_header=False)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    table.add_row(msg.ROW_ZIPPED, str(report.added))
    table.add_row(msg.ROW_ORIGINAL, human_size(report.added_bytes))
    table.add_row(msg.ROW_ZIP_SIZE, human_size(report.zip_size))
    if report.added_bytes > 0:
        saved = max(0.0, 1 - report.zip_size / report.added_bytes) * 100
        table.add_row(msg.ROW_SAVED, msg.SAVED_VALUE.format(percent=f"{saved:.0f}"))
    table.add_row(msg.ROW_OUTPUT, esc(report.out_path))

    console.print()
    console.print(table)


def print_errors(report: ArchiveReport) -> None:
    if not report.errors:
        return
    table = Table(title=msg.ERRORS_TITLE, box=box.ROUNDED)
    table.add_column(msg.COL_FILE, style="cyan", overflow="fold")
    table.add_column(msg.COL_PROBLEM, overflow="fold")
    for rel, problem in report.errors[:MAX_ERRORS_LISTED]:
        table.add_row(esc(rel), esc(problem))
    console.print()
    console.print(table)
    if len(report.errors) > MAX_ERRORS_LISTED:
        console.print(msg.ERRORS_MORE.format(count=len(report.errors) - MAX_ERRORS_LISTED))


def print_total(report: ArchiveReport) -> None:
    console.print(
        msg.TOTAL_LINE.format(
            total=report.added + len(report.errors),
            zipped=report.added,
            errors=len(report.errors),
        )
    )
    if report.added:
        console.print(msg.ZIP_LOCATION.format(path=esc(report.out_path)))
    else:
        console.print(msg.NO_ZIP_WRITTEN)
