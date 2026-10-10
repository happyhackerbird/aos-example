# aos-example

The example repository for [agent-os](https://github.com/lillyguo/agent-os) (AOS): a small
notes web app with a disposable PostgreSQL, deterministic unit tests, a browser
verification command and a committed `aos-policy.toml`. It exists so an unattended
AOS run can be shown end to end: edit code, install dependencies, test, launch the
app, exercise it in a real browser, and leave evidence.

## What the app does

`python -m notes` serves a start page that lists recent notes and a form that adds one.
`/api/notes` returns every note as JSON, `/health` answers when the database is reachable.
Notes live in one PostgreSQL table; `notes/db.py` is the whole data layer.

## Requirements

| Tool | Pinned where |
|---|---|
| Python 3.12 and [uv](https://docs.astral.sh/uv/) | `.python-version`, `uv.lock` |
| Docker with Compose v2 | `compose.yaml` pins `postgres:15-alpine` by digest |
| Chromium for Playwright | `playwright==1.63.0` in `uv.lock`; `uv run playwright install chromium` once |

## Quick start

```sh
uv sync --frozen
uv run playwright install chromium          # once per machine
export DATABASE_URL=$(scripts/db.sh up)     # disposable PostgreSQL on an ephemeral port
uv run python -m notes                      # prints the URL, serves until Ctrl-C
```

## Checks

```sh
uv run --frozen pytest -q                         # unit tests, need DATABASE_URL
uv run --frozen python scripts/verify_browser.py  # browser verification, needs DATABASE_URL
scripts/check.sh                                  # both, against a fresh database, then tear down
scripts/db.sh down                                # remove the database and its data
```

`scripts/check.sh` uses an existing `DATABASE_URL` when one is set (for example a database
the runner provisioned) and starts its own otherwise. Docker Compose reads
`COMPOSE_PROJECT_NAME`, so concurrent checkouts get separate databases.

The browser verification starts the app on a free port, fills the form in a fresh headless
Chromium profile, saves a note and proves it three ways: the total grew by one, the note is
first in the list, and its row is in the table. Screenshots, the page HTML, the server log
and `result.txt` land in `evidence/<UTC timestamp>/`, which is git-ignored and survives
teardown.

## The planted defect

The checkout ships with one known defect, kept on purpose: **a newly created note does not
appear in the list on the start page once more than five notes exist.** The unit tests pass;
`scripts/verify_browser.py` fails on it. The example AOS task is to repair it, with
`scripts/check.sh` as the acceptance command.

## Verification skill

`.claude/skills/verify/` is the project verification skill, generated with pstack's
`create-verification-skill` and kept by hand. Pi, Claude Code and Codex are told to read
`.claude/skills/verify/SKILL.md` by path (see `AGENTS.md` and the AOS runner prompt), so
one file serves all three. Its `features/` directory maps the user-facing features.

## Running it under AOS

```sh
aos repo set aos-example --host mac --test 'scripts/check.sh'
aos add --repo aos-example --title 'New notes do not show up on the start page' \
  --brief 'After saving a note on the start page it is missing from the list. Fix it and add a test.' \
  --accept 'uv sync --frozen' --accept 'scripts/check.sh'
```

`aos-policy.toml` grants the uv and Playwright caches, the package index and browser
download hosts, and local binding for the app and database ports. Under a policy run the
agent cannot reach the Docker socket, so the runner has to provide `DATABASE_URL`; without
one `scripts/check.sh` starts Compose itself and fails inside the sandbox.

## Layout

```
notes/            the app: db.py (data), app.py (routes), templates/, __main__.py (serve)
tests/            pytest; conftest resets and seeds the database per test
scripts/          db.sh, check.sh, verify_browser.py
compose.yaml      disposable PostgreSQL, tmpfs data, ephemeral host port
aos-policy.toml   AOS repository policy
.claude/skills/verify/   project verification skill and feature map
AGENTS.md, CLAUDE.md     the pointer every harness reads
```
