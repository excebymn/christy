"""Interactive prompts (arrows, space, enter). No wording lives here, it all
comes from messages. Every question can be skipped with a CLI flag; main.py
decides when to ask."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import questionary
from questionary import Choice, Separator, Style

import messages as msg
from models import (
    DEST_BESIDE,
    DEST_CUSTOM,
    DEST_FOLDER,
    DEST_REPLACE,
    EXTRA_KEYS,
    QUALITY_PRESETS,
    human_size,
)
from scanner import is_image
from ui import console, esc

QMARK = "?"
POINTER = ">"
MAX_SHORTCUTS = 36
MAX_FILES_LISTED = 150
WIDTH_PRESETS = (2560, 1920, 1600, 1280, 800)

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
    "recursive": msg.OPT_RECURSIVE,
    "keep_metadata": msg.OPT_KEEP_METADATA,
    "overwrite": msg.OPT_OVERWRITE,
    "include_webp": msg.OPT_INCLUDE_WEBP,
}


class Cancelled(Exception):
    """The user picked a cancel/quit option (exit 0). Ctrl+C is a plain
    KeyboardInterrupt instead (exit 130)."""


def _ask(question: questionary.Question):
    # unsafe_ask raises KeyboardInterrupt on Ctrl+C instead of printing its own
    # message, so main.py handles it in one place.
    return question.unsafe_ask()


def _select(message: str, choices: list, *, shortcuts: bool = True, default=None):
    selectable = sum(1 for c in choices if isinstance(c, Choice))
    use_shortcuts = shortcuts and selectable <= MAX_SHORTCUTS
    use_filter = shortcuts and not use_shortcuts  # long lists: type to filter
    instruction = msg.HINT_SHORTCUTS if use_shortcuts else (msg.HINT_SEARCH if use_filter else msg.HINT_ARROWS)
    kwargs = dict(
        style=STYLE, qmark=QMARK, pointer=POINTER, use_shortcuts=use_shortcuts,
        use_jk_keys=False, use_search_filter=use_filter, instruction=instruction,
    )
    if default is not None:
        kwargs["default"] = default
    return _ask(questionary.select(message, choices=choices, **kwargs))


def ask_confirm(message: str, default: bool = True) -> bool:
    return bool(_ask(questionary.confirm(message, default=default, style=STYLE, qmark=QMARK)))


def _ask_int(message: str, low: int, high: int) -> int:
    def check(text: str):
        try:
            value = int(text.strip())
        except ValueError:
            return msg.NUMBER_INVALID
        return True if low <= value <= high else msg.NUMBER_RANGE.format(low=low, high=high)

    return int(_ask(questionary.text(message, validate=check, style=STYLE, qmark=QMARK)).strip())


def parse_path_input(raw: str) -> Path:
    """Accepts pasted or drag-dropped paths, including quoted ones."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    return Path(text).expanduser().resolve()


# -- picking the image or folder -------------------------------------------

def _entries(directory: Path) -> tuple[list[Path], list[Path]]:
    """(visible subfolders, image files) of a folder."""
    try:
        items = [p for p in directory.iterdir() if not p.name.startswith(".")]
    except OSError:
        return [], []
    dirs = sorted((p for p in items if p.is_dir()), key=lambda p: p.name.lower())
    files = sorted((p for p in items if p.is_file() and is_image(p, True)), key=lambda p: p.name.lower())
    return dirs, files


def _size_of(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def browse(start: Path) -> Path:
    """Pick an image or a folder. Picking a subfolder or an image selects it
    right away; 'open a subfolder' goes deeper, 'go up' goes back."""
    current = start.resolve()
    while True:
        dirs, files = _entries(current)
        choices: list = [Choice(f"{d.name}/", value=("pick", d)) for d in dirs]
        shown = files[:MAX_FILES_LISTED]
        choices += [Choice(f"{f.name}  ({human_size(_size_of(f))})", value=("pick", f)) for f in shown]
        if len(files) > len(shown):
            choices.append(Separator(msg.BROWSE_MORE.format(count=len(files) - len(shown))))
        choices.append(Separator() if (dirs or shown) else Separator(msg.BROWSE_EMPTY))
        choices.append(Choice(msg.CHOICE_USE_THIS.format(name=current.name or str(current), count=len(files)), value=("use", current)))
        if dirs:
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
                [Choice(f"{d.name}/", value=d) for d in dirs] + [Separator(), Choice(msg.CHOICE_BACK, value="back")],
            )
            if opened != "back":
                current = opened
        elif action == "type":
            typed = parse_path_input(_ask(questionary.path(msg.TYPE_PATH_PROMPT, style=STYLE)))
            if typed.exists():
                return typed
            console.print(msg.BROWSE_PATH_MISSING.format(path=esc(typed)))


