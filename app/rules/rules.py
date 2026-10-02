"""Detection rules over normalized decoy events (event-contract v0.1).

Implements the project's four detection use cases as pure functions, each
carrying a severity and an alert verdict. The web frontend consumes these for
the Investigation (per-event) and Operations (aggregate/health) views, and the
runbook hangs its escalation thresholds off the severities here.

Design premise: the decoys impersonate internal services with NO legitimate
users, so *any* interaction is inherently suspicious. Severity escalates from
there (credential use > passive touch; coordinated multi-service recon highest).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum

__all__ = [
    "USE_CASES",
    "Finding",
    "Severity",
    "annotate_events",
    "evaluate",
    "summarize",
]

USE_CASES = (
    "unexpected_interaction",
    "authentication_attempt",
    "multi_service_probing",
    "pipeline_health",
)


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass
class Finding:
    """An aggregate detection (feeds the Operations alert list)."""

    use_case: str
    severity: Severity
    alert: bool
    summary: str
    src_ip: str | None = None
    service: str | None = None
    event_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "use_case": self.use_case,
            "severity": self.severity.label,
            "alert": self.alert,
            "summary": self.summary,
            "src_ip": self.src_ip,
            "service": self.service,
            "event_ids": self.event_ids,
            "count": len(self.event_ids),
        }


def _prober_ips(events: list[dict]) -> dict[str, set[str]]:
    """Map src_ip -> set of distinct services it touched (mapped events only)."""
    by_src: dict[str, set[str]] = {}
    for e in events:
        svc = e.get("service")
        ip = e.get("src_ip")
        if svc and ip:
            by_src.setdefault(ip, set()).add(svc)
    return by_src


def annotate_events(events: list[dict]) -> list[dict]:
    """Return each event with which rules fired, a max severity, and alert flag.

    Drives the Investigation view. Does not mutate the input events.
    """
    probers = {ip for ip, svcs in _prober_ips(events).items() if len(svcs) >= 2}
    annotated = []
    for e in events:
        rules: list[str] = []
        severities: list[Severity] = []

        if e.get("service"):
            rules.append("unexpected_interaction")
            severities.append(Severity.MEDIUM)
        else:
            # Unmapped/base events (e.g. OpenCanary startup) — operational only.
            rules.append("pipeline_health")
            severities.append(Severity.INFO)

        if e.get("event_category") == "auth_attempt":
            rules.append("authentication_attempt")
            severities.append(Severity.HIGH)

        if e.get("src_ip") in probers and e.get("service"):
            rules.append("multi_service_probing")
            severities.append(Severity.HIGH)

        max_sev = max(severities) if severities else Severity.INFO
        alert = any(r != "pipeline_health" for r in rules)
        annotated.append({
            **e,
            "rules": rules,
            "severity": max_sev.label,
            "severity_rank": int(max_sev),
            "alert": alert,
        })
    return annotated


def summarize(events: list[dict]) -> dict:
    """Aggregate findings + pipeline-health metrics (drives the Operations view)."""
    findings: list[Finding] = []

    # Use case 2: authentication attempts (one finding per src_ip+service group).
    auth = [e for e in events if e.get("event_category") == "auth_attempt"]
    auth_groups: dict[tuple, list[dict]] = {}
    for e in auth:
        auth_groups.setdefault((e.get("src_ip"), e.get("service")), []).append(e)
    for (ip, svc), evs in auth_groups.items():
        findings.append(Finding(
            use_case="authentication_attempt",
            severity=Severity.HIGH,
            alert=True,
            summary=f"{len(evs)} auth attempt(s) on {svc} from {ip}",
            src_ip=ip,
            service=svc,
            event_ids=[e["event_id"] for e in evs],
        ))

    # Use case 3: multi-service probing (one finding per offending src_ip).
    for ip, svcs in _prober_ips(events).items():
        if len(svcs) >= 2:
            ids = [e["event_id"] for e in events if e.get("src_ip") == ip and e.get("service")]
            findings.append(Finding(
                use_case="multi_service_probing",
                severity=Severity.HIGH,
                alert=True,
                summary=f"{ip} probed {len(svcs)} services: {', '.join(sorted(svcs))}",
                src_ip=ip,
                event_ids=ids,
            ))

    # Use case 1: unexpected interaction (aggregate count; per-event in Investigation).
    interactions = [e for e in events if e.get("service")]
    if interactions:
        findings.append(Finding(
            use_case="unexpected_interaction",
            severity=Severity.MEDIUM,
            alert=True,
            summary=f"{len(interactions)} interaction(s) with decoys (no legitimate users expected)",
            event_ids=[e["event_id"] for e in interactions],
        ))

    findings.sort(key=lambda f: (-int(f.severity), f.use_case))

    # Use case 4: pipeline health.
    timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
    unmapped = [e for e in events if not e.get("service")]
    health = {
        "total_events": len(events),
        "mapped_events": len(interactions),
        "unmapped_events": len(unmapped),
        "unmapped_rate": round(len(unmapped) / len(events), 3) if events else 0.0,
        "distinct_sources": len({e.get("src_ip") for e in events if e.get("src_ip")}),
        "events_by_service": dict(Counter(e["service"] for e in interactions)),
        "events_by_category": dict(
            Counter(e["event_category"] for e in events if e.get("event_category"))
        ),
        "last_event": max(timestamps) if timestamps else None,
        "alert_count": sum(1 for f in findings if f.alert),
    }
    return {
        "findings": [f.as_dict() for f in findings],
        "health": health,
    }


def evaluate(events: list[dict]) -> dict:
    """Full detection pass: annotated events + aggregate findings + health."""
    result = summarize(events)
    result["events"] = annotate_events(events)
    return result
