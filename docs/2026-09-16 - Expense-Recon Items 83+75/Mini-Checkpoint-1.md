# Mini-Checkpoint: Expense-Recon Items 83+75

**Date:** 2026-09-16
**Status:** Items 83 + 75 shipped and live (Fly v140); next is item 84
**Type:** mini

---

## Summary
Decided duplicate copies now leave the open receipt lists for `copies_set_aside[]`, and every unmatched receipt and charge carries a `reason_code`. It is a view-time change, so both live months read it without a re-match; the SPA prompt awaits the owner's paste.

## What Was Done
- Feedback store: still 51 notes (last 16:16:06 UTC), nothing to triage.
- Measured on labels before building: of the 14 live receipts whose label names a coverage kind, 11 are named correctly when the date edge is read before the card (item 69's card-first order: 9). The one wrong claim is Konsultancy 15,972 EUR dated 07-30 (a bank transfer read as neighbouring period). Redis and 360Crossmedia print no payment method and read `no_charge_on_any_loaded_statement`, which is true of them.
- PR #932 (merge `29f368bb`), Fly v140. New `unmatched_reasons.py`; `build_view` decides duplicate groups once, earlier, and splits `copies_to_collapse(...) ∩ effective unmatched` out of `unmatched_receipts`, `assignable_receipts`, `n_unmatched_rec` and the near-miss pool. `receipt_match_rate` is now read over receipts a card could settle. Charges get their own codes (`not_a_purchase`, `receipt_held_by_another_charge`, `already_booked`, `no_receipt_found`): the receipt vocabulary is false about a charge. Suite 1929 -> 1958 passed / 2 skipped; four regress proofs bite (set-aside wiring, near-miss exclusion, period wiring, charge wiring). Five existing tests asserted the old placement and were updated.
- Live after deploy, exactly as predicted: July 11 unmatched receipts (7 no charge found / 2 neighbouring / 2 not a card charge) + 2 set aside, charges 47 booked / 1 held (GOOGLE Workspace 71.64) / 24 no receipt, rate 75.0% -> 78.0%. August 10 (4 card not loaded / 4 neighbouring / 1 not a card / 1 no charge) + 11 set aside, charges 98 / 1 / 1 (the fee), rate 32.3% -> 50.0%. The receipt identity holds on both; no copy left in the picker.
- Cold drive (`agent-browser --session recon-item8375`): July card "Receipts without a charge 11", 11 table rows; the copies fold inside that view is gone; the duplicates panel reads "Copies set aside (2) · 3 kept apart" with "Not a copy" / "Same document" undos. August card 10, 10 rows, panel "Copies set aside (11)". No fallback strings. `reason_code` has no renderer yet; the API read shows it on both months.
- Item 84 prework (read-only): Categorized 49 vs 51 is three two-line receipts (July 0006, 0062; August 0019) whose second line is uncategorized, so `posting_category` shows line 1 while `categorized_counts` requires every line. MISSING RECEIPT IMAGE 2/1 is false: those rows read `has_receipt_image: false`, but the image endpoint serves all three files (200, PDF: July 0000 rendered body, 0071 Parada; August 0000).

## Current Status
Items 83 + 75 live. SPA half `docs/lovable-unmatched-reasons-prompt.md` is in PROMPT-STATUS Not applied. brisken ops status: platform unknown (no infrastructure assessment); comms-log none. Stale p2 status files (`p2-product-decks`, `p2-targeting`) belong to untouched p2 workstreams and were left alone.

## Next Steps
1. Item 84, on a fresh branch off origin/main: `expenses[].boxes[]` (values = count names without `n_`), with every tile count summed from those rows. Categorized goes through a per-row `is_categorized` pulled out of `categorized_counts`. `missing_receipt_image` = `has_image_info and not (receipt_image_available or has_receipt_image)`, on both payloads, so the name keeps one question (live: 0 and 0). The merged box is `needs_company_or_person` / `n_needs_company_or_person`; `n_needs_entity` / `n_needs_person` are unchanged. Cover the PRIVATE, cost-center and NOT IN REPORT tiles too. Add a contract test that every count equals its rows, then an SPA prompt.
2. Items 85 + 86 prompt: SPA head still `dcd875a7`; underlined controls re-listed at RunWorkbench L182/1411/1662/2222/2376/2634/2644/2953/3199/3296 and ExpensesReviewGrid L672/728/792/1112/1374/1694/1703/2173/2971/3004/3306 (the brief's L1357 `wb.credits.tip` has no `underline` class; check by key).
3. Item 88 (find "month sign-off" in code first), item 87 (read July's card strip first), item 82 (simulate ECB monthly rates with the S1 scorer first).
4. After the owner pastes the unmatched-reasons prompt: run the bundle audit on `copies_set_aside`, `wb.reason.breakdown`, `wb.reason.receipt.card_statement_not_loaded`, `wb.reason.charge.receipt_held_by_another_charge`, then a cold drive.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 83 shipped paragraph, 84, 85-88; Shipped row 52)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section: `copies_set_aside` + `reason_code`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/unmatched_reasons.py`
