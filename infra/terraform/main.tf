# Render a per-VM cloud-init file from the shared template, enabling only the
# chosen decoy modules, then launch one Multipass VM per rendered file.

locals {
  cloudinit_template = "${path.module}/../cloud-init/opencanary.yaml.tftpl"
}

resource "local_file" "cloudinit" {
  count    = var.vm_count
  filename = "${path.module}/.rendered/cloud-init-${count.index}.yaml"
  content = templatefile(local.cloudinit_template, {
    node_index     = count.index
    enabled_decoys = var.enabled_decoys
  })
}

resource "multipass_instance" "decoy" {
  count          = var.vm_count
  name           = "${var.name_prefix}-${count.index}"
  image          = var.vm_image
  cpus           = var.vm_cpus
  memory         = var.vm_mem
  disk           = var.vm_disk
  cloudinit_file = local_file.cloudinit[count.index].filename
}
