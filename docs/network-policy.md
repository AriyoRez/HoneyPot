# Network Policy

Required network paths for the lab deployment (local Multipass VM). The decoy VM is
**never publicly exposed**; everything stays on the lab network.

| Network path | Ports | Required policy |
| --- | --- | --- |
| Attacker / lab host → decoy VM (decoy services) | 2222 (ssh), 8080 (http), 3306 (mysql) | **Allow** — this is the point. Any connection is captured and treated as suspicious. |
| Admin / dev host → decoy VM (management) | 22 (real sshd) | **Allow from lab/admin only.** Kept separate from the decoy SSH on 2222 so management never collides with the decoy (and you can't lock yourself out). |
| Decoy VM → analysis host (log read path) | log pull via `multipass transfer` / scp, or a one-way ship | **Allow (pull/one-way).** The analysis host reads `/var/log/opencanary/opencanary.log`; the decoy initiates nothing inbound to analysis. |
| Decoy VM → external / internet (egress) | — | **Deny by default.** A honeypot is meant to be attacked; blocking egress prevents it being used as a pivot. Allow only package install during provisioning, then restrict. |
| Public internet → decoy VM | — | **Deny.** No public exposure in this lab; real-world placement (internal VLAN/DMZ) is a separate, sponsor-approved decision. |

## Notes
- Decoy ports (2222/8080/3306) are the MVP profile in
  `sensor/opencanary/opencanary.conf.template`. A more convincing deploy may move
  ssh/http to 22/80 — if so, relocate real management SSH first.
- Multipass places the VM on a host-only/NAT network (e.g. `172.21.x.x`), reachable
  only from the host — adequate for lab/demo, not for observing real adversaries.
