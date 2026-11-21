"""Tests for the live-probe target allowlist.

These are the most safety-relevant tests in the suite: they assert the probe
refuses to send traffic anywhere outside the lab. Every rejection path must fail
*before* a socket is opened, so the tests patch DNS rather than touching a network.
"""

from __future__ import annotations

import pytest

from tests.harness import probe
from tests.harness.probe import TargetNotAllowed, resolve_target


@pytest.fixture
def fake_dns(monkeypatch):
    """Point gethostbyname at a lookup table so no real DNS is used."""
    def _install(mapping: dict[str, str]):
        def _resolve(host):
            if host not in mapping:
                raise OSError("name or service not known")
            return mapping[host]
        monkeypatch.setattr(probe.socket, "gethostbyname", _resolve)
    return _install


# --- accepted targets -------------------------------------------------------

@pytest.mark.parametrize("host,addr", [
    ("decoy-0.mshome.net", "172.20.158.71"),
    ("decoy-12.mshome.net", "172.20.1.4"),
    ("decoy-0", "172.20.158.71"),
    ("localhost", "127.0.0.1"),
    ("10.1.2.3", "10.1.2.3"),
    ("192.168.0.5", "192.168.0.5"),
])
def test_lab_targets_are_allowed(host, addr, fake_dns):
    fake_dns({host: addr})
    assert resolve_target(host) == addr


def test_target_is_case_insensitive_and_trimmed(fake_dns):
    fake_dns({"decoy-0.mshome.net": "172.20.158.71"})
    assert resolve_target("  DECOY-0.MsHome.Net  ") == "172.20.158.71"


# --- rejected by check 1 (name) ---------------------------------------------

@pytest.mark.parametrize("host", [
    "example.com",
    "scanme.nmap.org",
    "decoy-0.evil.net",      # lab-looking prefix, wrong domain
    "notdecoy-0.mshome.net",
    "8.8.8.8",               # public literal
    "",
])
def test_non_lab_names_are_refused(host, fake_dns):
    fake_dns({})  # resolution must never even be reached for most of these
    with pytest.raises(TargetNotAllowed):
        resolve_target(host)


# --- rejected by check 2 (resolved address) ---------------------------------

def test_lab_name_resolving_to_public_ip_is_refused(fake_dns):
    """The decisive check: a permitted NAME pointing at a public address aborts."""
    fake_dns({"decoy-0.mshome.net": "93.184.216.34"})
    with pytest.raises(TargetNotAllowed, match="not a private address"):
        resolve_target("decoy-0.mshome.net")


def test_unresolvable_target_is_refused(fake_dns):
    fake_dns({})
    with pytest.raises(TargetNotAllowed, match="could not resolve"):
        resolve_target("decoy-9.mshome.net")


# --- run() routes everything through the allowlist ---------------------------

def test_run_refuses_before_sending_traffic(fake_dns, monkeypatch):
    """A refused target must not invoke any probe function."""
    fake_dns({})
    called = []
    for name in ("probe_ssh", "probe_http", "probe_mysql"):
        monkeypatch.setattr(probe, name, lambda *a, **k: called.append(1))
    monkeypatch.setattr(probe, "_PROBES", {
        "ssh": probe.probe_ssh, "http": probe.probe_http, "mysql": probe.probe_mysql,
    })
    with pytest.raises(TargetNotAllowed):
        probe.run("example.com", ["ssh", "http", "mysql"])
    assert called == []


def test_dry_run_sends_nothing(fake_dns, monkeypatch):
    fake_dns({"decoy-0.mshome.net": "172.20.158.71"})
    called = []
    monkeypatch.setattr(probe, "_PROBES", {
        "ssh": lambda *a, **k: called.append(1),
    })
    assert probe.run("decoy-0.mshome.net", ["ssh"], dry_run=True) == {}
    assert called == []


def test_unknown_service_rejected(fake_dns):
    fake_dns({"decoy-0.mshome.net": "172.20.158.71"})
    with pytest.raises(ValueError, match="unknown service"):
        probe.run("decoy-0.mshome.net", ["ssh", "telnet"])


def test_empty_services_rejected(fake_dns):
    fake_dns({"decoy-0.mshome.net": "172.20.158.71"})
    with pytest.raises(ValueError, match="must not be empty"):
        probe.run("decoy-0.mshome.net", [])


def test_probe_ports_match_the_generator():
    """Probe and synthetic generator must agree on decoy ports (no drift)."""
    from tests.harness.generator import DECOY_PORTS
    assert set(DECOY_PORTS) == set(probe._PROBES)


def test_no_real_credentials_in_module():
    """The probe must only ever send obvious placeholders."""
    assert "PLACEHOLDER" in probe.PROBE_PASSWORD
