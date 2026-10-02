"""Tests for the synthetic event generator."""

from __future__ import annotations

import json

import jsonschema
import pytest

from app.reader import load_schema, read_log
from tests.harness.generator import DECOY_PORTS, generate


def test_generate_writes_requested_count(tmp_path):
    out = tmp_path / "sample.log"
    n = generate(30, ["ssh", "http", "mysql"], out, seed=1)
    assert n == 30
    assert len(out.read_text(encoding="utf-8").splitlines()) == 30


def test_generated_events_pass_through_reader_and_schema(tmp_path):
    out = tmp_path / "sample.log"
    generate(24, ["ssh", "http", "mysql"], out, seed=7)
    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    events = list(read_log(out))
    assert len(events) == 24
    services = set()
    for e in events:
        validator.validate(e)
        services.add(e["service"])
    assert services == {"ssh", "http", "mysql"}


def test_respects_enabled_decoys(tmp_path):
    out = tmp_path / "ssh_only.log"
    generate(10, ["ssh"], out, seed=3)
    for e in read_log(out):
        assert e["service"] == "ssh"
        assert e["dst_port"] == DECOY_PORTS["ssh"]


def test_no_plaintext_password_in_generated_normalized_stream(tmp_path):
    # The generator embeds fake passwords in RAW events; the reader must hash them.
    raw_out = tmp_path / "raw.log"
    generate(20, ["ssh", "mysql"], raw_out, seed=5)
    raw_text = raw_out.read_text(encoding="utf-8")
    assert "PASSWORD" in raw_text  # present in raw
    normalized_blob = json.dumps(list(read_log(raw_out)))
    for fake_pw in ("hunter2", "Pa55w0rd!", "letmein", "changeme", "trustno1"):
        assert fake_pw not in normalized_blob


def test_rejects_unknown_decoy(tmp_path):
    with pytest.raises(ValueError):
        generate(5, ["ssh", "telnet"], tmp_path / "x.log")
