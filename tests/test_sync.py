"""Tests for the decoy log mirror.

The guards matter most here: a bad instance name sends the pull at the wrong VM,
and a bad destination writes a credential-bearing raw capture somewhere git tracks.
Both must fail before any subprocess runs, so these tests fake ``multipass transfer``
rather than needing Multipass.
"""

from __future__ import annotations

import subprocess

import pytest

from tests.harness import sync
from tests.harness.sync import (
    FetchError,
    InstanceNotAllowed,
    UnsafeDestination,
    check_destination,
    check_instance,
    sync_once,
)

SAMPLE = b'{"logtype": 3001}\n{"logtype": 8001}\n'


@pytest.fixture
def fake_multipass(monkeypatch):
    """Stand in for `multipass transfer`, writing ``payload`` to the target path."""
    calls = []

    def _install(payload=SAMPLE, returncode=0, stderr=b"", exc=None):
        def _run(argv, **kwargs):
            calls.append(argv)
            if exc is not None:
                raise exc
            if payload is not None:
                with open(argv[-1], "wb") as fh:
                    fh.write(payload)
            return subprocess.CompletedProcess(argv, returncode, b"", stderr)
        monkeypatch.setattr(sync.subprocess, "run", _run)
        return calls
    return _install


# --- instance guard ---------------------------------------------------------

@pytest.mark.parametrize("name", ["decoy-0", "decoy-12", "DECOY-3"])
def test_lab_instances_are_allowed(name):
    assert check_instance(name) == name


@pytest.mark.parametrize("name", ["", "decoy", "decoy-", "prod-db", "decoy-0.mshome.net"])
def test_non_lab_instances_are_refused(name):
    with pytest.raises(InstanceNotAllowed):
        check_instance(name)


def test_refused_instance_opens_no_subprocess(fake_multipass):
    calls = fake_multipass()
    with pytest.raises(InstanceNotAllowed):
        sync.run(instance="prod-db", dest="live-demo.log", once=True)
    assert calls == []


# --- destination guard ------------------------------------------------------

def test_log_destination_is_allowed(tmp_path):
    dest = tmp_path / "live-demo.log"
    assert check_destination(dest) == dest.resolve()


@pytest.mark.parametrize("name", ["capture.jsonl", "capture.txt", "capture"])
def test_non_log_destination_is_refused(tmp_path, name):
    # Anything outside the *.log gitignore rule could land a raw capture in a commit.
    with pytest.raises(UnsafeDestination):
        check_destination(tmp_path / name)


def test_evidence_destination_is_refused(tmp_path):
    with pytest.raises(UnsafeDestination):
        check_destination(tmp_path / "evidence" / "logs" / "pull.log")


def test_refused_destination_opens_no_subprocess(tmp_path, fake_multipass):
    calls = fake_multipass()
    with pytest.raises(UnsafeDestination):
        sync.run(instance="decoy-0", dest=tmp_path / "pull.jsonl", once=True)
    assert calls == []


# --- pulling ----------------------------------------------------------------

def test_sync_once_writes_and_counts(tmp_path, fake_multipass):
    fake_multipass()
    dest = tmp_path / "live-demo.log"
    assert sync_once("decoy-0", dest) == 2
    assert dest.read_bytes() == SAMPLE


def test_sync_once_pulls_from_the_named_instance(tmp_path, fake_multipass):
    calls = fake_multipass()
    dest = tmp_path / "live-demo.log"
    sync_once("decoy-0", dest)
    assert calls[0][:3] == ["multipass", "transfer",
                            "decoy-0:/var/log/opencanary/opencanary.log"]


def test_unchanged_log_is_not_rewritten(tmp_path, fake_multipass):
    fake_multipass()
    dest = tmp_path / "live-demo.log"
    sync_once("decoy-0", dest)
    before = dest.stat().st_mtime_ns
    assert sync_once("decoy-0", dest) is None
    assert dest.stat().st_mtime_ns == before


def test_growing_log_is_mirrored(tmp_path, fake_multipass):
    fake_multipass()
    dest = tmp_path / "live-demo.log"
    sync_once("decoy-0", dest)
    grown = SAMPLE + b'{"logtype": 4002}\n'
    fake_multipass(payload=grown)
    assert sync_once("decoy-0", dest) == 3
    assert dest.read_bytes() == grown


def test_sync_leaves_no_partial_file(tmp_path, fake_multipass):
    fake_multipass()
    dest = tmp_path / "live-demo.log"
    sync_once("decoy-0", dest)
    sync_once("decoy-0", dest)  # the unchanged path must clean up its temp too
    assert list(tmp_path.iterdir()) == [dest]


def test_windows_sftp_chmod_exit_code_is_not_a_failure(tmp_path, fake_multipass):
    # multipass transfer writes the whole file, then exits 2 because it cannot set
    # POSIX permissions on NTFS. Treating that as failure would reject every pull.
    fake_multipass(returncode=2, stderr=b"[error] [sftp] cannot set permissions")
    dest = tmp_path / "live-demo.log"
    assert sync_once("decoy-0", dest) == 2
    assert dest.read_bytes() == SAMPLE


# --- failure surfaces -------------------------------------------------------

def test_missing_multipass_is_reported(tmp_path, fake_multipass):
    fake_multipass(exc=FileNotFoundError())
    with pytest.raises(FetchError, match="multipass not found"):
        sync_once("decoy-0", tmp_path / "live-demo.log")


def test_stopped_vm_is_reported(tmp_path, fake_multipass):
    fake_multipass(payload=None, returncode=1, stderr=b'instance "decoy-0" is not running')
    with pytest.raises(FetchError, match="not running"):
        sync_once("decoy-0", tmp_path / "live-demo.log")


def test_empty_pull_does_not_clobber_the_mirror(tmp_path, fake_multipass):
    # The exec-based transport used to return exit 0 with no bytes, which silently
    # truncated a good mirror. An empty read must fail loudly instead.
    fake_multipass()
    dest = tmp_path / "live-demo.log"
    sync_once("decoy-0", dest)
    fake_multipass(payload=b"")
    with pytest.raises(FetchError, match="0 bytes"):
        sync_once("decoy-0", dest)
    assert dest.read_bytes() == SAMPLE


def test_empty_first_pull_is_allowed(tmp_path, fake_multipass):
    # A genuinely empty log (no events yet) is fine when there is nothing to lose.
    fake_multipass(payload=b"")
    dest = tmp_path / "live-demo.log"
    assert sync_once("decoy-0", dest) == 0


def test_first_pull_failure_exits_nonzero(tmp_path, fake_multipass):
    # A failure on the very first attempt means the setup is wrong, not transient,
    # so run() should give up rather than retry forever.
    fake_multipass(exc=FileNotFoundError())
    assert sync.run(instance="decoy-0", dest=tmp_path / "live-demo.log", once=False) == 2
