"""Runs the cleaning for a chosen target and collects the results."""

from __future__ import annotations

from pathlib import Path

import messages as msg
from cleaners import clean_file
from models import STATUS_CLEANED, STATUS_ERROR, Result, Stats
from scanner import (
    detect_category,
    gather_files,
    output_dir,
    resolve_destination,
    root_of,
)
from ui import console, make_progress


def run(target: Path, active_types: set[str], mode: str) -> Stats:
    stats = Stats()
    root = root_of(target)
    out_dir = output_dir(target, mode)

    if target.is_file():
        category = detect_category(target, active_types)
        if category is None:
            console.print(msg.WRONG_TYPE)
            return stats
        files = [(target, category)]
    else:
        files = gather_files(root, active_types)

    if not files:
        console.print(msg.NOTHING_FOUND)
        return stats

    if out_dir is not None:
        out_dir.mkdir(exist_ok=True)

    with make_progress() as progress:
        task = progress.add_task(msg.PROGRESS_LABEL, total=len(files))
        for src, category in files:
            dst = resolve_destination(root, src, mode, out_dir)
            ok, detail = clean_file(category, src, dst)
            stats.add(
                Result(
                    path=src,
                    category=category,
                    status=STATUS_CLEANED if ok else STATUS_ERROR,
                    detail=detail,
                )
            )
            progress.advance(task)

    return stats
