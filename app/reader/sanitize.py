"""Sanitization helpers for the reader.

Sanitization is the point of this pipeline: raw decoy capture may contain
attacker-supplied credentials. We NEVER persist a plaintext password. Instead we
record whether a password was present and a one-way SHA-256 hash of it, which lets
analysts correlate reused credentials across attempts without storing the secret.
"""

from __future__ import annotations

import hashlib

__all__ = ["hash_password", "mask_ip_last_octet", "password_fields"]


def hash_password(value: str) -> str:
    """Return the hex SHA-256 of ``value`` (UTF-8). One-way; not reversible."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def password_fields(logdata: dict) -> tuple[bool, str | None]:
    """Derive ``(password_present, password_sha256)`` from a raw ``logdata`` dict.

    The plaintext password is read only to hash it and is never returned or
    stored. A missing or empty ``PASSWORD`` yields ``(False, None)``.
    """
    raw = logdata.get("PASSWORD")
    if raw is None or raw == "":
        return False, None
    return True, hash_password(str(raw))


def mask_ip_last_octet(ip: str) -> str:
    """Mask the last octet of an IPv4 address (``1.2.3.4`` -> ``1.2.3.x``).

    Used only when exporting to ``evidence/``; the normalized log keeps the full
    ``src_ip`` (lab traffic is synthetic). Non-IPv4 input is returned unchanged.
    """
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    parts[-1] = "x"
    return ".".join(parts)
