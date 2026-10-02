# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

**Deception Detection Lab** — a student cybersecurity capstone. An **OpenCanary**
honeypot impersonates three internal services that have *no legitimate users*
(SSH, an HTTP web-admin page, MySQL). Events are read directly from the
OpenCanary log by a **custom frontend** we build and own, which surfaces them as
detections and dashboards.

The goal is a **reproducible pipeline**, not just a running honeypot:
- Four detection use cases: unexpected interaction, authentication attempts,
  multi-service probing, and pipeline health.
- Two dashboard views: **Investigation** and **Operations**.
- A triage **runbook** and a repeatable **test harness** with sanitized fixtures.

## Ground rules (read before generating anything)

- **Everything is synthetic.** No real credentials, no CUI, no production data.
  No company deployment happens without separate sponsor approval — this is a lab
  environment first.
- **Default to conservative, clearly-labeled placeholders** (e.g. `REPLACE_ME_*`,
  `PLACEHOLDER`) rather than guessing specifics like real ports, IPs, hostnames,
  tokens, or policies. If the brief hasn't provided a value, leave a labeled TODO
  — do not invent it. The existing docs (`docs/architecture.md`,
  `docs/network-policy.md`, `docs/runbook.md`) are intentional skeletons with
  `TODO:` bullets; keep that discipline.
- **Sanitization is the point.** The reader and frontend exist to strip/normalize
  data before it is displayed. Never introduce raw/unsanitized capture data or
  secrets into tracked files.
- **The test harness must only target approved lab hosts.** Never point any
  traffic-generating client at hosts outside the approved lab scope.
- **Secrets stay local.** `.env` is gitignored; only `.env.example` (placeholder
  names) is tracked. Filled-in `sensor/opencanary/opencanary.conf` is gitignored —
  only the `.template` is committed.

## Where the sensor actually runs

- The OpenCanary sensor is intended to run on an **isolated Linux VM with no public
  exposure**. That VM is the **authoritative install/deploy target**.
- This dev machine (Windows; the brief also references a Mac) is used **only** for
  writing code, running the frontend and test harness locally, and light iteration.
- `opencanary` has known install friction on macOS/Windows. `setup.sh` installs it
  **best-effort** and never lets it block the rest of the install — a local
  opencanary failure is expected and not fatal.

## Layout (each dir owned by one of four team roles)

- `infra/` — Terraform / cloud-init provisioning (currently **stubbed**). *Infrastructure lead.*
- `sensor/` — OpenCanary config template + fixtures. *Sensor lead.*
  - `sensor/opencanary/opencanary.conf.template` — JSON template; `_comment_*`
    keys are ignored by OpenCanary. MVP modules: ssh, http, mysql.
- `app/` — custom frontend: `reader/` (log-reader Python pkg), `rules/`, `dashboards/`. *Detection lead.*
- `tests/` — `harness/` (target-restricted test client, Python pkg) + `fixtures/`. *Validation lead.*
- `docs/` — architecture, network-policy, runbook, cost-model.
- `evidence/` — **sanitized** acceptance-test screenshots/logs only. Raw `*.log` /
  `*.raw` are gitignored.

Most code dirs are currently package stubs (`__init__.py` docstrings only) or
`.gitkeep` placeholders — the scaffolding is in place; implementation is pending.

## Dev environment

- Python **3.10+**, project-local `.venv`.
- Setup: `./setup.sh` (macOS/Linux/Git Bash), or double-click `bootstrap.command`
  (macOS) / `bootstrap.bat` (Windows). Safe to re-run. It creates `.venv`, installs
  deps, runs `pip freeze > requirements.lock.txt`, and copies `.env.example → .env`.
- Dependencies:
  - Runtime (`requirements.txt`): `opencanary`, `pyyaml`, `requests`,
    `python-dotenv`, `jsonschema`.
  - Dev (`requirements-dev.txt`): `pytest`, `ruff`, `pre-commit`.
  - `requirements.lock.txt` is **tracked** on purpose (reproducibility).
- Tests: `pytest`. Lint/format: `ruff`.

## Conventions

- Prefer sanitized fixtures and placeholder values in every generated artifact
  (config, code, docs). Label placeholders clearly.
- Keep role ownership boundaries: sensor config in `sensor/`, frontend + detection
  logic in `app/`, tests/fixtures in `tests/`, narrative in `docs/`, sanitized
  proof in `evidence/`.
- Config/docs default to strict JSON where the tool requires it (OpenCanary reads
  strict JSON — explanatory notes go in `_comment_*` keys).
