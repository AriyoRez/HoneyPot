"""Live web frontend for the Deception Detection Lab.

Reads the OpenCanary JSONL log on each request, normalizes + sanitizes it through
``app.reader``, runs ``app.rules.evaluate``, and serves two dashboards:

- ``/``              Operations  — health tiles + ranked findings
- ``/investigation`` Investigation — per-event table with filters

JSON endpoints (``/api/summary``, ``/api/events``) power the ~5s auto-refresh and
any external consumer. Only sanitized fields are ever rendered: the reader hashes
passwords, so no plaintext can reach a template or response.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from app.frontend.charts import by_decoy, donut, time_series, top_sources
from app.reader import read_log
from app.rules import evaluate

# Severity order used for the Operations severity bar + legend.
SEVERITY_ORDER = ("high", "medium", "low", "info")


def _load(log_path: str | Path) -> dict:
    """Read + normalize the log and run the detection pass. Missing file -> empty."""
    try:
        events = list(read_log(log_path))
    except FileNotFoundError:
        events = []
    return evaluate(events)


def _nav(data: dict) -> dict:
    """Small context for the sidebar, present on every page."""
    h = data["health"]
    return {"total": h["total_events"], "alerts": h["alert_count"]}


def _filter_events(events: list[dict]) -> list[dict]:
    """Apply optional query-param filters (service, severity, src_ip, sensor_node)."""
    service = request.args.get("service")
    severity = request.args.get("severity")
    src_ip = request.args.get("src_ip")
    sensor_node = request.args.get("sensor_node")
    out = events
    if service:
        out = [e for e in out if e.get("service") == service]
    if severity:
        out = [e for e in out if e.get("severity") == severity]
    if src_ip:
        out = [e for e in out if e.get("src_ip") == src_ip]
    if sensor_node:
        out = [e for e in out if e.get("sensor_node") == sensor_node]
    return out


def create_app(log_path: str | Path) -> Flask:
    app = Flask(__name__)
    app.config["LOG_PATH"] = str(log_path)

    @app.route("/")
    def operations():
        data = _load(app.config["LOG_PATH"])
        sev = Counter(f["severity"] for f in data["findings"])
        sev_counts = [(lvl, sev.get(lvl, 0)) for lvl in SEVERITY_ORDER]
        return render_template(
            "operations.html",
            health=data["health"],
            findings=data["findings"],
            sev_counts=sev_counts,
            donut=donut(sev_counts),
            timeseries=time_series(data["events"]),
            top_sources=top_sources(data["events"]),
            by_decoy=by_decoy(data["events"]),
            nav=_nav(data),
        )

    @app.route("/investigation")
    def investigation():
        data = _load(app.config["LOG_PATH"])
        events = _filter_events(data["events"])
        # Most recent first for triage.
        events = sorted(events, key=lambda e: e.get("timestamp") or "", reverse=True)
        return render_template(
            "investigation.html",
            events=events,
            total=len(data["events"]),
            shown=len(events),
            filters={k: request.args.get(k) for k in ("service", "severity", "src_ip", "sensor_node")},
            nav=_nav(data),
        )

    @app.route("/api/summary")
    def api_summary():
        data = _load(app.config["LOG_PATH"])
        return jsonify({"health": data["health"], "findings": data["findings"]})

    @app.route("/api/events")
    def api_events():
        data = _load(app.config["LOG_PATH"])
        return jsonify(_filter_events(data["events"]))

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "log_path": app.config["LOG_PATH"]})

    return app
