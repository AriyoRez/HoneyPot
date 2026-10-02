# HoneyPot

A student cybersecurity capstone: an **OpenCanary** honeypot that captures decoy
interactions, surfaced through a **custom frontend** we build and own. The MVP
runs three decoy modules — **ssh, http, mysql** — on a dedicated Linux VM. The
frontend reads OpenCanary's event log directly and presents the events as
detections and dashboards. This dev machine is used only for writing code and
running the frontend/test harness; the authoritative decoy deploy target is the
Linux VM.

See [docs/architecture.md](docs/architecture.md) for the system design.

## Repository layout
- [infra/](infra/README.md) — IaC / provisioning stubs (infrastructure lead)
- [sensor/](sensor/README.md) — OpenCanary config template + fixtures (sensor lead)
- [app/](app/README.md) — custom frontend: log reader, detection rules, dashboards (detection lead)
- [tests/](tests/README.md) — target-restricted test harness + fixtures (validation lead)
- [docs/](docs/README.md) — architecture, runbook, network policy, cost model
- [evidence/](evidence/README.md) — sanitized acceptance-test evidence only

## Getting started
Set up the project-local Python environment (`.venv`) and dependencies:

```bash
./setup.sh
```

- **macOS:** double-click `bootstrap.command` from Finder (first run may need
  right-click → Open once, due to Gatekeeper), or run `./setup.sh` in a terminal.
- **Windows:** double-click `bootstrap.bat`, or run `bash setup.sh` in Git Bash.

The script creates `.venv`, installs dependencies, pins them to
`requirements.lock.txt`, and copies `.env.example` to `.env`. It is safe to
re-run. OpenCanary itself may fail to install on macOS/Windows — that is expected;
the authoritative install target is the Linux VM.
