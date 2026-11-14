"""Remembers the last depth and extra options, used as the next defaults.

Stored under christy's state folder. Every failure is swallowed: remembering
is a convenience and must never break the tool.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from models import EXTRA_KEYS, Options


def _state_file() -> Path:
    base = os.environ.get("CHRISTY_STATE_DIR")
    if not base:
        data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(data_home, "christy")
    return Path(base) / "treeignore" / "last.json"


def load() -> tuple[Optional[int], set[str]]:
    """Returns (depth, checked option keys); empty defaults when nothing is stored."""
    try:
        data = json.loads(_state_file().read_text(encoding="utf-8"))
        depth = data.get("depth")
        if not (depth is None or (isinstance(depth, int) and not isinstance(depth, bool) and depth >= 1)):
            depth = None
        keys = {key for key in data.get("options", []) if key in EXTRA_KEYS}
        return depth, keys
    except (OSError, ValueError, AttributeError, TypeError):
        return None, set()


def save(opts: Options) -> None:
    payload = {"depth": opts.depth, "options": [key for key in EXTRA_KEYS if getattr(opts, key)]}
    try:
        path = _state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass
