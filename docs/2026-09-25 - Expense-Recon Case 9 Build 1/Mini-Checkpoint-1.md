# Mini-Checkpoint: Expense-Recon Case 9 Build 1

**Date:** 2026-09-25
**Status:** Shipped and live (PR #1362, merge `da4136f0`, Fly v229)
**Type:** mini

---

## Summary
Backlog item 204 step 2: an invoice that prints no card now takes the card its own payment receipt prints whenever the grid shows the two as one document. On September's live read the three predicted rows moved (`0008`, `0033` to 3645, `0029` to 9693) and `n_needs_entity` went 26 to 23.

## What Was Done
- `duplicates.lending_groups` (new): the reference groups plus every group behind `expenses[].duplicate` (not `ignore`, not `distinct`). `inherit_card_from_copies` walks it and takes optional `decisions`; with none it runs the ladder without file evidence (lends less, never more).
- `web/service.py`: only the three owned call lines (`# grid`, `# export`, `# before the card chain`) now pass `duplicate_decisions(run, receipts, resolutions)`. The Stripe pairs carry two numbers, so only rung 3 (the receipt printing the invoice's number, a file read) joins them; an evidence-free call would have lent nothing on the live rows.
- Guards unchanged, one added: a copy two shown groups would lend two different cards or entities gets neither.
- `tests/test_twin_card_c9.py` (9, route-level); `test_reference_duplicates.py`'s "a vendor/date pair lends nothing" unit test flipped in place; `docs/api-contract.md` section appended; backlog paragraph at the end of item 204, Shipped row 123, status paragraph.
- Four wiring points red under `tools/regress_check.py`: the group source in `inherit_card_from_copies` (7 of 70), grid line (3 of 9), export line (2 of 9), re-match bake line (1 of 9). Suite 3485 passed / 2 skipped. CI 8/8 green.
- Deployed from a detached `origin/main` worktree (fly.toml matched the live config); `/healthz` `da4136f0`; SPA driven cold over raw CDP: the three invoice rows render "Corporate Services from card · Credit Card Chase Visa - 3645 · Dirk Neumann - Corp Services" and "Cloud Services from card · Credit Card Chase Visa - 9693 · Brisken Cloud Services"; the three OpenAI 80.12 rows still read "No legal entity yet".

## What Did NOT Work (and why)
- **The plan's July Supermercado Fenix 803.11 prediction (copy 2 takes 3876):** copy 2 prints `CARTAO: xxxxxxxxxxxx3076`, which `_card_keys` reads as card 3076, so the pair names two cards and the kept guard lends nothing. Confirmed live after deploy: copy 2 still has no card.
- **`recon-match-attribution.py` as the before/after instrument:** 0 class moves and 0 row differences on all eight bundles, but every bundle receipt carries `payment_mode` None, so card lending cannot happen in bundle mode at all. A confident negative from a blind probe; the live API read was the measurement.
- **agent-browser `open` for the consumer drive:** hung past 150 s (fourth time on record). Raw CDP on port 9361 with a scratch profile drove it in three calls. The deploy-consumer gate does not recognise a CDP drive and kept advising "not driven".
- **`pytest -n auto`:** the module has no pytest-xdist; the run exits immediately having run nothing.
- **Inserting ledger lines with a CRLF-literal anchor after the merge:** a sibling's merged lines in `p1-improvement-backlog.md` are LF, so the anchor matched 0 times; the insert now reuses whatever ending sits at the anchor.

## Current Status
Live on v229. The three September invoices carry their twin's card, company and person. They still show a stale "no company yet, so no account was picked" category line (`review.refusal: entity_missing`): the GL categorization ran while they had no company and a card-chain company does not re-run the engine. That is open backlog item 206, not this build. Nothing was written to Criss's months; other rows move on read, the matcher scope at the month's next natural re-match.

## Next Steps
1. Builds 2 to 5 of the case-9 round run in their own sessions (no-card vendor guard; cross-month card flow-back; billing-account card memory, where the twin's printed card should outrank the account memory; honest status + suggestions + apply-to-vendor).
2. Item 206 (re-run the engine when a card gives a row its company) clears the stale category line on these three rows.
3. Owner / Criss: D2 (weekly Chase export, view access to 9693 / 1176), D3 (load the 9693 history and the April to June 3876 / 0340 sheets).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py` (`lending_groups`, `inherit_card_from_copies`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_twin_card_c9.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 204, "Build 1 (step 2)" paragraph
