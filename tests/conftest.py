"""Shared pytest fixtures and path helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture
def sample_raw_path() -> Path:
    return FIXTURES / "raw" / "opencanary_sample.jsonl"


@pytest.fixture
def malformed_raw_path() -> Path:
    return FIXTURES / "raw" / "malformed.jsonl"


@pytest.fixture
def expected_normalized() -> list[dict]:
    return _load_jsonl(FIXTURES / "expected" / "normalized.jsonl")
