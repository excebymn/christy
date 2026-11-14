"""Remembers the last quality, size and options, used as the next defaults.

Stored under christy's state folder. Every failure is swallowed: remembering is
a convenience and must never break the tool. The replace-originals destination
is deliberately never remembered."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from models import EXTRA_KEYS, Settings


def _state_file() -> Path:
    base = os.environ.get("CHRISTY_STATE_DIR")
    if not base:
        data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(data_home, "christy")
    return Path(base) / "webpify" / "last.json"


def load() -> dict:
    """{'quality': int, 'lossless': bool, 'max_width': int|None, 'options': [keys]} or {}"""
    try:
        data = json.loads(_state_file().read_text(encoding="utf-8"))
        result: dict = {}
        quality = data.get("quality")
        if isinstance(quality, int) and not isinstance(quality, bool) and 1 <= quality <= 100:
            result["quality"] = quality
        result["lossless"] = bool(data.get("lossless", False))
        width = data.get("max_width")
        result["max_width"] = width if isinstance(width, int) and not isinstance(width, bool) and width >= 1 else None
        result["options"] = [key for key in data.get("options", []) if key in EXTRA_KEYS]
        return result
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def save(settings: Settings) -> None:
    payload = {
        "quality": settings.quality,
        "lossless": settings.lossless,
        "max_width": settings.max_width,
        "options": [key for key in EXTRA_KEYS if getattr(settings, key)],
    }
    try:
        path = _state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass
