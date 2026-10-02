# app/

**Owner:** Detection lead

The **custom frontend** that reads OpenCanary decoy events directly and surfaces
them as detections and dashboards. This replaces the previous CrowdStrike
NG-SIEM integration — we now own the full read → detect → display path.

## What belongs here
- `reader/` — log-reader package. Reads OpenCanary events from the sensor's JSON
  log and normalizes + sanitizes them per [event-contract.md](../docs/event-contract.md).
- `rules/` — detection rules (the four use cases) with severity + alert verdict,
  evaluated against normalized events.
- `frontend/` — the **Flask web app** serving the two live dashboards
  (Operations + Investigation). Templates in `frontend/templates/`.

Run the dashboards:
```bash
python -m app.frontend --log /path/to/opencanary.log   # http://127.0.0.1:8000/
```

## What does NOT belong here
- Raw/unsanitized event data or secrets.
- Sensor decoy config (see [`../sensor/`](../sensor/README.md)).

> **Stack:** Python + Flask (chosen). Only sanitized fields are rendered — the
> reader hashes passwords, so no plaintext can reach a view.
