#!/usr/bin/env python3
"""cleanmeta entry point.

Runs in the caller's working directory (the browser starts there), so the
christy core must not chdir into the tool folder. Exit code is 0 on success,
1 if any file failed, 130 on Ctrl+C.
"""

from __future__ import annotations

import argparse
import sys

import messages as msg

try:
    from pipeline import run
    from prompts import ask_mode, ask_path, ask_types, confirm_overwrite
    from scanner import CATEGORY_EXTS, output_dir
    from models import STATUS_ERROR
    from ui import console, print_header, print_summary
except ImportError as exc:
    sys.exit(msg.MISSING_DEPENDENCY.format(error=exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cleanmeta", description=msg.CLI_DESCRIPTION)
    parser.add_argument("path", nargs="?", help=msg.CLI_HELP_PATH)
    parser.add_argument("--types", nargs="+", choices=sorted(CATEGORY_EXTS))
    parser.add_argument("--mode", choices=["overwrite", "copy"])
    parser.add_argument("-y", "--yes", action="store_true", help=msg.CLI_HELP_YES)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    print_header()
    target = ask_path(args.path)
    active_types = ask_types(args.types)
    mode = ask_mode(args.mode)

    if mode == "overwrite" and not args.yes and not confirm_overwrite():
        console.print(msg.CANCELLED)
        return 0

    console.print(msg.LOOKING_IN.format(target=target))
    console.print(msg.TYPES_LABEL.format(types=", ".join(sorted(active_types))))
    console.print(msg.MODE_LABEL.format(mode=mode))

    stats = run(target, active_types, mode)
    if stats.results:
        print_summary(stats, output_dir(target, mode))
    return 1 if stats.count(STATUS_ERROR) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print(f"\n{msg.CANCELLED}")
        sys.exit(130)
