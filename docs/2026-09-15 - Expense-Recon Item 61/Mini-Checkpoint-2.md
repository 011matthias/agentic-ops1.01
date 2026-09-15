# Mini-Checkpoint: Expense-Recon Item 61

**Date:** 2026-09-15
**Status:** Shipped (PR #832, merge `7c3f42c6`, Fly v118). SPA half pending the owner's paste.
**Type:** mini

---

## Summary

A month's candidate pool now reaches the company months either side of it, so a
receipt printed on the last day of a month can settle the charge that posts on
the 1st of the next statement. The item's named instance did not reproduce; the
same mechanism's failure is real one month further on, and that is what the fix
is for.

## What Was Done

- **The live read came first, and it corrected the item.** July's GOOGLE 71.64
  on 07-01 already meets its 06-30 receipt: month routing stamped the mail that
  carried it (arrived 07-01) rather than the date printed on it, so the receipt
  sits in July's own batch and the charge is reconciled. Both counts the item
  asked for are 0. The real instance is at the other end: August holds two
  Google receipts dated 08-31 (71.64 and 75.09) for charges that post 09-01,
  while August's own 08-01 Google 71.64 charge carries no candidate at all. Ten
  of July's and fifteen of August's unmatched charges sit on the first or last
  three days of their statements.
- **Six batches exist, not two.** January, May, June, July, August, September.
  June and September are the neighbours the two live months can reach. Exactly
  one receipt moves today (June's 06-30 Fenix 55.74 BRL into July, where no
  charge matches it), so the fix is for September's statement and every month
  after.
- **`adjacent_pool_for_month`** joins the trip pool inside `rematch_month`.
  Neighbours by LABEL (`month_from_label`, previous and next); eligibility by
  this statement's OWN period (`statement_period_for_month`, min..max of its
  charges), because no calendar rule predicts a workbook that opens on the 31st.
  Borrowed copies ride the existing `borrowed_receipts` / `receipt_sources` keys
  with `kind: "adjacent"`, so the claims protocol is untouched: the claim keys
  to the receipt's HOME month and one receipt still settles one charge.
- **`rows[].candidates[].from_batch`** names where a borrowed candidate's
  receipt lives, closing a gap older than this item: a borrowed receipt was
  anonymous until it WON, so an offered one read as this month's own. It names a
  trip borrow too. Plus `summary.n_adjacent_borrowed`.
- **Evidence.** Suite 1550 to 1556 for this branch's six tests; 1561 passed / 2
  skipped after rebasing onto the item-16 sibling. One regress proof RED first,
  through the caller: disabling `if adjacent:` inside `rematch_month` reddens the
  two route-level tests. The differential probe is the same fixture with the
  receipt dated 07-10 instead of 07-31, which borrows nothing.

## Current Status

Backend live at v118, `n_adjacent_borrowed` present and 0 on both live months
(the correct value: their neighbours lend nothing in period today). The SPA has
no renderer for the new fields yet, so the drive asserted the changed route
still renders with no regression, and the authenticated API read shows the field
on the live month; the renderer itself was not verified. Both July GOOGLE 71.64
rows were driven in the published SPA and render real content with no fallback
string: the reconciled one shows `Google LLC 71.64 USD` at 99% with a DATE
MISMATCH chip (the one-day gap), the duplicate copy shows "Closest free receipt,
off by 0.00, 1 days apart".

`docs/lovable-adjacent-month-prompt.md` is the SPA half, Pending in
PROMPT-STATUS with its decisive field names (`from_batch`,
`n_adjacent_borrowed`, `wb.charge.fromMonth`).

## Next Steps

1. Owner pastes `docs/lovable-adjacent-month-prompt.md`; then bundle-audit and
   move the PROMPT-STATUS row to Applied.
2. The renderer has no live case until a September statement is attached. That
   attach is also what first exercises the borrow for real (August's two 08-31
   Google receipts).
3. Not built, named as open: a neighbour's receipt arriving does not re-match
   this month (`rematch_months_after_trip_change` does that for trips, the
   company-month equivalent does not exist), and a borrowed receipt is not
   hand-pickable because `assignable_receipts[]` holds the month's own receipts
   only.
4. Four p2 status files are stale (p2-lead-gen-general 86d, p2-product-decks
   54d, p2-rome 55d, p2-targeting 55d). Untouched here on purpose: siblings are
   live in this tree and none of them is p1.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  (section "The adjacent-month pool: `from_batch` + `kind`")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`adjacent_pool_for_month`, `statement_period_for_month`, `borrowed_source_view`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_adjacent_month_pool.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 36)