# -- settings ---------------------------------------------------------------

def ask_quality(last: dict) -> tuple[int, bool]:
    """Returns (quality, lossless)."""
    last_quality = last.get("quality")
    choices = [
        Choice(msg.QUALITY_BALANCED, ("q", QUALITY_PRESETS["balanced"])),
        Choice(msg.QUALITY_SMALLER, ("q", QUALITY_PRESETS["smaller"])),
        Choice(msg.QUALITY_HIGH, ("q", QUALITY_PRESETS["high"])),
        Choice(msg.QUALITY_LOSSLESS, ("lossless", 100)),
    ]
    if last_quality is not None and last_quality not in QUALITY_PRESETS.values():
        choices.append(Choice(msg.QUALITY_LAST.format(value=last_quality), ("q", last_quality)))
    choices.append(Choice(msg.QUALITY_CUSTOM, ("custom", 0)))

    if last.get("lossless"):
        default = ("lossless", 100)
    else:
        default = ("q", last_quality if last_quality is not None else QUALITY_PRESETS["balanced"])
    answer = _select(msg.QUALITY_QUESTION, choices, shortcuts=False, default=default)

    kind, value = answer
    if kind == "lossless":
        return 100, True
    if kind == "custom":
        return _ask_int(msg.QUALITY_PROMPT, 1, 100), False
    return value, False


def ask_max_width(last_width: Optional[int]) -> Optional[int]:
    """Returns the maximum width, or None to keep the original size."""
    choices = [Choice(msg.WIDTH_KEEP, 0)] + [Choice(msg.WIDTH_N.format(value=w), w) for w in WIDTH_PRESETS]
    if last_width is not None and last_width not in WIDTH_PRESETS:
        choices.append(Choice(msg.WIDTH_LAST.format(value=last_width), last_width))
    choices.append(Choice(msg.WIDTH_CUSTOM, "custom"))
    answer = _select(msg.WIDTH_QUESTION, choices, shortcuts=False, default=last_width if last_width is not None else 0)
    if answer == "custom":
        return _ask_int(msg.WIDTH_PROMPT, 16, 20000)
    return answer or None


def ask_extras(single_file: bool, checked: set[str]) -> set[str]:
    keys = [key for key in EXTRA_KEYS if not (single_file and key == "recursive")]
    choices = [Choice(EXTRA_LABELS[key], value=key, checked=key in checked) for key in keys]
    return set(
        _ask(
            questionary.checkbox(
                msg.EXTRAS_QUESTION, choices=choices, style=STYLE, qmark=QMARK, pointer=POINTER,
                instruction=msg.EXTRAS_INSTRUCTION,
            )
        )
    )


def ask_destination() -> str:
    """The safe choice is always first and always the default; 'replace' is
    never remembered from one run to the next."""
    return _select(
        msg.DEST_QUESTION,
        [
            Choice(msg.DEST_FOLDER, DEST_FOLDER),
            Choice(msg.DEST_BESIDE, DEST_BESIDE),
            Choice(msg.DEST_CUSTOM, DEST_CUSTOM),
            Choice(msg.DEST_REPLACE, DEST_REPLACE),
        ],
        shortcuts=False,
        default=DEST_FOLDER,
    )


def ask_custom_dir() -> Path:
    def check(text: str):
        return True if text.strip() else msg.CUSTOM_DIR_EMPTY

    answer = _ask(questionary.path(msg.CUSTOM_DIR_PROMPT, only_directories=True, validate=check, style=STYLE, qmark=QMARK))
    return parse_path_input(answer)
