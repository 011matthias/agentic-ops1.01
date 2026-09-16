# Mini-Checkpoint: Expense-Recon Item 74

**Date:** 2026-09-16
**Status:** Shipped and live (PR #914, merge `6afb5cbd`, Fly v138); SPA half pending owner paste
**Type:** mini

---

## Summary

Item 74, "Duplicates mean one thing each": charge-side duplicate detection is deleted, and the tool decides every receipt group on a recorded rung (`basis`), with `state` / `decided_by` / `verdict` and `summary.n_duplicate_groups_open`. The owner approved resetting July's Google ruling, and July re-matched.

## What Was Done

- **Build.**
  - `find_duplicate_charges` is deleted.
  - The ladder in `duplicates.decide_receipt_groups`, rungs in order: hash, reference, printed_reference (a PDF text layer, local), distinct_reference, receipt_card, vendor_date.
  - Rung 7 is `restore_copies_with_their_own_charge`, run once per re-match in `rematch_month`.
  - Byte digests are persisted as `snapshot.receipt_digests`.
  - The PDF lists "Copies set aside" instead of asking.
  - `tools/recon-match-attribution.py` replays the ladder with `--files`.
- **Rebases.** Rebased twice before the first push, onto item 73 (#905) and then item 77 (#910); both times the `service.py` and `api-contract.md` conflicts were two appends, and both were kept. After the push, origin/main was merged in (ledger rows only, #913).
- **Suite:** 1900 -> 1907 passed, 2 skipped, on the rebased tree.
- **Regress proofs:** four, all red first, re-run on the rebased tree: ladder wiring, rung 3 `text_of` wiring, rung 7 re-match wiring, and the `state` field.
- **Measured on the rebased tree** with a live replay of both months on a DB copy with the real files, the six bundles, the pinned scorer and the guard. Results are identical to before:
  - July resolved_clean 31, August 8, wrong 0;
  - bundles 70/95;
  - scorer 56.8 / 19.2 / 76.0, determ_wrong 0;
  - guard 4/4;
  - the statement check restored nothing.
- **Live on v138**, all four payloads (run and batch, both months):
  - no charge groups, and `duplicate_charges` is `[]` on the run payloads;
  - `n_duplicate_groups_open` 0;
  - all 16 groups on the answer-key rung, with index pairing intact;
  - no other summary count moved.
  - Before the deploy: July had 8 groups (3 charge), August 12 (1 charge).
- **Browser drive** (agent-browser `recon-item74`, read-only; only the fold was opened):
  - July's and August's Matching panels read "5 decided" / "11 decided", with no "Duplicate charges" card;
  - view 1 reads "5 / 11 copies set aside";
  - Expenses reads "5 / 11 duplicate copies";
  - the July fold showed the right receipts under each card.
- **(c), owner yes via AskUserQuestion.**
  - Sent `POST /api/runs/50622baec444/duplicates/resolve {group_id: 03ba84fadeebe2a5, resolution: ignore}`, which returned 200 and re-matched July.
  - Afterwards the group reads `decided_by: reviewer`, `verdict: distinct`, `basis: distinct_reference`.
  - July: n_reconciled 32 -> 31, n_review 7 -> 8, n_unmatched_rec 14 -> 13, n_duplicate_copies 5 -> 4, `n_charges_receipt_taken` 0 -> 1.
  - Google charge `b7abd111d69921a3` is now a review row with both invoices exact; `b7abd111d69921a3-1` waits on that pick.
  - View 1 reads "4 copies set aside".
- **Lovable prompt.** `docs/lovable-duplicates-decided-prompt.md` was rewritten against item 79's PUBLISHED month pages (SPA `9df1a1e`), not the pending prompt, and got a PROMPT-STATUS Not-applied row.

## Current Status

- Backend live on Fly v138.
- The page still renders the old panel: the "Possible duplicates" title, the false "Advisory only" sentence, and "{n} decided" with two buttons per card. That changes only when the owner pastes the prompt.
- The backlog marks item 74 SHIPPED (row 50), and the status file carries the item 74 row. That row still says the Google pair is waiting on the owner's reset, which is now done, so it needs a follow-up correction.

## Next Steps

1. Correct the p1 status row and backlog row 50 to record Fly v138 and the Google reset (a follow-up client-branch PR, like item 77's #913).
2. Owner pastes `docs/lovable-duplicates-decided-prompt.md`; then bundle-audit `n_duplicate_groups_open` / `wb.dups.setAside.title` and run the prompt's five browser checks. July now expects "Copies set aside (4) · 1 kept apart", and its Google card reads "Kept apart by a reviewer".
3. Criss picks between the two Google invoices on July's review row (b7abd111d69921a3); the other charge then takes the remaining invoice on the next re-match.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-duplicates-decided-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (section "Duplicates mean one thing each")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py` (`decide_receipt_groups`, `restore_copies_with_their_own_charge`)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 50)
