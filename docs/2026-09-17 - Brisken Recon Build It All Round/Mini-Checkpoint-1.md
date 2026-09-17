# Mini-Checkpoint: Brisken Recon Build It All Round

**Date:** 2026-09-17
**Status:** Owner reversed the quote-separately ruling; items 109, 107, 124, 122, 119 live on Fly v174; the rest of the audit list is queued for the next session
**Type:** mini

---

## Summary
The owner's ruling changed mid-session: "we build it all and then agree on the 600 EUR license. no functioning tool = no 600 EUR license", with item 120 (moving hosting into a Brisken-paid organisation) excluded. Three parallel builders shipped the first five pieces, each reviewed, merged on green CI, deployed and verified live.

## What Was Done
- **#109** (PR #1059, v172): `PUT /api/runs/{id}/charges/{tx}/category` writes a reviewer's category on a receiptless charge into the existing `category_overrides` table; it survives a re-match, reaches the reconciled CSV, `report.xlsx`, the statement writeback and the reconciliation PDF, and sign-off learns it under the bank's normalized description. A model guess teaches nothing. Live: 174 receiptless July+August charges become editable, 146 carrying a guess today.
- **#107** (PR #1062, v173): `receipt_chase[]` groups the month's charges needing a receipt by card holder; `receipt-requested` records the ask without closing the charge, `no-receipt-expected` closes it and moves its money into `no_receipt_expected_by_ccy`. The request mail is composed in EN and PT-BR but cannot send (flag off, send route 403s, the module imports no transport). Live August: 36 + 24 + 1 = 61, exactly `n_charges_need_receipt`.
- **#124 + #122 + #119** (PR #1063, v174): the image installs from `uv.lock` (production had drifted to openai 3.14.1 and is now back on the tested 2.38.0); the intake floor is read from the volume (200 MB on 1 GB, was 500 MiB), `/healthz` carries a disk block, unknown senders get size and daily-byte limits, known senders skip the file cap; a backup zips the data folder to SharePoint through the Graph drive API (CLI plus a scheduler off by default), with a restore runbook that states no restore has been rehearsed.
- Memory `project_brisken_retainer_600_licence` records the reversed ruling and its exclusions.

## What Did NOT Work (and why)
- **Merging the infra PR straight after item 107 landed:** GitHub refused it on Shipped-table conflicts; re-merge, de-duplicate, re-run CI.
- **Letting each builder choose its own Shipped-table row number:** three builders and two sibling sessions all took the same next number; rows 75 and 77 collided twice. Assign the row at merge time instead.

## Current Status
Fly v174 carries everything above; `/healthz` reads 83.4% free, floor 200 MB, `intake_refusing: false`. Five SPA prompts from the earlier round plus `lovable-charge-category-prompt.md` and `lovable-receipt-chasing-prompt.md` are queued for the owner. The openai downgrade is tested but has not run a live vision or categorize call yet: the first receipt arrival exercises it.

## Next Steps
1. Build the rest under the new ruling: #98, #104, #123, #125, #127, #128, #129, #108's screen half, #118's entries-survive fix.
2. Defects still open: #115, #130, #111's box count; verify the sibling's #103.
3. Owner: volume extend to 5 GB, backup env vars, restore rehearsal, #121 recipients, #118 names, #108 statements, #126 Criss closing August.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 98-133, Shipped rows 74-79)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/backup-and-restore.md`
