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
