# Mini-Checkpoint: Expense-Recon Item 65

**Date:** 2026-09-15
**Status:** Shipped (PR #831, merge `ce75fced`, Fly v119) and driven live
**Type:** mini

---

## Summary

Report totals are formed in `Decimal` at both PDF total sites, and a row whose
amount cannot be read now carries a caption plus a counted footer line instead
of vanishing from the total in silence. Section 12 row 13 of the
storage-system description is marked remediated.

## What Was Done

- **Live first, and the predicted defect did not reproduce.** Both months'
  reports were built through the real route and each printed total compared to
  a Decimal sum over the expense view's own amounts. August
  (`074a7b8905d7`, 75 pp) printed `EUR 700.00 · USD 2,663.95`; July
  (`50622baec444`, 122 pp) printed `BRL 2,329.90 · EUR 18,087.84 · USD
  28,430.03`. Both equal the Decimal sum to the cent, zero unreadable
  amounts, zero expenses with no amount. The float error is real but below
  the printed digit: August accumulated USD `2663.9500000000007` against an
  exact `2663.95` (delta `7E-13`). July's report says 54 expenses against 51
  view rows; that is the per-account fan-out (4 split receipts), not money.
- **The probe was differential-validated before those zeros were believed.**
  Salting three live rows with `"not a number"`, `""` and `"NaN"` changes the
  classifier's output, so the zeros are a reading rather than a blind spot.
- **Why it still shipped.** Through the app the Amount cell is always a finite
  two-decimal string (`_amount` formats a Decimal; `validate_expense_field`
  refuses a non-finite total at the edge), so the drop path is unreachable
  from the route. What ships is the arithmetic class removed, which is what
  row 13 actually claims, plus defence in depth on a builder whose row
  contract is "export rows", not two decimals. `NaN` is the trap that makes
  the guard load-bearing: it parses as a Decimal AND as a float, and a float
  sum would have carried it into every other row, turning a whole currency's
  total into `nan`.
- **Built.** `output/_pdf_common.py` now owns the arithmetic for both
  documents (`parse_amount`, `sum_amounts`, `format_totals`, `excluded_note`);
  the month report's header total and its per-person section sums both go
  through it. An unreadable amount gets a caption on its own listing row
  (`amount unreadable, not in total`) and a footer naming the numbers
  (`2 receipts excluded from the total: expenses 4, 7.`), both silent at zero.
  `summary.n_amounts_unreadable` is the payload half (parallel scalar).
- **Verified.** Module suite 1550 -> 1562 with this change alone, 1573 after
  merging the item-16 and item-61 siblings. Three `regress_check.py` proofs,
  each RED first and each biting through the route-level tests: silent drop
  restored (4 failed), float arithmetic restored (2 failed), payload count
  disabled (1 failed).
- **Deployed + driven.** Fly v119. Both months re-probed live
  (`n_amounts_unreadable: 0`), both reports rebuilt through the deployed route
  with identical Decimal totals, and both batch pages driven cold in
  `agent-browser --session recon-item65` from the login gate: TOTALS tiles
  render `700.00` / `2,663.95` and `2,329.90` / `18,087.84` / `28,430.03`,
  zero fallback strings across 1604 + 2423 snapshot lines.

## Current Status

Backend live at v119. Item 65 closed; backlog Shipped row 37. The SPA half
(`docs/lovable-amounts-unreadable-prompt.md`) is PROMPT-STATUS Pending and
renders nothing at 0, which is both live months, so applying it changes
nothing visible today. The PDF half needed no SPA change.

Three shared files (PROMPT-STATUS, api-contract, the backlog) conflicted twice
against siblings #828 and #832; every conflict was append-vs-append and both
sides were kept, with my Shipped row renumbering 35 -> 36 -> 37 as siblings
took the numbers ahead of me.

## Next Steps

1. Owner pastes `docs/lovable-amounts-unreadable-prompt.md`, then re-run
   `uv run tools/lovable-bundle-audit.py` and move the row to Applied.
2. Section 12's preamble still reads "None of these is yet remediated" while
   row 13 is now marked remediated. That sentence is shared by items 65 to 68
   running concurrently; whichever lands last should fix it rather than four
   sessions conflicting on one line.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`
  ("Report totals are formed in Decimal")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/_pdf_common.py`
  (the four money helpers)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_report_totals_decimal.py`
  (the live findings are in its module docstring)
