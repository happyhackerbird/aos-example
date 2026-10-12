# Recent notes list

The start page lists the five newest notes under "Recent notes", newest first. Above the
form, "N notes in total" counts every note. A note saved a moment ago is always the first
item, however many notes exist.

## Sub-features

- `recent-limit`: at most five items, even when the total is larger.
- `recent-order`: newest first. The items equal the first five of `/api/notes`.
- `recent-new-first`: a note saved just now heads the list.
- `recent-total`: "N notes in total" equals the number of rows.

## How to get to it (user POV)

- Open `<url>/`. This is the only page. The list is also re-rendered after every save
  and after a rejected save.

## Driving it with Playwright

Preconditions:

- The baseline from `README.md`. The recipe itself adds notes until the total is more
  than five, so it works on a fresh or a used database.

- **Whole recipe.** Run `.venv/bin/python .claude/skills/verify/scripts/drive.py recent-list "$RUN"`.
  Exit 0 and every line `PASS`. The evidence is in `$RUN/recent-list/`.
- **Get past five.** Save `Verify filler <hex>` notes through the form while
  `get_by_test_id("total")` is 5 or less.
- **Save the watched note.** Fill "Title" with `Verify recent <hex>` and choose "Save note".
- **Compare.** `get_by_test_id("note-title").all_inner_texts()` has 5 items, item 0 is
  the watched note, and the list equals `[n["title"] for n in GET /api/notes][:5]`.
  `result.txt` records both lists.

## Gotchas

- **Fails on `main` (planted defect):** `notes/app.py` `index` sorts oldest-first before
  taking five, so the list shows the five oldest notes and the new one is missing. The
  expected result there is `FAIL newest note is first` and `FAIL ... newest first`, while
  `PASS Recent notes shows 5 items`. Do not "fix" this unless the task asks you to.
- With five or fewer notes the bug does not show: every note fits, so the item set is
  correct, though the order is still oldest-first. Always go past five.
- Seeded notes are 10 to 50 minutes old, and new notes use `now()`. Order is by
  `created_at`, so on a fresh database new notes are always the newest.
- The rejected-save page (HTTP 400) renders the same list with the same code path. It
  shows the same defect.
