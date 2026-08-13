---
project: brisken
workstream: p2-outreach-engine
group: lead-generation
spec: p2
state: active
updated: 2026-08-13
build_progress: "TRUTH+ENGINE SPRINT 2026-08-13 (plan we-need-to-establish-foamy-sedgewick): nine PRs merged+deployed in one day (#511-#523: Graph primitives, v11 truth tables + unmatched queue + campaign attribution, v12 in-thread reply steps, drill runbook+CLI, wave enumeration/visibility, deep truth reconcile + scheduler, backfill CLI, events read API + capture-verify, truth UI + /sheet + /unmatched). Prod = user_version 12, suite 392 passing. Truth sweep ran: ledger complete:true, 0 failed folders, ~508-touch history corpus-arbitered (E1=242, all prior counts wrong). Suppression list LIVE in-engine (2,454 entries, 91 contacts flipped). Deep scan LIVE (first run recovered 6 events; 711 unmatched queued for review). Capture-adequacy verdict: CAPTURE-GAPS (66/122 missing over T3/GA windows) - the daily deep scan is REQUIRED and running. Sender still dormant (kill_switch=1, 0 sends ever). Remaining gates: ledger sign-off -> backfill run; Dirk mail -> Phase 1.3 variant + drill date; drill -> arm."
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
| Phase 1: Dirk-wave release action | pending | Shared core SHIPPED 2026-08-13 (PR #515): `enumerate_wave` with guard pre-checks + "Staged in Dirk's Drafts" card + stale banner. `send_draft_by_id` primitive shipped (PR #511). Remaining: variant A only (gated release route + `wave_releases` audit table, ~1.5 days) IF Dirk picks per-wave release; variant B (he clicks each draft) is already fully live | Build variant A on Dirk's answer, else nothing | Dirk answer | plan §Phase 1.3 |
| Deploy engine to Fly prod | done | DONE 2026-08-13: three deploys (v7-v10, then v11, then v12 + wave/scan/UI). Prod verified by DB read after each: `user_version=12`, recipient-pin guards live, kill_switch still `1`, `send_attempts` still 0. Rollback-compat checked first (v34 runner early-returns on newer schema) | none | none | prod probes 2026-08-13 |
| Phase 1: arm the sender | pending | Still dormant on prod (kill_switch=1, 0 send_attempts, verified after every 2026-08-13 deploy). ARMING-DRILL.md + `lead-desk-drill` CLI shipped (PR #513) and verified working on prod (`lead-desk-drill status` returns clean readiness audit). Steps 1-4 + 6-prep are Matthias-solo; only step 7 needs Dirk | Run drill steps 1-4 solo; schedule step 7 with Dirk | drill session with Dirk | ARMING-DRILL.md; rule_instantly_invasive |
| Dirk on the Lead Desk | done | VERIFIED 2026-08-11: `users.last_login_at = 2026-08-07T07:00:22Z`, 69s after the magic-link mail at 06:59:13Z. He is admin+approved and has actually signed in. The tool he saw is the Jul 25 build | none | none | prod `users` table; magic-link login PR #443 |
| Pending access request: owner@maintainiq.com | open | Self-registered 2026-08-03, status `pending`, unapproved 8 days. Not a Brisken or UnpauseAI address. Expected behaviour of the request/approve design, but it is an unactioned access decision on a client lead system | Approve or reject; ask Dirk if the address is his invite | owner decision | prod `users` table |
| Phase 2: GA non-responder follow-up | pending | First engine-native wave, start_not_before ~08-18/08-25 (vacation returns); responders auto-excluded by reply-halt | Enroll GA non-responders once armed | Phase 1 arm + Dirk timing answer | `context/lead-generation/rome-ga-wave.md` |
| Phase 2: OOO hold_until | pending | Per-enrollment deferral from captured OOO (parsed return date, else +14d) | Build after first engine wave | none | plan §Phase 2 |
| Phase 3: in-thread createReply steps | done | SHIPPED 2026-08-13 (PRs #511 + #514, merged + deployed, v12). Sequence steps carry `reply_to_prior`; worker resolves the prior send's imid to the live anchor, `create_reply_draft` (createReplyAll, body above quoted history), sends via guarded `send_draft_by_id`, asserts conversationId (mismatch acks + alerts `thread_verify_failed`); missing anchor PARKS with alert, never fresh-sends; `POST /attempts/send-fresh` operator override; Zoho BCC on replies pinned by test. draft-dirk reply steps stage into his Drafts. The `.scratch/` script dependency for follow-ups is structurally retired | Rehearse threading via drill step 2 (draft-to-self on a reply-step campaign) | none | plan §Phase 3; PRs #511/#514 |
| Reply draft to Dirk | done | Staged 2026-07-29, nothing sent | User shapes + sends | none | `context/drafts/outreach-engine-plan-to-dirk.md` |

## Target: all campaigns on Lead Desk from September (owner, 2026-08-11)

Updated 2026-08-13 after the truth+engine sprint. Of the original four gaps,
the two code gaps are CLOSED (everything merged + deployed, prod at v12);
what remains is human-gated:

| Need | State on 2026-08-13 |
|---|---|
| Engine code current in prod | DONE (three deploys, verified by DB reads) |
| Follow-ups as in-thread replies (Phase 3) | DONE (PRs #511/#514, deployed) |
| Sender armed | dormant; drill runbook + CLI ready; steps 1-4 Matthias-solo, step 7 needs Dirk |
| Send in Dirk's name at wave scale (Phase 1.3) | staging + visibility live; variant-A release surface (~1.5d) only if Dirk picks per-wave release |

The truth side (owner directive 2026-08-13, plan
`~/.claude/plans/we-need-to-establish-foamy-sedgewick.md`): the mailbox corpus
is the arbiter, Lead Desk is the operating record, the sheet's status columns
freeze after one final reconcile pass. The sweep ran clean (ledger
`context/lead-generation/outreach-truth/outreach-truth-ledger.json`,
complete:true, 0 failed folders). Its capture-adequacy check proved live
capture alone is NOT sufficient (66 of 122 corpus sends missing from the DB
over the T3/GA windows - filed mail and calendar accepts escape the
sentitems poll), which is exactly what the now-live daily deep scan closes.
Backfill CLI is built (PR #521) and its prod run waits on the owner signing
the ledger. Suppression list is live in-engine: 2,454 entries, 91 contacts
flipped, claim + execute guards check the table directly.

The long pole is still the conversation:
`context/drafts/outreach-engine-plan-to-dirk.md`, staged 2026-07-29, revised
2026-08-11, unsent. With code done early, the schedule compresses: drill steps
1-4 can run solo immediately; the moment Dirk gives a 45-minute slot, step 7
arms the engine, and the first engine-native wave can go with
`start_not_before` 2026-09-01.

Zoho BCC filing is still UNVERIFIED and has to be proven in drill step 6, or
the CRM record breaks on the first live wave.

## Open decisions / gates

- T3 touch-2 fork (decide now, not in September): 9 days past its ~08-02 date,
  but a send this week is still only three weeks behind touch-1, an ordinary
  second-touch interval. Waiting for the armed engine makes it seven weeks,
  which is too long to be worth sending. So it goes by script this week or it
  is dropped; drifting picks the worst of both. Copy for touch-2 does not exist
  yet and has to be written and approved either way.
- **CORRECTED 2026-08-13: 1 human reply across the 43 post-Rome sends, not 0.**
  Stiaan Scheepers (Global Payments) replied to the GA send at
  2026-07-27T10:59Z, ~2.5h after it landed, and **Dirk answered him
  personally the same day** (his answer BCC'd matthias.silva, not the Zoho
  dropbox, so that reply is not in CRM). The 2026-08-11 "0 human replies"
  check missed it: its inbound pull was page-capped and it matched the sent
  alias, not the sheet-primary address. The full-corpus sweep caught it; the
  live capture had the reply event all along (`ss50866@globalpayments.com`,
  source graph-auto). T3 stands at 24 sent, 0 replies, 3 out-of-office; GA is
  19 sent, 1 reply (handled), 2 out-of-office.
- What that does and does not mean. Both cohorts are the deliberately cold end
  of Rome: T3 attended without speaking to us, GA is ecosystem rather than
  buyers (`Tier_reason = "general awareness, not a warm lead"`). The warm
  conversations went to Dirk personally and are not in this sample. Delivery,
  pacing, capture and the guards all behaved correctly, so this is not a system
  fault. But it is the entire body of engine-eligible outreach to date, and it
  returned one reply.
- Consequence for September, worth deciding before arming: 1/43 (~2.3%) is
  thin evidence for the current copy shape. The offer, copy and segment remain
  the likelier binding constraint than sending mechanics, and the first
  engine-native wave should probably test a different angle rather than repeat
  the TreasuryCentral note at higher throughput. (The one reply came from the
  plainer Sequence-A note within hours, for what one data point is worth.)
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
