# infra/cloud-init

cloud-init provisioning for the decoy VMs.

- `opencanary.yaml.tftpl` — Terraform templated cloud-init that installs OpenCanary
  on first boot and enables **only** the modules passed in `enabled_decoys`
  (ssh/http/mysql). Rendered per-VM by [`../terraform/main.tf`](../terraform/main.tf)
  (output goes to the gitignored `.rendered/`).

The no-Terraform fallback ([`../deploy.sh`](../deploy.sh) /
[`../deploy.ps1`](../deploy.ps1)) generates its own equivalent inline cloud-init
and launches the VMs directly with `multipass launch`.

Lab only — the VMs it provisions must never be publicly exposed.
