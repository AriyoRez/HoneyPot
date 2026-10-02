"""CLI for the synthetic event generator (lab-only, file writer).

Usage:
    python -m tests.harness --count 50 --decoys ssh,http,mysql --out sample.log
"""

from __future__ import annotations

import argparse

from .generator import generate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tests.harness")
    parser.add_argument("--count", type=int, default=50, help="number of events to write")
    parser.add_argument(
        "--decoys",
        default="ssh,http,mysql",
        help="comma-separated subset of ssh,http,mysql",
    )
    parser.add_argument("--out", required=True, help="output JSONL log path")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (reproducible)")
    parser.add_argument("--node-id", default="decoy-01", help="non-identifying sensor label")
    args = parser.parse_args(argv)

    decoys = [d.strip() for d in args.decoys.split(",") if d.strip()]
    written = generate(args.count, decoys, args.out, seed=args.seed, node_id=args.node_id)
    print(f"wrote {written} synthetic event(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
