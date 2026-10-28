# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** All three item 216 Build 2 SPA prompts published and verified; backend steps 1-3 live. Build 2 is closed.
**Type:** mini

---

## Summary
The owner re-pasted the suggestion-label and who-answered prompts; both are in the SPA repo and the published app, and they render what the payloads say. This supersedes Mini-Checkpoint-5's "not applied".

## What Was Done
- **SPA repo:** `630e9a4` 15:01 UTC "Displayed suggestions on month pages", `68b1f09` 15:02 "Added 'Who answered' line" (plus `779f4ed`, the refusal sentence, earlier).
- **Bundle (in-page grep):** `expx.suggestion.label` / `.confirm` / `expx.review.reason.model_suggestion` / `sum.byOrigin.label` present, EN + PT ("Sugerida", "Confirmar {account}", "Who answered the categories").
- **Screen, July replayed from the 03:05 backup** (payloads built by the real app on `origin/main` via `.scratch/dump_payloads.py`; no live month read, since all three GL months had been read once this session; 0 writes): Expenses shows "Suggested · <account>" under an empty picker and "Confirm <account>" (30 badges, 24 buttons); the Confirm click fires `POST .../confirm-category` (aborted). Matching shows the badge on 45 receiptless + 20 matched + 3 review rows = 68, and "Who answered the categories: 11 by a rule · 68 suggested by the model · 41 without a category", equal to the payload.
- `PROMPT-STATUS.md` rows set to PASTED + PUBLISHED with the evidence (PR #1461, merged).

## What Did NOT Work (and why)
- **Counting Matching badges on the tab as it opens:** read 0, because the tab opens on "Receipts without a charge", which has no category column. Open the charge tiles ("Charges without a receipt", "Matched", "Needs review") with "Show decided rows" on.
- **Clicking Confirm on the published app:** the feedback widget's first-run hint dialog (`aria-labelledby="fb-hint-title"`) intercepts pointer events; close it first.
- **A second live read of a month to redo a crashed drive:** not allowed (each month once per session); rebuilding the payloads locally from the backup replaced it.

## Current Status
Item 216 Build 2 (steps 1-4 plus the who-answered counts) is live on backend and SPA. Observed on the replay: a July OPENAI receiptless charge still suggests the parent `E500010`, a stored pick from before step 1 that is re-asked at July's next natural re-match. Nothing written on Criss's months. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. Item 216 levers per Mini-Checkpoint-4: the per-company account map waits on Dirk's 7 questions and the owner's call on OpenAI / Anthropic / Lovable; registry aliases for the non-gated names; re-run `tools/recon-categorization-score.py` after the next Zoho re-pull.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (item 216 rows)
- `docs/2026-09-25 - Brisken Recon Item 216 Build 2/Mini-Checkpoint-4.md`
