# JSON API and health

Two read-only JSON routes sit beside the start page. `GET /api/notes` returns every note
(not only five), newest first. `GET /health` answers `{"status": "ok"}` when the server
can reach its database. The proofs and the launch readiness check use both routes as
second views.

## Sub-features

- `api-all`: `/api/notes` returns one object per row, with `id`, `title`, `body` and `created_at` (ISO 8601).
- `api-order`: newest first by `created_at`, then `id`.
- `health-ok`: `/health` returns 200 `{"status":"ok"}` only while the database answers.

## How to get to it (user POV)

- `curl -s <url>/api/notes` and `curl -s <url>/health` (the URL is in `$RUN/url`).

## Driving it with Playwright

Preconditions:

- The baseline from `README.md`. No browser is needed; the recipe uses HTTP directly.

- **Whole recipe.** Run `.venv/bin/python .claude/skills/verify/scripts/drive.py api-health "$RUN"`.
  Exit 0 and every line `PASS`. The evidence is in `$RUN/api-health/`: `health.json`,
  `api-notes.json` and `result.txt`.
- **Health.** `curl -fsS "$(cat $RUN/url)/health"` prints `{"status":"ok"}` and exits 0.
- **All notes.** `curl -fsS "$(cat $RUN/url)/api/notes"` returns as many items as
  `SELECT count(*) FROM notes`, sorted newest first.

## Gotchas

- `/api/notes` sorts correctly on `main`. Only the start page has the planted defect, so
  compare against the API to show that the page is wrong.
- When the database is down, `/health` returns a Flask 500 HTML page, not JSON. Use
  `curl -f` and test the exit status, not the body.
- `created_at` is serialized with its UTC offset. Compare the parsed values, or the
  strings as returned. Do not compare them with the page's `%Y-%m-%d %H:%M` rendering.
