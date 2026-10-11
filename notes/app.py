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

    @app.get("/")
    def index():
        with db.connect() as conn:
            notes = db.list_notes(conn)
        recent = sorted(notes, key=lambda note: note["created_at"])[:RECENT]
        return render_template("index.html", notes=recent, total=len(notes), error=None)

    @app.post("/notes")
    def create():
        title = request.form.get("title", "")
        body = request.form.get("body", "")
        with db.connect() as conn:
            try:
                db.add_note(conn, title, body)
            except ValueError as exc:
                notes = db.list_notes(conn)
                recent = sorted(notes, key=lambda note: note["created_at"])[:RECENT]
                return render_template("index.html", notes=recent, total=len(notes), error=str(exc)), 400
        return redirect(url_for("index"))

    @app.get("/api/notes")
    def api_notes():
        with db.connect() as conn:
            notes = db.list_notes(conn)
        return jsonify([note | {"created_at": note["created_at"].isoformat()} for note in notes])

    return app
