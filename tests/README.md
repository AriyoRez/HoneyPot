# tests/

**Owner:** Validation lead

Test harness and fixtures for validating the decoy → frontend pipeline.

## What belongs here
- `harness/` — target-restricted test client code (Python package). Two tools,
  deliberately separated by whether they touch the network:
  - `generator.py` — **opens no sockets.** Writes synthetic OpenCanary events to a
    JSONL file so the reader/rules/frontend can be exercised with no VM at all.
  - `probe.py` — **sends real traffic** to a decoy VM so OpenCanary records genuine
    events. Enforces the allowlist described below.
  - `sync.py` — **opens no sockets of its own.** Mirrors the decoy's OpenCanary log
    onto this host via `multipass transfer` so the frontend sees live events.
- `fixtures/` — malformed and known-good test fixtures used to validate the
  log reader and detection logic.

## Live probe (`probe.py`)

```bash
python -m tests.harness.probe --dry-run          # check scope, send nothing
python -m tests.harness.probe                    # ssh + http + mysql
python -m tests.harness.probe --services ssh,mysql
python -m tests.harness.probe --target decoy-1.mshome.net
```

**Don't hardcode the decoy's IP.** Multipass hands out a DHCP lease that changes on
reboot — ours has moved three times — so the default target is the hostname
`decoy-0.mshome.net`, which Multipass registers on Windows/Hyper-V and which
follows the lease. On macOS/Linux that name won't resolve; get the address with
`multipass list`, or:

```bash
multipass info decoy-0 --format json \
  | python -c "import sys,json;print(json.load(sys.stdin)['info']['decoy-0']['ipv4'][0])"
```

### How the target restriction is enforced

Two independent checks run in `resolve_target()` **before any socket opens**, and
there is no flag to disable them:

1. **Name** — must be `decoy-N[.mshome.net]`, loopback, or a literal RFC 1918
   address. Catches a typo that would otherwise reach a public host.
2. **Address** — whatever it resolves to must be private or loopback. This is the
   decisive one: a permitted *name* pointing at a public *address* still aborts.

Covered by `test_probe.py`, including the case of a lab-looking hostname resolving
to a public IP. Credentials sent are fixed placeholders; it is a detection probe,
one attempt per service, not a brute-forcer.

## Log mirror (`sync.py`)

```bash
python -m tests.harness.sync --once              # one pull
python -m tests.harness.sync                     # follow, pulling every 3s
python -m tests.harness.sync --instance decoy-1 --dest live-demo.log
```

The sensor logs inside the VM; the frontend reads a file on this host. Without the
mirror the dashboard shows whatever snapshot was last copied by hand, so live
attacks never appear. Run the follow form in its own terminal alongside
`python -m app.frontend --log live-demo.log`.

Pull-only, per `docs/network-policy.md`: this host initiates every fetch and the
decoy is never asked to push. Two guards run before the first pull — the instance
must be a `decoy-N`, and the destination must be a `*.log` outside `evidence/`,
because what lands is a **raw** capture with plaintext passwords. Covered by
`test_sync.py`.

## What does NOT belong here
- Any client configured to target hosts outside the approved lab scope.
- Real credentials or unsanitized capture data.
- Wordlists, or any loop that would turn `probe.py` into a credential-stuffing tool.

## What does NOT belong here
- Any client configured to target hosts outside the approved lab scope.
- Real credentials or unsanitized capture data.
