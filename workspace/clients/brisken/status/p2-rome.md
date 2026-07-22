---
project: brisken
workstream: p2-rome
group: lead-generation
spec: p2
state: active
updated: 2026-07-22
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
| Post-event follow-up | in-progress | T3 touch-1 SENT 2026-07-21 (24 emails from Dirk via Graph, TreasuryCentral pptx + skim-link, Zoho-filed, 24/24 in Sent Items); GA wave still to go, then per-tier non-responder follow-up | T3 touch-2 to non-responders ~2026-08-02 then stop; prepare GA wave; draft per-tier follow-up | GA sends | wave: context/lead-generation/rome-t3-wave-rebuilt.md |
| GA cohort in Lead Desk | active | 40 GA contacts moved from "Held" to the active pipeline (owner 2026-07-17); they receive their own GA outreach wave | Prepare the GA wave | none | `automations/lead-desk` migrate.py `is_held` change |
| Partner/SAP personal outreach (17) | in-progress | 16/17 mailbox-verified covered (10 notes + ICD-cluster send 07-12, Sharandakov call 07-14); Planner card synced 07-17; replies: Mehlkopf, Szczecina | Dirk sends the last one: Kulkarni draft in his Drafts since 07-13 | Dirk send | Planner "17 Rome partner and SAP contacts"; `deliverables/lead-generation/rome-2026/dirk-send-pack/partner-sap-outreach.md` |
| Ashok (Accenture) MDH referral | in-progress | Dirk's 07-13 re-connect verified + synced to Lead Desk and sheet 07-17; note-brief now a threaded reply in his Drafts; Ashok back from OOO, silent. Dirk chased 07-21 asking Ashok to confirm the ~40-45 central-bank integration scope + decision status | Watch thread for Ashok's reply | Ashok reply | memory `project_brisken_ashok_accenture_referral`; Planner card |
| Master-sheet `email outreach_status` accuracy | done | Reconciled against BOTH mailboxes (all folders, from 06-01, alt-emails + calendar) 2026-07-21/22; 29 cells corrected and verified (28 + Georgiou), 0 unintended changes. Earlier post-event-only pass produced 9 FALSE downgrades (meetings/during-event replies invisible) - retracted | None; re-run the same method after each wave | none | method recorded in memory `feedback_brisken_outreach_truth_is_mailbox` |
| Graph app-only WRITE on the MARKETING site | done | `Sites.ReadWrite.All` (Application) granted + admin-consented 2026-07-21. App-only workbook PATCH returns 200; no browser/delegated token needed. Was first added as *Delegated*, which client-credentials silently ignores | Use the workbook range API for all future sheet writes | none | memory `feedback_brisken_outreach_truth_is_mailbox` (write section) |
| Lead Desk stale `next_step` (Asako/NYK) | in-progress | Root-caused + fixed: a next_step authored before a reply was surfaced as the board action ("No reply yet..." next to a captured reply). PRs #314 + #316 MERGED to main (new `next_step_at` col, v5 migration, staleness rule in `recommended_action`/`is_dangling`) | DEPLOY to brisken-lead-desk.fly.dev (Band-3, owner order) - fix is NOT live until then | owner deploy order | `automations/lead-desk`; PRs #314/#316 |

## Open decisions / gates

- Publish go-ahead + sending identity (group gates 1-3 in `status/p2-lead-gen-general.md`).

## Pointers

- Deliverables: `deliverables/lead-generation/rome-2026/`
- Context: `context/lead-generation/Rome-Event/`, `context/lead-generation/TA Cook 2026/`
