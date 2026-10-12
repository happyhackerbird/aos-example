# Reject an empty title

When a user saves a note with an empty or whitespace-only title, the start page comes
back with HTTP 400 and an alert reading "title is required". Nothing is stored, and the
total is unchanged.

## Sub-features

- `empty-alert`: `role=alert` shows the text `title is required`.
- `empty-status`: `POST /notes` answers 400. There is no redirect.
- `empty-no-row`: the row count and "N notes in total" are unchanged.

## How to get to it (user POV)

- Open `<url>/`, leave "Title" empty or type only spaces, optionally fill "Body", and
  choose "Save note".

## Driving it with Playwright

Preconditions:

- The baseline from `README.md`.

- **Whole recipe.** Run `.venv/bin/python .claude/skills/verify/scripts/drive.py empty-title "$RUN"`.
  Exit 0 and every line `PASS`. The evidence is in `$RUN/empty-title/`.
- **Submit blank.** Fill `get_by_test_id("title")` with three spaces and
  `get_by_test_id("body")` with text, wrapping the "Save note" click in
  `page.expect_response(...)` on the `POST /notes`. The status is 400.
- **See the alert.** `get_by_role("alert").inner_text() == "title is required"`.
  Evidence: `01-after-save.png` and its `.aria.txt`.
- **Nothing stored.** `SELECT count(*) FROM notes` and `get_by_test_id("total")` are the
  same as before the click.

## Gotchas

- The URL stays `/notes` after the rejected POST. A reload re-posts the form, so do not
  reload to "reset". Navigate to `/` instead.
- The body the user typed is not refilled into the form after the error. That is
  current behaviour, not a regression.
- The 400 page renders "Recent notes" with the same sort as `/`, so it shows the planted
  defect too. Do not count that against this feature.
