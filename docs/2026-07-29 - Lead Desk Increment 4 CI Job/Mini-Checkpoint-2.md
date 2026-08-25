# Mini-Checkpoint: Lead Desk Increment 4 CI Job

**Date:** 2026-07-29
**Status:** Increment 4 fully shipped + now CI-gated. Engine dormant (kill_switch=1). Three items remain gated by owner order.
**Type:** mini

---

## Summary

Follow-on to the increment-4 checkpoint: closed the standing "lead-desk suite isn't in CI" owner note by adding a `lead-desk` CI job (PR #482), then corrected the status file's stale infra note (PR #489). The 325-test suite now gates every lead-desk PR structurally (the repo auto-merges on `gh pr checks` green).

## What Was Done
- PR #482 — `lead-desk` CI job in `.github/workflows/ci.yml`: `uv run --directory workspace/clients/brisken/automations/lead-desk --extra web --extra dev pytest -q`. Its own run went green in CI (26s); verified the exact relative-path command locally first (325 passed, exit 0).
- PR #489 — status file infra note updated ("NOT in CI" → now in CI via #482).

## Current Status
Increments 1-4 in main; suite 325 passing and now CI-gated. Engine dormant, no send ever fired. Migrations v7-v10 merged, NOT on the Fly prod volume. Three items remain GATED by explicit owner order (do not start autonomously): Dirk-wave "release enumerated drafts" send action (waits on Dirk's sender-policy answer, open question 1); deploy v7-v10 to brisken-lead-desk.fly.dev; watched send drill → kill_switch off.

## Next Steps
1. Dirk-wave release action — build once Dirk answers the sender-policy question (per-wave release vs per-mail clicks). Design in plan §Phase 1.3.
2. Deploy v7-v10 to Fly + watched arming drill (both gated on owner order, sequenced together).
3. Phase 0 T3 touch-2 non-responder list before ~08-02 (script path, per-wave Dirk yes).

## Files to Read First
- `docs/2026-07-29 - Lead Desk Increment 4 Live Sequence Editing/Checkpoint.md` (the full increment-4 checkpoint)
- `~/.claude/plans/brisken-refactored-hopper.md` (§Phase 1.3 Dirk-wave)
- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `automations/lead-desk/src/lead_desk/web/cadence.py` (`apply_sequence_delta`, `enrollment_state`)
