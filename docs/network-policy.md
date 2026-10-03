# Network Policy

Required network paths for the lab deployment (local Multipass VM). The decoy VM is
**never publicly exposed**; everything stays on the lab network.

| Network path | Ports | Required policy |
| --- | --- | --- |
| Attacker / lab host → decoy VM (decoy services) | **Believable profile:** 22 (ssh), 80/443 (http), 3306 (mysql). **Local Multipass lab:** 2222 (ssh), 8080 (http), 3306 (mysql). | **Allow** — this is the point. Any connection is captured and treated as suspicious. Standard ports blend in; the lab keeps high ports to coexist with Multipass management (see note + `docs/deception-profile.md`). |
| Admin / dev host → decoy VM (management) | Multipass: SSH :22 (Multipass-managed, out of band via `multipass shell`). Dedicated decoy host: management sshd on a **separate** mgmt interface/port. | **Allow from lab/admin only.** Management must never collide with a decoy on the same port. On a plain Multipass guest, Multipass itself owns :22, so the decoy stays on 2222; to put the decoy on :22 (dedicated host), relocate management sshd first so you can't lock yourself out. |
| Decoy VM → analysis host (log read path) | log pull via `multipass transfer` / scp, or a one-way ship | **Allow (pull/one-way).** The analysis host reads `/var/log/opencanary/opencanary.log`; the decoy initiates nothing inbound to analysis. |
| Decoy VM → external / internet (egress) | — | **Deny by default.** A honeypot is meant to be attacked; blocking egress prevents it being used as a pivot. Allow only package install during provisioning, then restrict. |
| Public internet → decoy VM | — | **Deny.** No public exposure in this lab; real-world placement (internal VLAN/DMZ) is a separate, sponsor-approved decision. |

## Notes
- **Believability:** the authoritative template
  (`sensor/opencanary/opencanary.conf.template`) now targets **standard** ports
  (22/80/3306) with OS-consistent banners, because non-standard ports are the loudest
  honeypot tell. See `docs/deception-profile.md` for the full rationale and the two ways
  to free up :22 for the decoy (dedicated decoy NIC, or a host-level 22→2222 / 80→8080
  redirect).
- **Lab exception:** the Multipass emitters (`infra/cloud-init`, `infra/deploy.*`,
  `sensor/install.sh`) keep OpenCanary on **2222/8080/3306**. Multipass manages the
  guest over SSH on :22, so a decoy bound to :22 would collide with management and fail
  to start. Banners are still realistic in the lab; only the ports differ.
- Binding ports <1024 needs root or `cap_net_bind_service` on the interpreter.
- Multipass places the VM on a host-only/NAT network (e.g. `172.21.x.x`), reachable
  only from the host — adequate for lab/demo, not for observing real adversaries.
