"""Interactive prompts (arrow keys, space, enter). Every question can be
skipped with a CLI flag; main.py decides when to ask.

Prompts are drawn on stderr when stdout is redirected, so the picker still
works for `christy treeignore > tree.txt`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import questionary
from questionary import Choice, Separator, Style

import messages as msg
from models import EXTRA_KEYS, human_size
from scanner import SUGGESTED_EXCLUDES, dir_size, list_top_level_dirs
from ui import console, esc

QMARK = "?"
POINTER = ">"
MAX_SHORTCUTS = 36  # questionary can only bind this many shortcut keys
DEPTH_PRESETS = (1, 2, 3)

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

EXTRA_LABELS = {
    "dirs_only": msg.OPT_DIRS_ONLY,
    "hidden": msg.OPT_HIDDEN,
    "sizes": msg.OPT_SIZES,
    "dates": msg.OPT_DATES,
    "perms": msg.OPT_PERMS,
    "paths": msg.OPT_PATHS,
    "counts": msg.OPT_COUNTS,
    "show_ignored": msg.OPT_SHOW_IGNORED,
    "ascii": msg.OPT_ASCII,
    "largest_first": msg.OPT_LARGEST,
    "mixed": msg.OPT_MIXED,
}


class Cancelled(Exception):
    """The user picked a cancel/quit option (exit 0). Ctrl+C is a plain
    KeyboardInterrupt instead (exit 130)."""


def _io_kwargs() -> dict:
    """When stdout is redirected, draw the prompts on stderr instead."""
    if sys.stdout.isatty():
        return {}
    from prompt_toolkit.output import create_output

    return {"output": create_output(stdout=sys.stderr)}


def _ask(question: questionary.Question):
    # unsafe_ask raises KeyboardInterrupt on Ctrl+C instead of printing its own
    # message and returning None, so main.py handles it in one place.
    return question.unsafe_ask()


def _select(message: str, choices: list, instruction: Optional[str] = None,
            shortcuts: bool = True, default=None):
    selectable = sum(1 for c in choices if isinstance(c, Choice))
    use_shortcuts = shortcuts and selectable <= MAX_SHORTCUTS
    use_filter = shortcuts and not use_shortcuts  # long lists: type to filter
    if instruction is None:
        if use_shortcuts:
            instruction = msg.HINT_SHORTCUTS
        elif use_filter:
            instruction = msg.HINT_SEARCH
        else:
            instruction = msg.HINT_ARROWS
    kwargs = dict(
        style=STYLE,
        qmark=QMARK,
        pointer=POINTER,
        use_shortcuts=use_shortcuts,
        use_jk_keys=False,
        use_search_filter=use_filter,
        instruction=instruction,
        **_io_kwargs(),
    )
    if default is not None:
        kwargs["default"] = default
    return _ask(questionary.select(message, choices=choices, **kwargs))


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
    """Pick the folder to show. Picking a subfolder selects it right away;
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
            typed = parse_path_input(
                _ask(questionary.path(msg.TYPE_PATH_PROMPT, only_directories=True, style=STYLE, **_io_kwargs()))
            )
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
            **_io_kwargs(),
        )
    )
    return set(picked)


def ask_depth(last: Optional[int] = None) -> Optional[int]:
    """How many levels to show. Returns None for 'as deep as it goes'.

    Shortcut keys are off on purpose: "1" would be ambiguous between the
    first menu item and the "1 level" item."""
    choices: list = [
        Choice(msg.DEPTH_UNLIMITED, value="unlimited"),
        Choice(msg.DEPTH_ONE, value=1),
        Choice(msg.DEPTH_N.format(count=2), value=2),
        Choice(msg.DEPTH_N.format(count=3), value=3),
    ]
    if last is not None and last not in DEPTH_PRESETS:
        choices.append(Choice(msg.DEPTH_LAST.format(count=last), value=last))
    choices.append(Choice(msg.DEPTH_CUSTOM, value="custom"))

    default = "unlimited" if last is None else last
    answer = _select(msg.DEPTH_QUESTION, choices, shortcuts=False, default=default)

    if answer == "unlimited":
        return None
    if answer == "custom":
        typed = _ask(
            questionary.text(
                msg.DEPTH_INPUT_PROMPT,
                validate=lambda text: True if text.strip().isdigit() and int(text) >= 1 else msg.DEPTH_INVALID,
                style=STYLE,
                qmark=QMARK,
                **_io_kwargs(),
            )
        )
        return int(typed.strip())
    return answer


def ask_extras(checked: set[str]) -> set[str]:
    """The checklist of extra options. `checked` are the starting ticks."""
    choices = [Choice(EXTRA_LABELS[key], value=key, checked=key in checked) for key in EXTRA_KEYS]
    picked = _ask(
        questionary.checkbox(
            msg.EXTRAS_QUESTION,
            choices=choices,
            style=STYLE,
            qmark=QMARK,
            pointer=POINTER,
            instruction=msg.EXTRAS_INSTRUCTION,
            **_io_kwargs(),
        )
    )
    return set(picked)


def ask_long_output(lines: int) -> str:
    """Returns 'save', 'print' or 'depth'."""
    answer = _select(
        msg.LONG_QUESTION.format(lines=f"{lines:,}"),
        [
            Choice(msg.LONG_OPT_SAVE, value="save"),
            Choice(msg.LONG_OPT_PRINT, value="print"),
            Choice(msg.LONG_OPT_DEPTH, value="depth"),
            Choice(msg.OPT_CANCEL, value="cancel"),
        ],
    )
    if answer == "cancel":
        raise Cancelled
    return answer


def ask_save_name(default_name: str) -> str:
    return _ask(
        questionary.text(
            msg.SAVE_NAME_PROMPT,
            default=default_name,
            validate=lambda text: True if text.strip() else msg.SAVE_NAME_EMPTY,
            style=STYLE,
            qmark=QMARK,
            **_io_kwargs(),
        )
    )


def ask_confirm(message: str, default: bool = True) -> bool:
    return bool(_ask(questionary.confirm(message, default=default, style=STYLE, qmark=QMARK, **_io_kwargs())))
