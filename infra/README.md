# infra/

**Owner:** Infrastructure lead

Infrastructure-as-code and provisioning for the honeypot deployment environment.

## What belongs here
- `terraform/` — parameterized **local** VM provisioning via Multipass
  (`vm_count` + `enabled_decoys`). See [`terraform/README.md`](terraform/README.md).
- `cloud-init/` — cloud-init template that installs OpenCanary and enables only the
  chosen decoys on first boot (`cloud-init/opencanary.yaml.tftpl`).
- `deploy.sh` / `deploy.ps1` — no-Terraform fallback that launches the same VMs
  directly with `multipass launch`.

## Deploy target
Local Multipass VMs (lab only) — no cloud provider, no public exposure. `apply` /
`deploy` provisions real local VMs and should run only on the approved lab host.

## Reaching a decoy (don't hardcode the IP)

Multipass assigns a DHCP lease that **changes on reboot** — and the whole subnet can
shift when the host restarts. Never write an address into docs or scripts; it will
go stale silently and the first symptom is a demo that won't connect.

| Platform | Stable handle |
| --- | --- |
| Windows / Hyper-V | `decoy-0.mshome.net` — Multipass registers each guest in DNS and the record follows the lease |
| Any platform | `multipass list`, or the JSON form below |

```bash
multipass info decoy-0 --format json \
  | python -c "import sys,json;print(json.load(sys.stdin)['info']['decoy-0']['ipv4'][0])"
```

The VM name comes from `name_prefix` (Terraform) / `-Prefix` (`deploy.ps1`), so it is
something you control — unlike the lease. `tests/harness/probe.py` defaults to the
hostname for this reason.

Decoy services listen on **2222 / 8080 / 3306** in the Multipass lab (Multipass owns
:22 for guest management) — see [`../docs/network-policy.md`](../docs/network-policy.md).

## What does NOT belong here
- Sensor decoy config (see [`../sensor/`](../sensor/README.md)).
- Secrets or `*.tfstate` files — these are gitignored.
