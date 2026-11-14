"""Runs the conversion for a planned list of jobs and collects the results."""

from __future__ import annotations

import messages as msg
from converter import convert_image
from models import (
    DEST_REPLACE,
    STATUS_CONVERTED,
    STATUS_ERROR,
    STATUS_KEPT,
    STATUS_SKIPPED,
    Job,
    Result,
    Settings,
    Stats,
)
from ui import esc, make_progress, shorten


def run(jobs: list[Job], settings: Settings) -> Stats:
    stats = Stats()
    replace = settings.destination == DEST_REPLACE

    with make_progress() as progress:
        task = progress.add_task(msg.PROGRESS_LABEL, total=len(jobs), current="")
        for job in jobs:
            progress.update(task, current=esc(shorten(job.src.name)))
            if job.skip_reason:
                stats.add(Result(job.src, None, STATUS_SKIPPED, job.src_size, 0, job.skip_reason))
                progress.advance(task)
                continue

            outcome = convert_image(job.src, job.dst, settings, job.src_size)
            if not outcome.ok:
                stats.add(Result(job.src, None, STATUS_ERROR, job.src_size, 0, outcome.detail))
            elif outcome.kept_original:
                stats.add(Result(job.src, None, STATUS_KEPT, job.src_size, outcome.new_size, outcome.detail))
            else:
                detail = outcome.detail
                # The original goes only after its WebP is written and checked
                # (convert_image does both), and never when src is dst.
                if replace and job.src != job.dst:
                    try:
                        job.src.unlink()
                    except OSError as exc:
                        detail = msg.ORIGINAL_NOT_DELETED.format(error=exc.strerror or exc)
                stats.add(Result(job.src, job.dst, STATUS_CONVERTED, job.src_size, outcome.new_size, detail))
            progress.advance(task)
    return stats
