# History fold, with per-line undo (item 104)

Paste into Lovable. Front end only; the backend shipped 2026-09-18 and is
live. Nothing here needs a new endpoint.

## Why

Every verdict in the tool overwrites the one before it. Until now the screen
could show what a row says today and nothing about how it got there, so
"who confirmed this, and when" had no answer, and a bulk action that moved
forty rows left no trace. The backend now records one line per change that
actually moved a value, with the name of the person who signed in.

## The data

`GET /api/runs/{runId}/history` (newest first):

```json
{ "run_id": "50622baec444", "n_entries": 12, "has_more": false,
  "entries": [
    { "id": 12, "row_key": "tx-0007", "row_kind": "charge",
      "field": "decision",
      "old": { "status": "pending", "chosen_document_id": null },
      "new": { "status": "confirmed", "chosen_document_id": "0003__lovable.pdf" },
      "who": "criss", "at": "2026-09-18T09:12:03+00:00",
      "trigger": "click",
      "summary": "pending to confirmed, receipt lovable.pdf",
      "undoable": true } ] }
```

Query parameters: `limit` (1-500, default 200), `before_id` (page further
back), `row_key` (one row's own story). `n_entries` follows the
filter, so the per-row fold can show its own count.

`field` is `decision`, `disposition`, `charge_category`, `receipt_category`
or `duplicate`. `trigger` is `click`, `bulk`, `rematch`, `tool` or `undo`.
A line already put back carries `undone_at` and `undone_by`, and
`undoable: false`.

`summary` is English. Build the Portuguese from `field`, `old` and `new`,
the same way every other reason code on this screen is handled; do not
translate `summary`.

## What to build

1. **A "History" fold on the month page**, collapsed by default, under the
   existing month header. The label carries the count: `History (12)` /
   `Histórico (12)`. Fetch only when it is opened.
2. **One row per line**, in this reading order: when, who, what row, what
   changed, and why it happened.
   - when: short local time, with the full timestamp on hover
   - who: the name as given (`criss`, `matthias`); render `operator` as
     "shared login" / "login compartilhado", because that is what it means
   - what row: `row_key`; for a charge, show the vendor and amount from the
     row already in the page's state when you can find it, and fall back to
     the id when you cannot
   - what changed: from `old` to `new`, using the field's own vocabulary and
     the labels the grid already uses for statuses and categories
   - why: a small chip for `trigger`. `bulk` reads "bulk action" /
     "ação em massa"; `undo` reads "undone" / "desfeito"; `click` needs no
     chip.
3. **Group consecutive lines that share `who`, `trigger` and the same
   minute** under one heading ("criss confirmed 34 rows, bulk action"),
   expandable to the individual lines. A bulk confirm writes one line per
   row it moved, and forty separate rows is not readable.
4. **An Undo button on each line where `undoable` is true.**
   `POST /api/runs/{runId}/history/{id}/undo`, then refetch the month and
   the history. Show nothing on lines where `undoable` is false.
5. **The per-row fold.** On a charge's row in the grid, a small "history"
   affordance opens the same list filtered with `?row_key={transaction_id}`.

## The refusals, which are the point

Undo answers 409 with a `code`. Show the sentence, do not retry, and refetch
the history so the screen agrees with the server:

- `history_superseded` - "This row has changed since. Putting this back
  would throw away the later change." / "Esta linha mudou desde então.
  Desfazer aqui descartaria a alteração mais recente."
- `history_already_undone` - "This change has already been put back." /
  "Esta alteração já foi desfeita."
- `history_not_undoable` - a duplicate ruling, or a first disposition.
  "This change is recorded but cannot be put back here." / "Esta alteração
  está registrada, mas não pode ser desfeita aqui."
- `history_entry_not_found` (404) - the line is gone; refetch.

Also possible: a 409 carrying an R4 claim conflict (another month settled
that receipt meanwhile) and a 400 carrying a service refusal. Both already
have handling on this screen; reuse it.

Draw the Undo button from `undoable` alone; do not infer it from `field`.
The server already withholds it wherever the write could not be honoured.

## Checking it landed

1. Open a month, open History. A month nobody has touched since 2026-09-18
   reads empty, and that is correct: nothing before the deploy was recorded.
2. Confirm one row. The fold shows one new line, top of the list, with your
   own login name, `click`, and the status it moved from and to.
3. Click Undo on it. The row returns to its previous state, the original
   line reads "undone", and a new line appears above it.
4. Confirm the same row again, then click Undo on the NOW-STALE first line.
   The screen shows the `history_superseded` sentence and the row does not
   move.
5. Switch the language to Portuguese and read the same three lines.
