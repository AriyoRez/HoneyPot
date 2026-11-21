"""Target-restricted live probe against a lab decoy VM.

Unlike ``generator.py`` (a pure file writer that opens no sockets), this module
DOES generate real network traffic: it connects to a decoy's ssh/http/mysql
listeners so OpenCanary records genuine events. That makes the target allowlist
below the most important code in this package.

SAFETY MODEL (two independent checks, both must pass before any socket opens):

1. **Name check** — the target must be a recognised lab name (``decoy-N.mshome.net``,
   the hostname Multipass registers on Windows/Hyper-V), loopback, or a literal
   RFC 1918 address. Guards against a typo reaching a public hostname.
2. **Address check** — whatever the name resolves to must be private or loopback.
   This is the non-negotiable one: even if a name slipped past check 1, or DNS
   returned something unexpected, a public address aborts the run.

Both run in ``resolve_target()`` before a single connection is attempted. There is
no flag to disable them. Credentials sent are obvious fakes; nothing here is a
brute-forcer (one attempt per service by default).

Usage:
    python -m tests.harness.probe --dry-run
    python -m tests.harness.probe --target decoy-0.mshome.net
    python -m tests.harness.probe --services ssh,mysql
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from .generator import DECOY_PORTS

__all__ = [
    "ALLOWED_HOST_PATTERN",
    "ALLOWED_LITERAL_HOSTS",
    "DEFAULT_TARGET",
    "TargetNotAllowed",
    "probe_http",
    "probe_mysql",
    "probe_ssh",
    "resolve_target",
    "run",
]

# Multipass on Windows/Hyper-V registers each guest as <name>.mshome.net, and that
# record follows the VM's DHCP lease. Preferring it over a literal IP is deliberate:
# the lab IP changes on reboot, so a pinned address goes stale silently.
DEFAULT_TARGET = "decoy-0.mshome.net"

ALLOWED_HOST_PATTERN = re.compile(r"^decoy-\d+(\.mshome\.net)?$", re.IGNORECASE)
ALLOWED_LITERAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Obvious fakes. Never real credentials, and never a wordlist -- this is a
# detection probe, not a brute-forcer.
PROBE_USERNAME = "admin"
PROBE_PASSWORD = "PLACEHOLDER-probe-pw"
# OpenCanary's basicLogin skin serves and accepts POSTs at /index.html; '/' only
# 302-redirects there and '/login' is a 404.
HTTP_PATH = "/index.html"

CONNECT_TIMEOUT = 8


class TargetNotAllowed(RuntimeError):
    """Raised when a target fails either allowlist check. No traffic is sent."""


def _is_private(addr: str) -> bool:
    """True if ``addr`` is an RFC 1918 / loopback / link-local address."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def resolve_target(target: str) -> str:
    """Validate ``target`` against both allowlist checks and return its IP.

    Raises ``TargetNotAllowed`` without opening any connection if either check
    fails. Callers must route every probe through this function.
    """
    host = target.strip().lower()
    if not host:
        raise TargetNotAllowed("empty target")

    # Check 1 -- recognised lab name, loopback, or a literal private address.
    named_ok = bool(ALLOWED_HOST_PATTERN.match(host)) or host in ALLOWED_LITERAL_HOSTS
    if not named_ok and not _is_private(host):
        raise TargetNotAllowed(
            f"{target!r} is not a recognised lab target. Allowed: decoy-N[.mshome.net], "
            f"localhost, or a literal RFC 1918 address. "
            f"Find yours with: multipass list"
        )

    # Check 2 -- the decisive one. Whatever it resolves to must be private.
    try:
        addr = socket.gethostbyname(host)
    except OSError as exc:
        raise TargetNotAllowed(
            f"could not resolve {target!r} ({exc}). Is the VM running? Try: multipass list"
        ) from None

    if not _is_private(addr):
        raise TargetNotAllowed(
            f"{target!r} resolves to {addr}, which is not a private address. "
            f"Refusing to send traffic outside the lab."
        )
    return addr


