# Mini-Checkpoint: Expense-Recon Item 84

**Date:** 2026-09-16
**Status:** Item 84 shipped and live (Fly v141); items 85 + 86 next
**Type:** mini

---

## Summary
Every expense row now names the boxes it belongs to, and every box count on the Expenses view is summed from those rows, so a box that opens its rows lists exactly its number. The merged "no company or person" box exists, and MISSING RECEIPT IMAGE stopped naming receipts that open.

## What Was Done
- PR #935 (merge `15cdd140`), Fly v141. `service.expense_boxes` (one call per row), `is_categorized` (the `categorized_counts` rule per row), and `receipt_image_missing`, which the run payload's count also uses. `n_needs_company_or_person` is new; the other box counts are now `n_box(...)` sums. Suite 1958 -> 1968 passed / 2 skipped; five regress proofs bite (categorized wiring, both image wirings, the merged-box rule, a count's wiring).
- Resolved before building: Categorized 49 vs 51 is three two-line receipts whose second line has no category (July 0006, 0062; August 0019). MISSING RECEIPT IMAGE 2/1 named receipts the image endpoint serves (200, PDF).
- Live after deploy: July 49 / 3 / 14 / 33 / 33 / 33 / 24 / 0 missing image, August 27 / 4 / 10 / 13 / 13 / 13 / 8 / 0. Every count equals its rows; the run payload's `n_missing_receipt_image` is also 0 and 0. Driven: July's Expenses page renders MISSING RECEIPT IMAGE 0 with the other tiles unchanged; the boxes have no renderer until `docs/lovable-expense-boxes-prompt.md` is pasted.
- Correction to a standing fact: CI DOES run the module suite. `.github/workflows/expense-recon-tests.yml` (check name `test`) runs `pytest` with the dev + web extras on every PR touching the module; it passed on #932 and #935. The brief and the usability-loop memory still say it does not.
- `gh pr checks --watch` right after a push printed "no checks reported" and exited 0; `gh run list --branch` filtered on the head SHA is the reliable wait.

## Current Status
Items 83 + 75 and 84 live; both SPA prompts sit in PROMPT-STATUS Not applied. brisken ops status: platform unknown; comms-log none.

## Next Steps
1. Items 85 + 86: one SPA-only prompt. Inventory at SPA head `dcd875a7`, RunWorkbench: L182 receipt label, L1411 Settings link, L1662 DecidedFold Show/Hide (notes #50/#51), L2222 and L2644 held-by jumps, L2376 FX Details, L2634 rejected undo, L2953 Open original, L3199 duplicates panel Show/Hide, L3296 empty-cards toggle. ExpensesReviewGrid: L672 NEEDS PERSON link (moves in the item 84 prompt), L728 not-in-report toggle, L792 duplicate count toggle, L1112 forget, L1374 View email intake, L1694 Delete the extra, L1703 Not a copy, L2173 settled-outside undo, L2971 private undo, L3004 Confirm private expense (note #47), L3306 spellings toggle. `wb.credits.tip` (the brief's L1357) is a card's title attribute, not a text control. Item 86: `wb.decided.foldPosted.*` names `statements[].file` and the yellow rule, with "booked" as the word.
2. Item 88 (find month sign-off in code), item 87 (read July's card strip), item 82 (simulate first).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 85-88, 82)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-expense-boxes-prompt.md`
