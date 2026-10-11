"""The notes web app: a start page listing recent notes and a form to add one."""
from flask import Flask, jsonify, redirect, render_template, request, url_for

from . import db

RECENT = 5


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        with db.connect() as conn:
            conn.execute("SELECT 1")
        return jsonify(status="ok")

    def start_page(conn, error: str | None = None) -> str:
        """Render the start page: the total and the RECENT newest notes, newest first.

        Every route that shows the list goes through here so the order is defined once:
        `db.list_notes` already returns newest first, so the head of that list is the
        recent list and a just-saved note is its first entry.
        """
        notes = db.list_notes(conn)
        return render_template("index.html", notes=notes[:RECENT], total=len(notes), error=error)

    @app.get("/")
    def index():
        with db.connect() as conn:
            return start_page(conn)

    @app.post("/notes")
    def create():
        title = request.form.get("title", "")
        body = request.form.get("body", "")
        with db.connect() as conn:
            try:
                db.add_note(conn, title, body)
            except ValueError as exc:
                return start_page(conn, error=str(exc)), 400
        return redirect(url_for("index"))

    @app.get("/api/notes")
    def api_notes():
        with db.connect() as conn:
            notes = db.list_notes(conn)
        return jsonify([note | {"created_at": note["created_at"].isoformat()} for note in notes])

    return app
