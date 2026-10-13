"""Browser verification of the notes app.

Starts the app on a free port against DATABASE_URL, drives the real start page in a fresh
headless Chromium profile (Playwright), creates a note through the form, and proves the
result three ways: the total grew by one, the new note is first in the list, and its row is
in the database. Evidence goes to evidence/<UTC timestamp>/ and survives cleanup; the server
this script started is the only process it stops.

Exit status: 0 all checks pass, 1 a check failed, 2 could not run (no database, no browser).
"""
import datetime
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

import psycopg

READY_SECONDS = 20


def wait_ready(url: str, log: pathlib.Path) -> None:
    deadline = time.monotonic() + READY_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    raise RuntimeError(f"app did not answer /health within {READY_SECONDS}s; see {log}")


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set; run `export DATABASE_URL=$(scripts/db.sh up)` first", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        print("playwright is not installed; run `uv sync --frozen`", file=sys.stderr)
        return 2

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = pathlib.Path(os.environ.get("EVIDENCE_DIR", "evidence")) / stamp
    evidence.mkdir(parents=True)
    server_log = evidence / "server.log"
    title = f"Verify {uuid.uuid4().hex[:8]}"
    checks: list[tuple[str, bool]] = []

    with server_log.open("w") as log:
        server = subprocess.Popen([sys.executable, "-m", "notes", "--port", "0"],
                                  stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            url = (server.stdout.readline() or "").strip()
            if not url.startswith("http://"):
                raise RuntimeError(f"app did not print its URL; see {server_log}")
            wait_ready(url, server_log)
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(args=["--no-zygote", "--disable-gpu"])
                except PlaywrightError as exc:
                    print(f"cannot launch Chromium: {exc}\nrun `uv run playwright install chromium`", file=sys.stderr)
                    return 2
                page = browser.new_page()
                page.goto(url + "/")
                page.screenshot(path=str(evidence / "01-start-page.png"), full_page=True)
                before = int(page.get_by_test_id("total").inner_text())
                page.get_by_test_id("title").fill(title)
                page.get_by_test_id("body").fill("created by scripts/verify_browser.py")
                page.get_by_test_id("save").click()
                page.wait_for_load_state()
                page.screenshot(path=str(evidence / "02-after-save.png"), full_page=True)
                (evidence / "after-save.html").write_text(page.content())
                after = int(page.get_by_test_id("total").inner_text())
                titles = page.get_by_test_id("note-title").all_inner_texts()
                browser.close()
            checks.append(("total count grew by one", after == before + 1))
            checks.append(("new note is first in the list", bool(titles) and titles[0] == title))
            checks.append(("new note is visible in the list", title in titles))
            with psycopg.connect(database_url) as conn:
                rows = conn.execute("SELECT count(*) FROM notes WHERE title = %s", (title,)).fetchone()[0]
            checks.append(("row inserted in the notes table", rows == 1))
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    lines = [f"{'PASS' if ok else 'FAIL'} {name}" for name, ok in checks]
    lines.append(f"note title: {title}")
    lines.append(f"list titles: {titles}")
    (evidence / "result.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"evidence: {evidence}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
