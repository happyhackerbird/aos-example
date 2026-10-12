---
name: verify
description: Launch, check, drive and prove the aos-example notes web app (Flask start page with a note form, /api/notes, /health, on a disposable PostgreSQL) in headless Chromium, and leave evidence under evidence/<UTC stamp>/. Use before claiming any change to notes/ works, to reproduce a bug in the real app, or to check a feature from features/.
---

# Verify the notes app

The app is a Flask server (`python -m notes`) with one user surface, the start page `/`:
a total count, a "New note" form and a "Recent notes" list. Two JSON routes sit beside it:
`/api/notes` and `/health`. Data is one PostgreSQL table behind `DATABASE_URL`.

Run every command from the repository root. All of them are plain shell; any agent can
run them. The feature recipes are in `features/` next to this file; read
`features/README.md` before driving.

## Known state of `main`

`main` carries a planted defect on purpose (README, "The planted defect"): the start
page sorts oldest-first before taking five, so once more than five notes exist a new note
is missing from "Recent notes". `scripts/verify_browser.py` and the `create-note` and
`recent-list` drives fail on it on an unmodified `main`. That failure is the expected
result there, not a broken harness. Do not change `notes/` to make a proof pass unless
the task is to fix that defect.

## Setup, once per checkout

```sh
uv sync --frozen                      # creates .venv; exit 0
uv run playwright install chromium    # once per machine; skips if cached
```

Docker with Compose v2 must answer `docker info`. Under a sandbox without the Docker
socket, the runner must provide `DATABASE_URL` instead, and you skip `scripts/db.sh`.

## Launch

1. Pick a run directory. It is the evidence directory too:

   ```sh
   RUN=evidence/$(date -u +%Y%m%dT%H%M%SZ)
   ```

2. Start the database. Use only `scripts/db.sh`. It owns one Compose project,
   `COMPOSE_PROJECT_NAME` (default `aos-example-$USER`), and never touches other
   containers:

   ```sh
   export DATABASE_URL=$(scripts/db.sh reset)    # fresh, empty; prints postgresql://notes:notes@127.0.0.1:<port>/notes
   ```

   Use `scripts/db.sh up` instead of `reset` to keep existing rows.

3. Start the server:

   ```sh
   .claude/skills/verify/scripts/app.sh start "$RUN"    # prints http://127.0.0.1:<port>
   ```

   The script runs `.venv/bin/python -m notes --port 0` detached, through
   `.claude/skills/verify/scripts/detach.py` (double fork, own session and process
   group), so the server survives the end of the shell call that started it. The server
   migrates the database and seeds five notes (only into an empty table), then prints its
   URL. The script records `url`, `database_url`, `server.log`, `launcher.pid`,
   `detached.pid` and `server.pid` in `$RUN`. `server.pid` is the process that holds the
   port, read with `lsof` and accepted only if it is the detached process (the pid
   `detach.py` wrote to `detached.pid`) or that process's child. Do not assume `$!` is the
   server: it is `detach.py`, which exits as soon as the server is detached.
   **Ready** means the script printed the URL: `/health` answered 200. It exits 1 if the
   server dies or does not answer within 20 s. The cause is then in `$RUN/server.log`.

Bash state does not always carry over between tool calls. Re-derive the values with
`RUN=evidence/<stamp>` and `export DATABASE_URL=$(cat $RUN/database_url)` when needed.

## Doctor

Run this first, and again whenever anything looks off. It is read-only:

```sh
.claude/skills/verify/scripts/app.sh doctor "$RUN"
```

It prints one `ok`/`FAIL` line per check and exits 1 on any `FAIL`:

- the PID in `$RUN/server.pid` is alive and is a `-m notes` process;
- `<url>/health` answers 200 `{"status":"ok"}` (so the database is reachable);
- that PID owns the listening port;
- the server's database is the one `scripts/db.sh url` reports for this checkout. When
  no Compose database is running, the check uses `$DATABASE_URL` from the environment
  instead.

The last line gives the build: the commit, and `+ uncommitted changes in notes/` when
`notes/` differs from HEAD. A server started before you edited `notes/` runs old code.
The server has no reloader, so restart it with `stop` then `start` after every code change.

Do not drive an instance that this run did not start. If doctor fails, stop and start
again. Do not reuse a URL you found some other way.

## Drive

The harness is Playwright 1.63 (sync API, headless Chromium, fresh profile per run). You
can drive the app in two ways.

**One mapped feature against your instance** (the normal way):

```sh
.venv/bin/python .claude/skills/verify/scripts/drive.py create-note "$RUN"
```

