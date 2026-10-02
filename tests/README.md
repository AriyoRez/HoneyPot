# tests/

**Owner:** Validation lead

Test harness and fixtures for validating the decoy → frontend pipeline.

## What belongs here
- `harness/` — target-restricted test client code (Python package). Generates
  test events against **approved lab targets only**.
- `fixtures/` — malformed and known-good test fixtures used to validate the
  log reader and detection logic.

## What does NOT belong here
- Any client configured to target hosts outside the approved lab scope.
- Real credentials or unsanitized capture data.