def probe_ssh(addr: str, port: int) -> str:
    """One SSH auth attempt. OpenCanary always rejects; the attempt is the point."""
    import paramiko  # imported lazily so --dry-run works without dev deps

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            addr, port=port, username=PROBE_USERNAME, password=PROBE_PASSWORD,
            timeout=CONNECT_TIMEOUT, allow_agent=False, look_for_keys=False,
        )
        return "connected (unexpected -- a decoy should never grant a session)"
    except paramiko.AuthenticationException:
        return "auth rejected (credentials captured)"
    except Exception as exc:  # noqa: BLE001 - report, never abort the whole run
        return f"{type(exc).__name__}: {exc}"
    finally:
        client.close()


def probe_http(addr: str, port: int) -> str:
    """One GET (recon) plus one credential POST against the fake admin login."""
    url = f"http://{addr}:{port}{HTTP_PATH}"
    try:
        urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT).read(2048)
        body = urllib.parse.urlencode(
            {"username": PROBE_USERNAME, "password": PROBE_PASSWORD}
        ).encode()
        urllib.request.urlopen(url, data=body, timeout=CONNECT_TIMEOUT).read(2048)
        return "GET + credential POST sent (both captured)"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code} (still logged by the decoy)"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


def probe_mysql(addr: str, port: int) -> str:
    """One MySQL auth attempt.

    Note: MySQL never sends the password -- it sends a per-connection salted
    challenge-response -- so the decoy logs a scramble, not the secret. See
    docs/event-contract.md on why mysql hashes cannot be correlated for reuse.
    """
    import pymysql  # imported lazily so --dry-run works without dev deps

    try:
        pymysql.connect(
            host=addr, port=port, user=PROBE_USERNAME, password=PROBE_PASSWORD,
            connect_timeout=CONNECT_TIMEOUT,
        )
        return "connected (unexpected -- a decoy should never grant a session)"
    except pymysql.err.OperationalError:
        return "access denied (credentials captured)"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


_PROBES = {"ssh": probe_ssh, "http": probe_http, "mysql": probe_mysql}


def run(target: str, services: list[str], dry_run: bool = False) -> dict[str, str]:
    """Validate ``target``, then probe each service. Returns {service: result}."""
    unknown = [s for s in services if s not in _PROBES]
    if unknown:
        raise ValueError(f"unknown service(s): {unknown}; valid: {sorted(_PROBES)}")
    if not services:
        raise ValueError("services must not be empty")

    addr = resolve_target(target)
    print(f"target   : {target} -> {addr}  (allowlist checks passed)")
    if dry_run:
        print("dry-run  : target is in scope; no traffic sent.")
        return {}

    results = {}
    for svc in services:
        port = DECOY_PORTS[svc]
        results[svc] = _PROBES[svc](addr, port)
        print(f"  {svc:<6} :{port:<5} {results[svc]}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests.harness.probe",
        description="Send real decoy traffic to an approved lab VM (allowlist enforced).",
    )
    parser.add_argument("--target", default=DEFAULT_TARGET,
                        help=f"lab decoy hostname or private IP (default: {DEFAULT_TARGET})")
    parser.add_argument("--services", default="ssh,http,mysql",
                        help="comma-separated subset of ssh,http,mysql")
    parser.add_argument("--dry-run", action="store_true",
                        help="run the allowlist checks and exit without sending traffic")
    args = parser.parse_args(argv)

    services = [s.strip() for s in args.services.split(",") if s.strip()]
    try:
        run(args.target, services, dry_run=args.dry_run)
    except TargetNotAllowed as exc:
        print(f"REFUSED: {exc}")
        return 2
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    if not args.dry_run:
        print("\nNext: mirror the log and run the pipeline --")
        print("  python -m tests.harness.sync --once      # or drop --once to follow")
        print("  python -m app.frontend --log live-demo.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