The `FEATURE` argument is one of `create-note`, `recent-list`, `empty-title`,
`api-health`. Each one maps to a file in `features/`. The script prints one PASS/FAIL line
per check and the evidence path. Exit status: 0 all checks pass, 1 a check failed, 2 it
could not run (no `$RUN/url`, or Chromium is missing).

**The repository's acceptance check**. It is self-contained: it starts its own server on
another free port and stops it.

```sh
uv run --frozen python scripts/verify_browser.py    # needs DATABASE_URL; exit 0 / 1 / 2 as above
scripts/check.sh                                     # pytest, then verify_browser.py, on a reset DB
```

To drive by hand (a new feature, or an ad-hoc reproduction), use the stable handles from
`notes/templates/index.html`. Do not use positions or CSS layout:

| Handle | What it is |
|---|---|
| `get_by_test_id("total")` | the number in "N notes in total" |
| `get_by_role("form", name="New note")` | the form, `POST /notes` |
| `get_by_test_id("title")`, `get_by_test_id("body")` | the inputs (labels "Title", "Body") |
| `get_by_test_id("save")` / `get_by_role("button", name="Save note")` | submit |
| `get_by_role("alert")` | validation error, only after a rejected save |
| `get_by_test_id("notes")` / `get_by_test_id("note")` / `get_by_test_id("note-title")` | "Recent notes" list, items, titles |

Here is a minimal ad-hoc session. It uses the same URL and evidence directory:

```sh
.venv/bin/python - "$RUN" <<'EOF'
import pathlib, sys
from playwright.sync_api import sync_playwright
run = pathlib.Path(sys.argv[1]); url = (run / "url").read_text().split()[0]
with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto(url + "/")
    print(page.get_by_test_id("note-title").all_inner_texts())
    page.screenshot(path=str(run / "adhoc.png"), full_page=True)
EOF
```

## Evidence

Everything goes under `evidence/<UTC stamp>/`. The directory is git-ignored, and no
script here ever deletes it:

- `$RUN/server.log`, `url`, `database_url`: the instance you drove.
- `$RUN/<feature>/`: `NN-<step>.png`, `NN-<step>.aria.txt` (ARIA snapshot), `NN-<step>.html`,
  JSON bodies where relevant, and `result.txt` (PASS/FAIL lines plus the values compared).
- `scripts/verify_browser.py` writes its own `evidence/<stamp>/` with `01-start-page.png`,
  `02-after-save.png`, `after-save.html`, `server.log`, `result.txt`.

A proof must meet these standards:

- Drive the real user path: the form at `/`, submitted with the "Save note" button. Do
  not call `notes.db` functions or insert rows to stand in for the user. Read the
  database or `/api/notes` only to check the result.
- Capture the action and the state it produced: the page before, the filled form and the
  page after. A final screenshot alone is not enough.
- Check the side effect next to the visible result. The `notes` row must exist (or must
  not exist, for a rejected save), and `/api/notes` must agree with what the page shows.
- Nothing is mocked. The database is real and disposable.
- Report the evidence path, the exit status of each command, and every FAIL line. A run
  that could not drive a mapped entry point counts as not verified. Do not report it as
  passing through some other path.

## Cleanup

Stop only what this run started, in this order:

```sh
.claude/skills/verify/scripts/app.sh stop "$RUN"    # TERM, then KILL after 10 s, of $RUN/server.pid, then $RUN/detached.pid and $RUN/launcher.pid if still alive
scripts/db.sh down                                  # removes this checkout's Compose project: container, network, tmpfs data
ls "$RUN"                                           # the evidence is still there
```

`app.sh stop` is idempotent. Run it after every failed attempt as well. Never use `pkill`,
`killall`, or `docker stop`/`rm` on containers that `scripts/db.sh` did not create. If
the runner provided `DATABASE_URL`, skip `scripts/db.sh down`; the runner owns that
database. Leave `evidence/` in place.

## Isolation

- Each server binds a free port on `127.0.0.1` (`--port 0`), so any number of servers
  can run side by side.
- The database is shared by every server on the same `DATABASE_URL`. Two agents driving
  one database will see each other's notes, and `recent-list` assumptions break. Give
  concurrent checkouts their own `COMPOSE_PROJECT_NAME` (for example
  `COMPOSE_PROJECT_NAME=aos-example-$USER-2 scripts/db.sh up`), and use that same value
  for `db.sh url` and `db.sh down`.
- `scripts/check.sh`, `scripts/db.sh reset` and the unit tests (`TRUNCATE`) wipe the
  table. Do not run them against a database another run is driving.
