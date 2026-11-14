"""Rich-based output helpers. No text lives here, it all comes from messages.

Header, prompts and status go to stderr. The tree itself goes to stdout, so
`christy treeignore > tree.txt` or `| less` only carries the tree.
"""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

import messages as msg
from renderer import Line

console = Console(stderr=True)
out_console = Console(highlight=False)


def esc(value: object) -> str:
    """Escape user-provided text (paths, file names) for rich markup."""
    return escape(str(value))


def print_header() -> None:
    console.print()
    console.print(
        Panel.fit(
            f"{msg.HEADER_TITLE}\n{msg.HEADER_SUBTITLE}",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print()


def print_tree(lines: list[Line]) -> None:
    """Print to stdout. Colours appear only on a terminal; rich drops them
    when the output is piped or redirected."""
    for line in lines:
        text = Text.assemble(*[(chunk, style or None) for chunk, style in line])
        # soft_wrap: never re-wrap or crop a tree line to the terminal width.
        out_console.print(text, soft_wrap=True, highlight=False)
