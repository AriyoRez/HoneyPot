"""Live web frontend package (Flask dashboards over normalized decoy events)."""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
