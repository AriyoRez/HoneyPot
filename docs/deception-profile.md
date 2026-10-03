# Deception Profile — making the decoys believable

> **Status: design guidance (lab-first).** This is the "how it's done professionally"
> blueprint for the decoy VM. It explains *why* a decoy gets fingerprinted as a honeypot
> and what to change so a competent attacker doesn't instantly bail. Everything here is
> **synthetic and lab-scoped**; real/production placement is a separate, sponsor-approved
> decision (see `CLAUDE.md`). Fill the `TODO:` items against your actual host before any
> non-lab use.

## Why this matters

A low-interaction honeypot like OpenCanary is cheap and safe, but it is only useful if
an attacker *engages* with it. Skilled attackers (and automated recon) fingerprint and
skip honeypots using cheap signals: **non-standard ports, static/mismatched service
banners, a bare host with no legitimate activity, and shallow interaction** (the service
falls over the moment you do more than connect). The fixes below are ordered by
bang-for-buck.

## The current tells (and the fix)

| Tell | Why it flags as a honeypot | Fix |
|---|---|---|
| SSH on 2222, HTTP on 8080 | Real internal hosts run 22/80/443; odd ports on an otherwise-bare host scream "test/decoy". | **Standard ports** (22/80/3306). See "Ports" below. |
| Generic / mismatched banners | Fingerprint tools match known emulated banners; an SSH banner that disagrees with the MySQL/OS version is incoherent. | **One OS persona**, consistent versions. See "Persona". |
| No host identity | No hostname, no PTR/DNS, no TLS cert, generic TCP/IP stack. | **Give it an identity.** See "Host identity". |
| Lonely, silent host | A host with only 3 open ports and zero normal traffic/logs is suspicious. | **Placement + breadcrumbs + ambient activity.** |
| Shallow interaction | OpenCanary logs the first touch, then nothing; one command exposes it. | **Layer in medium/high interaction** (next tier). |
| Observable telemetry | If the attacker can see the logging/alerting, the game is up. | **Out-of-band telemetry.** |

## Credible host persona (pick ONE, keep everything consistent)

Choose a single OS/service story and make every advertised version agree with it.
Mismatched versions are themselves a tell.

- **Persona (lab default):** Ubuntu 22.04 LTS ("jammy").
- SSH banner: `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10`
- HTTP `Server`: `nginx/1.18.0 (Ubuntu)` (skin should match a plausible web-admin)
- MySQL banner: `8.0.36-0ubuntu0.22.04.1`
- These are set in `sensor/opencanary/opencanary.conf.template`. **TODO:** re-check the
  exact package versions against the VM you actually deploy, so banner == reality.
- **TODO:** pick a hostname that fits a naming convention (e.g. `REPLACE_ME_hostname`
  like `svc-db-07`) — never a name that reveals "honeypot/canary/decoy".

## Ports — present on the standard ports

Non-standard ports are the single loudest tell. Two professional ways to serve the
decoy on 22/80/443/3306:

1. **Native bind on a dedicated decoy interface/host.** OpenCanary binds 22/80 directly.
   Requires: run as root or grant `cap_net_bind_service` (ports <1024), and ensure the
   host's **real management sshd is NOT on :22** — move it to a management interface/port
   first (dual-NIC decoy pattern) so you don't lock yourself out.
2. **Redirection shield (host-level DNAT/REDIRECT).** OpenCanary binds unprivileged
   2222/8080; a firewall rule redirects inbound 22→2222 and 80→8080. The attacker's scan
   sees 22/80 open; management sshd keeps :22 on the admin interface. No privilege needed.
   - **TODO:** add the `iptables`/`nftables` REDIRECT rules for the chosen decoy host.

**Multipass lab exception:** Multipass manages each guest over SSH on :22, so in the
local lab the decoy stays on **2222/8080/3306** (see `docs/network-policy.md`). The
believable standard-port profile is the authoritative template's default and applies to
a dedicated decoy host.

## Host identity

A believable host is more than open ports:

- **DNS:** forward + reverse (PTR) records consistent with the hostname/persona.
  **TODO:** `REPLACE_ME_fqdn` / PTR.
- **TLS:** a real cert on 443 (internal CA is fine) so HTTPS doesn't look self-signed-by-
  a-toy. **TODO:** cert source.
- **OS/TCP fingerprint:** running OpenCanary on a real Linux host (not an emulator) means
  nmap's OS/TTL/window fingerprint already matches the persona — keep it that way.
- **Reachability:** the host should resolve and respond like its neighbors.

## Network placement (proximity decoys)

- Place decoys **among real assets** on a production-like subnet ("proximity decoys"),
  not alone on an empty range — isolation is itself a signal. Keep them segmented so a
  compromised decoy can't pivot (VLAN/firewall; egress-deny per `network-policy.md`).
- **TODO:** target subnet / VLAN (sponsor-approved; out of lab scope).

## Breadcrumbs & ambient activity

- Plant **breadcrumbs** elsewhere that point at the decoy (fake creds in a config, a
  bookmarked "admin" URL, a DB connection string) so the decoy is *discovered* the way a
  real asset would be, and so touching it is high-signal.
- A totally silent host is suspicious; a little benign ambient traffic/logging helps.
  **TODO:** decide what (if any) synthetic ambient activity is in scope for the lab.

## Out-of-band telemetry

- Ship decoy logs off-box (pull / one-way) so an attacker on the VM can't see or tamper
  with detection — already the model in `docs/network-policy.md`. Keep alerting on the
  analysis side, never visible from the decoy.

## Interaction depth — the ceiling (next tier, not built here)

OpenCanary is **low-interaction**: it records the first interaction and cannot sustain a
shell/session. A skilled attacker who authenticates and runs one command will know. The
professional layered pattern pairs low-interaction breadth (OpenCanary across many ports)
with a **medium/high-interaction** service for depth:

- **SSH:** [Cowrie](https://cowrie.org/) — medium/high-interaction SSH/Telnet with a fake
  shell + filesystem; logs full sessions. Would wire into this same pipeline via a reader
  adapter mapping Cowrie events to the normalized contract (`docs/event-contract.md`).
- **Trade-off:** more convincing, but higher cost and more containment risk — sandbox
  hard, deny egress. Deferred to a later tier.

## References

- [A Review of Honeypots: Fingerprinting, Detection, and Evasion (MDPI, 2025)](https://www.mdpi.com/1999-5903/18/4/190)
- [A Survey on Honeypot Software and Data Analysis (arXiv)](https://arxiv.org/pdf/1608.06249)
- [Protecting Your Network With Honeypots — TCM Security](https://tcm-sec.com/protecting-your-network-with-honeypots/)
- [3 Ways to Implement Deception Technology in 2025 — SecurityHive](https://www.securityhive.io/blog/3-ways-to-implement-deception-technology-in-2025-as-part-of-your-cybersecurity-strategy)
- [Cowrie — medium/high-interaction SSH honeypot](https://cowrie.org/)
- [LLMHoney: dynamic SSH honeypot responses (arXiv, 2025)](https://arxiv.org/pdf/2509.01463)
