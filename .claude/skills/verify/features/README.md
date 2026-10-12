# Notes verification map

This directory is the maintained source for verifying what a user of the notes app can
do. Read this index before driving the app, then use the matching feature file as the
recipe. `../SKILL.md` covers launch, doctor, evidence and cleanup.

## Baseline preconditions

- Run all commands from the repository root after `uv sync --frozen`.
- Use a fresh disposable database: `export DATABASE_URL=$(scripts/db.sh reset)`. It
  starts empty, and the server seeds five notes on start: "Buy milk", "Call the
  plumber", "Renew passport", "Book the dentist" and "Water the plants". "Water the
  plants" is the newest of the five, and each is 10 minutes newer than the one before.
- Start the server with `RUN=evidence/$(date -u +%Y%m%dT%H%M%SZ)` and
  `.claude/skills/verify/scripts/app.sh start "$RUN"`.
- Run `.claude/skills/verify/scripts/app.sh doctor "$RUN"` and require every line to be `ok`.
- Never drive a server or a database that this run did not start.

## Driving conventions

- Every recipe starts from the baseline unless its preconditions say otherwise.
  Recipes add notes and never delete them. A second recipe on the same database sees
  more notes than five; the recipes allow for that.
- Use `data-testid` handles and ARIA roles, never positions. The full table is in
  `../SKILL.md` under Drive.
- Drive through the start-page form. `/api/notes` and the `notes` table are only
  second views of the result.
- `drive.py <feature> "$RUN"` runs a whole recipe and writes `$RUN/<feature>/`.

## Proof and skip reporting

- Capture the user action and the state it produced: the before, filled and after
  screenshots, plus ARIA snapshots.
- A mutation proof includes a read of the stored row (`notes` table) and of `/api/notes`.
- Record the feature, the entry point, the evidence path and the exit status of every
  command.
- If an entry point cannot be reached, report the command you tried and the precondition
  that was not met. Do not report it as verified through some other path.

## Feature entry contract

Each feature file starts with an H1 and one paragraph on the user-visible behaviour, then
four H2s in this order: `Sub-features`, `How to get to it (user POV)`,
`Driving it with Playwright`, `Gotchas`. The driving section starts with
`Preconditions:` and pairs each user action with an exact command or handle and the
observable result.

## Features

- [Create a note](./create-note.md): the form saves a note, the page and the table both show it.
- [Recent notes list](./recent-list.md): the start page shows the five newest notes, newest first. **Fails on `main` (planted defect).**
- [Reject an empty title](./empty-title.md): a blank title is refused with an alert and nothing is stored.
- [JSON API and health](./api-health.md): `/api/notes` returns every note newest first, and `/health` reports the database reachable.
