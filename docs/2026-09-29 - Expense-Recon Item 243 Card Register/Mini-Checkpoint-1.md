# Mini-Checkpoint: Expense-Recon Item 243 Card Register

**Date:** 2026-09-29
**Status:** item 243 live on Fly (`3b650304`); waits on Criss's Settings entry
**Type:** mini

---

## Summary
Item 240's July dry run showed a slip printing the corporate card's second number (1672) losing its true 2838 charge to the FX uniqueness gate. After a read-only measurement and a corrected owner decision, the card score now reads the print through the card register. The fix is deployed; it acts once 1672 is on the 2838 card in Settings.

## What Was Done
- Measured live, read-only: 2 receipts carry a number no Brisken card has (German girocards 6481, 4817, no Chase charge); nothing is wrongly unpaired today. The printed card lives in `payment_hint`; `card_ending` is blind to it (proven on the two girocard rows).
- First owner question framed 1672 as a phone-wallet number, and the owner picked "ignore every non-Brisken card". Reading `cards.py` showed 1672 is the corporate card's plastic (the statement marker is 2838; Zoho says "CorpServ 2838/1672"). The broad option would also have weakened the gate's calibrated evidence (14 of 14 absent-card coincidences wrong). Re-asked with the corrected facts: owner chose the register-aware check, with Criss adding 1672 in Settings.
- PR #1548 (`3b650304`): `_card_score` adds the register card's numbers when the card was resolved FROM the print (`hint`) and the printed digits are one of them. Hint words, picks, remembered cards and girocards unchanged. `tests/test_card_register_gate_item_243.py` (9); regress_check bites on both mutations; full module suite and 8/8 CI green, match-accuracy gate included.
- Deployed via `deploy.py` from a detached origin/main worktree: `/healthz` on `3b650304`. Cold read-only SPA drive: April, August and July render with no failure text and no write leaving the browser.

## What Did NOT Work (and why)
- **Describing 1672 as a wallet number in the first owner question:** it was inferred from the slip, not checked against `cards.py`, whose own notes name 1672 as the 2838 card's plastic; the owner decided on that wrong premise and had to be asked again.
- **Counting unlisted cards from `card_ending`:** empty in every month, including the two girocard rows written that morning; the printed card is in `payment_hint`.

## Current Status
p1 recon live on `3b650304`. Item 240 applied (7 months). Item 243 built and deployed, inert until the register lists 1672 on the 2838 card.

## Next Steps
1. Criss: Settings > Cards, add 1672 to the 2838 card ("Credit Card - 2838"). It takes effect at each month's next re-match.
2. Criss: 5 tool confirmations back in review (July ElevenLabs USD 5, Anthropic USD 50.54; August Fireflies USD 18, Lovable USD 50, Anthropic USD 51.38) and April's Fenix page holding two purchases.
3. LIMITATION: no Lovable tool in the agent's reach. `docs/lovable-receipts-reread-trigger-prompt.md` (one i18n key) is pasted into Lovable by the owner if the re-read trigger should appear in the SPA.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 240 (applied table) and 243
- `src/expense_recon/matching/deterministic.py` `_card_score`; `tests/test_card_register_gate_item_243.py`
