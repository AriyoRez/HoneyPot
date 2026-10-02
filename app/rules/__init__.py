"""Detection rules over normalized decoy events.

Exposes the four project use cases (see ``docs/event-contract.md``) as pure,
tested functions carrying severity + alert verdict. Consumed by the web frontend
(``app/frontend``) and referenced by the triage runbook.
"""

from __future__ import annotations

from .rules import (
    USE_CASES,
    Finding,
    Severity,
    annotate_events,
    evaluate,
    summarize,
)

__all__ = [
    "USE_CASES",
    "Finding",
    "Severity",
    "annotate_events",
    "evaluate",
    "summarize",
]
