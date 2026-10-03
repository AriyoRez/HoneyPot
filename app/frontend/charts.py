"""Pure chart-data helpers for the Operations dashboard.

No Flask, no rendering — these turn normalized events into small structures the
templates draw as inline SVG / CSS bars. Kept pure so they are easily tested.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime

__all__ = ["by_decoy", "donut", "time_series", "top_sources"]

# Donut geometry (shared by template + tests). viewBox 0 0 120 120.
DONUT_R = 42
DONUT_C = 2 * math.pi * DONUT_R


def donut(sev_counts: list[tuple[str, int]]) -> dict:
    """Turn ``(level, count)`` pairs into SVG donut-slice stroke geometry.

    Each slice is a ring arc drawn with ``stroke-dasharray``/``-dashoffset`` on a
    circle of radius ``DONUT_R``. Returns slices (in input order, zero-count
    dropped), the total, and the ring circumference.
    """
    slices = []
    total = sum(n for _, n in sev_counts)
    if total <= 0:
        return {"slices": [], "total": 0, "circumference": round(DONUT_C, 2),
                "radius": DONUT_R}
    cumulative = 0.0
    for level, n in sev_counts:
        if n <= 0:
            continue
        frac = n / total
        dash = frac * DONUT_C
        slices.append({
            "level": level,
            "count": n,
            "pct": round(frac * 100, 1),
            "dash": round(dash, 2),
            "gap": round(DONUT_C - dash, 2),
            "offset": round(-cumulative * DONUT_C, 2),
        })
        cumulative += frac
    return {"slices": slices, "total": total, "circumference": round(DONUT_C, 2),
            "radius": DONUT_R}


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def time_series(events: list[dict], buckets: int = 24) -> dict:
    """Bucket events across their time span into ``buckets`` bins.

    Returns counts plus a ready-to-draw SVG line + area path (viewBox 0 0 100 30),
    and short start/end labels. Safe on empty / single-timestamp input.
    """
    buckets = max(buckets, 1)
    times = sorted(t for t in (_parse(e.get("timestamp")) for e in events) if t)
    counts = [0] * buckets

    if not times:
        return {"counts": counts, "max": 0, "total": 0, "line": "", "area": "",
                "start": None, "end": None}

    start, end = times[0], times[-1]
    span = (end - start).total_seconds()
    for t in times:
        if span <= 0:
            idx = buckets - 1
        else:
            frac = (t - start).total_seconds() / span
            idx = min(int(frac * buckets), buckets - 1)
        counts[idx] += 1

    peak = max(counts) or 1
    # viewBox 0..100 wide, 0..30 tall; leave 2px headroom.
    step = 100 / (buckets - 1) if buckets > 1 else 0
    pts = []
    for i, c in enumerate(counts):
        x = round(i * step, 2)
        y = round(30 - (c / peak) * 28, 2)
        pts.append((x, y))
    line = " ".join(f"{x},{y}" for x, y in pts)
    area = f"M0,30 L{line.replace(' ', ' L')} L100,30 Z" if pts else ""

    return {
        "counts": counts,
        "max": max(counts),
        "total": sum(counts),
        "line": line,
        "area": area,
        "start": start.strftime("%H:%M:%S"),
        "end": end.strftime("%H:%M:%S"),
    }


def top_sources(events: list[dict], k: int = 5) -> list[dict]:
    """Rank the noisiest source IPs among mapped events.

    Ignores unmapped/health events and missing IPs. Each row carries a ``pct``
    (0-100) relative to the busiest source, for bar widths.
    """
    counter = Counter(
        e["src_ip"] for e in events if e.get("service") and e.get("src_ip")
    )
    ranked = counter.most_common(k)
    if not ranked:
        return []
    top = ranked[0][1]
    return [
        {"src_ip": ip, "count": n, "pct": round(n / top * 100, 1)}
        for ip, n in ranked
    ]


def by_decoy(events: list[dict], k: int = 8) -> list[dict]:
    """Rank decoy nodes by mapped-event volume, with the services each one saw.

    Makes the three decoys read as distinct in the GUI even when they share one
    attacker ``src_ip`` (they differ by ``sensor_node`` / ``dst_ip`` / port).
    Ignores unmapped/health events and events with no node. ``pct`` is relative to
    the busiest node, for bar widths.
    """
    counter = Counter(
        e["sensor_node"] for e in events if e.get("service") and e.get("sensor_node")
    )
    ranked = counter.most_common(k)
    if not ranked:
        return []
    services: dict[str, set[str]] = {}
    for e in events:
        if e.get("service") and e.get("sensor_node"):
            services.setdefault(e["sensor_node"], set()).add(e["service"])
    top = ranked[0][1]
    return [
        {
            "node": node,
            "count": n,
            "pct": round(n / top * 100, 1),
            "services": ", ".join(sorted(services.get(node, set()))),
        }
        for node, n in ranked
    ]
