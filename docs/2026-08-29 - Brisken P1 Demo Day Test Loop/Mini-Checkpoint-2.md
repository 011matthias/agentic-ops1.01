# Mini-Checkpoint: Brisken P1 Demo Day Test Loop

**Date:** 2026-08-29
**Status:** Backend trio PR #657 open (CI running); Lovable prompts A-C handed, D gated on deploy
**Type:** mini

---

## Summary
The user ran the April demo pack through the live app and raised four
problems (attach-dialog ambiguity, card-strip spellings/tender rows, stale
Zoho wording + the GL question, month auto-recognition). Every problem was
solution-designed, adversarially verified against BOTH repos, logged
(backlog items 35-37 + escalations, PRs #654-#656 merged), and answered
with four Lovable prompts; the decision-free backend trio then shipped as
PR #657 on the user's order.

## What Was Done
- Verified pipeline works: local no-LLM April run (94 tx / 36 receipts /
  0 parse errors) + live-app guidance; Fly was at v101 with the #646 fix.
- Backlog items 35 (card strip), 36 (month suggestion), 37 (dead
  column-mapping retry, a LIVE defect found by verification) + Zoho-copy
  escalation on item 23; PRs #654/#655/#656 merged.
- Four Lovable prompts drafted, refuted by 4 verify agents (all failed
  round 1: card_key premise, wrong i18n key, generic-flag coverage,
  unaccented PT), corrected; final copies in
  `.scratch/lovable-prompts-2026-08-28/` and pasted in-chat. A/B/C apply
  now; D gated on period_suggestion deploying.
- PR #657 (open): tef/compra/dias vocabulary + sub-floor digit tolerance,
  `period_suggestion` on the batch view (api-contract section added),
  map_date/map_description/map_currency aliases on the statement route.
  Suite 1400/2, calibrate green, all new tests proven green-red-green.

## Current Status
brisken platform: unknown plan (no platform section; FastAPI on Fly).
PR #657 awaits CI -> auto-merge -> Fly deploy (pre-authorized) -> browser
verification of the strip's generic notes -> tell the user D is unlocked.
The GL-codes-vs-categories question and the backend Zoho-string sweep
(paid-through banner, filenames, export headers) stay gated on Dirk/Criss.

## Next Steps
1. Merge #657 on green; deploy Fly from a clean origin/main worktree;
   verify /healthz + drive the April batch strip in a browser (the four
   tender phrases should show the generic this-month-only note).
2. Tell the user prompt D is go (A-C were already go).
3. After the owner GL decision: backend Zoho-string sweep + canonical
   last-4 server grouping (item 35 second half).
4. p2 status files are 37-69d stale (flagged by the sweep) — next p2
   session should update or prune them.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 35-37)
- workspace/clients/brisken/context/expense-reconciliation/2026-08-28-demo-run-sheet.md
- .scratch/lovable-prompts-2026-08-28/ (the four prompts)
