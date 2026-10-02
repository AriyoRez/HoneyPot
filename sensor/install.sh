#!/usr/bin/env bash
# =============================================================================
# install.sh — stand up a bare OpenCanary decoy on an EXISTING Debian/Ubuntu VM.
#
# This is the repo-free SENSOR side: it installs OpenCanary and starts the
# decoys. It does NOT install the analysis pipeline (reader/rules/frontend) —
# that runs on the analysis host and reads the log this produces.
#
# Usage (on the decoy VM, as a sudo-capable user):
#   DECOYS="ssh,http,mysql" NODE_ID="decoy-01" ./install.sh
#
# Lab only. The decoy VM must never be publicly exposed. Idempotent-ish: safe to
# re-run; it overwrites the config and restarts the daemon.
# =============================================================================
set -euo pipefail

DECOYS="${DECOYS:-ssh,http,mysql}"
NODE_ID="${NODE_ID:-decoy-01}"
VENV="/opt/opencanary/venv"
CONF="/etc/opencanaryd/opencanary.conf"   # one of OpenCanary's search paths
LOG_DIR="/var/log/opencanary"

enabled() { case ",$DECOYS," in *",$1,"*) echo true ;; *) echo false ;; esac; }
SSH_EN="$(enabled ssh)"; HTTP_EN="$(enabled http)"; MYSQL_EN="$(enabled mysql)"

echo "==> Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv python3-dev libssl-dev libpcap-dev

echo "==> Creating venv + installing opencanary"
sudo python3 -m venv "$VENV"
sudo "$VENV/bin/pip" install --upgrade pip
sudo "$VENV/bin/pip" install opencanary scapy

echo "==> Writing config to $CONF (OpenCanary has no --config flag; path matters)"
sudo mkdir -p /etc/opencanaryd "$LOG_DIR"
sudo tee "$CONF" >/dev/null <<EOF
{
    "device.node_id": "$NODE_ID",
    "ip.ignorelist": [], "logtype.ignorelist": [],
    "ssh.enabled": $SSH_EN, "ssh.port": 2222,
    "ssh.version": "SSH-2.0-OpenSSH_X.Y_PLACEHOLDER",
    "http.enabled": $HTTP_EN, "http.port": 8080,
    "http.banner": "Server: PLACEHOLDER-Web/0.0", "http.skin": "basicLogin",
    "mysql.enabled": $MYSQL_EN, "mysql.port": 3306,
    "mysql.banner": "5.X.Y-PLACEHOLDER",
    "logger": {"class": "PyLogger", "kwargs": {
        "formatters": {"plain": {"format": "%(message)s"}},
        "handlers": {"file": {"class": "logging.FileHandler",
            "filename": "$LOG_DIR/opencanary.log"}}}}
}
EOF

echo "==> Applying basicLogin skin fix (upstream ships without redirect.html)"
SK="$(sudo find "$VENV" -type d -name basicLogin 2>/dev/null | head -1 || true)"
if [ -n "$SK" ] && [ ! -f "$SK/redirect.html" ]; then
    echo '<html><body>Redirecting...</body></html>' | sudo tee "$SK/redirect.html" >/dev/null
fi

echo "==> Starting opencanaryd"
sudo "$VENV/bin/opencanaryd" --stop 2>/dev/null || true
sudo "$VENV/bin/opencanaryd" --start

echo ""
echo "============================================================"
echo " Decoy '$NODE_ID' up (ssh=$SSH_EN http=$HTTP_EN mysql=$MYSQL_EN)."
echo " Verify:  sudo ss -tlnp | grep -E ':2222|:8080|:3306'"
echo " Log:     $LOG_DIR/opencanary.log"
echo " Feed it to the analysis pipeline:  python -m app.reader <that log>"
echo "============================================================"
