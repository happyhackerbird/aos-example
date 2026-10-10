---
name: verify
description: "Drive the aos-example notes app (a Flask web UI over PostgreSQL) the way a user does and prove behaviour with evidence: start it against a disposable database, check it is healthy, create notes through the real form in a fresh headless Chromium, capture screenshots, page HTML and database state, then clean up. Use before claiming any change to what a user sees in the notes app works, when a task's acceptance names scripts/check.sh, or when a report needs proof rather than prose."
---

# Verify the notes app

Pi, Claude Code and Codex all read this file by path (`AGENTS.md` and the AOS runner prompt
point here). Nothing in it needs a harness-specific tool: every step is a shell command run
from the repository root. Two instances can run side by side: the app picks a free port and
the database is isolated by `COMPOSE_PROJECT_NAME`, so a verification run never has to touch
an instance it did not start.

Pick a scratch directory for the run's handles first and keep it outside `evidence/`:

```sh
RUN=${RUN_TMP:-/tmp}/notes-verify-$$; mkdir -p "$RUN"
```

## Launch

```sh
uv sync --frozen                                  # dependencies, pinned by uv.lock
uv run playwright install chromium                # once per machine; no-op when cached
export DATABASE_URL=$(scripts/db.sh up)           # disposable PostgreSQL; `reset` for a fresh one
uv run --frozen python -m notes --port 0 > "$RUN/notes.url" 2> "$RUN/server.log" &
echo $! > "$RUN/notes.pid"
```

Skip `scripts/db.sh up` when `DATABASE_URL` is already set (the runner may provision the
database); the app migrates and seeds it on start, idempotently, and the tests reset it.
The server prints its base URL as its first stdout line, then serves. It is ready when:

```sh
URL=$(head -n1 "$RUN/notes.url")                  # retry until non-empty, within a second
curl -fsS "$URL/health"                           # -> {"status":"ok"}
```

Teardown is in Cleanup below. A failed launch attempt still needs it.

## Doctor

One read-only pass that says whether this instance is worth driving:

```sh
kill -0 "$(cat "$RUN/notes.pid")"                 # our server process is alive
curl -fsS "$URL/health"                           # the app reaches its database
[ "$(scripts/db.sh url)" = "$DATABASE_URL" ]      # the app talks to the database we started (skip when DATABASE_URL was provided)
curl -fsS "$URL/api/notes" | uv run --frozen python -c 'import json,sys; print(len(json.load(sys.stdin)), "notes")'   # 5 on a fresh database
```

If any line fails, read `$RUN/server.log` before doing anything else.

## Drive

**Scripted path, preferred.** `scripts/verify_browser.py` is the complete drive for the
create-a-note feature; it starts and stops its own server, so it needs only
`DATABASE_URL`:

```sh
uv run --frozen python scripts/verify_browser.py   # exit 0 all checks pass, 1 a check failed, 2 could not run
```

**Ad-hoc browser drive** (Python, Playwright is installed in the venv). Stable handles are
`data-testid` attributes, the form's accessible name `New note` and the button text
`Save note`:

```sh
uv run --frozen python - "$URL" <<'PY'
import sys
from playwright.sync_api import sync_playwright
url = sys.argv[1]
with sync_playwright() as p:
    page = p.chromium.launch().new_page()          # a fresh profile every time
    page.goto(url + "/")
    page.get_by_test_id("title").fill("Verify ad hoc")
    page.get_by_test_id("body").fill("typed in the form")
    page.get_by_test_id("save").click(); page.wait_for_load_state()
    print(page.get_by_test_id("total").inner_text(), page.get_by_test_id("note-title").all_inner_texts())
PY
```

**HTTP drive**, for the service surface and for second-view proof:

```sh
curl -fsS "$URL/api/notes"                                   # every note, newest first, JSON
curl -sS -o /dev/null -w '%{http_code}\n' -d 'title=Via curl' -d 'body=' "$URL/notes"   # 302 on success, 400 when the title is empty
```

The feature map in [`features/`](features/README.md) says what each user-facing feature is,
how a user reaches it and what observable end state proves it. Start from the index.

## Evidence

Proof goes under `evidence/<UTC timestamp>/` (git-ignored, survives cleanup);
`scripts/verify_browser.py` writes `01-start-page.png`, `02-after-save.png`,
`after-save.html`, `server.log` and `result.txt` there and prints the directory as its last
line. An ad-hoc drive writes to the same place:

```sh
EVIDENCE=evidence/$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$EVIDENCE"
```

Standards for a proof here:

- Exercise the real user path: the form at `/`, not an `INSERT`, not `db.add_note`.
- Capture the action and the resulting state, not only the final screen: the page before,
  the page after, and the list titles.
- Verify the side effect alongside what is visible: the row in `notes`, through
  `GET /api/notes` or `psql`, as a second view.
- No mocks: the database is real and disposable, the browser is real and headless.
- Name the evidence directory in the report. A screenshot that does not show the new note's
  title is not proof that it was created.

## Cleanup

Stop what this run started, by the handles it recorded, never by process name:

```sh
kill "$(cat "$RUN/notes.pid")" 2>/dev/null; rm -rf "$RUN"
scripts/db.sh down                                # only if this run started the database
```

Do not run `scripts/db.sh down` when `DATABASE_URL` was handed to you. Never `pkill -f notes`
or stop containers by name: another run's instance may be alive. `evidence/` stays.

## Helpers

| Helper | Invocation | Role |
|---|---|---|
| `scripts/db.sh` | `scripts/db.sh up\|url\|reset\|down` | disposable PostgreSQL via Compose, prints `DATABASE_URL` |
| `scripts/verify_browser.py` | `uv run --frozen python scripts/verify_browser.py` | the scripted browser drive with evidence; needs `DATABASE_URL` |
| `scripts/check.sh` | `scripts/check.sh` | fresh database, unit tests, browser drive, teardown; the acceptance command |

All three are executable and documented in `README.md`.
