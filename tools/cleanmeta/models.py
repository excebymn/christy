"""Plain data containers shared across cleanmeta modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

STATUS_CLEANED = "cleaned"
STATUS_ERROR = "error"


@dataclass
class Result:
    path: Path
    category: str
    status: str
    detail: str = ""


@dataclass
class Stats:
    results: list[Result] = field(default_factory=list)

    def add(self, result: Result) -> None:
        self.results.append(result)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)
