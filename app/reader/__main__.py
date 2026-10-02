"""CLI: normalize an OpenCanary JSONL log and print normalized events as JSONL.

Usage:
    python -m app.reader <logfile>

Normalized events are written to stdout (one JSON object per line); a summary of
any malformed/skipped input lines is written to stderr. This is the stable
interface the GUI team builds against.
"""

from __future__ import annotations

import argparse
import json
import sys

from .reader import MalformedLine, read_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.reader")
    parser.add_argument("logfile", help="path to an OpenCanary JSONL log")
    args = parser.parse_args(argv)

    errors: list[MalformedLine] = []
    try:
        for event in read_log(args.logfile, errors=errors):
            sys.stdout.write(json.dumps(event) + "\n")
    except FileNotFoundError:
        print(f"error: no such file: {args.logfile}", file=sys.stderr)
        return 2

    if errors:
        print(f"skipped {len(errors)} malformed line(s):", file=sys.stderr)
        for e in errors:
            print(f"  line {e.line_number}: {e.reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
