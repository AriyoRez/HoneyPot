"""Tests for the pure chart-data helpers."""

from __future__ import annotations

from app.frontend.charts import by_decoy, donut, time_series, top_sources


def _ev(ts=None, service="ssh", src_ip="10.0.0.1", sensor_node="decoy-01"):
    return {"timestamp": ts, "service": service, "src_ip": src_ip,
            "sensor_node": sensor_node}


def test_time_series_counts_sum_to_timestamped_events():
    events = [
        _ev("2026-10-01T12:00:00+00:00"),
        _ev("2026-10-01T12:00:30+00:00"),
        _ev("2026-10-01T12:01:00+00:00"),
        _ev(None),  # no timestamp -> excluded
    ]
    ts = time_series(events, buckets=12)
    assert ts["total"] == 3
    assert sum(ts["counts"]) == 3
    assert len(ts["counts"]) == 12
    assert ts["line"] and ts["area"]
    assert ts["start"] and ts["end"]


def test_time_series_empty_is_safe():
    ts = time_series([], buckets=10)
    assert ts["total"] == 0
    assert ts["max"] == 0
    assert ts["line"] == "" and ts["area"] == ""
    assert ts["start"] is None


def test_time_series_single_timestamp():
    ts = time_series([_ev("2026-10-01T12:00:00+00:00")], buckets=8)
    assert ts["total"] == 1
    assert sum(ts["counts"]) == 1


def test_top_sources_ranks_and_limits():
    events = (
        [_ev(src_ip="10.0.0.9") for _ in range(5)]
        + [_ev(src_ip="10.0.0.2") for _ in range(2)]
        + [_ev(src_ip="10.0.0.3")]
    )
    rows = top_sources(events, k=2)
    assert [r["src_ip"] for r in rows] == ["10.0.0.9", "10.0.0.2"]
    assert rows[0]["count"] == 5
    assert rows[0]["pct"] == 100.0
    assert rows[1]["pct"] == 40.0  # 2 / 5


def test_top_sources_ignores_unmapped_and_missing_ip():
    events = [
        _ev(service=None, src_ip="10.0.0.1"),  # unmapped -> ignored
        _ev(service="ssh", src_ip=None),        # no ip -> ignored
        _ev(service="http", src_ip="10.0.0.5"),
    ]
    rows = top_sources(events)
    assert [r["src_ip"] for r in rows] == ["10.0.0.5"]


def test_top_sources_empty():
    assert top_sources([]) == []


def test_by_decoy_ranks_nodes_with_services():
    events = (
        [_ev(sensor_node="decoy-01", service="ssh") for _ in range(3)]
        + [_ev(sensor_node="decoy-01", service="http")]
        + [_ev(sensor_node="decoy-02", service="mysql")]
    )
    rows = by_decoy(events)
    assert [r["node"] for r in rows] == ["decoy-01", "decoy-02"]
    assert rows[0]["count"] == 4
    assert rows[0]["pct"] == 100.0
    assert rows[0]["services"] == "http, ssh"
    assert rows[1]["pct"] == 25.0  # 1 / 4


def test_by_decoy_ignores_unmapped_and_missing_node():
    events = [
        _ev(service=None, sensor_node="decoy-01"),   # unmapped -> ignored
        _ev(service="ssh", sensor_node=None),          # no node -> ignored
        _ev(service="http", sensor_node="decoy-09"),
    ]
    rows = by_decoy(events)
    assert [r["node"] for r in rows] == ["decoy-09"]


def test_by_decoy_empty():
    assert by_decoy([]) == []


def test_donut_slices_sum_and_offsets():
    d = donut([("high", 3), ("medium", 0), ("low", 1)])
    assert d["total"] == 4
    # zero-count levels dropped
    assert [s["level"] for s in d["slices"]] == ["high", "low"]
    # dash + gap equals the full circumference for every slice
    for s in d["slices"]:
        assert abs(s["dash"] + s["gap"] - d["circumference"]) < 0.1
    # first slice starts at offset 0; percentages sum to ~100
    assert d["slices"][0]["offset"] == 0.0
    assert abs(sum(s["pct"] for s in d["slices"]) - 100) < 0.2


def test_donut_empty_is_safe():
    d = donut([("high", 0), ("low", 0)])
    assert d["total"] == 0
    assert d["slices"] == []
