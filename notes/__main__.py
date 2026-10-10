"""Serve the app: `python -m notes [--port N]`.

Migrates and seeds the database named by DATABASE_URL, then prints the base URL as the
first stdout line and serves until terminated. --port 0 (the default) picks a free port.
"""
import argparse
import socket
import sys

from . import db
from .app import create_app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m notes")
    parser.add_argument("--port", type=int, default=0, help="port to listen on; 0 picks a free one")
    args = parser.parse_args()
    with db.connect() as conn:
        db.migrate(conn)
        db.seed(conn)
    port = args.port or free_port()
    print(f"http://127.0.0.1:{port}", flush=True)
    create_app().run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    sys.exit(main())
