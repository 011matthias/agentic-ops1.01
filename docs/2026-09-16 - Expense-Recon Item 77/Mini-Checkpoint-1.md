# Mini-Checkpoint: Expense-Recon Item 77

**Date:** 2026-09-16
**Status:** Shipped + deployed (Fly v137); live fix applied on owner yes; SPA prompt pending paste
**Type:** mini

---

## Summary

Item 77 was built to unblock item 82 (the ECB monthly reference rate, whose gate needs 77 and 81 shipped). The date-correction half shipped: a reviewer-typed date that belongs in another month offers a move, and one POST files the receipt there. The locale half was measured and not built, because the reported misread is a glyph (the model sees `04/07/26` as `04/01/26`), not the day/month order.

## What Was Done

- **Gate check first.** On origin/main neither 77 nor 81 was shipped. 81 was mid-build in a live sibling worktree, so it was left alone (it merged as #903 during this session). 77 had no owner.
- **Measured the prompt against all 129 stored receipts, re-read with no cache on the production models, two runs per arm.** The locale rule moved 0 dates. A one-word wording change alone moves 12 stable readings (the perturbation floor). Listing the three amendment fields in the instructions moved 39-41 readings, including a Microsoft invoice re-read as `statement` and an Amazon.de order re-read as Yubico. The same fields in the response schema only, with the instruction text byte-identical, moved 31 readings, none of them a date, total, currency, document type or resolvable card. That variant shipped, verified identical to the measured one.
- **PR #910 (merge `2b2f1755`):**
  - `expenses[].month_move {month, label, batch_id?}` and `summary.n_month_moves`.
  - `POST /api/runs/{id}/expenses/{doc}/move`, which carries the reading, file, header and category edits and provenance, creates the month when absent (`created_by: "move"`), soft-deletes the source row and re-matches both months.
  - `time` / `invoice_number` / `receipt_number` as absent-or-string fields on `expenses[]`.
  - Suite 1887 -> 1900 passed / 2 skipped. Four regress proofs bit: offer wiring (8 red), edits carried (2), target re-match (1), stored time (3).
- **Deployed Fly v137.** API read: January was the only month with an offer (naming July `50622baec444`); the other five months carried none, and no field came back null. Drove January's page with agent-browser from a cold login: it renders, and there is no `month_move` renderer yet (prompt pending).
- **Live fix, owner approved.** Moved the Parada Obrigatória receipt from January into July, where it settled `MP *PARADAOBRIGAT` USD 6.20 as `fx_reference` 0.99 (32.00 BRL at 0.192448 = 6.16, +0.68%). Exactly one July row changed, with 0 new model calls. January 2026 is now empty and was kept.
- **PR #913** records the deploy and the move in the status and backlog files.

## Current Status

Backend is live. `docs/lovable-month-move-prompt.md` is in PROMPT-STATUS "Not applied"; paste it after `lovable-month-views-prompt.md` if both are still pending. Item 81 has shipped (#903) and item 77 has shipped (#910), so item 82's gate is now open. Ops status for brisken p1 is unknown: `infrastructure.yaml` has no platform plan.

## Next Steps

1. Item 82 (ECB monthly reference rate) as its own session under PARALLEL-ROUND-PROTOCOL: its gate is open now.
2. Owner pastes `lovable-month-move-prompt.md`. Afterwards, run `tools/lovable-bundle-audit.py` for `month_move` / `n_month_moves` / `expx.review.monthMove`. No live offer remains to drive, so construct one only with a per-action yes.
3. Optionally delete the empty "January 2026" month (typed-confirm delete, live write, owner call).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`, section "A corrected date moves the receipt"
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, item 77 and Shipped row 49
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_month_move.py`
