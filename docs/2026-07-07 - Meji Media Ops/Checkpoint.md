# Checkpoint: Meji Media Ops (P2 Send, Referral Sourcing, Weekly Report, P1 Ramp)

**Date:** 2026-07-07
**Status:** P2 first batch complete + P2B replenished; referral list screened (pre-reveal); two client drafts final; P1 warm ramped.

---

## Summary
Ran the Meji P2 corporate-cold first-batch send end to end (reveal → NeverBounce → load → activate), diagnosed the bounce spike to Mimecast specifically, sourced + website-screened a new referral-partner list (250 agencies), built a client-facing weekly report + a list-depletion layer into the review engine, and ramped the best-converting warm campaign (P1) that was starved by a single sending cap.

---

## What Was Done This Session

### P2 corporate-cold first batch (send + completion)
1. Revealed 252 emails via Apollo bulk_match (credit-probe-first), NeverBounce kept 154 (valid+catchall), formatted 128 (78 P2A + 50 P2B, 26 organisers held over the drip cap).
2. Deleted the 5 never-emailed old queued P2B leads; loaded 128 into paused P2A/P2B; B5 readiness audit green; activated both.
3. Batch completed by 2026-07-06: P2A 78 new → 68 delivered / 10 bounced (12.8%); P2B 50 → 41 / 1 bounced. Neither auto-paused (cumulative 2.9% / 3.8%).

### Bounce diagnosis (the headline finding)
4. Full-batch MX cross-tab: **Mimecast bounced 10/11 (91%); Proofpoint 0/6, Microsoft-direct 1/80, Google 0/18.** It is Mimecast specifically, not gateways broadly, and not pacing/seniority. NeverBounce cannot detect a gateway block.
5. Built `--mxfilter` pre-load gate into `meji_p2_batch_2026-07-01.py` (nslookup MX, flag Mimecast + no-MX). Saved/sharpened `reference_cold_email_gateway_bounces` memory.
6. Built + ran a background P2A bounce monitor (`.scratch/p2a_monitor.py`); it correctly detected campaign completion (status 3) after a mislabeled first alert, then was fixed to distinguish completed vs bounce-paused.

### P2B drip-two
7. Reconstructed the 26 held organisers, MX-classified them (20 safe / 6 risky), loaded the 20 MX-safe into active P2B (414 → 434), all fresh, 6-check pre-fire readiness green.
8. Held P2A from reload (owner decision): needs a new PAID Apollo pull and P2 cold is at 0 replies / 181 contacted.

### Referral-partner sourcing (NEW ICP — Gurmej request, comms Block 25)
9. Logged Gurmej's request verbatim (Block 25). Built `meji_referral_partners_sourcing_2026-07-07.py`; pulled 250 Midlands event agencies (1-50 staff first) from a 1,531 universe.
10. Ran a 20-agent Workflow that website-screened all 250: 13 competitors (own shared Christmas parties), 19 no-site, 218 partners; tiered (22 venue-finders, 71 adjacent, 125 full-service inc. 23 conflicted); flagged 4 past M&M-customer warm doors.

### Review engine + weekly report
11. Added **layer L (list-depletion runway)** to `meji_campaign_health_check.py`: fresh-to-first-touch, ~new/day, runway days, DEPLETED / ≤3d action items.
12. Added `--client-report` mode (outcome-first structure → `context/drafts/weekly-report-{end}.md`). Drafted edition 1 for Gurmej with live data (validator-clean).

### P1 warm ramp
13. P1 (best converter: 14 replies + 5 opps / 739 contacted) was starved: 327 fresh leads first-touching at ~1.4/day because the single warmed mailbox + campaign were both capped at 40/day (eaten by follow-ups). Owner authorized ramp; raised both to **90/day** (PATCH accounts + campaign), verified. Clears the 327 in ~1-2 weeks.

### Comms drafts
14. Referral-partner reply draft (with our proposition; warm-list bullet upgraded to report the ramp as done; clearer plain-language rewrite; references the attached weekly report + the June hours ask). Excluded referral work from the weekly report per owner (just started, payoff unknown).
15. Reworded Matthias→Gurmej weekly-hour-cap message (dropped the apology, neutral fact + soft request).
16. Saved `feedback_value_radar_posture` memory (owner directive: sweep each client session for high-value action; make delivered value visible).

---

## Key Decisions Made
### Mimecast is the bounce cause, not gateways broadly
- **Choice:** Pre-filter Mimecast (and no-MX) domains before load; keep Proofpoint/Microsoft/Google.
- **Rationale:** 91% Mimecast bounce vs ~0% elsewhere across 128 sends; NeverBounce-valid can't catch it.

### P1 ramp to 90/day, not higher
- **Choice:** 2.25x on the single warmed mailbox (warmup 98, 0.4% bounce).
- **Rationale:** Warm re-engagement to known contacts is lowest-risk; clears backlog before season without shocking deliverability. Only one working warm mailbox exists (3 `.co` are NXDOMAIN-dead), so further step-up needs a new warm domain.

### Referral work excluded from the weekly report
- **Choice:** Report stays at the standing 8h/week and the campaign pieces; referral covered in the covering message.
- **Rationale:** Owner — it just started, scope/payoff unknown; don't bank hours or tout an unproven channel.

