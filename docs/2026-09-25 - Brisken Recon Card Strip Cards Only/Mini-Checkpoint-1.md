# Mini-Checkpoint: Brisken Recon Card Strip Cards Only

**Date:** 2026-09-25
**Status:** Item 214 backend LIVE (Fly `4f8e36f8`); SPA prompt written, not pasted. Loop queue empty.
**Type:** mini

---

## Summary
Item 213 had already been shipped by a sibling (PR #1393, live `c5a426aa`), so this session built item 214: the card strip drops private rows whose card is known and its dropdown is fed cards only (company + private list), backend live and driven.

## What Was Done
- PR #1411 (merge `4f8e36f8`, deployed, `/healthz` commit matches): `card_review` moves a private row out of `unresolved_hints` into `n_private_rows` when its printed number is on the private list or the strip assigned its hint for the month; a hand-marked row on a receipt with no listed number stays. New `card_review.private_cards[]` (active entries, label "3281 · Dirk Neumann (private)") and per-group `private_card_options[]` (`cards.private_card_fits_hint`). Strip route takes `{"hint", "private_card"}` (month record for the card's person, never a list write), refuses `private_card_not_listed` / `private_card_number_mismatch`; `private_to` still accepted.
- Tests `tests/test_card_strip_private_item_214.py` (16); four wires proven RED with `regress_check.py`; suite 3654 passed / 2 skipped; `api-contract.md` section "The strip asks only without payment info; its dropdown holds cards (item 214)".
- Live, GET only: before/after census of all 7 months diffed against a prediction from the before payload. Six months exact; September's 3281 group left as predicted. July `0044__` (Stripe "Link") joined the strip from sibling PR #1404's copy veto, first carried live by this deploy.
- Scripted cold drive (headless Chrome, only non-GET the login): "Card ending 3281" gone from September's strip; "Kartenzahlung erhalten", "girocard", "credit card" still render.
- SPA prompt `docs/lovable-card-strip-cards-only-prompt.md` (EN + PT), listed on PROMPT-STATUS Not applied. Record PR #1416 (backlog item 214 LIVE + status file).
- Feedback store read: still 87 notes, nothing new.

## What Did NOT Work (and why)
- **Writing a scratch script via a `..\..\..\..` path relative to the worktree:** it resolved to `C:\NEUMA_~1\...`, outside the scratchpad; the file was moved back, but removing the stray empty `C:\NEUMA_~1` tree is refused by the rm safety check (owner has to delete it). Use the absolute scratchpad path.
- **First rebase of the item 214 branch:** conflicted on PROMPT-STATUS and the backlog because sibling #1400 appended its item 213 record at the same ends; resolved by keeping both sides.

## Current Status
Backend live on Fly `4f8e36f8`. The published SPA still shows "New card..." and "Private card of..." (both still work) until the owner pastes the item 214 prompt. The item 214 reading of rule 4 ("private card registry") is not acted on: the Settings tab keeps "Private cards".

## Next Steps
1. Owner: paste `docs/lovable-card-strip-cards-only-prompt.md`; then verify the bundle (`private_card_options`, `__pc__:`, `expx.cards.strip.notPrivate`; `expx.cards.strip.newCard` ABSENT) and drive September's strip (girocard shows only "3281 · Dirk Neumann (private)" + "Not private").
2. Owner: paste `docs/lovable-short-review-lines-prompt.md` (item 213's SPA half, sibling's).
3. Owner: confirm or replace the 3281 placeholder; say whether "private card registry" means renaming the Settings tab.
4. Owner: delete the empty stray folder `C:\NEUMA_~1`.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 214)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (item 214 section)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-strip-cards-only-prompt.md`
