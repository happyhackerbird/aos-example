from notes import create_app, db


def test_seed_inserts_five_notes_once(conn):
    assert len(db.list_notes(conn)) == 5
    db.seed(conn)
    assert len(db.list_notes(conn)) == 5


def test_add_note_persists_and_lists_newest_first(conn):
    note = db.add_note(conn, "  Pay rent  ", " Before the 3rd. ")
    assert note["title"] == "Pay rent"
    assert note["body"] == "Before the 3rd."
    notes = db.list_notes(conn)
    assert len(notes) == 6
    assert notes[0]["id"] == note["id"]


def test_add_note_requires_a_title(conn):
    try:
        db.add_note(conn, "   ")
    except ValueError as exc:
        assert "title" in str(exc)
    else:
        raise AssertionError("empty title accepted")
    assert len(db.list_notes(conn)) == 5


def test_health_answers_ok(conn):
    client = create_app().test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_start_page_lists_the_seed_notes(conn):
    client = create_app().test_client()
    page = client.get("/").get_data(as_text=True)
    for title, _ in db.SEED:
        assert title in page
    assert '<span data-testid="total">5</span>' in page


def test_form_post_creates_a_note_and_redirects(conn):
    client = create_app().test_client()
    response = client.post("/notes", data={"title": "From the form", "body": ""})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert db.list_notes(conn)[0]["title"] == "From the form"


def test_form_post_without_title_is_rejected(conn):
    client = create_app().test_client()
    response = client.post("/notes", data={"title": "", "body": "x"})
    assert response.status_code == 400
    assert 'role="alert"' in response.get_data(as_text=True)
    assert len(db.list_notes(conn)) == 5


def test_api_returns_every_note_newest_first(conn):
    client = create_app().test_client()
    db.add_note(conn, "Newest")
    notes = client.get("/api/notes").get_json()
    assert [note["title"] for note in notes][:2] == ["Newest", "Water the plants"]
    assert len(notes) == 6
