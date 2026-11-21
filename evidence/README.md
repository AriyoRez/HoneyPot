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
2. Confirm it is up and note how to reach it — **never hardcode the IP**, Multipass
   changes it on reboot:
   ```bash
   multipass list                      # State should be Running
   ```
   Targets are `decoy-0.mshome.net` on ssh:2222, http:8080, mysql:3306.
3. Generate attacker hits from an approved lab host:
   ```bash
   python -m tests.harness.probe       # allowlist-enforced; see tests/README.md
   ```
4. Pull `/var/log/opencanary/opencanary.log` from the VM:
   ```bash
   python -m tests.harness.sync --once          # snapshot
   python -m tests.harness.sync                 # or: follow, pulling every 3s
   ```
   Leave the follow form running in its own terminal for a live demo — the frontend
   re-reads the log on every request, so new hits appear within one refresh.
   The equivalent by hand is `multipass transfer
   decoy-0:/var/log/opencanary/opencanary.log ./live-demo.log` (no `sudo` needed —
   the log is 0644). On Git Bash, `export MSYS_NO_PATHCONV=1` first, otherwise
   `/var/log/...` is rewritten into a Windows path, and keep the destination
   **relative**: `multipass transfer` reads `C:/...` as an instance name. An
   `[sftp] cannot set permissions` warning on Windows is harmless; the file arrives.
   Avoid `multipass exec ... cat` as a transport — on Windows repeated calls hang or
   return success with an empty file, which silently truncates the mirror.
5. `python -m app.frontend --log live-demo.log` → open http://127.0.0.1:8000/ and
   capture the two dashboard views.
6. `logs/normalized-sample.jsonl` is the reader output with masking applied (see above).

> The pulled `live-demo.log` is a **raw** capture containing plaintext SSH/HTTP
> passwords. It is gitignored (`*.log`) and must never be committed or pasted into a
> slide — show the reader's sanitized output instead.

## Screenshots
`screenshots/operations.png` and `screenshots/investigation.png` are captured
manually from the running dashboard (browser screenshot). This is the one manual
step — everything else is scripted/reproducible.
