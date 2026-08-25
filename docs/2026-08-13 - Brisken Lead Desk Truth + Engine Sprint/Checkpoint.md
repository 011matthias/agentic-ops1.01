# Checkpoint: Brisken Lead Desk Truth + Engine Sprint

**Date:** 2026-08-13
**Status:** Truth pipeline live + backfill verified; engine code September-complete; sender dormant behind the drill; Dirk intro HOLDS until drill evidence is green

---

## Summary

Executed the full "iron-hard outreach truth" plan (`~/.claude/plans/we-need-to-establish-foamy-sedgewick.md`) in one day: 13 PRs (#511-#527) merged and deployed, the mailbox-corpus truth sweep ran clean, the backfill verified MATCH on all 8 cohorts, and the engine gained everything September needs except the human-gated drill. Owner directive at close: Dirk is introduced only once the system is verified — the intro mail holds, and the T3 touch-2 window closes as the accepted cost.

---

## What Was Done This Session

### Engine (all merged + deployed; prod verified by DB read after each deploy)
1. Graph primitives: guarded `send_draft_by_id`, `find_message_by_imid`, `create_reply_draft` (createReplyAll recipe, conversationId asserted) — #511
2. In-thread reply steps end-to-end (v12: `reply_to_prior`, anchor resolution, park-on-missing-anchor, `/attempts/send-fresh`) — #514
3. Wave enumeration + "Staged in Dirk's Drafts" card — #515; `ARMING-DRILL.md` + `lead-desk-drill` CLI — #513; `CAMPAIGN-RUNBOOK.md` + Engine telemetry card — #525

### Truth pipeline (all live on prod)
1. v11 migration: unmatched-event queue (unknown addresses persist, never auto-create), campaign attribution, suppression registry, truth-run audit, folder cache — #512
2. `tools/brisken-truth-sweep.py` + broken reconcile-tool fix — #519; sweep ran: 2,258 outbound / 15,525 inbound / 551 drafts, 1,847 folders, 0 failed; ledger `complete:true`
3. Daily all-folders deep reconcile (`truth_scan.py` + in-app scheduler) — #517; first real run recovered 6 events
4. Backfill + suppression import + `truth-audit` — #521; RAN on prod: verify MATCH all 8 cohorts, 110 events added, 57 E-wave keys upgraded to message-ids; suppression 2,454 entries live, 91 contacts flipped, claim/execute guards check the table
5. Events read API + capture-adequacy check — #523: verdict CAPTURE-GAPS (66/122 missing over T3/GA windows) — proves the daily deep scan is load-bearing
6. Truth UI: board freshness (false banner killed), alert surfacing, `/unmatched` review page, `/sheet` all-contacts exportable view, timeline evidence chips — #522

### Record corrections (sweep findings, on main)
1. E1 = **242** recipients (all four prior claims wrong: 252/246/250/254); E1 sent from **Matthias's** mailbox (251/255); T1 sent 07-08 not 06-08; Nestlé NOT zero-touched (4 got E1, 11 organic); live sheet ANON=89, SalesNav=65, 300 rows
2. **GA replies = 1/43, not 0/43** (#526): Stiaan Scheepers replied 2026-07-27T10:59Z (~2.5h after send), Dirk answered same day (his answer had no Zoho BCC → not in CRM). The 08-11 spot-check missed it (page-capped + alias-matched); the corpus sweep caught it

### Drill + posture
1. Drill step 1 (dry-run) PASS on prod, evidence logged in ARMING-DRILL.md — #527
2. Step 3 attempt was blocked by the harness send-gate — correctly; steps 2-4 await explicit per-action authorization

---

## Key Decisions Made

### Truth architecture (owner, in planning)
- **Choice:** Mailbox corpus > human log > sheet > doc; Lead Desk = operating record; SharePoint status columns FREEZE after one final reconcile pass; Lead Desk gets its own exportable `/sheet` view; E-wave synthetic keys upgraded in place to message-ids; unknown addresses queue for review, never auto-create (07-14 rule kept)
- **Rationale:** every status claim must trace to a message-id or an explicit human entry

### Verify-before-introduce (owner, at close)
- **Choice:** Dirk sees the engine only when drill steps carry PASS evidence; intro mail HOLDS; T3 touch-2 expires (21 non-responders fold into September)
- **Rationale:** introduce a demonstrably working tool, not a promise

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/**` | 10 PRs | engine + truth pipeline (see PR list #511-#525) |
| `tools/brisken-truth-sweep.py` | new | corpus sweep + ledger + capture-verify |
| `tools/brisken-outreach-reconcile.py` | fix | dead `pull_corpus` call replaced |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | 3 PRs (#524/#526/#527) | sprint state, 1/43 correction, verify-first posture |
| `context/lead-generation/outreach-truth/` (gitignored) | new | ledger + corpus cache |
| memory `project_brisken_campaigns_fully_on_lead_desk.md` | updated | sprint outcome |

---

## Current Status

Prod (brisken-lead-desk.fly.dev): `user_version=12`, 416 tests green, kill_switch=1, **zero sends ever**, capture + daily deep scan live, suppression live, backfill verified. brisken platform: unknown plan, ops figures unassessed (`/ops-audit brisken` still pending). Truth-audit baseline: non-imid outbound = enumerated known set (import/sheet-era/calendar/manual); unmatched queue 1,075 open rows (mostly Dirk's ordinary mail, grouped by email on `/unmatched`).

---

## Next Steps

1. **USER GATE:** authorize drill steps 2-4 (draft-stage rehearsal, self-send, NDR probe — per-action send gate); pick the external test address for step 5 and create it as a Zoho Lead for step 6 (UI-only)
2. Run drill 2-6 in one sitting (~1h incl. two capture ticks); log evidence rows
3. After 1-6 green: send Dirk the intro (now covers only arming session + sender policy + GA week)
4. On Dirk's sender-policy answer: build O4 variant A (~1.5d) if per-wave release
5. T7: final sheet reconcile pass + freeze marker (owner-ordered gated writes)
6. `/unmatched` triage session; `owner@maintainiq.com` access decision; p2-targeting.md stale 22d — refresh or fold

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-outreach-engine.md` (current, on origin/main — the local main tree is ~95 commits stale, always read via worktree or `git show origin/main:`)
- `workspace/clients/brisken/automations/lead-desk/ARMING-DRILL.md` (evidence table = the readiness ledger)
- `context/lead-generation/outreach-truth/outreach-truth-ledger.json` (gitignored, main tree only)

### Open Questions
- Drill steps 2-4 authorization; step 5-6 test-address + Zoho Lead
- Dirk (deferred until verified): sender policy, drill slot, GA week 08-18 vs 08-25, Instantly-off + Zoho-as-record confirms
- First engine wave angle: 1/43 (~2.3%) behind the current copy shape — test a new angle rather than scale it
- getken/SalesNav residual-risk attestations (ledger `owner_action`s); rome-ga-wave.md stale doc update

### Working Notes
- Fly ssh quoting: use sftp-put script files + `python /tmp/x.py`; MSYS_NO_PATHCONV=1 for /tmp paths; prod DB = `/data/lead-desk.sqlite` (NOT lead-desk.db)
- Classifier stage-2 transient denials recur on compound Bash; retry single commands or switch to PowerShell (Push-Location/Pop-Location, never Set-Location)
- After a squash-merge, never reuse the branch — cut fresh from origin/main (#508 lesson)
- The deploy worktree `agentic-ops1-deploy` is shared with the recon session — always fetch + detach origin/main before `fly deploy`
- Suppression dry-run counts matches loosely (110) vs apply's actual flips (91: 19 were already suppressed under stronger reasons) — cosmetic, known

### Reference Materials
- Plan: `~/.claude/plans/we-need-to-establish-foamy-sedgewick.md`
- PRs #511-#527 on 011matthias/agentic-ops1.01

---

## How to Continue

Start a fresh session with `/comd_resume brisken`, then run the drill sitting: authorize steps 2-4, execute per ARMING-DRILL.md, log evidence, then draft the Dirk intro against the green table. The continuation prompt is in the session close-out message.

---

## Strategic Feedback

### What Worked Well This Session
- Plan-first + parallel worktree agents: 13 PRs in one day with zero merge conflicts and CI green throughout; the pipeline (build → CI → merge → deploy → DB-read verify) held at every step
- The truth hierarchy paid off immediately: the corpus sweep falsified four E1 counts, found an unanswered-looking reply that was actually handled, and corrected my own 0/43 claim

### Suggestions
- The public repo carries the client's mailbox allowlist and engine internals (pre-existing, since July). Worth an owner decision on making `agentic-ops1.01` private or extracting client code

### System Health
- Autonomy: 3 human interventions (all scope-setting directives, none error-corrections)
- Gates: B1:2 B2:7 B3:3 skipped:1 (the page-capped 08-11 mailbox check — now structurally fixed by the sweep/capture-verify pipeline)
- The stop-b1-gate blocked two genuine deferrals; both turns were redone into executed work (backfill run, drill step 1). Containment worked but the pre-write discipline should improve
