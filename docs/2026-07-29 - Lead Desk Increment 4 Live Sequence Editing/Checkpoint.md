# Checkpoint: Lead Desk Increment 4 Live Sequence Editing

**Date:** 2026-07-29
**Status:** Increment 4 SHIPPED (PRs #477 + #478 merged). Engine dormant; kill_switch=1. Two gated items remain (Dirk-wave release, arming drill) plus a deploy.

---

## Summary

Built the owner's "insert, edit and add sequences to running campaigns" ask for the outreach engine (Lead Desk): cadence progress is now keyed on the SET of sent step_nos (not a positional count), and an operator can append/insert/swap FUTURE sequence steps on a live campaign without demoting it to draft. Two stacked PRs, each pytest-verified and merged on green CI. Suite 306 -> 325.

---

## What Was Done This Session

### Part 1 — step_no-keyed progress (PR #477)
1. `enrollment_progress` view exposes `sent_steps` (comma-joined step_nos; v10 migration refreshes the view onto prod).
2. `enrollment_state` picks the first step whose step_no is UNSENT and treats `done` as every sequence step_no sent; `steps_done` output stays a count (unchanged for append-only). `due_items` / `project_schedule` / `service._attach_cadence` pass the set.
3. 9 tests: first-unsent selection, the gap case `{1,3}` a count index would re-send, out-of-sequence sent step_no ignored, view column, end-to-end claim by identity.

### Part 2 — live sequence editing / delta approval (PR #478)
1. `store.frozen_step_nos(campaign, degree)` = step_nos with a send_attempt or landed sent event (immutable history).
2. `cadence.sequence_delta_report` + `apply_sequence_delta`: frozen steps must stay as the byte-identical leading prefix; future steps get fresh step_nos ABOVE every attempted one; re-pin only changed/new template keys; campaign KEEPS its status (no supersede). Refuses any change to a sent step and routes to the interim pause->edit->re-approve path.
3. `POST /campaigns/{cid}/sequences/{degree}/delta` + an "Edit live (keep sending)" form per degree (approved/sending/paused only).
4. 10 tests: append stays sending, TRUE insert runs before the old next step (end-to-end claim), swap-future-version re-pins only that key, refuse changing/removing a sent step, refuse on draft, approved-unsent full re-sequence, recipient-drift still blocks after a delta, every future step pinned; plus an HTTP route test.

### Ledger / status
- `status/p2-outreach-engine.md` was untracked (loose end from increments 1-3); committed to main + brought current (PR #479).

---

## Key Decisions Made

### step_no is the stable send-identity; identity != order-position
- **Choice:** progress keys on the sent step_no SET; the delta assigns future steps fresh step_nos above every attempted one, keeping frozen (sent) step_nos fixed.
- **Rationale:** the ext_key `cadence:{eid}:{step_no}` is the send-dedup key. Renumbering a SENT step's step_no is the corruption source (re-send old copy + skip new). Keeping sent step_nos frozen and only editing the beyond-frozen region is the one place an edit is provably safe for ALL enrollments regardless of progress.

### Delta refuses; interim path stays the fallback
- **Choice:** the delta only edits the future region; any touch to a sent step is refused (route to pause->edit->re-approve), rather than trying to make arbitrary reorders safe.
- **Rationale:** a mid-insert before a contact's furthest-sent step cannot be made safe with a single shared sequence; refusing is honest and keeps send-safety absolute. The heavier interim path already handles the rare "must rewrite sent history" case.

### Two stacked PRs, merge-commit
- **Choice:** Part 1 off origin/main, merged; Part 2 off the updated main; `--merge` not squash.
- **Rationale:** send-safety code reviews/reverts best in small units; merge-commit stacking keeps each PR diff to its own change (continues the increments 1-3 pattern).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/lead-desk/src/lead_desk/web/store.py` | edited | v10 view (`sent_steps`), `frozen_step_nos`, `enrollments_for_campaign` select |
| `automations/lead-desk/src/lead_desk/web/cadence.py` | edited | `parse_sent_steps`, step_no-keyed `enrollment_state`, `sequence_delta_report`/`apply_sequence_delta`, `due_items`/`project_schedule` |
| `automations/lead-desk/src/lead_desk/web/service.py` | edited | `_attach_cadence` passes `sent_steps` |
| `automations/lead-desk/src/lead_desk/web/app.py` | edited | `POST /campaigns/{cid}/sequences/{degree}/delta` |
| `automations/lead-desk/src/lead_desk/web/templates/campaign.html` | edited | "Edit live (keep sending)" delta form |
| `automations/lead-desk/tests/test_step_no_progress.py` | created | 9 part-1 tests |
| `automations/lead-desk/tests/test_sequence_delta.py` | created | 9 part-2 tests |
| `automations/lead-desk/tests/test_webflow.py` | edited | delta route HTTP test |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | created | tracked on main + increment 4 |

---

## Current Status

Increments 1-4 in `main`; migrations v7-v10 NOT yet on the Fly prod volume. Engine dormant: kill_switch=1, no campaign `sending`, no real send ever fired. Suite 325 passing locally (not in CI). brisken platform ops: unknown plan (Fly-hosted lead-desk, no `platform` section in infrastructure.yaml for this workstream). Rome workload unchanged: GA 19 sent 07-27, T3 touch-2 due ~08-02 (script path), SAP-15 + 4 in-thread held with Dirk.

---

## Next Steps

1. **Dirk-wave release action** (GATED on Dirk's sender-policy answer): stage enumerated drafts in his Drafts, release exactly those ids on his per-wave yes.
2. **Deploy v7-v10 migrations** to brisken-lead-desk.fly.dev (additive/safe) from a clean origin/main worktree, sequenced just before arming.
3. **Watched send drill** + Dirk greenlight -> kill_switch off (the arming gate).
4. Phase 0: T3 touch-2 non-responder list + in-thread drafts before ~08-02 (script path, per-wave Dirk yes).
5. Phase 2: OOO `hold_until` (per-enrollment deferral from captured OOO).
6. Owner ask: add a lead-desk CI job (the 325-test suite is not run by any CI job; only local pytest gates it).

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/brisken-refactored-hopper.md` (§Phase 1.3 Dirk-wave, §Phase 2/3)
- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `automations/lead-desk/src/lead_desk/web/cadence.py` (`apply_sequence_delta`, `enrollment_state`)

### Open Questions (for Dirk)
- Sender policy for his-name waves (per-wave release vs per-mail clicks); Instantly-off confirm; Zoho-as-record confirm; drill date; GA follow-up week (08-18 vs 08-25).

### Working Notes
- The delta's safety envelope: frozen = step_nos with any send_attempt OR sent event (belt-and-suspenders over both). It must be a CONTIGUOUS leading prefix; a gap (a pending LinkedIn step wedged before a sent one) is refused -> pause/re-approve. Brisken's waves are pure email, so the contiguous case is the norm.
- Re-pin rule: keep all existing pins; pin latest for each template_key a FUTURE step uses; a key shared with a frozen step keeps its frozen version. So "swap a future step's version" = save a new template version, then run the delta.
- Test env: `uv run --directory <lead-desk> --extra web --extra dev pytest -q` (the `fastapi` web extra is NOT in the default env; 7 TestClient files collect-error without it).
- Worktree `agentic-ops1-ldharden` was reused for all four branches this session (sequence-editing, sequence-delta, status-inc4, this docs branch). The primary clone has 3 live sibling sessions on deckgen-native; do not commit there.

### Reference Materials
- PRs: github.com/011matthias/agentic-ops1.01/pull/{477,478,479}
- `rule_brisken_graph_send_by_id.md`, `project_lead_desk_4d_graph_send` memory

---

## How to Continue

`/comd_resume brisken`, read the plan §Phase 1.3, then either build the Dirk-wave release action (once Dirk answers open question 1) or run the deploy + watched arming drill (both gated on an owner order). Nothing in the remaining work is autonomous.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the full send-critical path (cadence/store/service/app + the exact test regression surface) before the first edit meant both PRs passed the full suite first try, no build-test-fix iterations. The one test failure was a wrong assertion in my own new test (expected message), self-caught in one iteration.
- Confronting the identity-vs-order tension explicitly up front (rather than coding the naive renumber) avoided shipping an unsafe mid-insert; the "refuse outside the frozen prefix" envelope is the honest safe boundary.

### Suggestions
- Add the lead-desk suite (325 tests) to CI. It gates real-send-critical code and is run only by local pytest today; a CI job would make the Band-1 verification structural for this automation. Raised in increments 1-3 too — now a 2x suggestion.

### System Health
- Autonomy: fully autonomous session (0 human interventions after the task brief).
- Gates: B2 fired on every build/test + ship (named pytest, full suite, CI-green before each merge); B6 honored (Band-1 ship, Band-2 merge on green, no Band-3 deploy without order); branch-isolation honored (ledger via this docs PR, client files on client branches, all in the isolated worktree). skipped:0.
- Register at 415 KB - archive split shipping in this docs PR.
