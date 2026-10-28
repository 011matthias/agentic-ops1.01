# Mini-Checkpoint: Expense-Recon Front 1 Chase

**Date:** 2026-09-25
**Status:** Front 1 shipped (backlog item 221, PR #1468, Fly `f92a2f87`), owner-approved live writes done; record PR #1471; SPA prompt not pasted
**Type:** mini

---

## Summary
Front 1 of the five-front parallel round (charges with nothing behind them) shipped and deployed; every per-row prediction held on the live months, and the owner's three decisions were applied the same evening.

## What Was Done
- Measured first on fresh GETs of July / August / September: gray-closed charges reading `no_receipt_found` 24 / 40 / 0; `n_already_posted` inflated by card payments (3 / 1 / 0); active cards with nothing loaded 3 / 4 / 7; chased charges dated outside their run month 0 / 14 / 19; resting inbound mail 0 of 146; Zoho (read-only, company + currency + cent + 3 days, one-cent control 0) holds 0 / 11 / 11 open charges.
- Shipped in #1468: charge `reason_code` `closed_recurring` / `no_receipt_expected` + reviewer path for `already_booked` + `reason_label`; `n_already_posted` = booked purchases; `summary.n_cards_uncovered` / `cards_uncovered[]` + Publish refusal sentence; `receipt_chase` `date_range` / `charge_month` and the mail grouped by month; ask age, `overdue_days`, `POST .../receipt-requests/mark-all`; CLI `python -m expense_recon.zoho.booked_report`. 11 new tests, suite 3,906 passed after the rebase onto front 2 (#1466), six regress proofs all bit.
- Deployed `f92a2f87`; after-GETs matched every prediction row for row; SPA driven cold over raw CDP with payload replay (August chase "(57)", September "(28)", July no panel, 0 writes).
- Owner decisions (AskUserQuestion): Publish warns only; YES to writing already-booked verdicts from the Zoho report; chase holders from known senders. Written after a green readiness check: 22 verdicts (August need-receipt 57 -> 46, September 28 -> 17, `n_already_posted` 0 -> 11 / 1 -> 12) and `receipt_requests.holders` for Dirk (three card spellings) and Nicolas, chase still disabled.
- Item renumbered 220 -> 221 at the rebase (front 2 merged first).

## What Did NOT Work (and why)
- **Step 6, the inbound-mail link on chase rows:** not built. The live inbound log holds 0 held / pooled / failed mails (127 ingested, 19 dismissed TEST drills and one Hostinger forward that matches no open charge), so the gap does not reproduce.
- **`gh pr create -R akkton/agentic-ops`:** wrong slug; this clone's remote is `011matthias/agentic-ops1.01`, and `MSYS_NO_PATHCONV=1` also left the `/c/...` body path unconverted. Run `gh` from the worktree without `-R` and pass a Windows path.
- **The vault for the app code:** `vault.py get "Expense Recon App"` output was not the bare code (401 on login); `EXPENSE_RECON_OPERATOR_CODE` in the main clone's `workspace/clients/brisken/context/.env` is what the tools read.

## Current Status
Item 221 live and verified. PR #1471 (status-only record of the deploy verification and the writes) open, merges on green. SPA half `docs/lovable-chase-honesty-prompt.md` not pasted: until then the 64 gray rows show no reason line (blank, not wrong) and July's Charges-without-a-receipt pill still counts them open. Front 1's build queue is empty; no continuation prompt is written (SESSION LOOP step 9).

## Next Steps
1. Owner: paste `docs/lovable-chase-honesty-prompt.md`; then verify by its section 7 with replayed payloads (July 0 open, 3 uncovered cards named; August chase range 2026-07-03..2026-08-04 with 13 "July 2026 charge" chips).
2. Owner: say who answers for the company-named cards 9693 (Brisken Cloud Services) and 1176 (Brisken Consulting), and whether Criss (0340) gets an address; the chase stays unsendable until item 107's separate send approval.
3. Criss: the report's "not in Zoho" lists (July 3 yellow, August 40 gray, September 1 yellow SAP SE 481.07) are hers to check; re-run `booked_report` for her when she asks.
4. Reopen step 6 only when the inbound log shows a held or pooled mail naming an open charge's vendor and amount.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 221
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section, front 1)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-chase-honesty-prompt.md`
