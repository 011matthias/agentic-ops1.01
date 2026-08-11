---
project: brisken
workstream: p2-outreach-engine
group: lead-generation
spec: p2
state: active
updated: 2026-08-11
build_progress: "Phase 1 increments 1-4 SHIPPED. 1-3 (PRs #473/#474/#475): send-safety guards, start_not_before, spaced sending. 4 (PRs #477/#478): step_no-keyed cadence progress + live sequence-delta editing. Engine suite 325 passing, still dormant. OWNER TARGET 2026-08-11: all Brisken campaigns run entirely on Lead Desk from September. That makes Phase 3 (in-thread createReply) critical path, not post-Phase-2, and puts the whole plan behind one unsent Dirk mail. Prod verified pinned to the 2026-07-25 build (v34): migrations v7-v10 NOT applied."
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Outreach Automation Engine (p2)

The campaign engine promised to Dirk (thread "Post Event Outreach", 2026-07-25;
his reply named Instantly / build / Zoho as candidate directions). Decision
2026-07-29 (plan `~/.claude/plans/brisken-refactored-hopper.md`): build on Lead
Desk (`automations/lead-desk`, live at brisken-lead-desk.fly.dev). Zoho stays
the CRM of record + BCC filing target, not the sequencer (Cadences sends from
Zoho servers, excluded from Email Relay, so it cannot originate from the warm
mailboxes). Instantly stays off; named re-entry trigger = engine-wave bounce
rate above ~3% or reply collapse, or a future cold-farm build-out. The
Cristian/getken cold trial is a separate motion; shared artifact = the
suppression list only. Canonical status store = the Lead Desk event log
(mailbox-grounded via capture); Rome identity/tier stays sheet-authoritative in,
sheet status cols are an upgrades-only projection out.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Phase 0: T3 touch-2 (script path) | in-progress | LIST BUILT 2026-08-11 from both-mailbox truth (all folders, since 07-20). All 24 touch-1 mails confirmed sent 2026-07-21 from dirk.neumann. **Zero human replies at three weeks.** 3 out-of-office only (ana.matos@ / miguel.carvalho@adidas.com, line.ehlers@dsv.com; return dates not captured by the tool, check before sending to those). 21 non-responders are the touch-2 set. Goes as in-thread replies from Dirk's mailbox (engine has no createReply, no Dirk auto-send); ga_send_wave guard shape; then stop, no third email | Decide send-this-week vs drop. Touch-2 copy is NOT written. Needs per-wave Dirk yes | Dirk per-wave yes; copy unwritten | `context/lead-generation/rome-t3-wave-rebuilt.md`; `.scratch/t3-touch2-truth.json`; `.scratch/ga_send_wave.py` pattern |
| Phase 1: guard port | done | SHIPPED PR #473 (merged). campaign_recipient_pins (v7); approval pins (contact_id,email); claim-time recipient-drift + domain-deny (sap.com/brisken.com floor + send_deny_domains state) + unpinned-template guards -> send_guard_alert; worker execute-time denied-domain backstop. 10 tests | Suppression-list.csv import still a small follow-up (data-ops, not code) | none | `rule_brisken_graph_send_by_id` |
| Phase 1: start_not_before | done | SHIPPED PR #474 (merged). Nullable campaigns.start_not_before (v8); claim skips before it; first step anchors on max(approved_at, start_not_before); scope text; POST /campaigns/{cid}/schedule + Schedule card. 5 tests | none | none | plan §Phase 1.2 |
| Phase 1: spaced sending | done | SHIPPED PR #475 (merged). ramp_per_day (v9) per-day new-contact ramp; per-mailbox daily cap across campaigns (mailbox_daily_cap state); project_schedule preview on the confirm page. 7 tests | none | none | plan §Phase 1.6 |
| Phase 1/2: step_no-keyed progress | done | SHIPPED PR #477 (merged). enrollment_progress view exposes sent_steps (v10); enrollment_state picks first UNSENT step by identity, not a positional count; due_items/project_schedule/service pass the set. Append-only unchanged. Foundation for the delta path. 9 tests | none | none | plan §Phase 2(a); branch client/brisken/lead-desk-sequence-editing |
| Phase 2: live sequence editing (delta approval) | done | SHIPPED PR #478 (merged). Append/insert/swap FUTURE steps on an approved/sending campaign WITHOUT demote to draft; sent step_nos frozen (immutable history); future steps get fresh step_nos above every attempted one; re-pin only changed/new keys; recipient pins + hash untouched so increment-1 guards hold. store.frozen_step_nos, cadence.sequence_delta_report/apply_sequence_delta, POST /campaigns/{cid}/sequences/{degree}/delta, "Edit live" UI. 10 tests. Interim pause->edit->re-approve path kept working | none | none | plan §Phase 2(b); branch client/brisken/lead-desk-sequence-delta |
| Phase 1: Dirk-wave release action | pending | Waves in Dirk's name: engine stages enumerated drafts in his Drafts, gated action releases exactly those ids on his single per-wave yes; continuous auto-send as Dirk stays impossible | Awaits Dirk's sender-policy answer (open question 1) | Dirk answer | plan §Phase 1.3 |
| Deploy migrations v7-v10 to Fly prod | pending | Additive (columns + a view refresh), safe. VERIFIED ABSENT 2026-08-11: prod is release v34 (Jul 25 09:20) and its schema has `campaign_template_pins` but no `campaign_recipient_pins` (v7), so the Phase 1 recipient-pin guards do not exist on the running machine. The old "nothing sends so no urgency" premise is weaker now that Dirk is a live user | Deploy from a clean origin/main worktree in the 08-18 week, ahead of the drill | owner order (Fly deploys pre-authorized, but sequenced with arming) | checkpoint 2026-07-29; prod read 2026-08-11 |
| Phase 1: arm the sender | pending | VERIFIED DORMANT 2026-08-11 on prod: `kill_switch=1`, `send_attempts` 0 rows. Cloud worker alive (heartbeat 2026-08-11T21:02Z, counters sent/drafted/failed all 0) so capture runs and sending cannot | Watched send drill (draft-to-self, real self-send, Zoho BCC filing verify) + Dirk greenlight, then kill_switch off | drill session with Dirk | `project_lead_desk_4d_graph_send` memory; rule_instantly_invasive |
| Dirk on the Lead Desk | done | VERIFIED 2026-08-11: `users.last_login_at = 2026-08-07T07:00:22Z`, 69s after the magic-link mail at 06:59:13Z. He is admin+approved and has actually signed in. The tool he saw is the Jul 25 build | none | none | prod `users` table; magic-link login PR #443 |
| Pending access request: owner@maintainiq.com | open | Self-registered 2026-08-03, status `pending`, unapproved 8 days. Not a Brisken or UnpauseAI address. Expected behaviour of the request/approve design, but it is an unactioned access decision on a client lead system | Approve or reject; ask Dirk if the address is his invite | owner decision | prod `users` table |
| Phase 2: GA non-responder follow-up | pending | First engine-native wave, start_not_before ~08-18/08-25 (vacation returns); responders auto-excluded by reply-halt | Enroll GA non-responders once armed | Phase 1 arm + Dirk timing answer | `context/lead-generation/rome-ga-wave.md` |
| Phase 2: OOO hold_until | pending | Per-enrollment deferral from captured OOO (parsed return date, else +14d) | Build after first engine wave | none | plan §Phase 2 |
| Phase 3: in-thread createReply steps | pending | CRITICAL PATH for the September target, promoted 2026-08-11 from "design after Phase 2". Continuing a campaign means writing into threads that already exist; `graph_mail.py` today exposes only send_auto / create_draft / poll_sent / search_sent_for / readback_sent, with no reply primitive, so every follow-up still goes out through a `.scratch/` script. Until this ships, "entirely on Lead Desk" is not true no matter what else is armed | Build in parallel with Phase 1.3 in the 08-18 week, not after the first wave | none | plan §Phase 3; `graph_mail.py` read 2026-08-11 |
| Reply draft to Dirk | done | Staged 2026-07-29, nothing sent | User shapes + sends | none | `context/drafts/outreach-engine-plan-to-dirk.md` |

