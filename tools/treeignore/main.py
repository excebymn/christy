#!/usr/bin/env python3
"""treeignore entry point.

Runs in the caller's working directory (the browser starts there), so the
christy core must not chdir into the tool folder. Exit code is 0 on success
or cancel, 1 if something failed, 130 on Ctrl+C.

The tree goes to stdout; the header, prompts and status go to stderr (or the
terminal), so redirecting stdout gives a clean file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import messages as msg

try:
    import history
    from models import EXTRA_KEYS, MODE_ALL, MODE_GITIGNORE, MODE_PICK, Options
    from prompts import (
        Cancelled,
        ask_confirm,
        ask_depth,
        ask_excluded,
        ask_extras,
        ask_gitignore_choice,
        ask_long_output,
        ask_no_gitignore_choice,
        ask_save_name,
        browse_folder,
        parse_path_input,
    )
    from renderer import Line, plain, render
    from scanner import build_tree, count_rules
    from ui import console, esc, print_header, print_tree
except ImportError as exc:
    sys.exit(msg.MISSING_DEPENDENCY.format(error=exc))

# A tree longer than this (counting the summary lines) triggers the
# "save it as a .txt?" question, but only on a terminal.
LONG_OUTPUT_LINES = 100


class Fatal(Exception):
    """A problem worth a clear message and exit code 1."""


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(msg.CLI_DEPTH_INVALID.format(value=value))
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="treeignore", description=msg.CLI_DESCRIPTION, epilog=msg.CLI_EPILOG)
    parser.add_argument("path", nargs="?", help=msg.CLI_HELP_PATH)
    parser.add_argument("-L", "--depth", type=positive_int, metavar="N", help=msg.CLI_HELP_DEPTH)
    parser.add_argument("-d", "--dirs-only", dest="dirs_only", action="store_true", help=msg.CLI_HELP_DIRS_ONLY)
    parser.add_argument("-a", "--hidden", action="store_true", help=msg.CLI_HELP_HIDDEN)
    parser.add_argument("-s", "--sizes", action="store_true", help=msg.CLI_HELP_SIZES)
    parser.add_argument("-D", "--dates", action="store_true", help=msg.CLI_HELP_DATES)
    parser.add_argument("-p", "--perms", action="store_true", help=msg.CLI_HELP_PERMS)
    parser.add_argument("-f", "--paths", action="store_true", help=msg.CLI_HELP_PATHS)
    parser.add_argument("-c", "--counts", action="store_true", help=msg.CLI_HELP_COUNTS)
    parser.add_argument("--show-ignored", dest="show_ignored", action="store_true", help=msg.CLI_HELP_SHOW_IGNORED)
    parser.add_argument("--ascii", action="store_true", help=msg.CLI_HELP_ASCII)
    parser.add_argument("--largest-first", dest="largest_first", action="store_true", help=msg.CLI_HELP_LARGEST)
    parser.add_argument("--mixed", action="store_true", help=msg.CLI_HELP_MIXED)
    parser.add_argument("-x", "--exclude", action="append", default=[], metavar="PATH", help=msg.CLI_HELP_EXCLUDE)
    parser.add_argument("--all", action="store_true", help=msg.CLI_HELP_ALL)
    parser.add_argument("-o", "--output", metavar="FILE", help=msg.CLI_HELP_OUTPUT)
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
    """Decide what gets left out. Returns (mode, paths to leave out).

    Showing a tree is read-only, so unlike a zip there is no need to refuse
    when nobody can be asked: without a .gitignore the answer is "everything".
    """
    gitignore = root / ".gitignore"
    ask = interactive and not args.yes

    if args.all:
        return MODE_ALL, extra

    if gitignore.is_file():
        if ask and ask_gitignore_choice(count_rules(gitignore)) == "manual":
            return MODE_PICK, extra | ask_excluded(root)
        return MODE_GITIGNORE, extra

    if extra:
        return MODE_PICK, extra
    if ask and ask_no_gitignore_choice() == "pick":
        return MODE_PICK, ask_excluded(root)
    return MODE_ALL, extra


def gather_options(args: argparse.Namespace, interactive: bool) -> Options:
    """Options come from flags; whatever a flag didn't settle is asked."""
    opts = Options(depth=args.depth, **{key: getattr(args, key) for key in EXTRA_KEYS})
    if not interactive or args.yes:
        return opts

    last_depth, last_extras = history.load()
    asked = False
    if args.depth is None:
        opts.depth = ask_depth(last_depth)
        asked = True
    if not any(getattr(args, key) for key in EXTRA_KEYS):
        chosen = ask_extras(last_extras)
        for key in EXTRA_KEYS:
            setattr(opts, key, key in chosen)
        asked = True
    if asked:
        history.save(opts)
    return opts


