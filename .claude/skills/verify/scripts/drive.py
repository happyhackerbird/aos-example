"""Drive one mapped feature of a running notes server and record the proof.

    .venv/bin/python .claude/skills/verify/scripts/drive.py FEATURE RUN_DIR

FEATURE is create-note, recent-list, empty-title or api-health (one file each in features/).
RUN_DIR is the directory given to `app.sh start`; the URL and database are read from it.
Writes RUN_DIR/<FEATURE>/: numbered screenshots, ARIA snapshots, page HTML, response bodies,
and result.txt with one PASS/FAIL line per check.

Exit status: 0 every check passed, 1 a check failed, 2 could not run.
"""
import json
import pathlib
import sys
import urllib.request
import uuid

import psycopg
from playwright.sync_api import Error as PlaywrightError, sync_playwright

RECENT = 5


class Proof:
    def __init__(self, out: pathlib.Path):
        self.out = out
        self.checks: list[tuple[str, bool]] = []
        self.notes: list[str] = []
        self.step = 0

    def check(self, name: str, ok: bool) -> None:
        self.checks.append((name, ok))

    def capture(self, page, label: str) -> None:
        self.step += 1
        stem = self.out / f"{self.step:02d}-{label}"
        page.screenshot(path=f"{stem}.png", full_page=True)
        pathlib.Path(f"{stem}.aria.txt").write_text(page.locator("body").aria_snapshot() + "\n")
        pathlib.Path(f"{stem}.html").write_text(page.content())

    def save(self, name: str, text: str) -> None:
        (self.out / name).write_text(text)


def titles(page) -> list[str]:
    return page.get_by_test_id("note-title").all_inner_texts()


def total(page) -> int:
    return int(page.get_by_test_id("total").inner_text())


def db_rows(database_url: str, sql: str, *args):
    with psycopg.connect(database_url) as conn:
        return conn.execute(sql, args).fetchall()


def api_notes(url: str) -> list[dict]:
    with urllib.request.urlopen(url + "/api/notes", timeout=5) as response:
        return json.load(response)


def save_note(page, title: str, body: str) -> int:
    """Fill the form and choose "Save note"; returns the HTTP status of the POST /notes."""
    page.get_by_test_id("title").fill(title)
    page.get_by_test_id("body").fill(body)
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/notes")) as posted:
        page.get_by_test_id("save").click()
    page.wait_for_load_state()
    return posted.value.status


def create_note(page, url, database_url, proof: Proof) -> None:
    page.goto(url + "/")
    proof.capture(page, "start-page")
    before = total(page)
    title = f"Verify create {uuid.uuid4().hex[:8]}"
    body = "created through the start-page form"
    page.get_by_test_id("title").fill(title)
    page.get_by_test_id("body").fill(body)
    proof.capture(page, "form-filled")
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/notes")) as posted:
        page.get_by_test_id("save").click()
    page.wait_for_load_state()
    proof.capture(page, "after-save")
    shown = titles(page)
    proof.notes += [f"note title: {title}", f"total before/after: {before}/{total(page)}", f"list titles: {shown}"]
    proof.check("POST /notes redirects (303/302)", posted.value.status in (302, 303))
    proof.check("browser is back on the start page", page.url.rstrip("/") == url)
    proof.check("total grew by one", total(page) == before + 1)
    proof.check("new note is visible in Recent notes", title in shown)
    proof.check("new note is first in Recent notes", bool(shown) and shown[0] == title)
    rows = db_rows(database_url, "SELECT title, body FROM notes WHERE title = %s", title)
    proof.notes.append(f"db rows: {rows}")
    proof.check("exactly one row with that title and body in notes", rows == [(title, body)])
    api = api_notes(url)
    proof.check("/api/notes lists the new note first", bool(api) and api[0]["title"] == title)


