# Create a note

Create a note lets a user save a titled note from the form on the start page and see it in
the list straight away; an empty title is rejected with a message and nothing is saved.

## Sub-features

- `create-save` persists a title and body from the form and returns to the start page.
- `create-trim` stores the title without surrounding whitespace.
- `create-empty` rejects a blank title with an alert and keeps the list unchanged.
- `create-http` accepts the same form fields as a plain HTTP post.

## How to get to it (user POV)

- Fill `Title` and `Body` in the `New note` form on the start page and choose `Save note`.
- Post `title` and `body` form fields to `/notes`.

## Driving it with Playwright and curl

Preconditions:

- Baseline from the index; `$URL` answers `/health`.
- No note is titled `Release checklist`.

- **Fill the form.** Run `page.get_by_test_id("title").fill("Release checklist")` and
  `page.get_by_test_id("body").fill("Tag and publish")` after `page.goto(url + "/")`. Both
  inputs show the typed values.
- **Save.** Run `page.get_by_test_id("save").click(); page.wait_for_load_state()`. The page
  is the start page again, `page.get_by_test_id("total").inner_text()` is one higher than
  before, and `page.get_by_test_id("note-title").all_inner_texts()[0]` is
  `Release checklist`.
- **Second view.** Run `curl -fsS "$URL/api/notes"`. The first object has `"title":
  "Release checklist"` and `"body": "Tag and publish"`.
- **Empty title.** Run `page.get_by_test_id("title").fill("   ")` then click `save`. A
  `role=alert` paragraph reads `title is required`, the response status is 400 and the
  total is unchanged.
- **HTTP entry.** Run `curl -sS -o /dev/null -w '%{http_code}\n' -d 'title=Via curl' -d
  'body=' "$URL/notes"`. Prints `302`; `GET /api/notes` now lists `Via curl` first.
- **Proof.** Screenshot before and after the save (`01-start-page.png`,
  `02-after-save.png`), save `page.content()` as `after-save.html`, and keep the
  `/api/notes` body. `scripts/verify_browser.py` does exactly this.

## Gotchas

- The `Title` input has no `required` attribute on purpose, so the empty-title path reaches
  the server; do not rely on browser validation.
- Titles are trimmed on save: assert the rendered title, not the draft input value.
- The redirect after a save lands on `/`; a `wait_for_url` on the bare base URL without the
  trailing slash never resolves.
- The start page shows at most five notes; a note that saved is still proven by the total
  and by `/api/notes` when the list is full. See [Recent notes list](./recent-list.md).
