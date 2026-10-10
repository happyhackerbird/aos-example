# Health and notes API

The app answers `/health` when it can reach its database and lists every note as JSON at
`/api/notes`, newest first; both are how a user or an operator checks the service without
the page, and how a verification run proves a mutation from a second view.

## Sub-features

- `health-ok` answers `200 {"status":"ok"}` when the database is reachable.
- `health-down` fails (non-200) when the database is unreachable.
- `api-list` returns every note with `id`, `title`, `body` and ISO-8601 `created_at`.
- `api-order` orders newest first and is not capped at five.

## How to get to it (user POV)

- `GET /health`.
- `GET /api/notes`.

## Driving it with Playwright and curl

Preconditions:

- Baseline from the index.

- **Health.** Run `curl -fsS -w '\n%{http_code}\n' "$URL/health"`. Prints
  `{"status":"ok"}` and `200`.
- **Listing.** Run `curl -fsS "$URL/api/notes"`. A JSON array of five objects; the first is
  `Water the plants`, each has `id`, `title`, `body`, `created_at`.
- **Order after a save.** Save a note through the form, then repeat the listing. Six
  objects, the new one first.
- **Health without the database.** Run `scripts/db.sh down` for a database this run
  started, then `curl -sS -o /dev/null -w '%{http_code}\n' "$URL/health"`. Prints `500`.
  Start the database again with `scripts/db.sh up` before any other recipe (the port, and
  so `DATABASE_URL`, may change: restart the app).
- **Proof.** Keep the commands, status codes and bodies in `evidence/<UTC timestamp>/`.

## Gotchas

- `/health` opens a new database connection per request; a database that was stopped
  mid-run shows up here first, before the start page errors.
- `created_at` is timezone-aware (`+00:00`); compare instants, not strings.
- Do not run the `health-down` step when `DATABASE_URL` was provided by the runner: that
  database is not yours to stop.
