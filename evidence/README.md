# evidence/

**Owner:** Validation lead

Sanitized acceptance-test evidence only. No raw/unsanitized captures, no plaintext
credentials, no CUI. Raw `*.log` / `*.raw` are gitignored; only vetted artifacts
are tracked.

## Sanitization applied to everything here
- Passwords: SHA-256 hashes only (never plaintext) — produced by `app/reader`.
- Source IPs: last octet masked via `app.reader.mask_ip_last_octet` (e.g.
  `172.21.16.x`).
- `event_id`: redacted (non-deterministic UUID; not meaningful in a static artifact).

## Artifacts → acceptance criteria

| Artifact | Demonstrates |
| --- | --- |
| `logs/normalized-sample.jsonl` | End-to-end pipeline on a **real** OpenCanary capture: raw decoy log → normalized, sanitized events matching `app/reader/schema.json`. Shows all three services, all four event categories, and hashed (not plaintext) passwords. |
| `screenshots/operations.png` | **Operations** dashboard: health tiles (total/alerts/sources/unmapped-rate/freshness) + ranked findings. Covers *pipeline health* use case. |
| `screenshots/investigation.png` | **Investigation** dashboard: per-event table with severity, source, user, hashed password, and fired rules. Covers *unexpected interaction*, *authentication attempts*, *multi-service probing*. |

## How this evidence was produced (reproducible)
1. Deploy a decoy VM: `infra/deploy.ps1 -Count 1 -Decoys ssh,http,mysql`.
2. Generate attacker hits from an approved lab host (ssh:2222, http:8080, mysql:3306).
3. Pull `/var/log/opencanary/opencanary.log` from the VM.
4. `python -m app.frontend --log opencanary.log` → open http://127.0.0.1:8000/ and
   capture the two dashboard views.
5. `logs/normalized-sample.jsonl` is the reader output with masking applied (see above).

## Screenshots
`screenshots/operations.png` and `screenshots/investigation.png` are captured
manually from the running dashboard (browser screenshot). This is the one manual
step — everything else is scripted/reproducible.
