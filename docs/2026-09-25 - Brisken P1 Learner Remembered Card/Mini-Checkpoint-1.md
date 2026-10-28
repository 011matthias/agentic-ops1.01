# Mini-Checkpoint: Brisken P1 Learner Remembered Card

**Date:** 2026-09-25
**Status:** Fixed and deployed (Fly v226, `d059856a`); session loop done
**Type:** mini

---

## Summary
Item 200's side finding is fixed on the owner's order: at month sign-off the merchant card learner no longer counts a card the tool only remembered as evidence, so a remembered card can no longer confirm itself into `cards_seen` or a learned `card_key`.

## What Was Done
- `learned` removed from `service._CARD_OBSERVATION_SOURCES` (now `override`, `hint`, `settled_charge`); api-contract, backlog item 200 note and Shipped row 120 updated (PR #1353).
- Route test through `POST /api/runs/{id}/publish`: `test_signing_off_a_remembered_card_teaches_the_registry_nothing` in `tests/test_remembered_card_read_time_item_169.py`. regress_check: RED with `learned` restored, green after. Learner modules 43 passed; CI green including the full module suite.
- Deployed v226; `/healthz` reports `d059856a`. The fix acts only at a month sign-off (none on record, item 126), so it is proven by the route test, not live. A cold agent-browser read-back of September showed the page unchanged (4 private chips, no fallback text).

## What Did NOT Work (and why)
- **A test month ingested before the correction:** the remembered card was only filled at read time (item 169), while the sign-off learner reads the ingest-time stamp (item 173), so the test stayed green with the leak restored. Ingesting after the correction made it bite.
- **Appending a Python test with a Bash heredoc:** blocked by heredoc-size-gate, the second hit this session after the same lesson earlier. Use the Edit tool.

## Current Status
p1 live at `d059856a` (v226). No live data written. Nothing pending from this session.

## Next Steps
1. Private-card-list session: fold `cards.positive_non_brisken_evidence` into `classify_payment_evidence` (step 4 = the evidence list, step 7 = WAIT).
2. Optional owner call: PayPal / PIX / boleto / cheque stay "no private evidence" until one appears.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 200, Shipped row 120)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`_CARD_OBSERVATION_SOURCES`)
