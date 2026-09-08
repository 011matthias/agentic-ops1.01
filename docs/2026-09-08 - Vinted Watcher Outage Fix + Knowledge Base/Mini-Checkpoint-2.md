# Mini-Checkpoint: Vinted Watcher Outage Fix + Knowledge Base

**Date:** 2026-09-08
**Status:** v2 verified healthy in production; first trustworthy outcome row recorded
**Type:** mini

---

## Summary

Post-merge verification of the v2 watcher running unattended under the
scheduled task. The rebuilt gone-detection produced its first organic
verdict (1 row, `source='404'`, in a 25-item batch) against the 25-of-25
fabrication pattern it replaced, and the kids-size fix holds: 16 leaked
alerts are all pre-fix, zero since deploy.

## What Was Done

- Merged the checkpoint ledger PR #714; primary clone synced to 42afdf2b;
  both worktrees removed, branches deleted local + remote.
- Verified the deployed v2 under the real scheduled task, not by hand:
  task LastRunTime 15:35:23 local, **Result 0 now meaningful** (the vbs
  waits and propagates; before the fix that 0 was unconditional).
- Confirmed the gone-detection repair produces plausible data: the single
  gone row carries `gone_source='404'` (exact status, not a redirect
  inference), sold_flag 0, at a ~4% batch rate versus the 40% discard
  ceiling. This is the first outcome datum the calibration can trust.
- Confirmed the kids backfill: 1552 of 29017 rows (5.3%) flagged
  retroactively; the 16 alerted kids rows span 09-06 11:25Z to 09-08
  12:35Z, all before the 13:14:31Z v2 deploy, none after.
- Watcher state clean: no backoff armed, no stall alert pending, token
  valid to 2026-09-09T11:38Z, 29017 listings (+483 since the checkpoint).

## Current Status

Nothing in flight. `main` carries the v2 watcher, the knowledge base, and
the checkpoint ledger. The scheduled task collects every 5 minutes while
the PC is on. Outcome data is accumulating clean under provenance from
zero. The owner-approved 8-point improvement prompt is stored and its
precondition (PR #712 merged) is satisfied.

Note: commit 409dce02 is a SIBLING session's checkpoint covering Vinted
bulk LISTING work (28/29 live) on the same account. That workstream is
separate from this watcher; coordinate before touching listing-side code.

## Next Steps

1. Paste `workspace/projects/vinted-reselling/improvement-prompt.md` into a
   fresh session for the 8-point alert-quality round.
2. Let gone_source data accumulate ~2 weeks, then build the backtest scorer
   as its own PR and run /comd_optimize.
3. Spot-check in a day that the recheck gone-rate stays organic and the
   stall alert stays silent while the PC is on.

## Files to Read First

- workspace/projects/vinted-reselling/README.md
- workspace/projects/vinted-reselling/api-notes.md
- workspace/projects/vinted-reselling/status/watcher.md
- docs/2026-09-08 - Vinted Watcher Outage Fix + Knowledge Base/Checkpoint.md
