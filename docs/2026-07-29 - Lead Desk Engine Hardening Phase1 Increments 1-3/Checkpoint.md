# Checkpoint: Lead Desk Engine Hardening (Phase 1 increments 1-3)

**Date:** 2026-07-29
**Status:** Increments 1-3 SHIPPED (PRs #473/#474/#475 merged to main). Increment 4 (live sequence editing) is next. Nothing armed; kill_switch=1.

---

## Summary

Executed the ungated core of the outreach-engine Phase 1 build on Lead Desk:
send-safety guard port, vacation-aware scheduling, and spaced sending. Three
isolated PRs, each pytest-verified and merged on green CI, in the worktree
`agentic-ops1-ldharden`. Full engine suite 294 -> 306 passing, no regressions.

---

## What Was Done This Session

### Increment 1 - send-safety guards (PR #473)
1. `campaign_recipient_pins` table (v7); `approve_campaign` freezes each
   approved contact's exact lowercased email.
2. `claim_sends` per-item guards: recipient-not-approved / recipient-drift
   (live email != frozen) / hard-denied domain (`sap.com`+`brisken.com` floor
   unioned with the `send_deny_domains` state) / unpinned-template. A breach
   blocks the item + writes `send_guard_alert:{cid}`; a clean pass clears it;
   `peek` never mutates state.
3. `cloud_worker.execute_one` immutable denied-domain backstop before the Graph
   POST (after the draft-to-self early return).

### Increment 2 - vacation scheduling (PR #474)
1. Nullable `campaigns.start_not_before` (v8); `claim_sends` skips before it;
   the first step anchors on `max(approved_at, start_not_before)`.
2. `approval_report.scope_text` states the start date; `POST
   /campaigns/{cid}/schedule` + a Schedule card.

### Increment 3 - spaced sending (PR #475)
1. `ramp_per_day` (v9): at most N step-1 (fresh-contact) sends per day;
   follow-ups unaffected. `first_step_sends_today` accounting.
2. Per-mailbox daily cap across all campaigns from one `from_address` (global
   `mailbox_daily_cap` state); `mailbox_sends_today` accounting; threaded
   through the claim pass so concurrent campaigns share the budget.
3. `cadence.project_schedule`: day-by-day forward projection (window +
   daily_cap + ramp) wired into `approval_report` and rendered on the confirm
   page; `/settings/mailbox-cap` route + per-mailbox cap control.

---

## Key Decisions Made

### Four increments, separate PRs, merge-commit stacking
- **Choice:** One PR per increment off `origin/main`, merged with `--merge`
  (not squash) so the next increment stacks cleanly (merge-base stays the prior
  tip, so each PR diff is only its own change).
- **Rationale:** send-safety code is best reviewed and reverted in small units;
  squash-merge would have double-shown the prior increment in the next PR diff.

### Stop after increment 3; increment 4 gets a fresh session
- **Choice:** Ship 1-3, checkpoint, hand off increment 4 (step_no-keyed
  progress + sequence-delta approval) rather than cram it now.
- **Rationale:** increment 4 refactors the cadence step-pointer (`steps_done`
  is a bare event count used as a positional index in `enrollment_state`;
  correct for append-only, corrupts on mid-sequence INSERT). It touches the
  cadence core and every cadence test, so it deserves fresh context. The user
  is not blocked: editing a sequence on a running campaign already works via
  pause -> edit -> re-approve -> start-sending (supersede_approval demotes to
  draft); increment 4 removes the pause and fixes the insert corruption.

### Deferred deploy
- **Choice:** did NOT deploy the merged migrations (v7/v8/v9) to
  brisken-lead-desk.fly.dev this session.
- **Rationale:** nothing sends (kill_switch=1), so there is no urgency;
  deploying at arming time avoids a redundant mid-build deploy. Deploy is safe
  (additive columns/table).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/lead-desk/src/lead_desk/web/store.py` | edited | v7/v8/v9 migrations + `_SCHEMA`; recipient-pin, ramp/mailbox accounting methods; `update_campaign` columns |
| `automations/lead-desk/src/lead_desk/web/cadence.py` | edited | guards, deny-domains, `start_not_before` skip+anchor, ramp/mailbox-cap, `project_schedule`, scope text |
| `automations/lead-desk/src/lead_desk/cloud_worker.py` | edited | execute-time denied-domain backstop |
| `automations/lead-desk/src/lead_desk/web/app.py` | edited | `/campaigns/{cid}/schedule` (date+ramp), `/settings/mailbox-cap`, campaigns context |
| `automations/lead-desk/src/lead_desk/web/templates/{campaign,campaigns}.html` | edited | Schedule & pacing card, projected schedule, mailbox-cap control |
| `automations/lead-desk/tests/test_{send_guards,scheduling,spaced_sending}.py` | created | 22 new tests |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | edited | marked increments 1-3 shipped |

---

## Current Status

Increments 1-3 in `main`, not yet on the Fly prod volume. Engine still dormant:
kill_switch=1, no campaign `sending`, no real send ever fired. brisken platform
ops: unknown plan (Fly-hosted lead-desk, no platform section in
infrastructure.yaml for this workstream). Rome workload unchanged: GA 19 sent
07-27, T3 touch-2 due ~08-02 (script path), SAP-15 + 4 in-thread held with Dirk.

---

## Next Steps

1. Increment 4 (own session): make cadence progress step_no-keyed so mid-sequence
   INSERT is safe, then sequence-delta approval (append/insert/swap a future
   step while the campaign stays `sending`; re-pin only changed keys).
2. Dirk-wave release action (staged drafts -> release enumerated ids on his
   per-wave yes) - gated on Dirk's sender-policy answer (open question 1 in the
   plan).
3. Deploy the merged migrations to brisken-lead-desk.fly.dev before the arming
   drill (from a clean worktree; additive, safe).
4. Watched send drill + Dirk greenlight -> kill_switch off (the arming gate).
5. Phase 0: T3 touch-2 non-responder list + in-thread drafts before ~08-02.
6. Register archive split (`checkpoint_scaffold.py archive-register`) - 414 KB.

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/brisken-refactored-hopper.md` (the plan; §Phase 2 has the
  sequence-delta spec)
- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `automations/lead-desk/src/lead_desk/web/cadence.py`
  (`enrollment_state`, `enrollment_progress` view in store.py)

### Open Questions (for Dirk)
- Sender policy for his-name waves (per-wave release vs per-mail clicks);
  Instantly-off confirm; Zoho-as-record confirm; drill date; GA follow-up week.

### Working Notes
- The increment-4 core: `store.enrollment_progress` view derives `steps_done`
  as `COUNT(*)` of cadence events; `cadence.enrollment_state` uses it as a
  positional index `steps[steps_done]` (comment: "1-based step_no == steps_done
  + 1"). To make INSERT safe: derive the SET of sent step_nos (parse ext_key
  `cadence:{eid}:{step_no}`), pick the first step whose step_no is unsent,
  `done` = all step_nos sent. This changes the view + `enrollment_state`
  signature + `due_items` + all cadence tests that build a `progress` dict with
  `steps_done`. Append-only is unaffected (the common case), so it is a
  refactor-with-invariant, not a behavior change for current campaigns.
- Worktree `agentic-ops1-ldharden` on branch
  `client/brisken/lead-desk-spaced-sending` (increment 3 tip = in main). Cut
  the increment-4 branch off `origin/main` after pulling.
- Test env: `uv run --directory <lead-desk> --extra web --extra dev pytest -q`
  (the `fastapi` extra is NOT in the default env; the 7 TestClient files
  collect-error without it). CI does NOT lint lead-desk (ruff scope is
  `tools .claude/hooks tools/tests` only), so pre-existing lead-desk ruff
  warnings (DEGREES import, `cur` in upsert_sequence) are out of scope.
- Merge-commit stacking worked: `gh pr merge N --merge` keeps the feature SHA
  in main, so the next branch off the prior tip PRs a clean single-increment
  diff. Do NOT squash these.

### Reference Materials
- PRs: github.com/011matthias/agentic-ops1.01/pull/{473,474,475}
- `.scratch/ga_send_wave.py` (the guard pattern that was ported)
- `rule_brisken_graph_send_by_id.md`, `project_lead_desk_4d_graph_send` memory

---

## How to Continue

`/comd_resume brisken`, read the plan §Phase 2, then cut a fresh
`client/brisken/lead-desk-sequence-editing` branch off `origin/main` in a
worktree and build increment 4 (step_no-keyed progress first, then delta
approval), pytest per rule_no_auto_commit Band 1, merge on green.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the real send-critical source (cadence/store/cloud_worker) before
  editing, anchored by the explorer's file:line map, meant every guard matched
  the actual code paths and the full suite passed each increment first try (no
  build-test-fix iterations).
- Merge-commit stacking let three dependent increments ship as clean separate
  PRs without stacked-branch fragility.

### Suggestions
- Add the lead-desk suite to CI (it has 306 tests and is not run by any CI
  job today; only local `pytest` gates it). A `lead-desk` CI job would make the
  Band-1 verification precondition structural for this automation, not just
  agent-run.

### System Health
- Autonomy: 1 human intervention (the designed scope question: which Phase-1
  track to start). Effectively autonomous.
- Gates: B2 fired every increment (named pytest + full suite + CI-green before
  merge); B6 honored (Band-1 ship, Band-2 merge on green, no Band-3 deploy
  without order). skipped:0.
- Friction register at 414 KB - archive split pending.
