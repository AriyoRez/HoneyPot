"""Normalize raw OpenCanary log events into the approved event contract.

The mapping implemented here is the canonical one documented in
``docs/event-contract.md`` (v0.2). The ``logtype`` codes and ``logdata`` keys are
taken from OpenCanary 0.9.10 source, not documentation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .sanitize import password_fields

__all__ = ["EVENT_CATEGORIES", "LOGTYPE_MAP", "SERVICES", "normalize_event"]

SERVICES = ("ssh", "http", "mysql")
EVENT_CATEGORIES = ("connection", "request", "auth_attempt")

# logtype -> (service, event_category). Source: opencanary/logger.py constants.
LOGTYPE_MAP: dict[int, tuple[str, str]] = {
    4000: ("ssh", "connection"),      # LOG_SSH_NEW_CONNECTION
    4001: ("ssh", "connection"),      # LOG_SSH_REMOTE_VERSION_SENT
    4002: ("ssh", "auth_attempt"),    # LOG_SSH_LOGIN_ATTEMPT
    3000: ("http", "request"),        # LOG_HTTP_GET
    3001: ("http", "auth_attempt"),   # LOG_HTTP_POST_LOGIN_ATTEMPT
    3002: ("http", "request"),        # LOG_HTTP_UNIMPLEMENTED_METHOD
    3003: ("http", "request"),        # LOG_HTTP_REDIRECT
    8001: ("mysql", "auth_attempt"),  # LOG_MYSQL_LOGIN_ATTEMPT
    9003: ("mysql", "connection"),    # LOG_MYSQL_CONNECTION_MADE
}

# OpenCanary emits "%Y-%m-%d %H:%M:%S.%f" (UTC, no tz suffix) for utc_time.
_OC_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def _to_iso_utc(utc_time: str | None) -> str | None:
    """Convert OpenCanary's ``utc_time`` string to ISO-8601 UTC, or None."""
    if not utc_time:
        return None
    try:
        dt = datetime.strptime(utc_time, _OC_TIME_FORMAT)  # noqa: DTZ007 (tz applied below)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat()


def normalize_event(raw: dict) -> dict:
    """Map one raw OpenCanary event dict into a normalized contract event.

    An unmapped ``logtype`` yields ``service`` / ``event_category`` of ``None``
    (the event is surfaced, never silently dropped — unmapped types feed the
    pipeline-health use case).
    """
    logtype = raw.get("logtype")
    service, category = LOGTYPE_MAP.get(logtype, (None, None))

    logdata = raw.get("logdata") or {}
    present, pw_hash = password_fields(logdata)

    username = logdata.get("USERNAME")

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _to_iso_utc(raw.get("utc_time")),
        "sensor_node": raw.get("node_id"),
        "service": service,
        "event_category": category,
        "logtype_raw": logtype,
        "src_ip": raw.get("src_host"),
        "src_port": raw.get("src_port"),
        "dst_ip": raw.get("dst_host"),
        "dst_port": raw.get("dst_port"),
        "username": username,
        "password_present": present,
        "password_sha256": pw_hash,
        "http_path": logdata.get("PATH"),
        "user_agent": logdata.get("USERAGENT"),
        "raw_logdata_keys": sorted(logdata.keys()),
    }
