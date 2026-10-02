"""Tests for the raw -> normalized mapping."""

from __future__ import annotations

import pytest

from app.reader import normalize_event
from app.reader.normalize import LOGTYPE_MAP


def _raw(logtype: int, **over) -> dict:
    base = {
        "node_id": "decoy-01",
        "utc_time": "2026-10-01 12:00:00.000000",
        "src_host": "198.51.100.1",
        "src_port": 1234,
        "dst_host": "203.0.113.10",
        "dst_port": 22,
        "logtype": logtype,
        "logdata": {},
    }
    base.update(over)
    return base


@pytest.mark.parametrize("logtype,service,category", [
    (4000, "ssh", "connection"),
    (4001, "ssh", "connection"),
    (4002, "ssh", "auth_attempt"),
    (3000, "http", "request"),
    (3001, "http", "auth_attempt"),
    (8001, "mysql", "auth_attempt"),
    (9003, "mysql", "connection"),
])
def test_logtype_derivation(logtype, service, category):
    out = normalize_event(_raw(logtype))
    assert out["service"] == service
    assert out["event_category"] == category
    assert out["logtype_raw"] == logtype


def test_unmapped_logtype_is_surfaced_not_dropped():
    out = normalize_event(_raw(99999))
    assert out["service"] is None
    assert out["event_category"] is None
    assert out["logtype_raw"] == 99999


def test_event_id_and_timestamp_shape():
    out = normalize_event(_raw(4000))
    assert isinstance(out["event_id"], str) and out["event_id"]
    assert out["timestamp"] == "2026-10-01T12:00:00+00:00"


def test_event_id_is_unique_per_call():
    a = normalize_event(_raw(4000))
    b = normalize_event(_raw(4000))
    assert a["event_id"] != b["event_id"]


def test_bad_timestamp_becomes_none():
    out = normalize_event(_raw(4000, utc_time="not-a-time"))
    assert out["timestamp"] is None


def test_raw_logdata_keys_sorted():
    out = normalize_event(_raw(3001, logdata={"USERNAME": "a", "PASSWORD": "b", "PATH": "/x"}))
    assert out["raw_logdata_keys"] == ["PASSWORD", "PATH", "USERNAME"]


def test_map_covers_all_mvp_codes():
    for code in (4000, 4001, 4002, 3000, 3001, 8001, 9003):
        assert code in LOGTYPE_MAP
