import re

from notes import create_app, db
from notes.app import RECENT

NOTE_TITLE = re.compile(r'data-testid="note-title">([^<]*)<')


def listed_titles(page: str) -> list[str]:
    """The note titles in the order the start page shows them."""
    return NOTE_TITLE.findall(page)


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


def test_start_page_lists_the_seed_notes_newest_first(conn):
    page = create_app().test_client().get("/").get_data(as_text=True)
    assert listed_titles(page) == [title for title, _ in reversed(db.SEED)]


def test_start_page_shows_the_newest_five_once_more_than_five_exist(conn):
    client = create_app().test_client()
    db.add_note(conn, "Sixth note")
    db.add_note(conn, "Seventh note")
    page = client.get("/").get_data(as_text=True)
    titles = listed_titles(page)
    assert len(titles) == RECENT
    assert titles == ["Seventh note", "Sixth note", "Water the plants", "Book the dentist", "Renew passport"]
    assert "Buy milk" not in titles
    assert '<span data-testid="total">7</span>' in page


def test_saved_note_is_first_on_the_start_page_after_redirect(conn):
    client = create_app().test_client()
    page = client.post("/notes", data={"title": "Sixth note", "body": ""}, follow_redirects=True).get_data(as_text=True)
    assert listed_titles(page)[0] == "Sixth note"
    assert "Buy milk" not in listed_titles(page)


def test_rejected_save_keeps_the_start_page_newest_first(conn):
    client = create_app().test_client()
    db.add_note(conn, "Sixth note")
    response = client.post("/notes", data={"title": "   ", "body": "x"})
    assert response.status_code == 400
    titles = listed_titles(response.get_data(as_text=True))
    assert titles == ["Sixth note", "Water the plants", "Book the dentist", "Renew passport", "Call the plumber"]


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
