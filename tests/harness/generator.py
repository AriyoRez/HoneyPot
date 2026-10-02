"""Synthetic OpenCanary event generator (lab-only).

Produces raw OpenCanary-format events and writes them to a JSONL log, so the
parser and GUI teams have a realistic stream without needing the live sensor.

SAFETY: this is a FILE WRITER only. It opens no sockets, makes no network
connections, and targets no hosts. All values are clearly-synthetic placeholders
(RFC 5737 TEST-NET source IPs, obvious fake credentials). It must never be turned
into a traffic-generating client against anything outside the approved lab scope.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

__all__ = ["DECOY_PORTS", "build_event", "generate"]

# Decoy listener ports (match sensor/opencanary/opencanary.conf.template).
DECOY_PORTS = {"ssh": 2222, "http": 8080, "mysql": 3306}

# Clearly-synthetic placeholders — never real credentials.
_FAKE_USERS = ["admin", "root", "test", "oracle", "ubuntu"]
_FAKE_PASSWORDS = ["hunter2", "Pa55w0rd!", "letmein", "changeme", "trustno1"]
_FAKE_PATHS = ["/", "/login", "/admin", "/wp-login.php"]
_FAKE_UA = "Mozilla/5.0 (PLACEHOLDER synthetic lab client)"

# Per-decoy catalogue of (logtype, logdata-builder). Mirrors OpenCanary 0.9.10.
_EVENT_SHAPES = {
    "ssh": [
        (4000, lambda r: {}),
        (4002, lambda r: {"USERNAME": r.choice(_FAKE_USERS), "PASSWORD": r.choice(_FAKE_PASSWORDS)}),
    ],
    "http": [
        (3000, lambda r: {"PATH": r.choice(_FAKE_PATHS), "USERAGENT": _FAKE_UA}),
        (3001, lambda r: {
            "USERNAME": r.choice(_FAKE_USERS),
            "PASSWORD": r.choice(_FAKE_PASSWORDS),
            "PATH": "/login",
            "USERAGENT": _FAKE_UA,
        }),
    ],
    "mysql": [
        (9003, lambda r: {}),
        (8001, lambda r: {"USERNAME": r.choice(_FAKE_USERS), "PASSWORD": r.choice(_FAKE_PASSWORDS)}),
    ],
}


def _oc_time(dt: datetime) -> str:
    """Format a datetime the way OpenCanary writes utc_time."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def build_event(decoy: str, rng: random.Random, when: datetime, node_id: str = "decoy-01") -> dict:
    """Build one synthetic raw OpenCanary event for ``decoy``."""
    logtype, make_logdata = rng.choice(_EVENT_SHAPES[decoy])
    src_ip = f"198.51.100.{rng.randint(1, 254)}"  # RFC 5737 TEST-NET-2
    stamp = _oc_time(when)
    return {
        "node_id": node_id,
        "local_time": stamp,
        "utc_time": stamp,
        "local_time_adjusted": stamp,
        "src_host": src_ip,
        "src_port": rng.randint(1024, 65535),
        "dst_host": "203.0.113.10",  # RFC 5737 TEST-NET-3 (fake decoy host)
        "dst_port": DECOY_PORTS[decoy],
        "logtype": logtype,
        "logdata": make_logdata(rng),
    }


def generate(
    count: int,
    enabled_decoys: list[str],
    out_path: str | Path,
    seed: int | None = None,
    node_id: str = "decoy-01",
) -> int:
    """Write ``count`` synthetic raw events (round-robin over ``enabled_decoys``).

    Returns the number of events written. Raises ValueError on bad input.
    """
    unknown = [d for d in enabled_decoys if d not in _EVENT_SHAPES]
    if unknown:
        raise ValueError(f"unknown decoy(s): {unknown}; valid: {sorted(_EVENT_SHAPES)}")
    if not enabled_decoys:
        raise ValueError("enabled_decoys must not be empty")
    if count < 0:
        raise ValueError("count must be >= 0")

    rng = random.Random(seed)
    base = datetime.now(timezone.utc).replace(tzinfo=None)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as fh:
        for i in range(count):
            decoy = enabled_decoys[i % len(enabled_decoys)]
            when = base + timedelta(seconds=i)
            event = build_event(decoy, rng, when, node_id=node_id)
            fh.write(json.dumps(event) + "\n")
    return count
