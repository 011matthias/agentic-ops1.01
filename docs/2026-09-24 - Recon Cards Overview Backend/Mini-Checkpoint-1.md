# Mini-Checkpoint: Recon Cards Overview Backend

**Date:** 2026-09-24
**Status:** Brisken p1 recon, item 192 backend live; SPA prompt not pasted
**Type:** mini

---

## Summary

Owner, on `/cards`: *"this should just be an overview and not another gate to inside the months. we can insert more relevant data though."* The backend now counts receipts per card, deployed as Fly `45d4c494`. The Lovable prompt that turns the page into a one-table overview is written from the live read and waits on the owner's paste and Publish. This supersedes the earlier 2026-09-24 mini-checkpoint's "queue empty".

## What Was Done

- Read live before building. `/api/cards/status` carried statement coverage, refunds and item 190's `receipt_months`, but no receipt figure. The month's "{n} without a charge" is `month_card_tabs` over the report view's `unmatched_receipts`, and one-card months drop their sections, so the roll-up could not sum sections.
- PR #1312 (`45d4c494`). `attach_expense_card_tabs` stamps `expenses[].without_charge` on every row from that set. `receipt_card_counts` returns `n_expenses` + `n_without_charge`. `build_card_status` adds `receipt_months[].n_without_charge` + `statement`, per card `n_receipts` / `n_receipts_without_charge` / `n_receipts_no_statement`, and `no_card.n_without_charge`. The footnote now says the overview's fold holds cards with no receipt either. `docs/api-contract.md` documents the fields.
- Verification: `tests/test_card_status_receipt_figures_item_192.py` (4, route-level). One test holds three counts equal: the row stamp, the card tab's own count and the roll-up. `regress_check` bites on the row stamp (4 red) and on the statement flag (2 red), and both went green again after restore. Item 190's exact-shape assertions were extended. Full suite 3303 passed / 2 skipped; ruff clean; CI green.
- Deployed from a clean detached worktree. Live read: 2838 has 41 receipts, 12 without a charge, 5 waiting for a statement; 3876 95 / 39 / 32; 9693 16 / 16 / 16; 1176 8 / 8 / 7; No card 72 / 62. August's row stamps equal every card tab's count. The published `/cards` was driven cold: it still renders and shows the new footnote.
- PR #1313 (`a1d845c2`): `docs/lovable-cards-overview-prompt.md` removes the strip, the card panel and the row clicks. It lays out one table (Statements cover plus "No statement for: {months}", Receipts, Without a charge, Credits, Statements as a count), a No card row last, a sort by open work, and a fold that lets 9693 into the table. Also in #1313: the PROMPT-STATUS row under Not applied, the backlog heading and the status file.

## What Did NOT Work (and why)

- None.

## Current Status

Backend live and consistent with the months. Known transitional gap until the prompt is published: the live footnote says the fold holds cards with no receipt, while the published page still folds 9693 (16 receipts) away. The sort is by open work (`n_unmatched_tx + n_review + n_receipts_without_charge`) rather than the proposed "Still open, largest first", because Still open is a per-currency map. Context ~395k at close.

## Next Steps

1. After the owner pastes AND publishes the item 192 prompt, check both the Lovable repo's `main` and the live bundle, then drive its §6 table cold. Then mark 192 applied (backlog + PROMPT-STATUS), PR, merge.
2. Item 191 (the sibling session's): its prompt is not pasted, and nothing nests until 3645, 3876 and 0340 get Account = "Credit Card - 2838" in Settings.
3. Waiting on others: Dirk (statements for 9693, 0113, 6013, 8311); Criss or the owner (card 3645 `zoho_account`, item 172; the two August HMVWDWIL invoices picked 2838); the owner (licence framing for directive-driven surfaces).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-cards-overview-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 192)
