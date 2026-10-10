# Recent notes list

The start page shows the total number of notes and the five most recent ones, newest first,
each with its title, time and body, so a note a user has just saved is the first entry.

## Sub-features

- `list-total` shows the total count in `<span data-testid="total">`.
- `list-recent` shows at most five notes.
- `list-order` orders them newest first; a just-saved note is first.
- `list-fields` shows title, `YYYY-MM-DD HH:MM` time and body per note.

## How to get to it (user POV)

- Open the start page `/`.
- Save a note and be redirected back to `/`.

## Driving it with Playwright and curl

Preconditions:

- Baseline from the index: five seed notes, nothing else.

- **Read the baseline list.** Run `page.goto(url + "/")` then
  `page.get_by_test_id("note-title").all_inner_texts()`. Five titles; the total reads `5`.
- **Add a sixth note.** Save `Sixth note` through the form (see
  [Create a note](./create-note.md)).
- **Check order and size.** Run `page.get_by_test_id("note-title").all_inner_texts()`. Still
  five entries, `Sixth note` first, `Buy milk` (the oldest seed) no longer shown; the total
  reads `6`.
- **Second view.** Run `curl -fsS "$URL/api/notes"`. Six objects, `Sixth note` first; the API
  is not capped.
- **Proof.** Full-page screenshot after the save with `Sixth note` visible at the top, plus
  the `/api/notes` body.

## Gotchas

- The checkout ships with the planted defect described in `README.md`: until it is repaired
  the list shows the oldest five notes and a sixth note never appears, although the total
  and `/api/notes` are right. A verification run must report that as a failure of
  `list-order`, not describe it as the expected state.
- The seed notes are created ten minutes apart, so order is deterministic; two notes saved
  within the same second are ordered by id.
- The time column is the server's rendering of `created_at`; do not compare it to the
  browser's clock.