def recent_list(page, url, database_url, proof: Proof) -> None:
    page.goto(url + "/")
    proof.capture(page, "start-page")
    # Save notes until the list has more than RECENT to choose from, then one more to watch.
    while total(page) <= RECENT:
        save_note(page, f"Verify filler {uuid.uuid4().hex[:8]}", "")
    title = f"Verify recent {uuid.uuid4().hex[:8]}"
    save_note(page, title, "should head the list")
    proof.capture(page, "after-save")
    shown = titles(page)
    expected = [note["title"] for note in api_notes(url)][:RECENT]
    proof.notes += [f"note title: {title}", f"total: {total(page)}", f"list titles: {shown}",
                    f"newest {RECENT} by /api/notes: {expected}"]
    proof.check(f"Recent notes shows {RECENT} items", len(shown) == RECENT)
    proof.check("newest note is first in Recent notes", bool(shown) and shown[0] == title)
    proof.check(f"Recent notes is the newest {RECENT}, newest first", shown == expected)


def empty_title(page, url, database_url, proof: Proof) -> None:
    page.goto(url + "/")
    before = total(page)
    rows_before = db_rows(database_url, "SELECT count(*) FROM notes")[0][0]
    status = save_note(page, "   ", "a body without a title")
    proof.capture(page, "after-save")
    alert = page.get_by_role("alert")
    proof.notes += [f"POST status: {status}", f"alert: {alert.all_inner_texts()}"]
    proof.check("POST /notes answers 400", status == 400)
    proof.check("alert reads 'title is required'", alert.count() == 1 and alert.inner_text() == "title is required")
    proof.check("total unchanged", total(page) == before)
    proof.check("no row inserted", db_rows(database_url, "SELECT count(*) FROM notes")[0][0] == rows_before)


def api_health(page, url, database_url, proof: Proof) -> None:
    with urllib.request.urlopen(url + "/health", timeout=5) as response:
        health_status, health = response.status, response.read().decode()
    proof.save("health.json", health)
    notes = api_notes(url)
    proof.save("api-notes.json", json.dumps(notes, indent=2) + "\n")
    count = db_rows(database_url, "SELECT count(*) FROM notes")[0][0]
    stamps = [note["created_at"] for note in notes]
    proof.notes += [f"/health: {health_status} {health.strip()}", f"/api/notes: {len(notes)} notes, db: {count}"]
    proof.check("/health answers 200 {\"status\": \"ok\"}", health_status == 200 and json.loads(health) == {"status": "ok"})
    proof.check("/api/notes returns every row", len(notes) == count)
    proof.check("/api/notes items have id, title, body, created_at",
                all(set(note) == {"id", "title", "body", "created_at"} for note in notes))
    proof.check("/api/notes is newest first", stamps == sorted(stamps, reverse=True))


FEATURES = {"create-note": create_note, "recent-list": recent_list,
            "empty-title": empty_title, "api-health": api_health}


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in FEATURES:
        print(f"usage: drive.py {'|'.join(FEATURES)} RUN_DIR", file=sys.stderr)
        return 2
    feature, run = sys.argv[1], pathlib.Path(sys.argv[2])
    try:
        url = (run / "url").read_text().split()[0]
        database_url = (run / "database_url").read_text().strip()
    except (OSError, IndexError):
        print(f"{run} has no url/database_url; run app.sh start {run} first", file=sys.stderr)
        return 2
    out = run / feature
    out.mkdir(parents=True, exist_ok=True)
    proof = Proof(out)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(args=["--no-zygote", "--disable-gpu"])
        except PlaywrightError as exc:
            print(f"cannot launch Chromium: {exc}\nrun: uv run playwright install chromium", file=sys.stderr)
            return 2
        try:
            FEATURES[feature](browser.new_page(), url, database_url, proof)
        finally:
            browser.close()
    lines = [f"{'PASS' if ok else 'FAIL'} {name}" for name, ok in proof.checks] + proof.notes
    proof.save("result.txt", "\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"evidence: {out}")
    return 0 if proof.checks and all(ok for _, ok in proof.checks) else 1


if __name__ == "__main__":
    sys.exit(main())
