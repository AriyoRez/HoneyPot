variable "vm_count" {
  description = "Number of decoy VMs to provision."
  type        = number
  default     = 1

  validation {
    condition     = var.vm_count >= 0
    error_message = "vm_count must be >= 0."
  }
}

variable "enabled_decoys" {
  description = "Which decoy modules each VM runs. Subset of ssh, http, mysql."
  type        = list(string)
  default     = ["ssh", "http", "mysql"]

  validation {
    condition     = length(setsubtract(toset(var.enabled_decoys), toset(["ssh", "http", "mysql"]))) == 0
    error_message = "enabled_decoys may only contain: ssh, http, mysql."
  }

  validation {
    condition     = length(var.enabled_decoys) > 0
    error_message = "enabled_decoys must not be empty."
  }
}

variable "vm_image" {
  description = "Multipass image/alias for the decoy VMs."
  type        = string
  default     = "22.04"
}

variable "vm_cpus" {
  description = "vCPUs per decoy VM."
  type        = number
  default     = 1
}

variable "vm_mem" {
  description = "Memory per decoy VM (Multipass size string, e.g. 1G)."
  type        = string
  default     = "1G"
}

variable "vm_disk" {
  description = "Disk per decoy VM (Multipass size string, e.g. 5G)."
  type        = string
  default     = "5G"
}

variable "name_prefix" {
  description = "Non-identifying VM name prefix."
  type        = string
  default     = "decoy"
}
