"""Database layer: one table, plain SQL through psycopg."""
import os

import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         SERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SEED = [
    ("Buy milk", "Two litres, whole."),
    ("Call the plumber", "The kitchen tap drips."),
    ("Renew passport", "It expires in March."),
    ("Book the dentist", "Six-month check-up."),
    ("Water the plants", "Every Sunday."),
]


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set; run `scripts/db.sh up` and export its output")
    return url


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url(), autocommit=True)


def migrate(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA)


def seed(conn: psycopg.Connection) -> None:
    """Insert the sample notes into an empty table; a non-empty table is left alone."""
    if conn.execute("SELECT count(*) FROM notes").fetchone()[0]:
        return
    for position, (title, body) in enumerate(SEED):
        minutes_ago = (len(SEED) - position) * 10
        conn.execute(
            "INSERT INTO notes (title, body, created_at) VALUES (%s, %s, now() - make_interval(mins => %s))",
            (title, body, minutes_ago),
        )


def reset(conn: psycopg.Connection) -> None:
    conn.execute("TRUNCATE notes RESTART IDENTITY")


def add_note(conn: psycopg.Connection, title: str, body: str = "") -> dict:
    title = title.strip()
    if not title:
        raise ValueError("title is required")
    row = conn.execute(
        "INSERT INTO notes (title, body) VALUES (%s, %s) RETURNING id, title, body, created_at",
        (title, body.strip()),
    ).fetchone()
    return _note(row)


def list_notes(conn: psycopg.Connection) -> list[dict]:
    """Every note, newest first."""
    rows = conn.execute("SELECT id, title, body, created_at FROM notes ORDER BY created_at DESC, id DESC")
    return [_note(row) for row in rows]


def _note(row) -> dict:
    return {"id": row[0], "title": row[1], "body": row[2], "created_at": row[3]}
