---
project: brisken
workstream: p2-outreach-engine
group: lead-generation
spec: p2
state: active
updated: 2026-07-29
build_progress: "Phase 1 increments 1-4 SHIPPED. 1-3 (PRs #473/#474/#475): send-safety guards, start_not_before, spaced sending. 4 (PRs #477/#478): step_no-keyed cadence progress + live sequence-delta editing. Engine suite 325 passing, still dormant. Next: Dirk-wave release action + arming drill (both gated). Migrations v7-v10 merged, NOT yet deployed to Fly prod."
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
| Phase 0: T3 touch-2 (script path) | in-progress | Due ~2026-08-02 as in-thread replies from Dirk's mailbox (engine has no createReply, no Dirk auto-send). Non-responders from mailbox truth; ga_send_wave guard shape; then stop, no third email | Build non-responder list + drafts for Dirk's look before 08-02; per-wave Dirk yes to send | Dirk per-wave yes | `context/lead-generation/rome-t3-wave-rebuilt.md`; `.scratch/ga_send_wave.py` pattern |
| Phase 1: guard port | done | SHIPPED PR #473 (merged). campaign_recipient_pins (v7); approval pins (contact_id,email); claim-time recipient-drift + domain-deny (sap.com/brisken.com floor + send_deny_domains state) + unpinned-template guards -> send_guard_alert; worker execute-time denied-domain backstop. 10 tests | Suppression-list.csv import still a small follow-up (data-ops, not code) | none | `rule_brisken_graph_send_by_id` |
| Phase 1: start_not_before | done | SHIPPED PR #474 (merged). Nullable campaigns.start_not_before (v8); claim skips before it; first step anchors on max(approved_at, start_not_before); scope text; POST /campaigns/{cid}/schedule + Schedule card. 5 tests | none | none | plan §Phase 1.2 |
| Phase 1: spaced sending | done | SHIPPED PR #475 (merged). ramp_per_day (v9) per-day new-contact ramp; per-mailbox daily cap across campaigns (mailbox_daily_cap state); project_schedule preview on the confirm page. 7 tests | none | none | plan §Phase 1.6 |
| Phase 1/2: step_no-keyed progress | done | SHIPPED PR #477 (merged). enrollment_progress view exposes sent_steps (v10); enrollment_state picks first UNSENT step by identity, not a positional count; due_items/project_schedule/service pass the set. Append-only unchanged. Foundation for the delta path. 9 tests | none | none | plan §Phase 2(a); branch client/brisken/lead-desk-sequence-editing |
| Phase 2: live sequence editing (delta approval) | done | SHIPPED PR #478 (merged). Append/insert/swap FUTURE steps on an approved/sending campaign WITHOUT demote to draft; sent step_nos frozen (immutable history); future steps get fresh step_nos above every attempted one; re-pin only changed/new keys; recipient pins + hash untouched so increment-1 guards hold. store.frozen_step_nos, cadence.sequence_delta_report/apply_sequence_delta, POST /campaigns/{cid}/sequences/{degree}/delta, "Edit live" UI. 10 tests. Interim pause->edit->re-approve path kept working | none | none | plan §Phase 2(b); branch client/brisken/lead-desk-sequence-delta |
| Phase 1: Dirk-wave release action | pending | Waves in Dirk's name: engine stages enumerated drafts in his Drafts, gated action releases exactly those ids on his single per-wave yes; continuous auto-send as Dirk stays impossible | Awaits Dirk's sender-policy answer (open question 1) | Dirk answer | plan §Phase 1.3 |
| Deploy migrations v7-v10 to Fly prod | pending | Additive (columns + a view refresh), safe. Not yet on the brisken-lead-desk.fly.dev volume; nothing sends so no urgency | Deploy from a clean origin/main worktree just before the arming drill | owner order (Fly deploys pre-authorized, but sequenced with arming) | checkpoint 2026-07-29 |
| Phase 1: arm the sender | pending | kill_switch=1; no real send ever fired via engine | Watched send drill (draft-to-self, real self-send, Zoho BCC filing verify) + Dirk greenlight, then kill_switch off | drill session with Dirk | `project_lead_desk_4d_graph_send` memory; rule_instantly_invasive |
| Phase 2: GA non-responder follow-up | pending | First engine-native wave, start_not_before ~08-18/08-25 (vacation returns); responders auto-excluded by reply-halt | Enroll GA non-responders once armed | Phase 1 arm + Dirk timing answer | `context/lead-generation/rome-ga-wave.md` |
| Phase 2: OOO hold_until | pending | Per-enrollment deferral from captured OOO (parsed return date, else +14d) | Build after first engine wave | none | plan §Phase 2 |
| Phase 3: in-thread createReply steps | pending | Retires the last script dependency (follow-up steps as replies in-thread) | Design after Phase 2 | none | plan §Phase 3 |
| Reply draft to Dirk | done | Staged 2026-07-29, nothing sent | User shapes + sends | none | `context/drafts/outreach-engine-plan-to-dirk.md` |

## Open decisions / gates

- Dirk: sender policy for his-name waves (per-wave release vs per-mail clicks);
  Instantly-off confirm; Zoho-as-record confirm (+ optional read-scope grant);
  drill scheduling; GA follow-up week (08-18 vs 08-25).
- Every send stays behind: two-gate approve/start-sending, per-wave owner yes
  for Dirk-voiced mail, watched drill before arming, kill_switch, hard mailbox
  allowlist. A sequence delta does not relax any of these (recipient pins +
  hash preserved).
- Infra note for owner: the lead-desk 325-test suite is NOT in CI (ruff/pytest
  scope is tools/.claude/hooks only). A lead-desk CI job would make the Band-1
  verification structural, not agent-run.

## Pointers

- Plan: `~/.claude/plans/brisken-refactored-hopper.md`
- Engine: `workspace/clients/brisken/automations/lead-desk/` (BLUEPRINT.md)
- Comms: `context/comms-log.md` 2026-07-25 entries (thread logged 2026-07-29)
