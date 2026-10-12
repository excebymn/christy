"""Rich-based output helpers. No text lives here, it all comes from messages."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
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
from models import STATUS_CLEANED, STATUS_ERROR, Stats

console = Console()

STATUS_LABELS = {
    STATUS_CLEANED: msg.STATUS_CLEANED,
    STATUS_ERROR: msg.STATUS_ERROR,
}


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
        TimeRemainingColumn(),
        console=console,
    )


def print_summary(stats: Stats, out_dir: Optional[Path]) -> None:
    table = Table(title=msg.SUMMARY_TITLE, box=box.ROUNDED, show_lines=False)
    table.add_column(msg.COL_FILE, style="cyan", overflow="fold")
    table.add_column(msg.COL_CATEGORY, justify="center")
    table.add_column(msg.COL_STATUS, justify="center")
    table.add_column(msg.COL_DETAIL, overflow="fold")

    for result in stats.results:
        table.add_row(
            result.path.name,
            result.category,
            STATUS_LABELS.get(result.status, result.status),
            result.detail,
        )

    console.print()
    console.print(table)
    console.print(
        msg.TOTAL_LINE.format(
            total=len(stats.results),
            cleaned=stats.count(STATUS_CLEANED),
            errors=stats.count(STATUS_ERROR),
        )
    )
    if out_dir is not None:
        console.print(msg.COPIES_LOCATION.format(out_dir=out_dir))
