# Triage Runbook

How to triage a decoy detection surfaced by the frontend
(`app/frontend` → Operations / Investigation). Severities come from `app/rules`.

> Core premise: the decoys impersonate internal services with **no legitimate
> users**. Any interaction is suspicious by default; triage is about scope and
> intent, not "is this real."

## Severity model (from `app/rules`)
| Severity | Fires when | Example |
| --- | --- | --- |
| **HIGH** | Credential use (`authentication_attempt`) OR one source hitting ≥2 services (`multi_service_probing`) | login attempt on the SSH decoy; one IP probing ssh+http+mysql |
| **MEDIUM** | Any interaction with a decoy service (`unexpected_interaction`) | a bare TCP/connection to a decoy |
| **INFO** | `pipeline_health` only (unmapped/startup events) | OpenCanary boot messages |

## Triage steps
1. **Open Operations (`/`).** Check `Alerts`, `Distinct sources`, and `Last event`
   freshness. A stale `Last event` may mean the sensor or log path is down, not calm.
2. **Rule out test traffic.** Confirm the `src_ip` is not a known validation host
   (the test harness is a file writer and should never appear as a live source; if a
   real probe IP matches a teammate's test box, annotate and lower priority).
3. **Open Investigation (`/investigation`).** Filter by the `src_ip` of interest.
   Check first, in order:
   - `event_category` — `auth_attempt` means credentials were sent (highest intent).
   - `service` spread — same IP across multiple services ⇒ `multi_service_probing`.
   - `username` + `password_present` / `password_sha256` — identical hashes across
     events/services indicate **credential reuse** (correlate without plaintext).
   - `timestamp` clustering — rapid bursts suggest automated scanning.

## Escalation path
- **HIGH** → escalate immediately. A `multi_service_probing` finding or any
  `auth_attempt` is a strong indicator of active recon/attack; notify the security
  on-call and preserve the `evidence/` artifacts for the source IP.
- **MEDIUM** → review within the shift. Single passive touches; watch for the same
  `src_ip` escalating to auth attempts or multiple services.
- **INFO** → no action; operational. A rising `unmapped_rate` or missing recent
  events is a **pipeline-health** issue — check the sensor and log transport.

## Interpretation rules
- Any decoy touch = suspicious (no legitimate users exist for these services).
- `pipeline_health`/unmapped events are **not** threats — they are OpenCanary's own
  log lines surfaced for observability (never silently dropped).
- Passwords are only ever hashes here; never expect or request plaintext.
- Known benign sources (documented lab/test hosts) may be excluded — record the
  exclusion; do not hard-code it into detection.
