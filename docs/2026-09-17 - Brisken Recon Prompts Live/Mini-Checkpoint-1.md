# Mini-Checkpoint: Brisken Recon Prompts Live

**Date:** 2026-09-17
**Status:** All thirteen pending Lovable prompts are applied; PROMPT-STATUS's Not-applied table is empty
**Type:** mini

---

## Summary
The owner published the five prompts that were still outstanding. A bundle re-audit (45 files, 1,217 KB, controls hit) finds every decisive key, and two cold drives confirm the rendering, so the SPA half of this round's backend work is live.

## What Was Done
- Bundle re-audit against the published SPA: `expx.review.reason.invoice_read_as_statement` (105), `expx.review.reason.untrusted_instructions` + the `expx.untrusted.kind.*` family (93), `wb.chargeCat.none` / `wb.chargeCat.guess.tip` (109), `receipt_chase` / `chase.title` / `wb.status.noReceiptExpected` (107), `err.company_card` / `adv.fx_rate_drift` / `warn.amountMismatch` (130). The eight earlier prompts (101, 139, 141, 142, 111, 140, 138 card tabs, 61) were already applied and had been recorded by sibling sessions.
- Cold drives of August `/runs/074a7b8905d7`, no non-GET request: "Receipts to chase (61)" over Nicolas Neumann / 3876 / 36 / USD 1,011.15, Dirk / 2838 / 24 / USD 6,361.53, Brisken Consulting / 1176 / 1 / USD 36.00, each "No address on file", with Preview and a disabled Send; the `?view=unmatched` section shows the LOVABLE 15.00 row as "Meals & Entertainment / GUESS" with its picker, and the new row actions "Mark the receipt as asked for" and "No receipt will exist".
- PR #1071: the five rows moved to Applied with that evidence, plus the dated audit line the file uses.

## What Did NOT Work (and why)
- **Searching the page text for "Guess":** the chip renders uppercase as "GUESS", so a case-sensitive needle reported a missing chip that was on the row.
- **Driving `/runs/does-not-exist` to prove the `err.*` copy:** that is the SPA's own missing-run screen, Portuguese before this prompt too. A real API refusal needs a write on a live month, so the `err.*` render stays bundle-verified only.

## Current Status
Backend Fly v174, SPA published. Nothing of this round waits on a paste. Live counts unchanged by the publish: August 61 charges needing a receipt, 8 rows to decide; July complete on receipts and 0 to decide.

## Next Steps
1. Build on: #98, #104, #123, #125, #127, #128, #129, #108's screen half, #118's entries-survive fix.
2. Trace July's company-or-person box (14 live against a predicted 12).
3. Owner: volume extend, backup env vars and a restore rehearsal, #121 recipients, #118 names, #108's 9693 statement, #126 Criss closing August, #105's two restore clicks.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped rows 74-79)
