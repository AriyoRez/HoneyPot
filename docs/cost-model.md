# Cost Model

## Lab deployment (current) — near zero
The lab runs on **local Multipass VMs** and a Python frontend on an existing dev
machine. No cloud account, no managed services.

| Item | Cost |
| --- | --- |
| Decoy VM(s) (Multipass, local) | $0 — uses local CPU/RAM/disk. ~1 vCPU / 1 GB / 5 GB per decoy by default. |
| Frontend + reader + rules | $0 — Python, runs on the dev/analysis machine. |
| OpenCanary, Flask, tooling | $0 — open source. |
| **Total** | **$0 recurring** (one-time: engineer time). |

## Assumptions / event volume
- Decoys have **no legitimate users**, so event volume = attacker/scan traffic only
  — low in a closed lab (tens–hundreds of events/run), potentially higher if ever
  placed on a reachable segment.
- Log + normalized event sizes are small (JSON lines); storage is negligible at lab
  scale. The reader processes the whole log per request — fine for lab volumes; a
  real deploy would stream/tail.

## If moved off local (future, sponsor-approved)
Not in scope for the lab, but the knobs that would drive cost:
- **Decoy host(s):** one small always-on Linux VM per sensor (cloud VM or on-prem).
  Cost = VM count × instance size × uptime.
- **Analysis/frontend host:** one small always-on host, or run alongside existing
  SOC tooling.
- **Log transport/retention:** collector/forwarder + retention window drive storage.
- **Scale:** `vm_count` × `enabled_decoys` is already parameterized in
  `infra/terraform`, so fleet cost scales linearly and predictably.
