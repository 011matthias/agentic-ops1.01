# Mini-Checkpoint: Expense-Recon Item 240 Applied

**Date:** 2026-09-28
**Status:** item 240 applied to all seven months; loop queue empty
**Type:** mini

---

## Summary
Gemini's re-read of the stored receipts (backlog item 240) ran on production: a dry run per month, the owner's per-month yes with five skips, then the real run, each reading identical to its dry run and the new values confirmed in a cold read-only SPA drive. A new defect class surfaced and is filed as item 243.

## What Was Done
- PR #1540 (`a4dc7dc5`): item 240 wording "route LIVE Fly v277, not yet run on a month".
- Seven production dry runs, one month per job, `/healthz` 0.1-0.3 s around each; USD 2.88 of Gemini reads. Receipts behind every pair, total or date change checked against the 09-28 backup's scans.
- Owner answered one AskUserQuestion per month group: all seven "apply with the proposed skips" (MEGA CENTER 04-11, Enchilada + Brauhaus Karlsruhe, ZE Normandie, RECANTO DO SABOR).
- Real runs after a read-only readiness check: 54 written, 2 set-aside pages joined, readings 56/56 identical to the dry runs, `gone` empty, USD 0.003. Pairs April 15 to 19, July 41 to 46, August 35 to 38; tool confirmations back to review exactly as predicted (July 2, August 3); no human confirmation touched.
- Cold read-only SPA drive (`/expenses/{id}`, discriminating values + a must-not): April JAQUEIRA ONLINE / no LANCHERIA, August A VIDA E BELA + Jose Cicero / old names gone, July AT&T Online Services / no BOULANGERIE JACQUES; no write left the browser.
- PR #1545 (`e96c876c`): per-month applied table in backlog item 240, p1 status row, new item 243. Memory `project_brisken_recon_gemini_receipt_reader_scope` updated.

## What Did NOT Work (and why)
- **Readiness check reading only `GET /api/runs/{id}` for July:** a month WITH a statement renders the reconciliation view, which leaves set-aside pages out, so the two joining pages read as "missing" and the check refused (correctly, nothing sent). `GET /api/expense-batches/{id}` `set_aside[]` lists them; the harness reads both now.
- **First SPA drive checks "COMERCIO ACAI" and "AT&T":** both strings are also the statement's charge text, so a pass proved nothing; replaced by values only the re-read could render plus the old value as must-not.

## Current Status
p1 recon live on Fly v277; every month carries Gemini's readings except the five skipped receipts. Item 243 (not built): Gemini writes a slip's card number that is not a Brisken card (wallet `1672`, girocards 6481/4817) and the card gate then refuses the pair; new wallet-paid arrivals hit this silently. Fresh Gemini reads are not fully repeatable (3 receipts differed from the morning's local run), so only the extraction cache makes a real run match its dry run.

## Next Steps
1. Item 243: measure first (live receipts with an unlisted card, and how many have a charge the gate refused), then the owner picks the fix direction (unlisted card = no card for the gate, or the reader drops it).
2. Paste `docs/lovable-receipts-reread-trigger-prompt.md` (one i18n key) when the owner wants the trigger in the SPA.
3. Criss reviews the 5 tool confirmations back in review (July ElevenLabs USD 5, Anthropic USD 50.54; August Fireflies USD 18, Lovable USD 50, Anthropic USD 51.38) and the April Fenix page that holds two purchases.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 240 (applied table) and 243
- Harness in the primary clone: `.scratch/reread240/prod_dry.py`, `prod_apply.py`, `summ.py`, `drive240b.py`; results `.scratch/reread240/prod/`

## Loop
The item 240 queue is empty; per SESSION LOOP step 9 no continuation prompt was written. Item 243 waits on the owner's go to measure and on his fix direction.
