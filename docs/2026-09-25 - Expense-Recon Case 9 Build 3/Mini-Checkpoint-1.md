# Mini-Checkpoint: Expense-Recon Case 9 Build 3

**Date:** 2026-09-25
**Status:** Shipped and deployed (PR #1364, merge `1a78c1ae`, Fly v232)
**Type:** mini

---

## Summary
Backlog item 204, step 3: a receipt that a neighbour month's statement settled now takes that charge's card, company and person. The row shows `card_source: "settled_charge"` and `settled_by` names the borrowing month. The grid, CSV, month PDF and the item-171 learner all read the same map. No live row moves today; the value is structural.

## What Was Done
- `settled_charge_cards` also merges `cards_settled_elsewhere` (end of `web/service.py`). That function reads the claims other runs hold on this run's receipts and re-checks each one against the holder's effective verdict via `month_charge_states`: the charge must be reconciled, still hold this document, and have borrowed it from this run. The card comes from `_charge_card_identity`, resolved in the receipt's own batch registry.
- `store.open_read_only` (end of `web/store.py`) opens a `RunStore` over a `mode=ro` connection with no schema pass. The settled-cards functions receive a run and no store, so the reader derives the database path from `run.work_dir` (`data_root/runs/{id}` → `data_root/recon-web.sqlite`). A wrong path or any SQLite error lends nothing.
- `tests/test_card_flows_back_c9.py` has 8 route-level tests:
  - Positive: deterministic match, confirmed pick, CSV + PDF, learner.
  - Negative: a tie left in review, a rejected pair, a receipt confirmed private before the borrow, a deleted neighbour month.
- `regress_check` on the wiring line took the tests green → RED (6 failed) → green.
- Suites and gates:
  - Local full suite: 3484 passed / 2 skipped on the pre-merge head.
  - Final merged head `9ea024a3`, locally: focused 153 passed, accuracy no-diff.
  - CI on `9ea024a3`: full `test` job green, and every other check green.
- Merged main three times (builds 1 and 2, item 208, checkpoints). My Shipped row became 126: build 1 = 123, item 208 = 124, build 2 = 125.
- Live, read-only, before and after deploy:
  - 2 rows carry `settled_by`: August's OpenAI receipts, borrowed by September. Both show `hint` 9693, unchanged.
  - July's borrowed receipt (June's SUPERMERCADO FENIX 10.82, 06-30) sits in review, with no claim.
  - The SPA was not driven, because no live row moved.

## What Did NOT Work (and why)
- **`pytest -n auto ... | tail || pytest ...`:** pytest-xdist is not installed, so `-n` is refused. `tail` masked the exit code, so the fallback never ran and one suite start was lost. Run pytest plainly and capture `$?` from pytest itself.
- **Forcing a review-bucket borrow by amount or FX confidence:**
  - A USD receipt 71.00 / 68.00 / 65.00 / 60.00 against a 71.64 USD charge still matches deterministically at 0.85 confidence. 55.00 yields no candidate.
  - Lowering the mocked FX confidence changes nothing: USD/USD pairs never take the FX-judgment path.
  - A EUR receipt yields no candidate at all (no reference rate).
  - What works: a tie, meaning an identical receipt in the borrowing month.
- **Edit tool / `Path.read_text` on the backlog and API contract:** the files mix CRLF and LF lines, and `read_text` folds CRLF. Edit anchors failed until the appends were done byte-wise with per-anchor line-ending detection.
- **Waiting for a 15-minute local suite between sibling merges:** three sibling merges landed during the runs, and two local runs were superseded and stopped. CI's full `test` job on the final head is the gate; locally, run the focused set plus accuracy on each merge.

## Current Status
- Live on Fly v232 (`/healthz` commit `1a78c1ae`). Brisken ops status in `infrastructure.yaml` is unknown (not assessed).
- Open findings recorded in the backlog under item 204's Build 3 paragraph:
  1. **Borrow window.** The window is the borrower's min..max charge date. Under D1's calendar-month exports, a receipt dated the day before a charge on the 1st is never borrowed.
  2. **FX twin.** `settled_charge_amounts` (the item-98 FX twin) does not follow the claim.

## Next Steps
1. Case 9 builds 4 (billing-account card memory) and 5 (status + suggestions + apply-to-vendor) run in their own sessions. Builds 1 and 2 are merged.
2. Owner decision: widen the adjacent borrow window for calendar-month exports (for example, the label month ± `ADJACENT_FALLBACK_DAYS`), or accept that a month-end receipt paid on the 1st stays unborrowed.
3. Optional follow-up: `settled_charge_amounts` reads the same claim, so a flowed-back row converts at the neighbour charge's amount.
4. Waiting on the owner or Criss: D2 (weekly Chase export, with view access to 9693 / 1176), D3 (loading the 9693 history and the April-June 3876 / 0340 sheets).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`: item 204, the "Build 3 (step 3)" paragraph
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`: `settled_charge_cards`, `cards_settled_elsewhere`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_card_flows_back_c9.py`
