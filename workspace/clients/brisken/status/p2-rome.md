---
project: brisken
workstream: p2-rome
group: lead-generation
spec: p2
state: active
updated: 2026-07-20
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Rome 2026 (p2)

The event motion around SAP T&WCM in Rome (24-25 Jun): a landing page, a
one-pager, and a targeted invite list, plus the "SAP T&WCM Rome 24-25 Jun" CTA
woven into triggered-cohort outreach. Shared lead-gen context (vision, strategy)
is in `status/p2-lead-gen-general.md`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Rome 2026 landing page | done | Built (HTML + OG image + icon) | Host on a Brisken property | Dirk publish go-ahead | `deliverables/lead-generation/rome-2026/brisken-rome-2026-landing.html` |
| Rome 2026 one-pager | done | Built (md + pdf) | Use as the forwardable invite asset | none | `deliverables/lead-generation/rome-2026/brisken-rome-2026-onepager.pdf` |
| Invite company list | in-progress | Wave list assembled (xlsx) | Tier + verify against the radar | none | `deliverables/lead-generation/rome-2026/brisken-rome-2026-invite-companies.xlsx` |
| Event CTA in outreach | in-progress | CTA defined for the triggered cohort | Wire into LinkedIn copy on go-live | Dirk sending identity | `specs/1-spec/p2-bant-lead-generation.md` next_steps |
| Post-event follow-up | in-progress | T3 REBUILT: 24 contacts (25 minus no-show Nedhal), 3 fixes applied (tier tag stripped from subject, no-shows dropped, same-company copy de-duped A1/A2/A3/B/B2) + short AI-focused "what Brisken does" line added to touch 1; QA-passed (no em-dash/tag/placeholder/banned words; booth variant only for 3 verified visitors). 2-touch sequence set (touch 1 day 0; touch 2 non-responders ~day 12; stop-on-reply, no touch 3). Copy in `context/lead-generation/rome-t3-wave-rebuilt.md`. Approval copy (placeholders) SENT to Dirk 07-20 17:02 (matthias->dirk). One-liner REVISED 07-20 per Dirk's TreasuryCentral slide-2 comments (dropped "command center"/"your live SAP data", "trading"->autonomous trading, +orchestration/process automation/governance) across all 24 emails; revised copy re-sent to Dirk 07-20 18:48 (Graph, confirmed Sent Items). Dirk replied "much better ... now keep it separate": SECOND revision applied across all 24 emails to his 3-pillar model (TreasuryCentral = treasury workspace/people+AI agents orchestrating the process; OnePilot's two applications underneath = market data governance + autonomous trading; dropped the flat task-list that made the 2 apps hang); full-sequence lay-out re-sent to Dirk for final approval 07-20 21:47 (Graph, confirmed Sent Items). Still awaiting his "approved". T2 kept in box: Kulkarni + Georgiou (finished), Ashok (brief). Untiered kept: Gupta, Tejay (briefs). GA never drafted; H5/T1 follow-up never drafted | Await Dirk "approved"; then load + send touch 1 from his Outlook (invasive, per-send readiness) | Dirk approval | Graph send verified in Sent Items |
| GA cohort in Lead Desk | active | 40 GA contacts moved from "Held" to the active pipeline (owner 2026-07-17); they receive their own GA outreach wave; no GA batch in Dirk's Drafts as of 07-20 (not yet loaded) | Prepare + load the GA wave | none | `automations/lead-desk` migrate.py `is_held` change |
| Partner/SAP personal outreach (17) | in-progress | 16/17 mailbox-verified covered (10 notes + ICD-cluster send 07-12, Sharandakov call 07-14); Planner card synced 07-17; replies: Mehlkopf, Szczecina | Dirk sends the last one: Kulkarni draft ("T2 After Rome: Nestle and the next cases") in his Drafts, still `isDraft=true` at Graph read 07-20 (unsent) | Dirk send | Planner "17 Rome partner and SAP contacts"; `deliverables/lead-generation/rome-2026/dirk-send-pack/partner-sap-outreach.md` |
| Ashok (Accenture) MDH referral | in-progress | Dirk's 07-13 re-connect verified + synced to Lead Desk and sheet 07-17; note-brief now a threaded reply in his Drafts ("RE: Worth fifteen minutes at Booth #2", still `isDraft=true` at Graph read 07-20, unsent); Ashok's 07-13 re-connect got only an OOO auto-reply, then silent | Dirk rewrites + sends the threaded reply; watch thread for Ashok | Dirk send | memory `project_brisken_ashok_accenture_referral`; Planner card |

## Open decisions / gates

- Publish go-ahead + sending identity (group gates 1-3 in `status/p2-lead-gen-general.md`).

## Pointers

- Deliverables: `deliverables/lead-generation/rome-2026/`
- Context: `context/lead-generation/Rome-Event/`, `context/lead-generation/TA Cook 2026/`
