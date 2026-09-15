# Mini-Checkpoint: Expense-Recon Item 68

**Date:** 2026-09-15
**Status:** Shipped (PR #838, Fly v125), driven live; Lovable half pending the owner's paste
**Type:** mini

---

## Summary

The Receipt column said "attached" about a file, which is a question answered
before anyone knows whether the file can become a page, and the reconciliation
report was built from a receipt pool that only catches up at the next
re-match. Both now answer the question the reader is actually holding.

## What Was Done

- **Read live first, and neither half reproduced.** August 2026: 31 expenses,
  31 called attached, 31 receipt pages in the built report. July 2026:
  51 / 51 / 51. Zero "could not be rendered" captions on either month, and the
  expense set is identical across the two documents, because no delete is
  pending on either. Both mechanisms stay reachable, so the fix shipped on
  constructed fixtures, the way item 60's had to.
- **The reconciliation report is built from the reviewer's live overlay**, the
  same `apply_expense_edits` pair the expense report and the grid use. The
  live pool is handed to `build_view` rather than filtered out of its output,
  because the unmatched list, the duplicates, the candidates and the counts
  are all derived in there; a second derivation at the report is what let the
  two documents disagree in the first place.
- **The report's own Receipt column reads the pages `prepare_evidence`
  admitted**, not the files it was handed. Main still counted files.
- **`expenses[].receipt_in_report` + `summary.n_receipts_in_report`**, both
  parallel and ABSENT until known.
- **Item 67 landed mid-flight and the design changed to match it.** 67 shipped
  the channel this needed (`prepare_evidence` writes each outcome back onto
  the evidence dict; the route persists `summary.receipt_render`), so the
  parallel machinery this branch had built for the same fact was deleted: a
  `size:mtime_ns` verdict cache (`web/receipt_pages.py`), an `on_prepared`
  callback on both builders, and the evidence-path plumbing behind them. The
  two fields stay and are now derived from 67's state. They are not a
  restatement of it: 67 answers "did this file break", which sends somebody to
  fix a file; 68 is the positive form over every expense, including the rows
  67 says nothing about (no file, so no page, no build needed to know it),
  which is what a coverage count can be summed from.
- The Lovable prompt was re-scoped for the same reason: item 67's prompt
  already renders a per-row "Not in report" chip, so this one asks for no
  second chip and is now the coverage line plus an optional filter.
- Suite 1550 to 1693 across four merges of `origin/main`. Three regress proofs
  re-run against the final wiring, each RED first.

## Current Status

Live at Fly v125. Both months read `n_receipts_in_report` equal to
`n_receipts` (31 and 51), which matches the pre-build page count exactly.
Both changed SPA routes drive clean with zero fallback strings; the new field
has no renderer yet, so the drive proves no regression and the API read proves
the field, which is the split protocol section 8 asks to be stated in those
words.

## Next Steps

1. Owner pastes `docs/lovable-render-failed-prompt.md` (item 67) and then
   `docs/lovable-receipt-coverage-prompt.md` (item 68), in that order; re-run
   `uv run tools/lovable-bundle-audit.py` afterwards and move both rows to
   Applied.
2. Open a backlog item for July's listing numbering: 54 rows for 51 expenses,
   rows 52-54 read "none" although every expense has a file, because the
   evidence falls back to one caption per receipt when the account fan-out
   does not align, which also misnumbers those captions.
3. The p2 status files flagged stale by the pre-flight (p2-rome, p2-targeting,
   p2-product-decks at 54-86 days, p2-lead-gen-general at 86) belong to the
   lead-gen workstream, not this one.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 68 SHIPPED block, Shipped row 37)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Attached is a file; a page is a page")
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_receipt_coverage.py`
- memory `project_brisken_expense_recon_usability_loop.md`
