# Notes verification map

This directory is the maintained source for verifying the user-facing behaviour of the
aos-example notes app. Read this index before driving the app, then use the matching
feature file as the recipe. The driving harness is Playwright (Python, headless Chromium)
for the browser and `curl` for HTTP; `../SKILL.md` has Launch, Doctor and Cleanup.

## Baseline preconditions

- The app was started by this run with `python -m notes --port 0` and `$URL` is its printed
  base URL; `curl -fsS "$URL/health"` answers `{"status":"ok"}`.
- `DATABASE_URL` names a disposable database (`scripts/db.sh up`) or one the runner
  provided; it holds the five seed notes: `Buy milk`, `Call the plumber`, `Renew passport`,
  `Book the dentist`, `Water the plants` (oldest to newest, ten minutes apart).
- Never drive an instance this run did not start.

## Driving conventions

- Start every recipe from the baseline unless its preconditions say otherwise.
- Prefer `data-testid` handles (`title`, `body`, `save`, `total`, `notes`, `note`,
  `note-title`) and accessible names (`New note` form, `Save note` button) over CSS
  position.
- Treat every command as literal; keep quoted values unchanged.
- Browser actions run through Playwright in a fresh context; HTTP actions through `curl`.
- A mutation needs a second view: `GET /api/notes` or a SQL count.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof is a full-page screenshot plus the page HTML, with the note title visible.
- HTTP proof is the command, the status code and the body.
- Record the feature ID and the entry point used with every artifact, under
  `evidence/<UTC timestamp>/`.
- Report an unreachable path with the attempted command and the unmet precondition. Do not
  report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible
behaviour, then exactly four H2 sections in this order: `Sub-features`, `How to get to it
(user POV)`, `Driving it with Playwright and curl` (starting with `Preconditions:`), and
`Gotchas`. Keep implementation details out; name user paths, stable handles, required state,
commands and observable proof.

## Features

- [Create a note](./create-note.md) covers saving from the form, the empty-title rejection,
  and the HTTP form post.
- [Recent notes list](./recent-list.md) covers the start page list, its order and size, and
  the total count.
- [Health and notes API](./health-and-api.md) covers the readiness endpoint and the JSON
  listing used as second-view proof.
