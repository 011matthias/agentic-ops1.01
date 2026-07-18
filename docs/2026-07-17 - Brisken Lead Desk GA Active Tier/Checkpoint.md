# Checkpoint: Brisken Lead Desk GA Active Tier

**Date:** 2026-07-17
**Status:** COMPLETE — shipped (PR #256), deployed, live-verified

---

## Summary
Reversed the Iteration-2 rule that parked the GA (general-audience) cohort as a hold: GA is now an active outreach tier in the Brisken Lead Desk, so its 40 contacts stay in the active pipeline to receive their own GA wave. Recorded the owner's follow-up sequencing (T3 + GA initial waves first, then per-tier follow-up on non-responders).

---

## What Was Done This Session
### Diagnosis (answered the opening question)
1. Confirmed GA classification from the Rome master sheet DOES flow into Lead Desk: `migrate.py` maps sheet `Tier` → contact `tier`, and Iteration 2 treated `tier='GA'` as a revisitable hold (`suppress_reason='held'`).
2. Queried the live Fly DB (read-only) to ground the answer: 40 GA rows, all `suppressed=1, reason='held'`.

### Change (owner directive: keep GA in the pipeline)
1. `is_held()` no longer treats `tier='GA'` / `dirk_notes='GA'` as a hold. Explicit `next_step` holds and all consent/exclusion suppression unchanged (GA + `stop=X` still suppresses as `stop`).
2. Updated board legend ("GA general audience (gets its own GA outreach wave)") and Held-chip tooltip.
3. Rewrote the two GA test cases (`test_ga_tier_stays_active`, `test_ga_dirk_note_not_held`) + BLUEPRINT.md Iteration-2 note documenting the reversal.
4. Recorded the sequencing in `status/p2-rome.md`: T3 + GA waves out first, then per-tier non-responder follow-up.

### Ship + deploy + verify
1. Isolated work in a git worktree (5+ sibling sessions share this clone), branch `client/brisken/lead-desk-ga-active`.
2. 252/252 tests pass (`uv run pytest` with `--extra dev --extra web --extra capture`).
3. PR #256 → CI green (5/5) → squash-merged to main.
4. `flyctl deploy` (explicit user order — gated floor); machine healthy, `/healthz` + board return 200.
5. Live-verified: all 40 GA rows now `suppressed=0` after the startup sync (`last_sync_ok 2026-07-17T04:23:45Z`); sender still dormant (`kill_switch=1`).
6. Cleaned up worktree + branch (local + remote).

---

## Key Decisions Made
### GA is an active tier, not a hold
- **Choice:** Drop the `tier='GA'` branch from `is_held()`; leave the `next_step`-hold branch and all consent/exclusion suppression intact.
- **Rationale:** Owner directive 2026-07-17. GA gets its own outreach wave; parking it as "held" hid 40 sendable contacts. Suppression is sheet-authoritative on re-sync, so the code change alone flips the live rows on the next sync (no manual DB edit).

### Sequencing recorded, not built
- **Choice:** Capture the T3+GA-first / then per-tier-follow-up order in the status file; do not build the follow-up engine this session.
- **Rationale:** The directive was a sequencing decision, not a build request. The follow-up capability is the next dev workstream; "non-responder" should be derived live from mailbox reply state, not sheet bookkeeping.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/migrate.py` | Modified | `is_held()` no longer parks GA; comment + suppression docstring updated |
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/templates/board.html` | Modified | Tier legend + Held-chip tooltip reflect GA-active |
| `workspace/clients/brisken/automations/lead-desk/tests/test_suppression.py` | Modified | GA-stays-active + GA-not-held test cases |
| `workspace/clients/brisken/automations/lead-desk/BLUEPRINT.md` | Modified | Iteration-2 note documents the 2026-07-17 reversal |
| `workspace/clients/brisken/status/p2-rome.md` | Modified | Follow-up sequencing + GA-cohort element; `updated:` bumped |

---

## Current Status
GA change is live and verified on brisken-lead-desk.fly.dev: 40 GA contacts active (`suppressed=0`), sender dormant (`kill_switch=1`, no send without the watched send-drill + owner greenlight). Lead Desk is not a Make.com/n8n platform client (self-hosted FastAPI on Fly) — no ops-limit line applies.

---

## Next Steps
1. **Per-tier non-responder follow-up (next dev workstream).** Design + build the capability that, once a tier's initial wave is out, targets only that tier's non-responders. Derive "non-responder" live from reply state (`service.py` `_unanswered` / "Awaiting their reply"; reply detection scans both mailboxes across ALL folders). Respect the two-gate campaign approval flow.
2. **Prepare the GA wave + T3 wave** as first-class board campaigns (copy + list), approved but NOT sent (sender dormant).
3. **Wire the board** to surface, per tier, the non-responder set that feeds step 1.

A ready-to-paste handoff prompt for the dev-side continuation was produced this session (in chat scrollback; not persisted per W1).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/lead-desk/BLUEPRINT.md` (stage/suppression model)
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/cadence.py` (campaign engine, two-gate approval)
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/service.py` (`_unanswered`, board derivation)
- `workspace/clients/brisken/status/p2-rome.md` (sequencing of record)

### Open Questions
- None blocking. Follow-up design (how a tier's wave is marked "out" so the follow-up phase can begin) is the first thing to settle in the next session.

### Working Notes
- Live DB verified twice by read-only `flyctl ssh console` query (the `Error: The handle is invalid.` trailer on Windows is a benign flyctl teardown artifact — the query output prints correctly before it).
- Test suite needs the `web`+`capture` extras or 6 modules fail collection on `fastapi` import — `uv run pytest` alone under-collects.
- Suppression is sheet-authoritative on re-sync, so the derivation change propagates to live rows via the daily/startup sync with no manual DB write.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/256 (squash `d949b15`)
- Live app: https://brisken-lead-desk.fly.dev
- Related memory: `project_brisken_lead_desk.md`, `project_lead_desk_4d_graph_send.md`, `project_brisken_rome_tier_classification.md`, `feedback_brisken_outreach_truth_is_mailbox.md`

---

## How to Continue
`/comd_resume brisken`, then read BLUEPRINT.md + cadence.py + service.py and propose the per-tier non-responder follow-up design before building. Everything stays behind the dormant-sender gate; deploy/ssh against the live app are gated-floor (pause for an explicit order).

---

## Strategic Feedback

### What Worked Well This Session
- The instruction chain was clean directives ("make sure they stay in pipeline", "deploy", "checkpoint"), which let the full verify→ship→deploy→verify loop run end to end without redirection.

### Suggestions
- When a directive sets a sequence (T3+GA first, then follow-up), the actionable half was the code flip; the sequencing half is a future build. Splitting "do now" vs "record for next" up front kept scope honest — worth keeping as the default for mixed directives.

### System Health
- `uv run pytest` under-collecting without the `web`/`capture` extras is a recurring foot-gun for anyone touching lead-desk. A one-line note in the lead-desk README (or a `pytest` addopts default) would remove the "6 errors during collection" false alarm. Not built this session; candidate for the next lead-desk dev pass.
- Autonomy score: 0 human interventions this session (the two B1 stop-hook catches were agent/hook-contained, reframed same turn; no user correction).
