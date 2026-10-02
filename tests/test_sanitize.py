"""Tests for sanitization — the non-negotiable 'no plaintext password' rule."""

from __future__ import annotations

import json

from app.reader import normalize_event
from app.reader.sanitize import hash_password, mask_ip_last_octet, password_fields


def test_password_hashed_not_stored():
    present, h = password_fields({"USERNAME": "root", "PASSWORD": "hunter2"})
    assert present is True
    assert h == hash_password("hunter2")
    assert "hunter2" not in (h or "")


def test_missing_password():
    assert password_fields({}) == (False, None)
    assert password_fields({"PASSWORD": ""}) == (False, None)


def test_plaintext_never_appears_in_normalized_output():
    secret = "SuperSecret!123"
    out = normalize_event({
        "node_id": "decoy-01",
        "utc_time": "2026-10-01 12:00:00.000000",
        "logtype": 4002,
        "logdata": {"USERNAME": "root", "PASSWORD": secret},
    })
    blob = json.dumps(out)
    assert secret not in blob
    assert out["password_present"] is True
    assert out["password_sha256"] == hash_password(secret)


def test_mask_ip_last_octet():
    assert mask_ip_last_octet("198.51.100.23") == "198.51.100.x"
    assert mask_ip_last_octet("not-an-ip") == "not-an-ip"
    assert mask_ip_last_octet("::1") == "::1"
