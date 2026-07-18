---
project: brisken
workstream: p2-rome
group: lead-generation
spec: p2
state: active
updated: 2026-07-17
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
| Post-event follow-up | in-progress | Sequencing set (owner 2026-07-17): T3 + GA initial waves go out first, then per-tier follow-up on every contact that did not respond to their tier's outreach | Get T3 + GA waves out, then draft per-tier non-responder follow-up | T3 + GA sends | Lead Desk board (brisken-lead-desk.fly.dev) |
| GA cohort in Lead Desk | active | 40 GA contacts moved from "Held" to the active pipeline (owner 2026-07-17); they receive their own GA outreach wave | Prepare the GA wave | none | `automations/lead-desk` migrate.py `is_held` change |
| Partner/SAP personal outreach (17) | in-progress | 16/17 mailbox-verified covered (10 notes + ICD-cluster send 07-12, Sharandakov call 07-14); Planner card synced 07-17; replies: Mehlkopf, Szczecina | Dirk sends the last one: Kulkarni draft in his Drafts since 07-13 | Dirk send | Planner "17 Rome partner and SAP contacts"; `deliverables/lead-generation/rome-2026/dirk-send-pack/partner-sap-outreach.md` |
| Ashok (Accenture) MDH referral | in-progress | Dirk's 07-13 re-connect verified + synced to Lead Desk and sheet 07-17; note-brief now a threaded reply in his Drafts; Ashok back from OOO, silent | Dirk rewrites + sends the threaded reply; watch thread for Ashok | Dirk send | memory `project_brisken_ashok_accenture_referral`; Planner card |

## Open decisions / gates

- Publish go-ahead + sending identity (group gates 1-3 in `status/p2-lead-gen-general.md`).

## Pointers

- Deliverables: `deliverables/lead-generation/rome-2026/`
- Context: `context/lead-generation/Rome-Event/`, `context/lead-generation/TA Cook 2026/`
