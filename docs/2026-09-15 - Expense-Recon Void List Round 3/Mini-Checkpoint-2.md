# Mini-Checkpoint: Expense-Recon Void List Round 3

**Date:** 2026-09-15
**Status:** Rounds 1 and 2 verified applied in the published SPA; item 60 shipped (PR #820, Fly v117); the bundle audit promoted to `tools/` (PR #821).
**Type:** mini

---

## Summary

The owner published the combined Lovable prompt, so the first move was proving it landed rather than assuming. Item 60 then shipped: a candidate receipt another charge holds now names its holder, so a dispossessed charge stops reading as "No receipt found".

## What Was Done

- **Post-publish audit.** Bundle audit finds `month_health`, `n_exact_pairs`, `n_charges_no_entity` and the matching i18n keys in the published chunks; CHARGES WITHOUT A COMPANY renders on both live months. `PROMPT-STATUS.md` moves both prompts to Applied and records three renderers that have no live case to exercise them: the blocked readiness bar (both months healthy), the "Card not defined" chip (every card defined), and `held_by`.
- **The audit instrument was blind first.** Version one fetched 16 chunks and reported `ready_to_post` and `coverage` as ABSENT; both are rendered today. Rewritten to crawl `/assets/*.js` transitively (48 files, 975 KB) and to refuse any report until known-present control fields are found. Promoted to `tools/lovable-bundle-audit.py` with that reason in its docstring, exit 2 for "instrument invalid" distinct from exit 1 "not applied".
- **Item 60.** `rows[].candidates[].held_by` names the holding charge (parallel, absent when uncontested) and `summary.n_charges_receipt_taken` counts rows whose every candidate is held elsewhere. Both read the effective verdict, so handing the receipt back clears them. The bucket was right all along; only the label derived from it was wrong.
- **Two live facts that changed the work.** The reported instance no longer reproduces (item 56's collapse gave that charge its own exact match; zero rows on either month are unmatched-with-candidates), so the fixture is constructed. The first construction was wrong: two identical charges competing for one receipt leave the loser in `unmatched_transactions`, which carries no candidates at all. The reproducible path is the steal through `POST /api/runs/{id}/manual-match`.
- Suite 1547 to 1550; two regress proofs RED first; deployed v117 and driven in the browser (1094 cells, no fallback strings; the 64 "No receipt found" labels are all on rows that genuinely have no candidates).

## Current Status

Backend live at v117. Items 57, 58, 59, 56 and 60 of the void list are shipped; 61 to 64 remain. One Lovable prompt is pending the owner's paste: `docs/lovable-receipt-taken-prompt.md`, and `tools/lovable-bundle-audit.py` already reports its two fields as not applied, which is the correct answer today.

## Next Steps

1. Item 61: receipts routed by receipt date never meet a charge in the neighbouring statement period. Extend the trip-pool idea to adjacent company months under the `receipt_claims` protocol.
2. Item 62: a "settled outside the card" disposition for receipts that will never post to a card (July's Redis 13,200.00 and Konsultancy 15,972.00 invoices).
3. Item 63: same-currency candidates use the 20% band meant for FX pairs; `calibrate` is the regression gate.
4. Item 64: record the column map and card currency per `statements[]` entry, and keep the printed sign for an unrecognized `Type` label.
5. After the owner pastes the receipt-taken prompt, re-run `uv run tools/lovable-bundle-audit.py` and move the row to Applied.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 61-64 open; Shipped rows 32-34)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("A candidate another charge holds")
- `tools/lovable-bundle-audit.py` (edit `NEW` per round; never trim `CONTROLS`)
- memory `project_brisken_expense_recon_usability_loop.md` (2026-09-15 paragraph)
