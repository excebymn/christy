#!/usr/bin/env python3
"""webpify entry point.

Runs in the caller's working directory (the browser starts there), so the
christy core must not chdir into the tool folder. Exit code is 0 on success or
cancel, 1 if something failed (including individual images that couldn't be
converted), 130 on Ctrl+C.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import messages as msg

try:
    import history
    from PIL import features
    from models import (
        DEST_BESIDE,
        DEST_CUSTOM,
        DEST_FOLDER,
        DEST_REPLACE,
        EXTRA_KEYS,
        STATUS_CONVERTED,
        STATUS_ERROR,
        Settings,
        human_size,
    )
    from pipeline import run as run_jobs
    from prompts import (
        Cancelled,
        ask_confirm,
        ask_custom_dir,
        ask_destination,
        ask_extras,
        ask_max_width,
        ask_quality,
        browse,
        parse_path_input,
    )
    from scanner import gather, is_image, output_root, plan, root_of
    from ui import console, esc, print_header, print_preview, print_summary
except ImportError as exc:
    sys.exit(msg.MISSING_DEPENDENCY.format(error=exc))


class Fatal(Exception):
    """A problem worth a clear message and exit code 1."""


def ranged_int(low: int, high: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError:
            number = low - 1
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(msg.CLI_NUMBER_INVALID.format(value=value))
        return number

    return parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="webpify", description=msg.CLI_DESCRIPTION, epilog=msg.CLI_EPILOG)
    parser.add_argument("path", nargs="?", help=msg.CLI_HELP_PATH)
    parser.add_argument("-q", "--quality", type=ranged_int(1, 100), metavar="N", help=msg.CLI_HELP_QUALITY)
    parser.add_argument("--lossless", action="store_true", help=msg.CLI_HELP_LOSSLESS)
    parser.add_argument("-w", "--max-width", dest="max_width", type=ranged_int(16, 20000), metavar="PX", help=msg.CLI_HELP_WIDTH)
    parser.add_argument("--no-subfolders", dest="no_subfolders", action="store_true", help=msg.CLI_HELP_NO_SUBFOLDERS)
    parser.add_argument("--keep-metadata", dest="keep_metadata", action="store_true", help=msg.CLI_HELP_KEEP_METADATA)
    parser.add_argument("--overwrite", action="store_true", help=msg.CLI_HELP_OVERWRITE)
    parser.add_argument("--include-webp", dest="include_webp", action="store_true", help=msg.CLI_HELP_INCLUDE_WEBP)
    where = parser.add_mutually_exclusive_group()
    where.add_argument("-o", "--output", metavar="DIR", help=msg.CLI_HELP_OUTPUT)
    where.add_argument("--beside", action="store_true", help=msg.CLI_HELP_BESIDE)
    where.add_argument("--replace", action="store_true", help=msg.CLI_HELP_REPLACE)
    parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", help=msg.CLI_HELP_DRY_RUN)
    parser.add_argument("-y", "--yes", action="store_true", help=msg.CLI_HELP_YES)
    return parser


def resolve_target(cli_path: Optional[str], interactive: bool) -> Path:
    if cli_path:
        target = parse_path_input(cli_path)
    elif interactive:
        target = browse(Path.cwd())
    else:
        console.print(msg.NO_BROWSER_TERMINAL)
        return Path.cwd().resolve()
    if not target.exists():
        raise Fatal(msg.PATH_NOT_FOUND.format(path=esc(target)))
    if target.is_file() and not is_image(target, True):
        raise Fatal(msg.NOT_AN_IMAGE.format(path=esc(target)))
    return target


def gather_settings(args: argparse.Namespace, interactive: bool, single: bool) -> Settings:
    """Flags settle what they cover; whatever they don't is asked."""
    settings = Settings()
    ask = interactive and not args.yes
    last = history.load() if ask else {}
    asked = False

    if args.lossless:
        settings.lossless, settings.quality = True, 100
    elif args.quality:
        settings.quality = args.quality
    elif ask:
        settings.quality, settings.lossless = ask_quality(last)
        asked = True

    if args.max_width:
        settings.max_width = args.max_width
    elif ask:
        settings.max_width = ask_max_width(last.get("max_width"))
        asked = True

    flags_given = args.no_subfolders or args.keep_metadata or args.overwrite or args.include_webp
    if flags_given or not ask:
        settings.recursive = not args.no_subfolders
        settings.keep_metadata = args.keep_metadata
        settings.overwrite = args.overwrite
        settings.include_webp = args.include_webp
    else:
        checked = set(last["options"]) if "options" in last else {"recursive"}
        chosen = ask_extras(single, checked)
        settings.recursive = single or "recursive" in chosen
        for key in EXTRA_KEYS:
            if key != "recursive":
                setattr(settings, key, key in chosen)
        asked = True

    if args.replace:
        settings.destination = DEST_REPLACE
    elif args.beside:
        settings.destination = DEST_BESIDE
    elif args.output:
        settings.destination, settings.custom_dir = DEST_CUSTOM, parse_path_input(args.output)
    elif ask:
        settings.destination = ask_destination()
        if settings.destination == DEST_CUSTOM:
            settings.custom_dir = ask_custom_dir()

    if asked:
        history.save(settings)
    return settings


def confirm_run(args: argparse.Namespace, interactive: bool, settings: Settings, jobs: list) -> None:
    """Nothing is written before this passes. Replacing originals is always
    confirmed in a terminal, even with -y."""
    todo = [job for job in jobs if not job.skip_reason]
    if settings.destination == DEST_REPLACE:
        if interactive:
            size = human_size(sum(job.src_size for job in todo))
            if not ask_confirm(msg.CONFIRM_REPLACE.format(count=len(todo), size=size), default=False):
                raise Cancelled
        elif not args.yes:
            raise Fatal(msg.NEEDS_YES_REPLACE)
    elif interactive and not args.yes:
        if not ask_confirm(msg.CONFIRM_START.format(count=len(todo)), default=True):
            raise Cancelled


def run(args: argparse.Namespace, interactive: bool) -> int:
    if not features.check("webp"):
        raise Fatal(msg.NO_WEBP_SUPPORT)

    print_header()
    target = resolve_target(args.path, interactive)
    settings = gather_settings(args, interactive, target.is_file())
    out_root = output_root(target, settings)

    with console.status(msg.SCANNING):
        files = gather(target, settings)
    if not files:
        console.print(msg.NOTHING_FOUND)
        return 1
    jobs = plan(files, target, settings)
    print_preview(target, jobs, settings, out_root)

    if not any(not job.skip_reason for job in jobs):
        console.print(msg.NOTHING_TO_CONVERT)
        return 1
    if args.dry_run:
        for job in jobs:
            print(f"{job.src} -> {job.dst}" if not job.skip_reason else f"{job.src} (skipped: {job.skip_reason})")
        return 0

    confirm_run(args, interactive, settings, jobs)

    stats = run_jobs(jobs, settings)
    replaced = settings.destination == DEST_REPLACE and stats.count(STATUS_CONVERTED) > 0
    print_summary(stats, root_of(target), out_root, replaced)
    return 1 if stats.count(STATUS_ERROR) else 0


def main() -> int:
    args = build_parser().parse_args()
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    try:
        return run(args, interactive)
    except Cancelled:
        console.print(msg.CANCELLED)
        return 0
    except Fatal as exc:
        console.print(str(exc))
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print(f"\n{msg.CANCELLED}")
        sys.exit(130)
