"""Interactive prompts. Every question can be skipped with a CLI flag."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from rich.prompt import Confirm, Prompt

import messages as msg
from scanner import CATEGORY_EXTS
from ui import console

MAX_LISTED = 30
ALL_TYPES = set(CATEGORY_EXTS)
TYPE_CHOICES = [{"image"}, {"document"}, {"code"}, ALL_TYPES]
MODE_CHOICES = ["overwrite", "copy"]


def parse_path_input(raw: str) -> Path:
    """Accepts pasted or drag-dropped paths, including quoted ones."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    return Path(text).expanduser().resolve()


def _list_entries(directory: Path) -> list[Path]:
    try:
        entries = [p for p in directory.iterdir() if not p.name.startswith(".")]
    except OSError:
        return []
    # Folders first, then files, each alphabetical.
    return sorted(entries, key=lambda p: (not p.is_dir(), p.name.lower()))


def browse_directory(start: Path) -> Path:
    current = start.resolve()
    while True:
        entries = _list_entries(current)
        shown = entries[:MAX_LISTED]

        console.print(f"\n[bold cyan]{current}[/bold cyan]")
        if not shown:
            console.print(msg.BROWSE_EMPTY)
        for index, entry in enumerate(shown, start=1):
            if entry.is_dir():
                console.print(f"  [bold]{index:>2}[/bold]  [blue]{entry.name}/[/blue]")
            else:
                console.print(f"  [bold]{index:>2}[/bold]  {entry.name}")
        if len(entries) > MAX_LISTED:
            console.print(msg.BROWSE_MORE.format(count=len(entries) - MAX_LISTED))
        console.print(msg.BROWSE_HINT)

        choice = Prompt.ask(msg.BROWSE_PROMPT).strip()
        lowered = choice.lower()

        if lowered == "q":
            console.print(msg.CANCELLED)
            raise SystemExit(0)
        if lowered == "u":
            return current
        if choice == "..":
            current = current.parent
            continue
        if lowered == "p":
            typed = parse_path_input(Prompt.ask(msg.BROWSE_TYPE_PATH_PROMPT))
            if typed.exists():
                if typed.is_dir():
                    current = typed
                    continue
                return typed
            console.print(msg.BROWSE_PATH_MISSING.format(path=typed))
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            picked = shown[int(choice) - 1]
            if picked.is_dir():
                current = picked
                continue
            return picked
        console.print(msg.BROWSE_BAD_CHOICE)


def ask_path(cli_path: Optional[str]) -> Path:
    if cli_path:
        target = parse_path_input(cli_path)
        if not target.exists():
            console.print(msg.PATH_NOT_FOUND.format(path=target))
            raise SystemExit(1)
        return target
    return browse_directory(Path.cwd())


def _ask_menu(title: str, options: tuple[str, ...]) -> int:
    console.print(title)
    for index, label in enumerate(options, start=1):
        console.print(f"  [bold]{index}[/bold]  {label}")
    choices = [str(i) for i in range(1, len(options) + 1)]
    return int(Prompt.ask(msg.PICK_ONE, choices=choices)) - 1


def ask_types(cli_types: Optional[list[str]]) -> set[str]:
    if cli_types:
        return set(cli_types)
    return set(TYPE_CHOICES[_ask_menu(msg.TYPES_TITLE, msg.TYPES_OPTIONS)])


def ask_mode(cli_mode: Optional[str]) -> str:
    if cli_mode:
        return cli_mode
    return MODE_CHOICES[_ask_menu(msg.MODE_TITLE, msg.MODE_OPTIONS)]


def confirm_overwrite() -> bool:
    if not sys.stdin.isatty():
        return False
    return Confirm.ask(msg.CONFIRM_OVERWRITE, default=False)
