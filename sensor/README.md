# sensor/

**Owner:** Sensor lead

Holds the OpenCanary decoy **configuration and sample fixtures** for the honeypot.

> **Deployment note:** The real OpenCanary decoy sensor runs on a **separate
> Linux VM** — that is the authoritative deployment target. This folder only
> holds the config template and captured event fixtures. Nothing here runs the
> production decoy; local runs (if any) are for sandboxed dev iteration only.

## What belongs here
- `opencanary/opencanary.conf.template` — commented **template** config with the
  MVP decoy modules (ssh, http, mysql). Placeholder ports and fake banners only;
  no real secrets. Copy to `opencanary.conf` on the VM and fill in real values.
  The filled `opencanary.conf` is **gitignored** and must never be committed.
- `fixtures/` — sample captured decoy events (sanitized) for parser/test use.

## What does NOT belong here
- Frontend / log-reader code (see [`../app/reader/`](../app/README.md)).
- Any real credentials, tokens, or a filled-in `opencanary.conf`.
