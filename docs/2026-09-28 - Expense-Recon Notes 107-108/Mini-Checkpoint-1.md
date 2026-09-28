# Mini-Checkpoint: Expense-Recon Notes 107-108

**Date:** 2026-09-28
**Status:** Notes #107-#108 itemized as backlog items 241-242, one SPA prompt written (not pasted); item 240's production step runs in sibling session db58be6b
**Type:** mini

---

## Summary
The pasted continuation prompt (item 240 build) was stale: #1538/#1540 had already shipped it and a live sibling was running the production dry runs, so this session left 240 alone and answered the two new operator notes instead (PRs #1541 + #1542).

## What Was Done
- Checked the sibling's transcript before acting: db58be6b had dry-run January, May, June, April on production, each matching the local measurement; no second run from here.
- Read `/feedback.jsonl` (108 notes). #107 ("make this an actual button", the "4 statements ˅" toggle) and #108 ("need the actual number tabs to be larger", the Totals pills), both on August Expenses 00:27 UTC, became items 241-242. Prompt `docs/lovable-statements-button-totals-prompt.md`: `StatementSummary` becomes an outline `Button` (FileText, turning ChevronDown, amber edge on an advisory); Totals pills `text-xs` to `text-xl font-semibold`. No backend change, no new key. Every replaced class string matched against a shallow clone of the SPA (`ExpensesReviewGrid.tsx:956/963/965`, `StatementPanels.tsx:388/392`).
- Published-bundle read (the 17 chunks the index names): items 231 and 232-235 are LIVE (`expx.review.attention.title`, `wb.statement.viewAll`, `wb.status.stillOpen.rest` present; control `receipts_reread`, in the SPA repo since 11:05 UTC, absent). PROMPT-STATUS rows and backlog headings corrected.
- Status row for 241-242 in `status/p1-expense-reconciliation.md` (#1542). Cleared the stale `pr-1514-ci-checks-watch` entry (PR merged long ago).

## What Did NOT Work (and why)
- **`GET /api/runs/{id}/expenses` for the Expenses payload:** 405, that path is POST only; the page reads `GET /api/expense-batches/{id}` (`getExpenseBatch`), which serves `summary.totals_by_ccy`.
- **`git -C /c/...` under `MSYS_NO_PATHCONV=1`:** "not a git repository", because the flag also stops the POSIX-path conversion git needs; use `C:/...` paths with that flag.
- **`gh pr merge 1541 --squash --delete-branch`:** printed "fatal: 'main' is already used by worktree" after the remote merge succeeded (known false-fail); the remote branch was deleted by hand.

## Current Status
Items 241-242: prompt written, NOT pasted. Item 240: route live Fly v277; dry runs, the owner's per-month list and the applies are db58be6b's. Its SPA label (`docs/lovable-receipts-reread-trigger-prompt.md`) is in the SPA repo (`2d3e505`) but not in the published bundle: needs a Publish, not a paste. No feedback note after #108.

## Next Steps
1. Owner: paste `docs/lovable-statements-button-totals-prompt.md` into Lovable and publish; publish the item 240 label.
2. After that publish, verify by structure (no key to grep): August's header toggle is a bordered button with an svg and `aria-expanded`; the Totals pills compute to 20 px bold.
3. Owner call: the Matching page shows both the header statements toggle and item 233's "View all statements loaded" for the same files; recommendation: hide the header one on Matching.
4. Item 240 continues in db58be6b (owner's per-month yes, then applies).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 240-242
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-statements-button-totals-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` last rows
