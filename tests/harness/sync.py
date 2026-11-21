"""Mirror a lab decoy's OpenCanary log onto the analysis host, on a poll loop.

The sensor writes ``/var/log/opencanary/opencanary.log`` inside the decoy VM, but
the frontend runs on the analysis host and re-reads its log file on every request.
Without something moving bytes between the two, the dashboard renders whatever
snapshot was last copied by hand -- live attacks land in the VM and never appear.

This module is that missing step: the manual pull from ``evidence/README.md``, run
on an interval.

DIRECTION IS DELIBERATE. ``docs/network-policy.md`` allows a *pull* from the
analysis host and nothing inbound to it from the decoy. We keep that: the host
initiates every fetch, the decoy is never asked to push, and no listener is opened
here. Mirroring is one-way -- local edits to the destination are overwritten, and
nothing is ever written back to the VM.

WHY ``multipass transfer`` AND NOT ``multipass exec ... cat``: on Windows, repeated
``exec`` invocations are unreliable. Measured back-to-back on this lab host, most
calls either hung until timeout or returned exit 0 with an empty stdout -- and an
empty "success" silently truncates the mirror. ``transfer`` uses the sftp path
instead and returned the full file on every attempt. No ``sudo`` is needed: the log
is mode 0644 in a world-traversable directory, so the VM's default user can read it.

Two guards run before the first fetch:

1. **Instance check** -- the VM must be a recognised lab name (``decoy-N``), so a
   typo cannot point the pull at an unrelated Multipass instance.
2. **Destination check** -- the local path must be a ``*.log`` (covered by the
   ``*.log`` rule in ``.gitignore``) and must not sit under ``evidence/``. What we
   pull is a RAW capture holding plaintext SSH/HTTP passwords; ``evidence/`` is for
   sanitized artifacts only, and an un-ignored path risks committing credentials.

Usage:
    python -m tests.harness.sync                      # follow decoy-0 -> live-demo.log
    python -m tests.harness.sync --once               # single pull, then exit
    python -m tests.harness.sync --interval 5 --dest live-demo.log
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from pathlib import Path

__all__ = [
    "ALLOWED_INSTANCE_PATTERN",
    "DEFAULT_DEST",
    "DEFAULT_INSTANCE",
    "DEFAULT_INTERVAL",
    "DEFAULT_REMOTE_LOG",
    "FetchError",
    "InstanceNotAllowed",
    "UnsafeDestination",
    "check_destination",
    "check_instance",
    "fetch",
    "run",
    "sync_once",
]

# Multipass *instance* names, not the ``.mshome.net`` hostnames probe.py connects
# to -- `multipass transfer` addresses the VM by instance name, so the bare form is
# the only one that works here.
DEFAULT_INSTANCE = "decoy-0"
ALLOWED_INSTANCE_PATTERN = re.compile(r"^decoy-\d+$", re.IGNORECASE)

DEFAULT_REMOTE_LOG = "/var/log/opencanary/opencanary.log"
DEFAULT_DEST = "live-demo.log"
# Fast enough to feel live against the frontend's 5s auto-refresh, slow enough that
# we are not spawning a subprocess continuously.
DEFAULT_INTERVAL = 3.0
FETCH_TIMEOUT = 20


class InstanceNotAllowed(RuntimeError):
    """Raised when the VM name is not a recognised lab decoy. No pull is attempted."""


class UnsafeDestination(RuntimeError):
    """Raised when the local path could leak a raw capture into tracked files."""


class FetchError(RuntimeError):
    """Raised when the pull itself fails (VM stopped, multipass missing, no log yet)."""


def check_instance(name: str) -> str:
    """Return ``name`` if it is a lab decoy instance, else raise InstanceNotAllowed."""
    if not ALLOWED_INSTANCE_PATTERN.match(name or ""):
        raise InstanceNotAllowed(
            f"{name!r} is not a recognised lab decoy instance (expected decoy-N)"
        )
    return name


def check_destination(path: str | Path) -> Path:
    """Return ``path`` resolved, if it is a safe place for a raw capture."""
    dest = Path(path).expanduser().resolve()
    if dest.suffix != ".log":
        raise UnsafeDestination(
            f"{dest} must end in .log -- raw captures hold plaintext passwords and "
            "rely on the *.log rule in .gitignore"
        )
    if any(part.lower() == "evidence" for part in dest.parts):
        raise UnsafeDestination(
            f"{dest} is under evidence/, which is for sanitized artifacts only"
        )
    return dest


def fetch(instance: str, into: Path, remote_log: str = DEFAULT_REMOTE_LOG) -> None:
    """Download the remote log to ``into``, raising FetchError if nothing arrived."""
    into.parent.mkdir(parents=True, exist_ok=True)
    if into.exists():
        into.unlink()  # so a failed transfer cannot leave us reading a stale temp
    try:
        proc = subprocess.run(
            ["multipass", "transfer", f"{instance}:{remote_log}", str(into)],
            capture_output=True,
            # Exit code is inspected below, not raised on -- see the note there.
            check=False,
            # Without this, multipass holds the channel open waiting on stdin.
            stdin=subprocess.DEVNULL,
            timeout=FETCH_TIMEOUT,
        )
    except FileNotFoundError as exc:  # multipass not installed / not on PATH
        raise FetchError("multipass not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise FetchError(f"timed out after {FETCH_TIMEOUT}s pulling from {instance}") from exc

    # The file landing is the real success signal, not the exit code: on Windows,
    # transfer writes the complete file and *then* reports exit 2 because sftp
    # cannot set POSIX permissions on an NTFS path. Trusting returncode here would
    # reject every single healthy pull.
    if not into.exists():
        detail = proc.stderr.decode("utf-8", "replace").strip() or f"exit {proc.returncode}"
        raise FetchError(detail)


def sync_once(instance: str, dest: Path, remote_log: str = DEFAULT_REMOTE_LOG) -> int | None:
    """Pull once. Returns the new line count if the log changed, else ``None``.

    The download lands in a sibling temp file and is renamed over ``dest`` in one
    step. The frontend re-reads the log on every request and parses it line by line,
    so a partially-written file would surface as a spurious parse error mid-refresh.
    """
    tmp = dest.with_name(dest.name + ".partial")
    fetch(instance, tmp, remote_log)
    data = tmp.read_bytes()

    # An empty read is treated as a failed pull, never as "the log was cleared".
    # Overwriting a good mirror with nothing would wipe the dashboard mid-demo.
    if not data and dest.exists() and dest.stat().st_size:
        tmp.unlink()
        raise FetchError("pulled 0 bytes over an existing mirror")

    if dest.exists() and dest.read_bytes() == data:
        tmp.unlink()
        return None

    os.replace(tmp, dest)
    return data.count(b"\n")


def run(
    instance: str = DEFAULT_INSTANCE,
    dest: str | Path = DEFAULT_DEST,
    interval: float = DEFAULT_INTERVAL,
    once: bool = False,
    remote_log: str = DEFAULT_REMOTE_LOG,
) -> int:
    """Poll until interrupted. Returns a process exit code."""
    check_instance(instance)
    target = check_destination(dest)

    print(f"sync: {instance}:{remote_log} -> {target}")
    if once:
        count = sync_once(instance, target, remote_log)
        print("  unchanged" if count is None else f"  {count} event(s)")
        return 0

    print(f"  polling every {interval}s -- Ctrl-C to stop", flush=True)
    # A failure mid-run is usually transient (VM rebooting, log not created until the
    # first event), so we keep polling and only surface a hard error on the first
    # attempt, where it means the setup is wrong rather than momentarily unavailable.
    first = True
    while True:
        try:
            count = sync_once(instance, target, remote_log)
            if count is not None:
                print(f"  {time.strftime('%H:%M:%S')}  {count} event(s)", flush=True)
            first = False
        except FetchError as exc:
            if first:
                print(f"error: {exc}")
                return 2
            print(f"  {time.strftime('%H:%M:%S')}  pull failed ({exc}) -- retrying", flush=True)
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests.harness.sync",
        description="Mirror a lab decoy's OpenCanary log to the analysis host (pull-only).",
    )
    parser.add_argument("--instance", default=DEFAULT_INSTANCE,
                        help=f"Multipass instance name (default: {DEFAULT_INSTANCE})")
    parser.add_argument("--dest", default=DEFAULT_DEST,
                        help=f"local *.log path to mirror into (default: {DEFAULT_DEST})")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                        help=f"seconds between pulls (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--once", action="store_true",
                        help="pull a single time and exit")
    parser.add_argument("--remote-log", default=DEFAULT_REMOTE_LOG,
                        help="path to the log inside the VM")
    args = parser.parse_args(argv)

    try:
        return run(args.instance, args.dest, args.interval, args.once, args.remote_log)
    except (InstanceNotAllowed, UnsafeDestination) as exc:
        print(f"REFUSED: {exc}")
        return 2
    except FetchError as exc:  # --once has no retry loop to fall back on
        print(f"error: {exc}")
        return 2
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
