#!/usr/bin/env python3
"""Serve workspace files with permissive CORS headers for Live Preview labs."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CORSStaticHandler(SimpleHTTPRequestHandler):
    """Simple static file handler with CORS and disabled caching."""

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802 - required HTTP method name
        self.send_response(204)
        self.end_headers()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run CORS static server for visual explorer CSV data."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8018, help="TCP port.")
    parser.add_argument("--root", default=".", help="Filesystem root to serve.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    handler_cls = partial(CORSStaticHandler, directory=str(root))

    with ThreadingHTTPServer((args.host, args.port), handler_cls) as server:
        print(f"Serving {root} on http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
