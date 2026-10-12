"""Interactive prompts (arrow keys, space, enter). Every question can be
skipped with a CLI flag; main.py decides when to ask."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import questionary
from questionary import Choice, Separator, Style

import messages as msg
from models import human_size
from scanner import SUGGESTED_EXCLUDES, dir_size, list_top_level_dirs
from ui import console, esc

QMARK = "?"
POINTER = ">"
MAX_SHORTCUTS = 36  # questionary can only bind this many shortcut keys

STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
        ("instruction", "fg:ansibrightblack"),
        ("separator", "fg:ansibrightblack"),
    ]
)


class Cancelled(Exception):
    """The user picked a cancel/quit option (exit 0). Ctrl+C is a plain
    KeyboardInterrupt instead (exit 130)."""


def _ask(question: questionary.Question):
    # unsafe_ask raises KeyboardInterrupt on Ctrl+C instead of printing its own
    # message and returning None, so main.py handles it in one place.
    return question.unsafe_ask()


def _select(message: str, choices: list, instruction: Optional[str] = None):
    selectable = sum(1 for c in choices if isinstance(c, Choice))
    shortcuts = selectable <= MAX_SHORTCUTS
    if instruction is None:
        instruction = msg.HINT_SHORTCUTS if shortcuts else msg.HINT_SEARCH
    return _ask(
        questionary.select(
            message,
            choices=choices,
            style=STYLE,
            qmark=QMARK,
            pointer=POINTER,
            use_shortcuts=shortcuts,
            use_jk_keys=False,
            # Long lists: let the user type to filter instead of shortcuts.
            use_search_filter=not shortcuts,
            instruction=instruction,
        )
    )


def parse_path_input(raw: str) -> Path:
    """Accepts pasted or drag-dropped paths, including quoted ones."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    return Path(text).expanduser().resolve()


def _visible_subdirs(directory: Path) -> list[Path]:
    try:
        entries = [p for p in directory.iterdir() if not p.name.startswith(".") and p.is_dir()]
    except OSError:
        return []
    return sorted(entries, key=lambda p: p.name.lower())


def browse_folder(start: Path) -> Path:
    """Pick the folder to zip. Picking a subfolder selects it right away;
    'open a subfolder' goes deeper, 'go up' goes back."""
    current = start.resolve()
    while True:
        subdirs = _visible_subdirs(current)
        choices: list = [Choice(f"{d.name}/", value=("pick", d)) for d in subdirs]
        if subdirs:
            choices.append(Separator())
        else:
            choices.append(Separator(msg.BROWSE_EMPTY))
        choices.append(Choice(msg.CHOICE_USE_THIS.format(name=current.name or str(current)), value=("use", current)))
        if subdirs:
            choices.append(Choice(msg.CHOICE_OPEN, value=("open", None)))
        if current.parent != current:
            choices.append(Choice(msg.CHOICE_UP, value=("up", None)))
        choices.append(Choice(msg.CHOICE_TYPE_PATH, value=("type", None)))
        choices.append(Choice(msg.CHOICE_QUIT, value=("quit", None)))

        action, value = _select(msg.BROWSE_QUESTION.format(current=current), choices)

        if action in ("pick", "use"):
            return value
        if action == "quit":
            raise Cancelled
        if action == "up":
            current = current.parent
        elif action == "open":
            opened = _select(
                msg.OPEN_QUESTION,
                [Choice(f"{d.name}/", value=d) for d in subdirs]
                + [Separator(), Choice(msg.CHOICE_BACK, value="back")],
            )
            if opened != "back":
                current = opened
        elif action == "type":
            typed = parse_path_input(_ask(questionary.path(msg.TYPE_PATH_PROMPT, only_directories=True, style=STYLE)))
            if not typed.exists():
                console.print(msg.BROWSE_PATH_MISSING.format(path=esc(typed)))
            elif not typed.is_dir():
                console.print(msg.BROWSE_PATH_NOT_FOLDER.format(path=esc(typed)))
            else:
                return typed


def ask_gitignore_choice(rules: int) -> str:
    """Returns 'follow' or 'manual'."""
    answer = _select(
        msg.GITIGNORE_FOUND.format(rules=rules),
        [
            Choice(msg.GITIGNORE_OPT_FOLLOW, value="follow"),
            Choice(msg.GITIGNORE_OPT_MANUAL, value="manual"),
            Choice(msg.OPT_CANCEL, value="cancel"),
        ],
    )
    if answer == "cancel":
        raise Cancelled
    return answer


def ask_no_gitignore_choice() -> str:
    """Returns 'all' or 'pick'."""
    answer = _select(
        msg.NO_GITIGNORE,
        [
            Choice(msg.NO_GITIGNORE_OPT_ALL, value="all"),
            Choice(msg.NO_GITIGNORE_OPT_PICK, value="pick"),
            Choice(msg.OPT_CANCEL, value="cancel"),
        ],
    )
    if answer == "cancel":
        raise Cancelled
    return answer


def ask_excluded(root: Path) -> set[str]:
    """Checklist of top-level folders to leave out. Heavy regenerable ones
    (node_modules, .venv, ...) start checked; biggest folders come first."""
    folders = list_top_level_dirs(root)
    if not folders:
        console.print(msg.PICK_NOTHING)
        return set()

    with console.status(msg.MEASURING):
        sized = [(folder, dir_size(folder)) for folder in folders]
    sized.sort(key=lambda item: (-item[1], item[0].name.lower()))

    width = max(len(folder.name) for folder, _ in sized) + 1
    choices = [
        Choice(
            f"{folder.name + '/':<{width}}  {human_size(size):>9}",
            value=folder.name,
            checked=folder.name in SUGGESTED_EXCLUDES,
        )
        for folder, size in sized
    ]
    picked = _ask(
        questionary.checkbox(
            msg.PICK_QUESTION,
            choices=choices,
            style=STYLE,
            qmark=QMARK,
            pointer=POINTER,
            instruction=msg.PICK_INSTRUCTION,
        )
    )
    return set(picked)


def ask_sensitive_choice() -> str:
    """Returns 'keep' or 'leave'."""
    answer = _select(
        msg.SENSITIVE_QUESTION,
        [
            Choice(msg.SENSITIVE_OPT_LEAVE, value="leave"),
            Choice(msg.SENSITIVE_OPT_KEEP, value="keep"),
            Choice(msg.OPT_CANCEL, value="cancel"),
        ],
    )
    if answer == "cancel":
        raise Cancelled
    return answer


def ask_confirm(message: str, default: bool = True) -> bool:
    return bool(_ask(questionary.confirm(message, default=default, style=STYLE, qmark=QMARK)))
