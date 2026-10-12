#!/usr/bin/env python3
"""zipignore entry point.

Runs in the caller's working directory (the browser starts there), so the
christy core must not chdir into the tool folder. Exit code is 0 on success
or cancel, 1 if something failed (including individual files that couldn't be
added), 130 on Ctrl+C.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import messages as msg

try:
    from archiver import build_zip, resolve_output, temp_path_for
    from models import MODE_ALL, MODE_GITIGNORE, MODE_PICK, ScanResult
    from prompts import (
        Cancelled,
        ask_confirm,
        ask_excluded,
        ask_gitignore_choice,
        ask_no_gitignore_choice,
        ask_sensitive_choice,
        browse_folder,
        parse_path_input,
    )
    from scanner import count_rules, find_sensitive, scan_folder
    from ui import (
        console,
        esc,
        make_progress,
        print_errors,
        print_header,
        print_preview,
        print_sensitive,
        print_summary,
        print_total,
        shorten,
    )
except ImportError as exc:
    sys.exit(msg.MISSING_DEPENDENCY.format(error=exc))


class Fatal(Exception):
    """A problem worth a clear message and exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zipignore",
        description=msg.CLI_DESCRIPTION,
        epilog=msg.CLI_EPILOG,
    )
    parser.add_argument("path", nargs="?", help=msg.CLI_HELP_PATH)
    parser.add_argument("-o", "--output", help=msg.CLI_HELP_OUTPUT)
    parser.add_argument("-x", "--exclude", action="append", default=[], metavar="PATH", help=msg.CLI_HELP_EXCLUDE)
    parser.add_argument("--all", action="store_true", help=msg.CLI_HELP_ALL)
    parser.add_argument("--flat", action="store_true", help=msg.CLI_HELP_FLAT)
    parser.add_argument("-n", "--dry-run", action="store_true", help=msg.CLI_HELP_DRY_RUN)
    parser.add_argument("-y", "--yes", action="store_true", help=msg.CLI_HELP_YES)
    return parser


def normalise_excludes(values: list[str]) -> set[str]:
    out: set[str] = set()
    for value in values:
        text = value.strip().replace("\\", "/")
        while text.startswith("./"):
            text = text[2:]
        text = text.strip("/")
        if text:
            out.add(text)
    return out


def resolve_root(cli_path: Optional[str], interactive: bool) -> Path:
    if cli_path:
        root = parse_path_input(cli_path)
        if not root.exists():
            raise Fatal(msg.PATH_NOT_FOUND.format(path=esc(root)))
        if not root.is_dir():
            raise Fatal(msg.NOT_A_FOLDER.format(path=esc(root)))
        return root
    if not interactive:
        console.print(msg.NO_BROWSER_TERMINAL)
        return Path.cwd().resolve()
    return browse_folder(Path.cwd())


def choose_mode(root: Path, args: argparse.Namespace, extra: set[str], interactive: bool) -> tuple[str, set[str]]:
    """Decide how the file list is built. Returns (mode, folders/paths to leave out)."""
    gitignore = root / ".gitignore"

    if args.all:
        return MODE_ALL, extra

    if gitignore.is_file():
        if interactive and not args.yes:
            if ask_gitignore_choice(count_rules(gitignore)) == "manual":
                return MODE_PICK, extra | ask_excluded(root)
        return MODE_GITIGNORE, extra

    if extra:
        return MODE_PICK, extra
    if not interactive:
        raise Fatal(msg.NEEDS_TERMINAL)
    if ask_no_gitignore_choice() == "all":
        return MODE_ALL, extra
    return MODE_PICK, ask_excluded(root)


def scan_with_status(root: Path, mode: str, picked: set[str], skip_paths: set[str]) -> ScanResult:
    with console.status(msg.SCANNING):
        return scan_folder(root, mode, picked, skip_paths)


def run(args: argparse.Namespace, interactive: bool) -> int:
    root = resolve_root(args.path, interactive)
    extra = normalise_excludes(args.exclude)
    mode, picked = choose_mode(root, args, extra, interactive)

    out_path = resolve_output(args.output, root)
    if out_path.is_dir():
        raise Fatal(msg.OUTPUT_IS_FOLDER.format(path=esc(out_path)))
    skip_paths = {str(out_path), str(temp_path_for(out_path))}

    scan = scan_with_status(root, mode, picked, skip_paths)

    # No .gitignore is protecting this zip, so look for secrets before writing it.
    if mode != MODE_GITIGNORE:
        flagged = find_sensitive(scan.files)
        if flagged:
            print_sensitive(flagged)
            if interactive and not args.yes and ask_sensitive_choice() == "leave":
                picked = picked | {entry.rel for entry in flagged}
                scan = scan_with_status(root, mode, picked, skip_paths)

    if not scan.files:
        console.print(msg.NOTHING_TO_ZIP)
        return 1

    print_preview(root, scan, mode, len(extra), out_path)

    if args.dry_run:
        for entry in scan.files:
            print(entry.rel)
        return 0

    confirmed = False
    if out_path.exists():
        if not args.yes:
            if not interactive:
                raise Fatal(msg.OVERWRITE_REFUSED.format(path=esc(out_path)))
            if not ask_confirm(msg.CONFIRM_OVERWRITE.format(path=esc(out_path)), default=False):
                raise Cancelled
            confirmed = True
    if interactive and not args.yes and not confirmed:
        if not ask_confirm(msg.CONFIRM_ZIP, default=True):
            raise Cancelled

    with make_progress() as progress:
        task = progress.add_task(msg.PROGRESS_LABEL, total=len(scan.files), current="")
        try:
            report = build_zip(
                root,
                scan.files,
                out_path,
                args.flat,
                on_file=lambda entry: progress.update(task, advance=1, current=esc(shorten(entry.rel))),
            )
        except OSError as exc:
            raise Fatal(msg.WRITE_FAILED.format(error=esc(exc.strerror or exc)))
        progress.update(task, current="")

    if report.added:
        print_summary(report)
    print_errors(report)
    print_total(report)
    return 1 if report.errors or not report.added else 0


def main() -> int:
    args = build_parser().parse_args()
    interactive = sys.stdin.isatty() and sys.stdout.isatty()

    print_header()
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
