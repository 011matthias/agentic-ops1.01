# Checkpoint: Brisken Outreach Engine Strategy

**Date:** 2026-07-29
**Status:** Decision made (build on Lead Desk); plan approved; no code yet

---

## Summary

Strategy session answering Dirk's 2026-07-25 "Post Event Outreach" reply
(Instantly / build / Zoho). Full B7 enumeration (Lead Desk code map, live Zoho
scope probes, mailbox thread pull) led to the decision: extend Lead Desk into
the campaign engine; Zoho stays CRM-of-record + BCC filing; Instantly stays off
with a named re-entry trigger. Plan, status file, comms backfill, and a staged
reply draft shipped; Phase 0/1 builds are separate ordered sessions.

---

## What Was Done This Session

### Enumeration (B7, three parallel explorers + live probes)
1. Lead Desk capability map vs the five promised features: F1/F2/F5 FULL, F3
   built-but-dormant (kill_switch=1), F4 partial. Local tree byte-identical to
   origin/main for lead-desk.
2. Code-verified gaps: send-by-id guards not ported; approval drift hole
   (contact_ids pinned, email read live at claim + overwritten by sheet-sync);
   no scheduled start; no per-contact OOO deferral; no in-thread createReply;
   auto-send matthias-only; getken suppression CSV not imported.
3. Zoho live probe: token scope is exactly `contacts.READ accounts.READ`
   (org/users/settings/Leads/Campaigns/Cadences all 401; edition unknown).
   Cadences sends from Zoho servers and is excluded from Email Relay, so it
   cannot originate from the warm mailboxes.
4. Pulled the 7/25 thread from the mailbox (read-only Graph); it was absent
   from comms-log.

### Decision + deliverables
1. Plan written and approved: `~/.claude/plans/brisken-refactored-hopper.md`
   (comparison table, phased architecture, open questions for Dirk, reply
   draft).
2. Comms-log backfilled with both 7/25 messages verbatim.
3. Reply draft staged: `context/drafts/outreach-engine-plan-to-dirk.md`
   (nothing sent).
4. Status file created: `status/p2-outreach-engine.md`; linked from
   `status/p2-lead-gen-general.md`.

---

## Key Decisions Made

### Build on Lead Desk (over Zoho-native / Instantly / scripts status quo)
- **Choice:** Lead Desk becomes the engine; canonical status store = its
  mailbox-grounded event log; Rome identity/tier stays sheet-authoritative in,
  sheet status cols become an upgrades-only projection out; suppression = a
  monotone union in Lead Desk.
- **Rationale:** ~90% already built and mailbox-true. Zoho Cadences is
  structurally disqualified (Zoho-server origin, relay-ineligible, edition
  unknown, read-only token). Instantly fails the subscription test: the build
  path (guarded Graph sends from two warm mailboxes at ≤40/day) does not fail
  at our volume; re-entry trigger = bounce >~3% / reply collapse / cold-farm
  build-out.

### Phasing around the imminent waves
- **Choice:** T3 touch-2 (~08-02) goes script path (in-thread replies as Dirk;
  engine has no createReply and no Dirk auto-send). Phase 1 (~08-04→08-15)
  hardens + arms the engine (guard port incl. the drift-hole fix,
  `start_not_before`, per-wave Dirk-draft release action, backup, watched
  drill). GA non-responder follow-up (~08-18/25) is the first engine-native
  wave.
- **Rationale:** days-away wave + never-fired sender = wrong first workload;
  vacation returns set the natural window for the first automated wave.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `~/.claude/plans/brisken-refactored-hopper.md` | created | The approved decision-ready plan |
| `workspace/clients/brisken/context/comms-log.md` | appended | 7/25 thread backfill (both messages verbatim) |
| `workspace/clients/brisken/context/drafts/outreach-engine-plan-to-dirk.md` | created | Reply draft for user to shape (not sent) |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | created | Engine workstream status-of-elements |
| `workspace/clients/brisken/status/p2-lead-gen-general.md` | edited | Workstream index row + updated bump |

---

## Current Status

Engine decision locked, nothing armed: kill_switch=1, no real engine send ever
fired, all sends still behind two-gate + per-wave owner yes + watched drill.
Rome: GA 19 sent 07-27; SAP-15 + 4 in-thread held with Dirk; T3 touch-2 due
~08-02. Reply draft awaiting the user's shaping + send. brisken platform ops:
unknown plan (no platform section in infrastructure.yaml for this workstream;
Fly-hosted lead-desk).

---

## Next Steps

1. User: shape + send the reply to Dirk (draft staged).
2. Phase 0 (before 08-02, own session): T3 non-responder list from mailbox
   truth + in-thread drafts for Dirk's look; per-wave yes to send.
3. On order: Phase 1 build (guard port + start_not_before + release action +
   backup), then schedule the watched send drill with Dirk.
4. Ship the register archive split (`checkpoint_scaffold.py archive-register`)
   in its own docs PR — register is 413 KB, advisory standing.

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/brisken-refactored-hopper.md` (the full plan)
- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `workspace/clients/brisken/automations/lead-desk/BLUEPRINT.md`

### Open Questions
- Dirk (5): sender policy for his-name waves (per-wave release vs per-mail
  clicks); Instantly-off confirm; Zoho-as-record confirm + optional read-scope
  grant; drill scheduling; GA follow-up week (08-18 vs 08-25).

### Working Notes
- Drift hole evidence: `approve_campaign` hashes contact_ids only
  (cadence.py); `claim_sends` reads `e["email"]` live; `migrate.py` sheet-sync
  overwrites email (only next_step/next_step_due app-owned). Fix = pin
  (contact_id, email) pairs at approval + claim-time re-assert.
- Zoho probe method: token mint returns the scope string verbatim; org/users
  401 so edition is UNVERIFIED (do not assert Enterprise).
- T3 touch-2 must be in-thread from Dirk's mailbox; engine lacks createReply —
  do not route it through the engine.
- Graph thread pull: aggregate `/messages` misses outbound; Sent Items
  per-folder worked for the 7/25 send.

### Reference Materials
- `docs/2026-07-27 - Brisken Rome GA Post-Event Wave/Checkpoint.md`
- `.scratch/ga_send_wave.py` (guard pattern being ported)
- `rule_brisken_graph_send_by_id.md`

---

## How to Continue

`/comd_resume brisken`, read the plan file, then either Phase 0 (T3 touch-2
prep) or Phase 1 (engine hardening) on explicit order. Dirk's answers to the
five open questions gate the release-action design and the drill date.

---

## Strategic Feedback

### What Worked Well This Session
- Three parallel explorers + one adversarial Plan agent found two code-level
  defects (drift hole, createReply gap) that a design-from-memory session
  would have missed; the plan's phasing changed because of them.

### Suggestions
- The 7/25 client reply sat un-logged for 4 days; consider a periodic
  mailbox→comms-log ingestion sweep (the capture worker already reads both
  mailboxes; a weekly "unlogged client-thread" report would close this class).

### System Health
- Autonomy: 0 human interventions (plan approval was the one designed gate).
- Friction register at 413 KB — archive split pending its own docs PR.
