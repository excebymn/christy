"""Rich output helpers. No wording lives here, it all comes from messages."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
    DEST_BESIDE,
    DEST_CUSTOM,
    DEST_FOLDER,
    DEST_REPLACE,
    EXTRA_KEYS,
    STATUS_CONVERTED,
    STATUS_ERROR,
    STATUS_KEPT,
    STATUS_SKIPPED,
    Job,
    Settings,
    Stats,
    human_size,
)

console = Console()

RESULT_LABELS = {
    STATUS_CONVERTED: msg.RESULT_CONVERTED,
    STATUS_KEPT: msg.RESULT_KEPT,
    STATUS_SKIPPED: msg.RESULT_SKIPPED,
    STATUS_ERROR: msg.RESULT_ERROR,
}
MAX_SUMMARY_ROWS = 40
CURRENT_FILE_WIDTH = 40


def esc(value: object) -> str:
    """Escape user-provided text (paths, file names) for rich markup."""
    return escape(str(value))


def shorten(text: str, width: int = CURRENT_FILE_WIDTH) -> str:
    return text if len(text) <= width else "..." + text[-(width - 3):]


def print_header() -> None:
    console.print()
    console.print(Panel.fit(f"{msg.HEADER_TITLE}\n{msg.HEADER_SUBTITLE}", border_style="cyan", padding=(1, 4)))
    console.print()


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


def _destination_label(settings: Settings, out_root: Optional[Path]) -> str:
    if settings.destination == DEST_FOLDER:
        return msg.DEST_LABEL_FOLDER.format(path=esc(out_root))
    if settings.destination == DEST_CUSTOM:
        return msg.DEST_LABEL_CUSTOM.format(path=esc(out_root))
    if settings.destination == DEST_BESIDE:
        return msg.DEST_LABEL_BESIDE
    return msg.DEST_LABEL_REPLACE


def print_preview(target: Path, jobs: list[Job], settings: Settings, out_root: Optional[Path]) -> None:
    table = Table(title=msg.PREVIEW_TITLE, box=box.ROUNDED, show_header=False)
    table.add_column(style="bold")
    table.add_column(overflow="fold")

    quality = msg.QUALITY_LOSSLESS_LABEL if settings.lossless else msg.QUALITY_LABEL.format(value=settings.quality)
    width = msg.WIDTH_LABEL.format(value=settings.max_width) if settings.max_width else msg.WIDTH_ORIGINAL
    tags = [msg.OPTION_TAGS[key] for key in EXTRA_KEYS if getattr(settings, key)]

    table.add_row(msg.ROW_SOURCE, esc(target))
    table.add_row(msg.ROW_IMAGES, str(len(jobs)))
    table.add_row(msg.ROW_SIZE, human_size(sum(job.src_size for job in jobs)))
    table.add_row(msg.ROW_QUALITY, quality)
    table.add_row(msg.ROW_WIDTH, width)
    table.add_row(msg.ROW_DEST, _destination_label(settings, out_root))
    table.add_row(msg.ROW_OPTIONS, ", ".join(tags) or msg.OPTIONS_NONE)

    reasons: dict[str, int] = {}
    for job in jobs:
        if job.skip_reason:
            reasons[job.skip_reason] = reasons.get(job.skip_reason, 0) + 1
    if reasons:
        table.add_row(msg.ROW_SKIPPED, "\n".join(msg.SKIPPED_LINE.format(count=n, reason=esc(r)) for r, n in reasons.items()))

    console.print()
    console.print(table)
    console.print()


def _percent(before: int, after: int) -> str:
    return f"{(1 - after / before) * 100:.0f}%" if before > 0 else "-"


def print_summary(stats: Stats, root: Path, out_root: Optional[Path], replaced: bool) -> None:
    table = Table(title=msg.SUMMARY_TITLE, box=box.ROUNDED)
    table.add_column(msg.COL_FILE, style="cyan", overflow="fold")
    table.add_column(msg.COL_BEFORE, justify="right")
    table.add_column(msg.COL_AFTER, justify="right")
    table.add_column(msg.COL_SAVED, justify="right")
    table.add_column(msg.COL_RESULT)

    for result in stats.results[:MAX_SUMMARY_ROWS]:
        try:
            name = str(result.src.relative_to(root))
        except ValueError:
            name = result.src.name
        converted = result.status == STATUS_CONVERTED
        detail = f"  [dim]{esc(result.detail)}[/dim]" if result.detail else ""
        table.add_row(
            esc(name),
            human_size(result.src_size),
            human_size(result.new_size) if converted else "-",
            _percent(result.src_size, result.new_size) if converted else "-",
            RESULT_LABELS.get(result.status, result.status) + detail,
        )
    if len(stats.results) > MAX_SUMMARY_ROWS:
        table.add_row(msg.SUMMARY_MORE.format(count=len(stats.results) - MAX_SUMMARY_ROWS), "", "", "", "")

    console.print()
    console.print(table)
    console.print(
        msg.TOTAL_LINE.format(
            total=len(stats.results),
            converted=stats.count(STATUS_CONVERTED),
            kept=stats.count(STATUS_KEPT),
            skipped=stats.count(STATUS_SKIPPED),
            errors=stats.count(STATUS_ERROR),
        )
    )
    before, after = stats.total_before, stats.total_after
    if stats.count(STATUS_CONVERTED):
        console.print(
            msg.SAVED_LINE.format(
                saved=human_size(max(0, before - after)),
                percent=_percent(before, after).rstrip("%"),
                before=human_size(before),
                after=human_size(after),
            )
        )
    if replaced:
        console.print(msg.REPLACED_NOTE)
    elif out_root is not None and stats.count(STATUS_CONVERTED):
        console.print(msg.RESULTS_LOCATION.format(path=esc(out_root)))
