<#
=============================================================================
 deploy.ps1 - launch N local OpenCanary decoy VMs with Multipass (no Terraform).

 Windows fallback for hosts without Terraform / the Multipass TF provider.
 Renders a cloud-init per VM with ONLY the chosen decoys enabled, then launches.

 Usage:
   ./deploy.ps1 -Count 2 -Decoys ssh,http,mysql
   ./deploy.ps1 -Count 1 -Decoys ssh

 Lab only. The decoy VMs must never be publicly exposed.
=============================================================================
#>
[CmdletBinding()]
param(
  [int]$Count = 1,
  [string[]]$Decoys = @("ssh", "http", "mysql"),
  [string]$Image = "22.04",
  [string]$Prefix = "decoy"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command multipass -ErrorAction SilentlyContinue)) {
  Write-Error "multipass not found. Install Multipass first."
  exit 1
}

function Enabled([string]$name) { if ($Decoys -contains $name) { "true" } else { "false" } }
$sshEn = Enabled "ssh"; $httpEn = Enabled "http"; $mysqlEn = Enabled "mysql"

$renderDir = Join-Path $env:TEMP ("decoy-ci-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $renderDir | Out-Null

try {
  for ($i = 0; $i -lt $Count; $i++) {
    $ci = Join-Path $renderDir "cloud-init-$i.yaml"
    $content = @"
#cloud-config
package_update: true
packages: [python3-pip, python3-venv, python3-dev, libssl-dev, libpcap-dev]
write_files:
  - path: /etc/opencanaryd/opencanary.conf
    permissions: "0640"
    content: |
      {
          "device.node_id": "$Prefix-$i",
          "ip.ignorelist": [], "logtype.ignorelist": [],
          "ssh.enabled": $sshEn, "ssh.port": 2222,
          "ssh.version": "SSH-2.0-OpenSSH_X.Y_PLACEHOLDER",
          "http.enabled": $httpEn, "http.port": 8080,
          "http.banner": "Server: PLACEHOLDER-Web/0.0", "http.skin": "basicLogin",
          "mysql.enabled": $mysqlEn, "mysql.port": 3306,
          "mysql.banner": "5.X.Y-PLACEHOLDER",
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
  - bash -c 'SK=`$(find /opt/opencanary/venv -type d -name basicLogin 2>/dev/null | head -1); [ -n "`$SK" ] && [ ! -f "`$SK/redirect.html" ] && echo "<html><body>Redirecting...</body></html>" > "`$SK/redirect.html"; true'
  - /opt/opencanary/venv/bin/opencanaryd --start
"@
    Set-Content -Path $ci -Value $content -Encoding utf8
    Write-Host "==> launching $Prefix-$i (ssh=$sshEn http=$httpEn mysql=$mysqlEn)"
    multipass launch $Image --name "$Prefix-$i" --cloud-init $ci
  }
  Write-Host "==> done. Run 'multipass list' for IPs (lab network only)."
}
finally {
  Remove-Item -Recurse -Force $renderDir -ErrorAction SilentlyContinue
}
