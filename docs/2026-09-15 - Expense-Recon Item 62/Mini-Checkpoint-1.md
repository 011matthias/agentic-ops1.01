# Mini-Checkpoint: Expense-Recon Item 62

**Date:** 2026-09-15
**Status:** Shipped (PR #843, merge 336611e4, Fly v124). SPA half pending the owner's paste.
**Type:** mini

---

## Summary

Receipts paid by bank transfer, cash or PayPal now get a reviewer disposition that retires them from the reconciliation pool without taking them out of the month. Reading the live months first killed the item's own premise: the three invoices it names carry an empty `payment_mode`, so the auto-suggestion that was supposed to spot them fires on none of them, and the one live receipt that does print "Pay with a bank transfer" had already settled on a card.

## What Was Done

- **The evidence, before any code.** July `50622baec444` and August `074a7b8905d7`, read live. Konsultancy 15,972.00 EUR, Redis 13,200.00 USD (twice, ref IUS25300) and 360Crossmedia 900.00 EUR all carry `payment_mode: ''`. Across both months no unmatched receipt carries a non-card tender at all; the genuine ones (`Cash`, `TEF`, `PAYE`, `Electronic Funds Transfer ...2838`) are all on matched receipts. August's `Pay $15.00 with a bank transfer` (Lovable) is matched to a card charge, so that string is an invoice's payment-option line, not a record of tender.
- **Two owner rulings**, both as recommended. The row still prints in the month report behind a caption naming the tender, because it is real company spend whose evidence is the invoice and dropping it would hide roughly 30k of July from the accountant. And the suggestion fires on the payment-option line too, with the caveat above recorded in the code, the contract and the prompt.
- **The disposition.** `POST`/`DELETE /api/runs/{id}/receipts/{doc}/settled-outside`. Bookkeeping, not matching: applied at view time from a snapshot key, never by re-matching, so it costs no model call and the undo is immediate. Written under `_BATCH_ADD_LOCK` against a fresh re-read. The run payload drops the receipt from `unmatched_receipts`, `n_unmatched_rec` and month health's pair scan and counts `summary.n_settled_outside`; the grid keeps the row with `settled_outside {how, note, at}`; `unmatched_receipts[].suggested_settled_outside` suggests and never applies.
- **Two deliberate non-moves.** `n_receipts` does not change, because the receipt is still in the month; `receipt_match_rate` is read over the receipts a card COULD settle, so a month whose only stragglers were paid by transfer reads 100% instead of looking permanently unfinished. The route refuses a receipt that currently settles a charge, so the month can never claim both that a card paid it and that none did.
- **Verified.** Suite 1550 to 1565 on the branch, 1686 after merging the siblings that landed during CI. Four regress proofs, each RED first: pool exclusion (3 red), month-health pool (1), grid row field plus suggestion (2), report caption (1). Live on v124: `n_settled_outside` present on both months, suggestions empty exactly as predicted. Three live route probes returned my own messages from the deployed binary without changing any state, including the idempotent DELETE (`removed: false`). Browser-driven both changed routes on `expenses.brisken.com`; the three named invoices render in the pool, no fallback strings.

## Current Status

Backend live at Fly v124. Items 57, 58, 59, 56, 60 and 62 of the void list are shipped. `docs/lovable-settled-outside-prompt.md` is Pending in `PROMPT-STATUS.md`: the published SPA has zero references to the new fields, which is the correct pre-paste reading, so the control, the chip, the undo and the tile do not exist on screen yet.

Three parallel sessions landed in `service.py` between my first push and the merge, so the branch took three conflict resolutions (append-vs-append each time, both sides kept, my Shipped row renumbered 35 to 41 to 42 as siblings claimed those numbers).

## Next Steps

1. Owner pastes `docs/lovable-settled-outside-prompt.md` and publishes; then `uv run tools/lovable-bundle-audit.py` and move the row to Applied.
2. Item 61 (receipts routed by receipt date never meet the neighbouring statement period) is the remaining open item of the original 61-64 block.
3. When a receipt with a real non-card tender next lands unmatched, check the chip actually fires: it has no live case today.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Settled outside the card")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-settled-outside-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_settled_outside.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 42)
