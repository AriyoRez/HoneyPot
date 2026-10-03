# docs/

Project documentation for the HoneyPot capstone.

- [architecture.md](architecture.md) — system overview, data flow, network policy, access boundaries
- [runbook.md](runbook.md) — triage, escalation, and interpretation procedures
- [network-policy.md](network-policy.md) — required network paths and policies
- [deception-profile.md](deception-profile.md) — making the decoys believable (ports, persona, placement)
- [event-contract.md](event-contract.md) — canonical normalized-event schema (v0.2) the pipeline produces/consumes
- [cost-model.md](cost-model.md) — cost model

> `architecture.md`, `runbook.md`, `network-policy.md`, `deception-profile.md`, and
> `event-contract.md` describe the built pipeline. Remaining `TODO:` bullets mark
> host-specific values (hostnames, DNS/TLS, subnets) to fill in against a real
> deploy target — don't invent details that haven't been specified.
