# Mini-Checkpoint: Expense-Recon Case 9 Build 4

**Date:** 2026-09-25
**Status:** Shipped and live (Fly v239, `3831e6cb`); Lovable prompt pending paste
**Type:** mini

---

## Summary

Backlog item 204 step 4 (owner D4): a receipt that prints no card and carries a
Stripe invoice number takes the card its billing account was paid with on at
least two other purchases and on no other card (`card_source: "account"`).
Shipped in #1366 (v237), one wrong row found in the post-deploy live diff and
fixed forward in #1389 (v239).

## What Was Done

- New `src/expense_recon/billing_account.py`: key from `invoice_number` else
  reference (`^[A-Z0-9]{8}[- ]?\d{4}$`, prefix not all digits); evidence per
  purchase (prefix + counter, across months); printed number / settling charge
  / pick count, two-digit ending and assigned hint word only contradict;
  leave-one-out; >=2 on one card, none on another; lazy per-request index.
- `web/service.py`: one link between `settled_charge` and `learned`, trailing
  `account_cards=` kwarg on the grid (`grid_card_chain` after item 206), export
  (only when settled cards are passed, so the matcher's pools never see it),
  month PDF card pass, cost-center roll-up, `report_receipt_cards`, refresh
  preview. `web/app.py`: one middleware opens the per-request scope (flagged
  deviation from the round's ownership list: the grid and export builders hold
  no store).
- `_CARD_OBSERVATION_SOURCES` already excluded `learned` (#1353); pinned the
  `account` half through `POST /api/runs/{id}/publish`.
- Tests `tests/test_account_card_c9.py` (18). Regress red at the chain link,
  the middleware, the export site, the purchase collapse, the evidence
  classification, the threshold, the contradiction rule and the
  unreadable-batch rule; the #1389 decided-copy test is red on the v237 module.
- Suites: 3492 (first merge) to 3595 passed, 2 skipped (fifth merge); CI green
  8/8 on the merged heads of #1366 and #1389; accuracy replay unchanged.
- Six merges from main while siblings landed builds 1, 2, 3, 5, item 206,
  items 180/181 and 207; Shipped row settled at 129.
- Cold drive (`agent-browser --session recon-c9-4`, from the login gate): May
  Expenses renders both account rows as "Credit Card Chase Visa - 3876 ·
  Nicolas Neumann", Corporate Services "from card"; no source line yet (the
  renderer waits on the Lovable prompt).

## What Did NOT Work (and why)

- **Dropping decided copies from the evidence (v237):** live, the Stripe
  RECEIPT is the decided copy and the only document that prints the card
  (`Receipt-2253-2007-8117.pdf` beside `Invoice-HMVWDWIL-0033.pdf`), so
  September's 3876 / 3645 purchases vanished and May's Lovable invoice
  `HMVWDWIL0023` read card-2838 off August's three picks. Fixed in #1389
  (inherit like the grid, fold copies into their purchase, empty index on any
  unreadable batch). The copies test had put its two copies in different
  months, which never exercises this shape.
- **Waiting on `gh pr checks --watch` right after a push:** it exits at once on
  "no checks reported" before CI registers; and "no checks after 10 minutes"
  meant the PR had turned conflicted (GitHub runs no PR workflow then), three
  times.
- **June SPA re-drive:** after closing the first browser session, a re-login
  rendered 5 lines and never reached the rows; June was verified by API only.

## Current Status

Live v239 (`3831e6cb`, carries #1366 + #1389). Nine predicted May/June rows all
read 3876: seven through their own statement charge (May/June sheets were
loaded 01:18-01:22 UTC by someone else, D3), two through `account` (May
Anthropic 99.95 and 90.00 EUR). September Anthropic 184.35 reads card-9693
via build 1's twin. `HMVWDWIL0023` now reads its statement card 3645. OpenAI
September: 12 blank, the one pick on its own row (D6). `/api/cards/status`
1.39 s before, 3.8-6.0 s after (all five builds plus the May/June statements
landed in the same window, so not attributable to this build alone).

## Next Steps

1. Owner: paste `docs/lovable-account-card-prompt.md` into Lovable and publish;
   then `uv run tools/lovable-bundle-audit.py` and drive May's two account rows.
2. Measure `/api/cards/status` per build (profile the index build vs build 3's
   neighbour reads) if the owner finds the Cards page slow.
3. (Corrected 2026-09-25.) No follow-up for build 3's neighbour-month cards:
   build 3 put the flow-back inside `settled_charge_cards`
   (`cards_settled_elsewhere`), which `month_evidence` already reads through
   `export_settled_cards`, so they count as statement evidence today. The
   earlier line also claimed missing evidence could only make the rule more
   silent; false: missing CONTRADICTING evidence decides wrong (the v237 shape).
4. Owner / Criss: D2 (weekly Chase export, view access to 9693 / 1176), D3
   (the 9693 history), D7 (close day per card).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/billing_account.py`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_account_card_c9.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 204, "Build 4 (step 4)")
