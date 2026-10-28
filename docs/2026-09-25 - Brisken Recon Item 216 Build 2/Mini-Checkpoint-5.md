# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Build 2 steps 1-3 live (step 3 by a sibling, see Mini-Checkpoint-4); the refusal-sentence prompt is published; the suggestion-label prompt is NOT applied despite being reported pasted
**Type:** mini

---

## Summary
After the owner reported both item 216 Lovable prompts pasted and published, the published app was checked against three instruments: only `model_picked_parent` landed. The suggestion-label prompt (`docs/lovable-model-suggests-prompt.md`, #1452) has no SPA commit, no key in the bundle, and no badge or Confirm on screen.

## What Was Done
- **Bundle (grepped in-page, 23 JS files, 835 KB, 0 fetch failures, ~13:50 UTC):** `gl.refusal.model_picked_parent` x2 and the PT sentence present; `expx.suggestion.label`, `expx.suggestion.confirm`, `expx.review.reason.model_suggestion`, `suggested_category`, "Sugerida" all 0.
- **SPA repo (`011matthias/brisken-expense-review`):** `779f4ed` 12:42 UTC "Added refusal sentence to i18n", `0ddda8d` 12:35 "Added Bills section to Expenses"; no commit carries the suggestion prompt.
- **Cold drive, August (one read each of grid + run, replayed on both API hosts, 0 writes):** Expenses 55/55 rows, no error boundary; the suggestion rows read "Pick an account" with the old vendor-guess line, 0 "Suggested" badges, 0 "Confirm <account>" buttons; Matching renders.
- `PROMPT-STATUS.md` rows recorded (PR #1454, merged): refusal sentence PASTED + PUBLISHED, suggestion prompt NOT APPLIED.
- Instruments for the re-check, in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-build2b\.scratch\`: `bundle_grep.py` (no API call, no login) and `drive_step4.py` (switch `RUN` to a month not yet read in that session).

## What Did NOT Work (and why)
- **Bundle grep with Python `urllib`:** every chunk answered 403 (the CDN refuses a plain Python client), so the first grep read 0 KB and proved nothing. Fetching from inside the page with Playwright (`page.evaluate` + `fetch`) reads all 23 files.
- **`gh pr merge` in the same command as its CI poll:** the no-auto-commit gate asked, because at hook time the checks were not provably green. Correct gate behaviour, not friction; run the merge as its own call after the poll.

## Current Status
Backend steps 1-3 live (Fly `2b6eeb7f` after the sibling's step 3). Live screen gap unchanged: Confirm is hidden on suggestion rows until the suggestion prompt is applied; a hand pick works. Nothing written on Criss's months. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. **Owner:** re-paste `docs/lovable-model-suggests-prompt.md` and `docs/lovable-categories-by-origin-prompt.md` (one publish), confirm Lovable made a commit for each, publish.
2. Verify: `bundle_grep.py` extended with `sum.byOrigin.label` and `categories_by_origin`, then a cold replayed drive of a month not yet read that session (badge + "Confirm <account>" on suggestion rows, the Confirm click aborted).
3. Item 216 levers per Mini-Checkpoint-4 (account map waits on Dirk's 7 questions and the owner's gated-vendor call; registry aliases; re-score after the next Zoho re-pull).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (the two item 216 rows)
- `docs/2026-09-25 - Brisken Recon Item 216 Build 2/Mini-Checkpoint-4.md`
