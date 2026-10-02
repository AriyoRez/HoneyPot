terraform {
  required_version = ">= 1.5.0"

  required_providers {
    # Local VM provisioning via Canonical Multipass (lab only, no cloud).
    multipass = {
      source  = "larstobi/multipass"
      version = "~> 1.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "multipass" {}
