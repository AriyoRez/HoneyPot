"""Tests for the log reader: fixture regression + schema validation."""

from __future__ import annotations

import jsonschema

from app.reader import load_schema, read_log
from app.reader.reader import read_lines


def _strip_volatile(event: dict) -> dict:
    out = dict(event)
    out.pop("event_id", None)  # generated per-call; not part of the oracle
    return out


def test_reader_matches_expected_oracle(sample_raw_path, expected_normalized):
    events = list(read_log(sample_raw_path))
    assert len(events) == len(expected_normalized)
    for got, want in zip(events, expected_normalized):
        assert _strip_volatile(got) == want


def test_every_event_validates_against_schema(sample_raw_path):
    schema = load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    for event in read_log(sample_raw_path):
        validator.validate(event)


def test_malformed_lines_are_skipped_and_reported(malformed_raw_path):
    errors: list = []
    events = list(read_log(malformed_raw_path, errors=errors))
    # fixture has 3 malformed lines + 1 valid-but-unmapped event
    assert len(errors) == 3
    assert len(events) == 1
    assert events[0]["service"] is None
    assert events[0]["logtype_raw"] == 99999


def test_blank_lines_ignored():
    events = list(read_lines(iter(["", "   ", "\n"])))
    assert events == []
