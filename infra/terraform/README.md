# infra/terraform

Parameterized **local** VM provisioning for the decoy fleet, using Canonical
**Multipass** (no cloud account, spend, or sponsor approval needed). Deploys
`vm_count` Linux VMs; each boots cloud-init that installs OpenCanary with **only**
the modules listed in `enabled_decoys`.

## Prerequisites
- [Multipass](https://multipass.run/) installed and working (`multipass version`).
- Terraform >= 1.5.
- The Multipass provider (`larstobi/multipass`) — fetched by `terraform init`.

## Usage
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit vm_count / enabled_decoys
terraform init
terraform plan
terraform apply        # provisions the VMs on THIS host (lab only)
multipass list         # find each VM's lab-network IP
terraform destroy      # tear down
```

## Variables
| Variable | Default | Purpose |
| --- | --- | --- |
| `vm_count` | `1` | Number of decoy VMs. |
| `enabled_decoys` | `["ssh","http","mysql"]` | Which modules each VM runs (subset). |
| `vm_image` | `22.04` | Multipass image/alias. |
| `vm_cpus` / `vm_mem` / `vm_disk` | `1` / `1G` / `5G` | Per-VM sizing. |

## Important
- **Lab only.** The decoy VMs must never be publicly exposed.
- `terraform apply` provisions real local VMs — run it on the approved lab host,
  not as part of CI. In this repo's current state the IaC is **validated but not
  applied**.
- Rendered per-VM cloud-init is written to `.rendered/` (gitignored); never commit
  a filled-in config.
- No Terraform? Use the fallback wrapper: [`../deploy.sh`](../deploy.sh) /
  [`../deploy.ps1`](../deploy.ps1).