## Target: all campaigns on Lead Desk from September (owner, 2026-08-11)

Four things stand between here and that. Two are built-and-undeployed, two are
not built at all:

| Need | State on 2026-08-11 |
|---|---|
| Guards, scheduling, ramp, delta editing running in prod | merged + CI-green, NOT deployed (prod = Jul 25 build) |
| Sender armed | dormant; needs the watched drill + Dirk greenlight |
| Send in Dirk's name at wave scale (Phase 1.3) | not built; design blocked on Dirk's sender-policy answer |
| Follow-ups as in-thread replies (Phase 3) | not built; no reply primitive in `graph_mail.py` |

The long pole is a conversation, not code. Every row above sits behind Dirk's
answers, and `context/drafts/outreach-engine-plan-to-dirk.md` has been staged
since 2026-07-29 without going out. Working schedule if it goes this week:
08-18 week builds Phase 1.3 + Phase 3 in parallel and deploys everything to
prod; 08-25 week runs the drill and arms; first fully engine-native wave from
2026-09-01. If the mail slips two more weeks the drill lands in September and
the target moves with it.

Zoho BCC filing is still UNVERIFIED and has to be proven in the drill, or the
CRM record breaks on the first live wave.

## Open decisions / gates

- T3 touch-2 fork (decide now, not in September): 9 days past its ~08-02 date,
  but a send this week is still only three weeks behind touch-1, an ordinary
  second-touch interval. Waiting for the armed engine makes it seven weeks,
  which is too long to be worth sending. So it goes by script this week or it
  is dropped; drifting picks the worst of both. Copy for touch-2 does not exist
  yet and has to be written and approved either way.
- Touch-1 returned **0 human replies from 24** at three weeks (verified
  2026-08-11, both mailboxes, all folders). T3 is the coldest Rome tier
  (attended, never spoke to us), so this is not a system fault, and capture,
  pacing and guards all behaved. It is still a real signal about copy and
  segment worth weighing before the September motion scales the same shape:
  compare against the GA wave's reply rate (19 sent 2026-07-27) before assuming
  the engine's throughput is the binding constraint.
- Dirk: sender policy for his-name waves (per-wave release vs per-mail clicks);
  Instantly-off confirm; Zoho-as-record confirm (+ optional read-scope grant);
  drill scheduling; GA follow-up week (08-18 vs 08-25).
- Every send stays behind: two-gate approve/start-sending, per-wave owner yes
  for Dirk-voiced mail, watched drill before arming, kill_switch, hard mailbox
  allowlist. A sequence delta does not relax any of these (recipient pins +
  hash preserved).
- Infra: the lead-desk 325-test suite now runs in CI (PR #482, `lead-desk`
  job); since the repo auto-merges on green, Band-1 verification is structural
  for this automation, not just agent-run.

## Pointers

- Plan: `~/.claude/plans/brisken-refactored-hopper.md`
- Engine: `workspace/clients/brisken/automations/lead-desk/` (BLUEPRINT.md)
- Comms: `context/comms-log.md` 2026-07-25 entries (thread logged 2026-07-29)
