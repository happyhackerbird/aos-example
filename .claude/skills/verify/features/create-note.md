# Create a note

A user types a title and an optional body into the "New note" form on the start page and
chooses "Save note". The browser returns to the start page, the total goes up by one,
the note appears at the top of "Recent notes", and it is stored.

## Sub-features

- `create-save`: a title and body are stored as one row, with surrounding whitespace removed.
- `create-redirect`: after a save the browser is back on `/` (POST/redirect/GET). A reload does not save again.
- `create-visible`: the new note is first in "Recent notes" and counts in "N notes in total".
- `create-api`: `/api/notes` lists the new note first.

## How to get to it (user POV)

- Open `<url>/`, fill "Title" and "Body", and choose "Save note".
- Press Enter in either input. This submits the same form.

## Driving it with Playwright

Preconditions:

- The baseline from `README.md`: a server started by this run, and doctor all `ok`.
- No note already has the title being created. `drive.py` uses `Verify create <8 hex>`.

- **Whole recipe.** Run `.venv/bin/python .claude/skills/verify/scripts/drive.py create-note "$RUN"`.
  Exit 0 and every line `PASS`. The evidence is in `$RUN/create-note/`.
- **Open the page.** `page.goto(url + "/")`. `get_by_test_id("total")` reads `5` on a fresh baseline.
  Evidence: `01-start-page.png`.
- **Fill the form.** `get_by_test_id("title").fill(title)` and `get_by_test_id("body").fill(body)`.
  Evidence: `02-form-filled.png`.
- **Save.** `get_by_test_id("save").click()`. The `POST /notes` answers 302 and the page
  reloads `/`. Evidence: `03-after-save.png`, `.aria.txt`, `.html`.
- **Visible result.** `total` is one more than before, and `get_by_test_id("note-title").all_inner_texts()[0] == title`.
- **Stored result.** `SELECT title, body FROM notes WHERE title = %s` returns exactly
  `[(title, body)]`, and `GET <url>/api/notes` has `[0]["title"] == title`.

## Gotchas

- On `main` the check "new note is visible/first in Recent notes" **fails**. This is the
  planted defect: with six or more notes, the page shows the five oldest. Total, row and
  API checks still pass. That split tells you the save works and the list is wrong.
- The server strips whitespace from the title and body before storing them. Compare the
  stored and rendered values with the stripped strings.
- The form has no `required` attribute, so the browser itself never blocks a blank title.
  The server does (see `empty-title.md`).
- Each run adds a row. To get back to five seeded notes, use `scripts/db.sh reset`, then
  restart the server so it seeds again.