### P2A held from reload
- **Choice:** No new paid pull for P2A until P2 shows a reply signal or copy is reworked.
- **Rationale:** 0 replies / 181 contacted; spend before signal is unwarranted.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/analysis-scripts/meji_p2_batch_2026-07-01.py` | Modified | reveal + format + `--mxfilter` stages |
| `context/analysis-scripts/meji_nb_verify.py` | Modified | `--file` input mode |
| `context/analysis-scripts/meji_campaign_health_check.py` | Modified | layer L (runway) + `--client-report` |
| `context/analysis-scripts/meji_referral_partners_sourcing_2026-07-07.py` | Created | new referral-partner ICP pull |
| `context/pilot-routing.md` | Modified | P2 activation, completion, P2B reload, P1 ramp |
| `context/comms-log.md` | Modified | Block 25 (Gurmej referral request, verbatim) |
| `context/drafts/weekly-report-2026-07-07.md` | Created | client weekly report (referral excluded) |
| `context/drafts/referral-partners-reply-2026-07-07.md` | Created | referral reply + proposition |
| `context/p2/*.json`, `context/referral/*.json` | Created | reveal/NB/screen provenance + load inputs |
| memory: `reference_cold_email_gateway_bounces.md`, `feedback_value_radar_posture.md`, `MEMORY.md` | Modified | Mimecast lesson + value-radar posture |
| `.scratch/p2a_monitor.py` (+log) | Created | ephemeral P2A bounce monitor |

All Meji files are under the gitignored `context/`; nothing to commit.

---

## Current Status
- **P2A:** completed (0 fresh), held from reload. **P2B:** active, 20 fresh loaded 2026-07-07. **P3:** active, ~232 fresh, ~8-day runway. **P1 warm:** ramped to 90/day, clearing 327 backlog in ~1-2 weeks (0.4% bounce).
- **Referral:** 250 pulled + all screened; 218 partners, 173 with email on file; awaiting the ~173-credit reveal go.
- **Drafts:** weekly report + referral reply both final and validator-clean, awaiting Matthias to send; hours line needs Matthias's confirmation.
- No `platform` section in Meji infra (Instantly/Apollo-driven, not a Make/n8n platform build) — no ops line needed.

---

## Next Steps
1. On owner go: Apollo reveal the ~173 screened referral partners → NeverBounce → Mimecast MX-filter → build the tiered working sheet.
2. Send the two drafts (Matthias) after confirming the hours (8 ongoing + any referral time he wants counted).
3. P3 Christmas cold: stage the 3-city top-up before ~8-day depletion.
4. Corporate P2 re-entry: rework copy for the September buying window (P2A stays held until then).
5. Watch P1 warm bounce as it ramps at 90/day (a further step-up needs a second warm domain).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/context/pilot-routing.md` (canonical routing + all 2026-07 changes)
- `workspace/clients/meji-media/context/drafts/weekly-report-2026-07-07.md` + `referral-partners-reply-2026-07-07.md`
- `workspace/clients/meji-media/context/referral/referral-partners-2026-07-07-screened.json` (tiered screen output)
- `workspace/clients/meji-media/context/comms-log.md` Block 25

### Open Questions
- Reveal the ~173 referral partners now, or send the 250-name list first? (Owner gate pending.)
- Exact hours to book for Meji this week (operator data; not queryable).

### Working Notes
- Apollo free/redacted search on this key returns company name + person title + first name + `has_email` flag ONLY; domains/emails/last-names/employee-counts require the paid bulk_match reveal. So the referral competitor site-screen had to run on NAMES (via web search) pre-reveal.
- Instantly `esp_code` on a lead = recipient ESP identity (999 = behind-gateway like Mimecast, 2 = Microsoft), NOT an SMTP code.
- Set mailbox/campaign daily_limit via `PATCH /accounts/{email}` and `PATCH /campaigns/{id}` with `{"daily_limit": N}`.
- P2A `status=3` = completed (all leads terminal), NOT auto-paused (that is `-2`).

### Reference Materials
- Referral site-screen workflow transcript: `subagents/workflows/wf_bcf3dc38-e7f/`
- Value-radar posture: `memory/feedback_value_radar_posture.md`

---

## How to Continue
Resume with `/resume meji-media`. The live send state is in `pilot-routing.md` (source of truth). The two client drafts are ready to send pending Matthias's hours confirmation; the one gated action is the ~173-credit referral reveal. Run `meji_campaign_health_check.py` for a fresh review (now includes the runway layer) or `--client-report` for next week's report draft.

---

## Strategic Feedback

### What Worked Well This Session
- The "value radar" directive turned the engagement from ticket-taking into proactive value-finding; it surfaced the P1 warm-list starvation (the single biggest near-term lever) that no single task asked about.
- The comms-critic agent caught a real credibility risk (a "40-50% warm reply rate" built from two n=10 weeks) before it reached an ROI-focused client.
- The 20-agent website screen turned an un-filterable spec ("exclude own-Christmas-party sellers") into a clean, evidence-backed exclusion.

### Suggestions
- The weekly report's hours line is the one number that can't be queried (no Meji timesheet). A lightweight Meji hours log (even a single tab in the existing tracker) would make the report fully self-generating and close the recurring ROI ask automatically.

### System Health
- The `agent-deferred` B1 turn-end cluster is still open (stop-b1-gate caught 2 more this session). The gate holds every time, so the harm is contained, but the generation-time phrasing reflex ("want me to…", "if you want…") persists across ~6 weeks. It is the one standing self-anneal that a rule/memory hasn't killed — worth a `/system-dev` look at whether the deferral reflex can be pre-empted at generation rather than caught at stop.
- Autonomy score: 3 human interventions this session (2 B1 turn-end deferrals auto-caught by the stop-gate; 1 client-prose clarity rewrite requested). Not elevated.