def lines_to_text(lines: list[Line]) -> str:
    return "\n".join(plain(line) for line in lines) + "\n"


def write_text_file(path: Path, lines: list[Line]) -> None:
    """Plain text, written to a temp file first and then moved into place."""
    tmp = path.with_name(f".{path.name}.treeignore-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(lines_to_text(lines), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        raise Fatal(msg.WRITE_FAILED.format(error=esc(exc.strerror or exc)))
    finally:
        tmp.unlink(missing_ok=True)


def save_flag_output(lines: list[Line], out_path: Path, args: argparse.Namespace, interactive: bool) -> None:
    if out_path.is_dir():
        raise Fatal(msg.OUTPUT_IS_FOLDER.format(path=esc(out_path)))
    if out_path.exists() and not args.yes:
        if not interactive:
            raise Fatal(msg.OVERWRITE_REFUSED.format(path=esc(out_path)))
        if not ask_confirm(msg.CONFIRM_OVERWRITE.format(path=esc(out_path)), default=False):
            raise Cancelled
    write_text_file(out_path, lines)
    console.print(msg.SAVED.format(lines=len(lines), path=esc(out_path)))


def save_interactive(lines: list[Line], default_name: str) -> None:
    """Ask for a name (pre-filled) until there is a file we may write."""
    while True:
        name = ask_save_name(default_name).strip()
        path = Path(name).expanduser()
        if not path.suffix:
            path = path.with_name(path.name + ".txt")
        path = path.resolve()
        if path.is_dir():
            console.print(msg.OUTPUT_IS_FOLDER.format(path=esc(path)))
            continue
        if path.exists() and not ask_confirm(msg.CONFIRM_OVERWRITE.format(path=esc(path)), default=False):
            continue
        write_text_file(path, lines)
        console.print(msg.SAVED.format(lines=len(lines), path=esc(path)))
        return


def run(args: argparse.Namespace, interactive: bool, stdout_is_terminal: bool) -> int:
    root = resolve_root(args.path, interactive)
    extra = normalise_excludes(args.exclude)
    mode, picked = choose_mode(root, args, extra, interactive)
    opts = gather_options(args, interactive)

    out_path = Path(args.output).expanduser().resolve() if args.output else None
    if out_path is not None and out_path.is_dir():
        out_path = out_path / f"{root.name or 'root'}-tree.txt"
    skip_paths = set()
    if out_path is not None:
        skip_paths = {str(out_path), str(out_path.with_name(f".{out_path.name}.treeignore-tmp"))}

    while True:
        with console.status(msg.SCANNING):
            tree = build_tree(root, mode, picked, skip_paths, opts)
        lines = render(tree, opts)
        if tree.unreadable:
            console.print(msg.UNREADABLE.format(count=tree.unreadable))

        if out_path is not None:
            save_flag_output(lines, out_path, args, interactive)
            return 0

        # Piped or redirected: the caller wants the whole tree, don't ask.
        if interactive and stdout_is_terminal and not args.yes and len(lines) > LONG_OUTPUT_LINES:
            choice = ask_long_output(len(lines))
            if choice == "save":
                save_interactive(lines, f"{root.name or 'root'}-tree.txt")
                return 0
            if choice == "depth":
                opts.depth = ask_depth(opts.depth)
                history.save(opts)
                continue

        print_tree(lines)
        return 0


def main() -> int:
    args = build_parser().parse_args()
    # Prompts need a keyboard and a screen: stdin and stderr stand for those,
    # so the picker keeps working when stdout is redirected to a file.
    interactive = sys.stdin.isatty() and sys.stderr.isatty()

    print_header()
    try:
        return run(args, interactive, sys.stdout.isatty())
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
    except BrokenPipeError:
        # e.g. `| head`: the reader left early, that's fine. Point stdout at
        # devnull so the interpreter doesn't complain again while exiting.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
