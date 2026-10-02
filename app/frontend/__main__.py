"""CLI entrypoint for the frontend.

Usage:
    python -m app.frontend --log sample.log [--host 127.0.0.1] [--port 8000]

Binds localhost by default (lab only — do not expose the dashboard publicly).
"""

from __future__ import annotations

import argparse

from .app import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.frontend")
    parser.add_argument("--log", required=True, help="path to an OpenCanary JSONL log")
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default localhost)")
    parser.add_argument("--port", type=int, default=8000, help="bind port (default 8000)")
    parser.add_argument("--debug", action="store_true", help="Flask debug mode")
    args = parser.parse_args(argv)

    app = create_app(args.log)
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
