output "decoy_vm_names" {
  description = "Names of the provisioned decoy VMs."
  value       = multipass_instance.decoy[*].name
}

output "enabled_decoys" {
  description = "Decoy modules enabled on each VM."
  value       = var.enabled_decoys
}

output "next_steps" {
  description = "How to find the lab-network IPs of the decoy VMs."
  value       = "Run `multipass list` to see each VM's IP. These are lab-network only; do not expose publicly."
}
