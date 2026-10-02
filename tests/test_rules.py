"""Tests for the detection rules (four use cases, severity + verdict)."""

from __future__ import annotations

from app.rules import Severity, annotate_events, evaluate, summarize


def _ev(eid, service, category, src_ip, ts="2026-10-01T12:00:00+00:00", user=None):
    return {
        "event_id": eid,
        "timestamp": ts,
        "service": service,
        "event_category": category,
        "src_ip": src_ip,
        "username": user,
        "password_present": category == "auth_attempt",
        "password_sha256": "0" * 64 if category == "auth_attempt" else None,
    }


def test_unexpected_interaction_fires_on_any_service_event():
    events = [_ev("1", "ssh", "connection", "10.0.0.1")]
    ann = annotate_events(events)
    assert "unexpected_interaction" in ann[0]["rules"]
    assert ann[0]["severity"] == "medium"
    assert ann[0]["alert"] is True


def test_auth_attempt_is_high_severity():
    events = [_ev("1", "mysql", "auth_attempt", "10.0.0.1", user="root")]
    ann = annotate_events(events)
    assert "authentication_attempt" in ann[0]["rules"]
    assert ann[0]["severity"] == "high"


def test_multi_service_probing_detects_one_src_across_services():
    events = [
        _ev("1", "ssh", "connection", "10.0.0.9"),
        _ev("2", "http", "request", "10.0.0.9"),
        _ev("3", "mysql", "auth_attempt", "10.0.0.9", user="root"),
        _ev("4", "ssh", "connection", "10.0.0.2"),  # single-service, not a prober
    ]
    out = summarize(events)
    probers = [f for f in out["findings"] if f["use_case"] == "multi_service_probing"]
    assert len(probers) == 1
    assert probers[0]["src_ip"] == "10.0.0.9"
    assert probers[0]["severity"] == "high"
    # The single-service source must not be flagged as a prober.
    ann = {e["event_id"]: e for e in annotate_events(events)}
    assert "multi_service_probing" not in ann["4"]["rules"]
    assert "multi_service_probing" in ann["1"]["rules"]


def test_pipeline_health_surfaces_unmapped_events():
    events = [
        _ev("1", None, None, None),           # unmapped (e.g. OpenCanary startup)
        _ev("2", "ssh", "auth_attempt", "10.0.0.1", user="root"),
    ]
    out = evaluate(events)
    health = out["health"]
    assert health["total_events"] == 2
    assert health["unmapped_events"] == 1
    assert health["mapped_events"] == 1
    assert health["unmapped_rate"] == 0.5
    assert health["events_by_service"] == {"ssh": 1}
    # Unmapped event is health-only: present but not an alert.
    ann = {e["event_id"]: e for e in out["events"]}
    assert ann["1"]["rules"] == ["pipeline_health"]
    assert ann["1"]["alert"] is False


def test_findings_sorted_by_severity_desc():
    events = [
        _ev("1", "ssh", "connection", "10.0.0.1"),
        _ev("2", "http", "auth_attempt", "10.0.0.1", user="admin"),
        _ev("3", "mysql", "connection", "10.0.0.1"),
    ]
    findings = summarize(events)["findings"]
    ranks = [Severity[f["severity"].upper()] for f in findings]
    assert ranks == sorted(ranks, reverse=True)


def test_empty_input_is_safe():
    out = evaluate([])
    assert out["events"] == []
    assert out["findings"] == []
    assert out["health"]["total_events"] == 0
    assert out["health"]["last_event"] is None
