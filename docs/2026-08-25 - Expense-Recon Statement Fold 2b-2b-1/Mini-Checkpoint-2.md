# Mini-Checkpoint: Expense-Recon Statement Fold 2b-2b-1

**Date:** 2026-08-25
**Status:** shipped + deployed (Fly v96); 2b-2b-2 is next
**Type:** mini

---

## Summary

Landed the parse / content-id / dedupe foundation under gradual statement
uploads (backlog item 29, PR 2b-2b-1) and proved it neutral before the
`statements[]` surface goes on top of it. Shipped as #632, recorded in #633
and #634, deployed to Fly v96 and verified live.

## What Was Done

- `ingest/_common.merge_transactions` folds a parsed statement into a month's
  charges **by identity**, keyed on the content id PR 2a made stable. No second
  definition of sameness enters the codebase: two rows are the same charge
  exactly when `transaction_content_id` says so. The occurrence suffix turns
  out to carry correctly ACROSS uploads, not only within a parse, so the
  partial-then-full case keeps one row per charge with no special handling.
- Three properties pinned by test: first-write-wins (a re-supplied row keeps
  the object the month committed, so decisions and `source_row` stay pointed at
  it), `existing` passes through untouched (the fold filters what an upload
  contributes, it never edits the month), and a sign contradiction lands as two
  rows rather than being deduped to whichever arrived first.
- `service.read_statement_upload` splits the STATEMENT half out of
  `execute_statement_attach` so an append reads its file the way the first one
  was read; `service.month_transactions` reads the charge block alone instead
  of rebuilding every receipt to reach it.
- Suite 1325 -> 1336 (the +11 are exactly the new tests, nothing pre-existing
  moved), calibrate exit 0, ruff `E9,F` clean on the diff.

**The honest half.** The first draft of the wiring test asserted the attach
"runs through the fold" and could not fail: on an empty month the fold IS the
identity function, and `prepare_statement_attach` still refuses a second
upload, so nothing can put a charge in `existing` on that path. Rewrote it to
pin neutrality and said so in the test file's own comments rather than shipping
an inert call dressed as a wiring proof. What does bite, by mutation via
`regress_check.py`: disabling the dedupe reddens 7, stubbing the extracted
read reddens 6 (four of them pre-existing living-month tests).

## Current Status

Backend live on Fly v96 at brisken-expense-recon.fly.dev, verified after
deploy: `/healthz` ok, 1/1 machine check passing, five statement-bearing months
read back with full transaction sets (80 / 87 / 94 / 94 / 94). Nothing was in
flight at deploy time (`/api/operator/state` processing empty). UI unchanged
(Lovable SPA); this round touched no view shape, so no SPA prompt is owed.

`brisken` platform ops status: unknown plan / unassessed in `infrastructure.yaml`
(pre-existing, not this session's).

## Next Steps

1. **PR 2b-2b-2, the `statements[]` surface.** Lift `prepare_statement_attach`'s
   refusal deliberately (a test pins it, so it cannot go by accident), call the
   three steps this round left in place, record `statements[]` as a parallel
   field. `merge.added` / `merge.duplicates` are already the `n_new` the entry
   wants.
2. **Answer the two hazards this build surfaced** (both recorded in backlog
   item 29, neither a defect in the one-shot path):
   - the cfg's `statement` block is single-valued, so a second upload leaves the
     run pointing at file #2 while holding rows from both, and `sheet_writeback`
     anchors `source_row` into whatever `cfg["statement"]["path"]` names, which
     would write accounts next to the wrong charges in Criss's workbook;
   - `account_id` is part of identity, so one card's statement typed against two
     account ids dedupes against nothing and the month silently doubles.
3. Decide the visible-warning call once, not twice: hazard 2 is the same shape
   as the sign disagreement pinned in 2a.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 29 — the
  work list; 2b-2b-2 block carries both hazards)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py`
  (`merge_transactions`, `assign_content_ids`, `transaction_content_id`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_statement_merge.py`
  (the fold's semantics, and the note on what its live-service tests cannot prove)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`read_statement_upload`, `execute_statement_attach`, `rematch_month`,
  `month_transactions`, `prepare_statement_attach`)
