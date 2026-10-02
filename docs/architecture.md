# Architecture

## Overview
The Deception Detection Lab runs an **OpenCanary** honeypot that impersonates three
internal services with no legitimate users — **SSH, an HTTP web-admin page, and
MySQL** — on an isolated Linux VM. A **custom frontend we own** reads the OpenCanary
JSON log, normalizes + sanitizes each event, applies detection rules, and surfaces
the results as two live dashboards. The goal is a reproducible *pipeline*, not just
a running honeypot.

- **MVP decoys:** ssh (port 2222), http (port 8080), mysql (port 3306).
- **MVP goal:** any interaction with a decoy is suspicious; detect and triage it.
- **Stack:** Python. `app/reader` (normalize + sanitize), `app/rules` (detections),
  `app/frontend` (Flask web app, two dashboard views). Sensor deploy via
  Multipass/cloud-init (`infra/`).

## Reference Data Flow
1. **Capture** — OpenCanary on the Linux VM writes JSON events to
   `/var/log/opencanary/opencanary.log`.
2. **Normalize + sanitize** — `app/reader` maps each raw event to the normalized
   schema per [event-contract.md](event-contract.md) (v0.1): derives
   service/category from `logtype`, hashes passwords (never stores plaintext),
   drops unmapped `logdata` values.
3. **Detect** — `app/rules` evaluates the four use cases (unexpected interaction,
   authentication attempt, multi-service probing, pipeline health) with a severity
   + alert verdict.
4. **Present** — `app/frontend` serves the **Operations** view (health + findings)
   and **Investigation** view (per-event table with filters), auto-refreshing.

```
OpenCanary (VM) ──log──> app/reader ──normalized──> app/rules ──findings──> app/frontend
                         (sanitize)                 (severity)             (dashboards)
```

## Network Policy Table
See [network-policy.md](network-policy.md). Summary: attacker/lab → decoy ports on
the VM; the analysis host reads the decoy log (pull/ship); management SSH on 22 is
separate from the decoy SSH on 2222; no public exposure.

## Access Boundaries
- **Who may reach the decoy VM:** only the lab network. The VM is never publicly
  exposed; it is intended to be attacked, so it is isolated and hardened.
- **Decoy ↔ analysis boundary:** the frontend/reader runs on the analysis host (can
  be the dev machine), reading the log pulled from the VM — the analysis side does
  not expose services back to the decoy.
- **Dev machine role:** code + frontend + test harness only. It is **not** the
  deploy target; the authoritative sensor runs on the isolated Linux VM.
