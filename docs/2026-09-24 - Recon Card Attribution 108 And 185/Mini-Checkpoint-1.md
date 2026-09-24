# Mini-Checkpoint: Recon Card Attribution 108 And 185

**Date:** 2026-09-24
**Status:** Both queue items shipped, merged and deployed (Fly `e28a6087`); the two SPA halves are owner pastes
**Type:** mini

---

## Summary

Item 108's 1176 half and item 185's backend both shipped and are live. The
1176 statement now sits on the card it always belonged to, verified cold on
`expenses.brisken.com`; `GET /api/cards/status` gives the card axis note #86
asked for, and names the four cards that have never been loaded at all.

## What Was Done

- **Item 108, the 1176 link** (PR #1267, merge `7f8f8ac2`). The coverage
  join's charge voice read `statement_anchors`, the writeback's row map,
  empty by construction for a PDF, so every PDF statement parked in the
  no-card row. It reads `statement_origins` now, with the anchors as the
  fallback for a month older than that record. Live August is such a month
  (its three `card-1176` charges read `statement_file: null`), so the file
  NAME is a last resort under one narrow rule: only a digit run resolving to
  a DEFINED card counts. Five route-level tests, both wires regress-checked.
- **Item 185, the backend** (PR #1273, merge `e28a6087`). `GET
  /api/cards/status`: one line per card across every expense batch, each with
  the months it is on. `build_card_status` sums `month_coverage` per month,
  so a card's line and its month row are one arithmetic. Trips count;
  `never_loaded` is the missing-card answer; an unknown card folds into a
  known one with the same digits, one way only.
- **The Lovable prompt's own numbers** (PR #1274). `batch_type` reads
  `company-month`, not the `expense_month` I had written from the code, and
  August's `n_cards` is 4. Both replaced with what the live route returned,
  plus the full six-chip table as the check-it-worked target.
- **Status roll-up** (PR #1275).

## What Did NOT Work (and why)

- **Switching the coverage join to `statement_origins` alone:** would not
  have moved live August. Its three `card-1176` charges read
  `statement_file: null`, `statement_id: null`, `source_page: null` on
  `GET /api/runs/074a7b8905d7`, so the month holds no origins entry for that
  upload and the anchors fallback is empty. The file-name resort is what
  actually moves it; the origins fix is what stops the next PDF needing one.
- **The first item 185 green run:** all five tests passed while months were
  ordered by `created_at`, which ties when two batches are created inside one
  second. The ordering assertion had passed on the tie. Only the regress pass
  surfaced it, by returning red on a DIFFERENT test than the mutation
  targeted. Months order by their own span now.
- **`card_sections` as the source for the cross-month roll-up:** it needs a
  full `report_view` per run, which is the expensive path. `month_coverage`
  answers the same question from the snapshot plus the decisions table.
- **Running the module suite from PowerShell without Git's `usr/bin` on
  PATH:** 7 `test_smtp_starttls.py` failures that look like a regression and
  are not. `ensure_cert` returns `None` with no `openssl` binary on PATH; the
  same file passes 10/10 with it.

## Current Status

Fly `brisken-expense-recon` serves `e28a6087`. August's coverage: the 1176
PDF on `card-1176`, and the no-card row gone because it held nothing else.
April and July byte-unchanged. `GET /api/cards/status` live and read: 2838
111 charges over 3 months, 3645 85 over 3, 3876 85 over 2, 0340 34 over 2,
1176 3 over 1, `digits:4700` 2 over 1, and 9693 / 0113 / 6013 / 8311
`never_loaded`.

Brisken ops: platform unknown plan, last assessed unknown. Comms log 16 days
stale.

## Next Steps

1. Paste `docs/lovable-card-status-prompt.md` into Lovable (item 185's page).
2. Paste `docs/lovable-private-reimburse-prompt.md` (items 175, 174, and the
   Paid Through duplicate). Its section 1 is the one that matters:
   `reimburse_to` is unreachable once a row is private.
3. Dirk: statements for cards 9693, 0113, 6013 and 8311. Item 108's remaining
   half is absent data, not a defect.
4. Criss or owner: card 3645's `zoho_account` (item 172), and the two August
   rows where her card pick contradicts the confirmed statement charge.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 108, 185)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-status-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`_statement_card_identities`, `_printed_by_upload`, `build_card_status`)
