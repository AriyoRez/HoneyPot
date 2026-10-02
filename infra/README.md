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

## What does NOT belong here
- Sensor decoy config (see [`../sensor/`](../sensor/README.md)).
- Secrets or `*.tfstate` files — these are gitignored.
