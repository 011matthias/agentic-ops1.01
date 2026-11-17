# Checkpoint: Upwork Email Marketer Call Prep

**Date:** 2026-11-09
**Status:** Call prep delivered 2026-11-05; call outcome not yet logged

---

## Summary
Built a live-call crib sheet for an Upwork "Email Marketer" posting (part-time, audience growth and engagement through targeted campaigns), with every stat traced to the 2026-11-05 outbound case study (#1725) or a campaign memory.

---

## What Was Done This Session
### Call prep (2026-11-05, prospect was already on the line)
1. Pulled the stats from `workspace/projects/platform/upwork-agency/assets/outbound-case-study.html` plus the Meji warm-rebuild, Mimecast-bounce and Brisken Lead Desk memories.
2. Delivered the 20-second intro, four stat blocks, the gaps to be honest about, and five discovery questions in chat. Nothing was written to the repo.

---

## Key Decisions Made
### Clients stay anonymized on the call
- **Choice:** "UK events company" / "treasury-software company", matching the case study.
- **Rationale:** The case study already set that convention, and a prospect call doesn't need client names.

### Name the measurement gaps up front
- **Choice:** Told the owner to say plainly that there are no open/click rates (tracking off for deliverability) and no newsletter-growth numbers.
- **Rationale:** The posting reads like newsletter/audience work. The records are outreach and reactivation, so an invented engagement number would be a B4 violation said aloud.

---

## What Did NOT Work (and why)
None

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `docs/2026-11-09 - Upwork Email Marketer Call Prep/Checkpoint.md` | created | this checkpoint |

---

## Current Status
- The crib sheet was delivered before the call, and the owner confirmed they were free right then (Upwork thread, 2026-11-05 18:33).
- No debrief yet: rate, hours and next step are all unknown.
- The `platform` project has no `infrastructure.yaml` and no comms-log, so there is no ops status to report.

---

## Next Steps
1. Debrief the call: was it a fit, were rate and hours discussed, what's the next step. If the lead advances, record it as a project memory the same way the 2026-11-04 VossMoos lead was.
2. If they ask for proof, send `outbound-case-study.pdf` (same folder as the HTML). It was built for Upwork attachments.

---

## Context for Next Session
### Files to Read First
- `workspace/projects/platform/upwork-agency/assets/outbound-case-study.html`

### Open Questions
- Is the prospect's work newsletter/nurture to opted-in subscribers, outbound to new leads, or both? This decides how well the outreach record transfers.

### Working Notes
Sourced email-marketing stats, reusable for the next email/outbound proposal without re-deriving:
- **Mimecast bounces (case study):** 128 cold first emails, all NeverBounce-valid. Bounce rate by mail server: Mimecast 91% (10/11), Microsoft 1% (1/80), Google 0/18, Proofpoint 0/6. An MX pre-filter held out 12 leads in October and 63 in November.
- **Reply tracking (case study):** 62 contacted, 12 replied per the mailboxes, 2 per the log. Fixed with a daily all-folder inbound scan; out-of-office replies can't move a contact's stage.
- **Warm list (memory project_meji_warm_rebuild_d1):** 967/983 (98.4%) matched to the booking DB as real past customers. 84% booked 2023+. Segmented 41 repliers / 942 non-repliers into a 4-touch reconnect sequence in the owner's voice.
- **Seasonality (memory project_meji_volume_forecast):** 11 years of enquiry data; August to October = 61% of annual intake.
- **Send hygiene (rule_brisken_graph_send_by_id):** 19 approved emails sent by ID, 19/19 verified in Sent, and the 21 unrelated drafts in the same folder left untouched.
- **Lead Desk (memory project_brisken_lead_desk):** 337 contacts, replacing ~9 fragmented stores; spreadsheet overstated sends ~5x (199 vs ~38). The 337 is the 2026-07-16 figure, so re-read it live before quoting it again.

### Reference Materials
- `workspace/projects/platform/upwork-agency/assets/outbound-case-study.pdf`
- `docs/2026-11-05 - VossMoos Call Prep and Debrief/Checkpoint.md` (same session shape)

---

## How to Continue
Ask the owner how the call went, then record the result: a project memory if the lead is live, nothing if it's dead.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the case study shipped the day before as the primary source. It already held the figures anonymized and checked, so the brief went out after four tool calls while the prospect was waiting.

### Suggestions
- Keep a single sourced "pitch facts" file per service line (outbound, recon, automations) under `workspace/projects/platform/upwork-agency/`. Each live-call prep currently re-assembles the numbers from memories, and memory figures go stale (the Lead Desk 337).

### System Health
- The mandatory session header was skipped again, this time under live-call pressure. That's the fifth missed-session-header recurrence, and the 2026-10-29 infrastructure-deferred row (a Stop-event header check) is still unbuilt.
- Autonomy: 0 human interventions (fully autonomous session).
