# Mini-Checkpoint 1 — Brisken expense-recon: the statements[] surface (2b-2b-2)

**Date:** 2026-08-25 · **Type:** client-dev · **Project:** brisken (p1)
**Shipped:** PR #636 (`2427f0ac`), deployed to Fly and verified on the
deployed origin.

## What the round was

Backlog item 29's next PR. `POST /api/expense-batches/{id}/statement`
becomes append-capable and repeatable, because a statement arrives per
card and often twice: a mid-month partial, then the closing cycle. The
fold PR 2b-2b-1 landed was deliberately inert (a second upload was still
refused, so `existing` was always empty and no test could tell a wired
fold from an unwired one). This round made it load-bearing.

The refusal came out of BOTH layers it sat in: the route gate
(`_mutable_expense_run_or_error`) and `prepare_statement_attach`'s own
check beneath it. 2b-2a had already established that lifting only the
route moves the 400 one layer down. Two tests pinned the closed door and
now pin the open one; the second was found by the full suite rather than
by reading, which is that pin working exactly as designed.

Each upload is recorded in `statements[]` (parallel field on both review
payloads), written by `rematch_month` inside the commit lock so the month
has one writer.

## The design error, and how it was caught

The plan said the per-row source travels with the row, and that was built
first: a `Transaction.source_file` field stamped at parse time, with the
writeback filtering to its own file's rows. It passed its tests and
mutation-proved green.

It is wrong. A charge occupies a row in EVERY file that prints it, at a
different row in each, because a partial and the closing cycle both
contain it. A field on the charge can only name one file, and
first-write-wins (correctly, for decisions) keeps the first. Walking the
canonical scenario in adversarial review is what surfaced it: the closing
cycle is the workbook Criss works from AND the default download, and it
would have been annotated only for the charges the cycle introduced,
every repeat left blank. Blank cells there do not read as "already
handled"; they read as charges the tool could not resolve.

The anchor is therefore per UPLOAD, not per charge: `statement_anchors`
(`{file: {transaction_id: row}}`), snapshot-only and never in a payload,
and `write_sheet_writeback(anchors=...)` writes exactly the charges that
file contains at the rows it puts them on. `source_file` was reverted
whole; once anchors existed nothing read it, and shipping a field nothing
reads is its own kind of slop.

Worth stating plainly: the round's own tests did not catch this. They
tested the thing that was built. Only re-deriving the user-facing
scenario from scratch did.

## Two more from the same review

- **A same-name second upload overwrote the first on disk.** Criss's
  per-card exports carry the bank's filename, so two cards genuinely
  arrive as one `statement.xlsx`. The first upload's charges kept their
  row numbers while the bytes beneath them became another card's.
  `_unique_upload_name` now gives each upload its own name.
- **A recorded-but-EMPTY anchor map read as "not recorded"**, which would
  drop a zero-row workbook back to placing every charge in the month by
  row number. `in` rather than truthiness.

## The hazard the brief asked to decide once

Both open cases (one card typed against two account ids; a sign inference
that differs between two exports) reach the same place: the fold honestly
produces two rows, and neither should be deduped, because deduping a
contradiction picks a winner arbitrarily. The addition is saying so.
`advisory` fires on either shape, on the entry and on the job's warning
channel beside `entity_mismatch`. Nothing is dropped, merged, or refused
on a heuristic about what an operator meant, and a clean per-card append
stays silent (pinned, because an advisory that fires on the normal case
is noise the reviewer learns to skip).

## A race the round opened, closed with it

Allowing a second upload created one: both the attach path and every
re-match read their charges minutes before committing them, and a
concurrent upload can now genuinely add rows in between. The older set
would have erased them with no error. `rematch_month` now refuses, inside
the lock, any commit that would DROP a charge the month already holds.
That is strictly stronger than the `require_no_statement` check it
replaces (which stopped meaning anything once a second statement was
allowed) and it covers the receipt re-match path too.

## Verification

- Suite **1336 → 1352**, 2 skipped. Calibrate exit 0. Ruff (E9,F) clean
  on the diff (the two remaining `cli.py` F821s are pre-existing string
  annotations in untouched code).
- **Nine mutations** via `tools/regress_check.py`, every guard red under
  its own: fold unwired, `statements[]` unrecorded, anchors unrecorded,
  anchors ignored, empty-map-as-absent, filename overwrite, race guard
  removed, advisory silenced, writeback unscoped.
- The **first** writeback test did not bite: it asserted on the
  workbook's own vendor column, which a wrong-file write never touches. A
  test that asserts a constant, exactly the trap the house loop names.
  `regress_check` caught it; rewritten to read the appended column and
  the rows that carry a value.
- Deployed origin verified after merge: `/healthz` 200, authenticated
  reads over 6 live batches, `statements` present-and-empty on both a
  pre-attach batch and the January reconciling month (80 transactions,
  workbench still renders). Empty is the correct legacy answer: those
  months were attached before the field existed.

## Next

PR 3, the coverage surface: per-card coverage in the batch view, the
month page's statement panel, per-card sections in the reconciliation
report. The backend half of the selector already exists (`?file=`), but
the SPA renders neither `statements[]` nor the selector, so from the UI a
month with two xlsx statements can still only download the current one.
That gap is stated in the backlog rather than left to be discovered.

Unchanged and still owner-side: `intake.known_senders` empty on
production, the three pooled Hostinger invoices for 2026-07, and the card
registry entity gaps.
