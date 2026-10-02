"""Custom frontend log-reader package.

Reads the OpenCanary JSON log, normalizes + sanitizes each event per the approved
event contract (``docs/event-contract.md`` v0.1), and yields events in the schema
defined by ``app/reader/schema.json``. Downstream rules and dashboards build on
this stable shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from .normalize import (
    EVENT_CATEGORIES,
    LOGTYPE_MAP,
    SERVICES,
    normalize_event,
)
from .reader import MalformedLine, read_lines, read_log
from .sanitize import hash_password, mask_ip_last_octet, password_fields

SCHEMA_PATH = Path(__file__).with_name("schema.json")

__all__ = [
    "EVENT_CATEGORIES",
    "LOGTYPE_MAP",
    "SCHEMA_PATH",
    "SERVICES",
    "MalformedLine",
    "hash_password",
    "load_schema",
    "mask_ip_last_octet",
    "normalize_event",
    "password_fields",
    "read_lines",
    "read_log",
]


def load_schema() -> dict:
    """Return the normalized-event JSON Schema as a dict."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)
