#!/usr/bin/env bash
# =============================================================================
# deploy.sh — launch N local OpenCanary decoy VMs with Multipass (no Terraform).
#
# Fallback for hosts without Terraform / the Multipass TF provider. Renders a
# cloud-init per VM with ONLY the chosen decoys enabled, then `multipass launch`.
#
# Usage:
#   ./deploy.sh --count 2 --decoys ssh,http,mysql
#   ./deploy.sh --count 1 --decoys ssh
#
# Lab only. The decoy VMs must never be publicly exposed.
# =============================================================================
set -euo pipefail

COUNT=1
DECOYS="ssh,http,mysql"
IMAGE="22.04"
PREFIX="decoy"

while [ $# -gt 0 ]; do
  case "$1" in
    --count)  COUNT="$2"; shift 2 ;;
    --decoys) DECOYS="$2"; shift 2 ;;
    --image)  IMAGE="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v multipass >/dev/null 2>&1 || { echo "ERROR: multipass not found. Install Multipass first." >&2; exit 1; }

is_enabled() { case ",$DECOYS," in *",$1,"*) echo true ;; *) echo false ;; esac; }
SSH_EN="$(is_enabled ssh)"; HTTP_EN="$(is_enabled http)"; MYSQL_EN="$(is_enabled mysql)"

RENDER_DIR="$(mktemp -d)"
trap 'rm -rf "$RENDER_DIR"' EXIT

for i in $(seq 0 $((COUNT - 1))); do
  CI="$RENDER_DIR/cloud-init-$i.yaml"
  cat > "$CI" <<EOF
#cloud-config
package_update: true
packages: [python3-pip, python3-venv, python3-dev, libssl-dev, libpcap-dev]
write_files:
  - path: /etc/opencanaryd/opencanary.conf
    permissions: "0640"
    content: |
      {
          "device.node_id": "${PREFIX}-${i}",
          "ip.ignorelist": [], "logtype.ignorelist": [],
          "ssh.enabled": ${SSH_EN}, "ssh.port": 2222,
          "ssh.version": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10",
          "http.enabled": ${HTTP_EN}, "http.port": 8080,
          "http.banner": "Server: nginx/1.18.0 (Ubuntu)", "http.skin": "basicLogin",
          "mysql.enabled": ${MYSQL_EN}, "mysql.port": 3306,
          "mysql.banner": "8.0.36-0ubuntu0.22.04.1",
          "logger": {"class": "PyLogger", "kwargs": {
              "formatters": {"plain": {"format": "%(message)s"}},
              "handlers": {"file": {"class": "logging.FileHandler",
                  "filename": "/var/log/opencanary/opencanary.log"}}}}
      }
runcmd:
  - mkdir -p /var/log/opencanary
  - python3 -m venv /opt/opencanary/venv
  - /opt/opencanary/venv/bin/pip install --upgrade pip
  - /opt/opencanary/venv/bin/pip install opencanary scapy
  - bash -c 'SK=\$(find /opt/opencanary/venv -type d -name basicLogin 2>/dev/null | head -1); [ -n "\$SK" ] && [ ! -f "\$SK/redirect.html" ] && echo "<html><body>Redirecting...</body></html>" > "\$SK/redirect.html"; true'
  - /opt/opencanary/venv/bin/opencanaryd --start
EOF
  echo "==> launching ${PREFIX}-${i} (ssh=$SSH_EN http=$HTTP_EN mysql=$MYSQL_EN)"
  multipass launch "$IMAGE" --name "${PREFIX}-${i}" --cloud-init "$CI"
done

echo "==> done. Run 'multipass list' for IPs (lab network only)."
