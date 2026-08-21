# Mini-Checkpoint: Brisken Recon Intake Quick-Wins

**Date:** 2026-08-21
**Status:** Round 4 of the 8-PR feedback wave shipped, deployed, live-verified
**Type:** mini

---

## Summary

Feedback-wave round 4 (themes C1+B, notes 2/3/13) shipped as PR #561 and
deployed: the intake log shows delivered filenames and an honest Month
column, and delete-month exists behind a typed confirm phrase with a
custody-preserving cascade. A 3-lens adversarial review before commit
caught a real event-loop freeze the change would have introduced, plus
three race defects; all fixed and pinned as tests.

## What Was Done

- Mail meta records delivered `files` at accept time; legacy archives
  derive them from `parts/` at read time; inbound log rows carry them.
- `batch_label` resolved for every routed log row (plain + detail);
  deleted months emit `batch_deleted` instead of per-document
  operator-removed misattribution; held rows render their held status.
- `POST /api/runs/{id}/delete`: typed confirm gate (400 bare, 409
  mismatch), cascade under `_BATCH_ADD_LOCK`, job rows purged, inbound
  metas stamped `batch_deleted` (mail archives never deleted), response
  reports `next_open_batch` + `learned_memory: kept`.
- Review fixes: handler kept sync (async parked the event loop on the
  OCR-held lock); every locked batch-RMW entry point refuses a deleted
  run; DONE-stamp re-check kills the dangling done-job race; replay
  clears stale delete stamps; `_update_meta` serialized + atomic.
- Suite 1188/2 (+10 tests, 9 proven failing pre-fix); calibrate OK.
- Live-verified on brisken-expense-recon.fly.dev: healthz 200, log rows
  carry files + "January" label, gate answers 400/409, batch untouched.
- Backlog: item 11 shipped; item 18 added (pre-existing async lock
  acquirers, same freeze class); stranded-mail design call folded into
  item 12. Status file + loop memory updated. Lovable half:
  `docs/lovable-intake-quickwins-prompt.md` (with owner, unpublished).

## Current Status

Cards R1-R3 (#555/#556/#559) + quick wins (#561) live. Remaining rounds
in order: body-only mail (Dirk's real held_body_only mail is the
acceptance test), memory validate/adjust, language + receipt visibility,
Cards R4 (pending owner answers, backlog item 10). Four Lovable prompts
wait on the owner; DOM-probe the SPA after publish (merge != live).

## Next Steps

1. Body-only mail round (C2): GET /api/inbound/{archive}/body, POST
   .../render-ingest (body->PDF -> normal ingest), POST .../dismiss;
   scope the per-archive re-ingest design call (backlog item 12) with it.
2. Backlog item 18 (async endpoints on the batch lock) rides the next
   code round.
3. When the owner publishes any Lovable prompt: DOM-probe the SPA.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 12, 18)
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (Theme C PR-C2 design)
