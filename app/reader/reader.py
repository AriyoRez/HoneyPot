"""Read an OpenCanary JSONL log and yield normalized events.

The reader is tolerant of malformed input: a line that is not valid JSON, or is
JSON but not an object, is skipped and recorded rather than crashing the stream.
This mirrors a real log tail where partial or garbage lines can appear.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import normalize_event

__all__ = ["MalformedLine", "read_lines", "read_log"]


@dataclass
class MalformedLine:
    """A log line that could not be parsed into a raw event."""

    line_number: int
    reason: str
    content: str


@dataclass
class ReadResult:
    """Collected errors from a read pass (events are yielded, not stored)."""

    errors: list[MalformedLine] = field(default_factory=list)


def read_lines(lines: Iterator[str], errors: list[MalformedLine] | None = None) -> Iterator[dict]:
    """Normalize an iterable of raw JSONL strings into contract events.

    Malformed lines are appended to ``errors`` (if provided) and skipped.
    """
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            if errors is not None:
                errors.append(MalformedLine(i, f"invalid JSON: {exc.msg}", stripped))
            continue
        if not isinstance(raw, dict):
            if errors is not None:
                errors.append(MalformedLine(i, "not a JSON object", stripped))
            continue
        yield normalize_event(raw)


def read_log(path: str | Path, errors: list[MalformedLine] | None = None) -> Iterator[dict]:
    """Yield normalized events from a JSONL log file at ``path``."""
    with open(path, "r", encoding="utf-8") as fh:
        yield from read_lines(fh, errors=errors)
