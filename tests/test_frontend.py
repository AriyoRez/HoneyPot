"""Tests for the Flask frontend (routes, filters, sanitization)."""

from __future__ import annotations

import pytest

from app.frontend import create_app
from tests.harness.generator import generate


@pytest.fixture
def client(tmp_path):
    log = tmp_path / "sample.log"
    generate(30, ["ssh", "http", "mysql"], log, seed=11)
    app = create_app(str(log))
    app.config.update(TESTING=True)
    return app.test_client()


def test_operations_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Operations" in body
    assert "Total events" in body


def test_investigation_renders(client):
    r = client.get("/investigation")
    assert r.status_code == 200
    assert "Investigation" in r.get_data(as_text=True)


def test_soc_shell_and_no_emoji(client):
    # Redesign: ClownStrike console shell present, old emoji wordmark gone.
    body = client.get("/").get_data(as_text=True)
    assert "CLOWN" in body and "STRIKE" in body   # parody wordmark
    assert "🕳️" not in body                        # no emoji
    assert 'class="sidebar"' in body              # sidebar layout


def test_severity_renders_on_operations(client):
    # High-severity findings must render with the severity class (not color alone).
    body = client.get("/").get_data(as_text=True)
    assert "sev-high" in body
    assert "Detections by severity" in body


def test_charts_render_on_operations(client):
    body = client.get("/").get_data(as_text=True)
    assert "Events over time" in body
    assert "Top sources" in body
    assert "Events by service" in body
    assert "By decoy" in body                       # per-decoy breakdown
    assert "decoy-01" in body                        # the generated node label
    assert "<svg" in body                          # inline sparkline


def test_api_events_carry_dst_ip(client):
    events = client.get("/api/events").get_json()
    assert events
    assert all("dst_ip" in e for e in events)


def test_api_events_filter_by_sensor_node(client):
    r = client.get("/api/events?sensor_node=decoy-01")
    events = r.get_json()
    assert events  # generator labels every event decoy-01
    assert all(e["sensor_node"] == "decoy-01" for e in events)
    assert client.get("/api/events?sensor_node=nope").get_json() == []


def test_self_hosted_fonts_referenced(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    assert "Space Grotesk" in css
    assert "JetBrains Mono" in css
    assert ".woff2" in css


def test_api_summary_shape(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.get_json()
    assert "health" in data and "findings" in data
    assert data["health"]["total_events"] == 30


def test_api_events_filter_by_service(client):
    r = client.get("/api/events?service=ssh")
    assert r.status_code == 200
    events = r.get_json()
    assert events  # some ssh events exist
    assert all(e["service"] == "ssh" for e in events)


def test_severity_filter(client):
    r = client.get("/api/events?severity=high")
    assert all(e["severity"] == "high" for e in r.get_json())


def test_no_plaintext_password_in_any_response(client):
    # Generator's fake passwords must never surface via the web layer.
    for path in ("/", "/investigation", "/api/summary", "/api/events"):
        body = client.get(path).get_data(as_text=True)
        for fake_pw in ("hunter2", "Pa55w0rd!", "letmein", "changeme", "trustno1"):
            assert fake_pw not in body


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_missing_log_is_handled(tmp_path):
    app = create_app(str(tmp_path / "does-not-exist.log"))
    app.config.update(TESTING=True)
    c = app.test_client()
    assert c.get("/").status_code == 200
    assert c.get("/api/summary").get_json()["health"]["total_events"] == 0
