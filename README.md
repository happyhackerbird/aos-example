# aos-example

The example repository for [agent-os](https://github.com/happyhackerbird/agent-os) (AOS): a small
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
| Docker with Compose v2 (host only; under AOS the runner provides the database) | `compose.yaml` pins `postgres:15-alpine` by digest |
| Chromium for Playwright | `playwright==1.63.0` in `uv.lock`; `uv run playwright install chromium` once on a host (preinstalled in the AOS sandbox image) |

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

## Verification contract

What a runner or an operator can rely on:

- **Reference commit and defect.** The default branch is `main`. The planted defect is in
  `notes/app.py` (`index`): the start page sorts oldest-first before taking five, so a sixth
  note never shows. Expected behaviour is newest-first; `features/recent-list.md` in the
  verify skill describes it.
- **Commands and exit status.**
  `uv sync --frozen` installs (0 on success).
  `uv run --frozen pytest -q` runs the unit tests (0 pass, 1 failures, 2+ usage errors);
  it fails fast with a message when `DATABASE_URL` is unset.
  `uv run --frozen python scripts/verify_browser.py` runs the browser check: 0 all checks
  pass, 1 a check failed, 2 could not run (no `DATABASE_URL`, no Chromium).
  `scripts/check.sh` runs both against a reset database and exits with the first failure's
  status; on this commit it exits 1 (browser check) and the unit tests pass.
- **Services and configuration.** One PostgreSQL 15 database named by `DATABASE_URL`
  (`postgresql://user:pass@host:port/db`), reachable from the checkout; a Chromium build
  for Playwright 1.63 in the Playwright cache; Docker with Compose only when nothing
  provides `DATABASE_URL`. Network: `pypi.org`, `files.pythonhosted.org` for `uv sync`,
  `cdn.playwright.dev` and `playwright.download.prss.microsoft.com` for the browser
  download. The app binds a free port on `127.0.0.1`.
- **State reset and evidence.** `scripts/db.sh reset` recreates the database;
  `python -m notes` migrates and seeds idempotently; every test resets the table
  (`TRUNCATE`) and reseeds. Evidence is written to `evidence/<UTC timestamp>/` under the
  checkout, git-ignored, never deleted by the scripts.
- **Who creates what.** The scripts create: the app server process (stopped by the script
  that started it), the `evidence/` directory, a Compose project `COMPOSE_PROJECT_NAME`
  (default `aos-example-<user>`) with one container and one network when they start the
  database themselves, and `scripts/db.sh down` removes those. AOS must provision and clean
  up: the database behind `DATABASE_URL` when the run cannot reach Docker (a policy run
  cannot), the `~/.cache/uv` and Playwright caches it grants, and the worktree.

## Running it under AOS

```sh
aos repo set aos-example --host mac --test 'scripts/check.sh'
printf '%s\n' 'After saving a note on the start page it is missing from the list once there are more than five notes. Repair it and add a unit test for the order of the start-page list.' > brief.md
aos add --repo aos-example --title 'New notes do not show up on the start page' \
  --brief-file brief.md --accept 'uv sync --frozen' --accept 'scripts/check.sh'
aos ready AO-1
aos run AO-1 --dry-run     # prints the rendered prompt, including the verify-skill pointer, and the policy hash
```

`aos-policy.toml` is the committed v2 policy for the OpenShell sandbox backend. It is
fail-closed and grants network access to `pypi.org:443` and `files.pythonhosted.org:443`
only (for `uv sync --frozen`). Nothing else is reachable.

Inside the sandbox the image provides uv, Python 3.12 and Playwright's Chromium, and the
runner starts a per-run PostgreSQL and exposes `DATABASE_URL` (via `/sandbox/services.env`).
There is no Docker socket, so `scripts/db.sh` is not used; `scripts/check.sh` takes the
provided `DATABASE_URL`.

Before queueing a task, the AOS operator creates two git-ignored files in the source
checkout (this repository cannot carry them, it ignores `.aos/`):

```
# .aos/services.toml  (git-ignored)
[postgres]
```

```
# .aos/evidence.toml  (git-ignored)
dir = "evidence"
```

The acceptance command is `bash scripts/check.sh`. The agent writes proof to
`evidence/<stamp>/` and ends its final message with `Evidence directory: evidence/<stamp>`;
the runner copies that directory out before the sandbox is deleted.

On an unmodified `main` the acceptance check is expected to FAIL (the planted defect). The
branch `solution` carries the reference fix and passes.

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
