# Mini-Checkpoint: Expense-Recon Notes 109-110

**Date:** 2026-09-29
**Status:** notes #109 and #110 itemized as backlog items 244-245, merged (PR #1550, `036a1f09`); SPA prompt not pasted; loop queue empty
**Type:** mini

---

## Summary
The handed-over prompt (item 240) was stale: a sibling had applied it on 09-28 (#1545) and another was building item 243 (merged #1548 during this session). The live feedback store held two newer notes, #109 and #110, which became items 244-245 with one Lovable prompt and one route test.

## What Was Done
- Note #109 (owner, 13:48 UTC, `/months`): measured live read-only, the header tabs sit behind a hidden horizontal scrollbar (`DashboardHeader.tsx`); PT shows 724 of 905 px at 1600/2500 px, clipping "Comparar" and "Configurações", EN clips "Settings". Prompt §1 moves the tabs to their own `flex-wrap` row.
- Note #110 (owner, 14:04 UTC, August row `0002__rendered-body.pdf`, Perplexity AI USD 25.00 waiting for 0340): answered from the code. "Paid by bank transfer" is one `PUT payment_path = "bill"`, which takes the row out of the card side and the month's total and into `bills.csv`; nothing posts. New test `test_a_card_receipt_moved_to_bills_by_mistake_returns_when_its_charge_arrives` pins that a card-paid receipt moved there returns once its statement charge is matched; regress proven on `month_paths`. Prompt §2 adds tooltip key `expx.bills.moveToBill.tip` (EN + PT).
- Both prompt halves applied to a scratch clone of the SPA and run locally against the live API with every write aborted: 0 clipped tabs at 800-2500 px in both languages, tooltip renders on focus.
- PR #1550: prompt `docs/lovable-nav-no-scroll-bill-tip-prompt.md`, backlog items 244-245, PROMPT-STATUS row, p1 status row. Suite `test_bills_path_218` + `test_payment_path_218` 63 passed; CI green.

## What Did NOT Work (and why)
- **Regress-checking `if held_by_charge:` in `resolve_payment_path`:** TEST DOES NOT BITE, because `month_paths` always passes `held_by_charge=False` and checks the hold itself at line 300; the live wiring is `if unheld != (PATH_CARD, SOURCE_NONE) and doc in held_docs:`.
- **Vite dev server started through the 8.3 short path (`C:\Users\NEUMA_~1\...`):** Vite answered its own `@fs` modules 403 and `@vite/client` 404, the page never hydrated and Log in stayed disabled; started from the long path (`C:\Users\neuma_p1qrsic\...`) it hydrates.
- **Hover to open the bank-transfer tooltip:** `Locator.hover` timed out (the first-visit feedback dialog intercepts pointer events); removing `[data-fb-widget] [role=dialog]` and focusing the button opens it.

## Current Status
p1 recon backend unchanged this session (test and docs only, no deploy). Feedback store: 110 notes, every one itemized. Item 243 shipped by a sibling (#1548); it takes effect once Criss adds 1672 to the 2838 card in Settings > Cards. brisken ops status: platform unknown plan (pre-flight).

## Next Steps
1. Owner pastes `docs/lovable-nav-no-scroll-bill-tip-prompt.md` into Lovable and publishes; verify by the key `expx.bills.moveToBill.tip` in the bundle, then a cold drive: header `nav` computes `overflow-x: visible`, sits below the logo, no clipped tab.
2. Owner call on #110's open option: show "Paid by bank transfer" only on rows carrying `bill_suggestion` (hides it from card-paid rows like Perplexity, and from bank-paid invoices with no detected signal).
3. Still unpasted from earlier: `lovable-statements-button-totals-prompt.md` (241-242), `lovable-receipts-reread-trigger-prompt.md` (240), and the rest of PROMPT-STATUS "Not applied".

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 244-245
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-nav-no-scroll-bill-tip-prompt.md`
- Scratch drives (session scratchpad, not committed): `nav109.py` (live measurement), `nav109_local.py` (edited clone), `apply_prompt.py` (applies the prompt's code to a clone)
