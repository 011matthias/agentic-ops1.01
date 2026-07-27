---
project: brisken
workstream: p2-outreach
group: lead-generation
spec: p2
state: active
updated: 2026-07-27
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Outreach (p2)

The outbound motion: borrowed-trust (AEO answer pages + a published research
report) under a precision-LinkedIn tail. Shared lead-gen context is in
`status/p2-lead-gen-general.md`.

## 2026-07-25 — cold-email TRIAL reopened via Cristian Fuze (getken)

Matthias reopened cold email as a scoped TRIAL run by Cristian Fuze on getken
(834-lead AI-qualified pool, sends from a generic domain). This reverses, for a
measured trial only, the 2026-06-12 retirement (Brisken's own ~150 mailboxes /
~2M cold emails returned 0 leads). Metric: meetings booked; judged on results.
NOTE: no Dirk sign-off for the trial is logged here; Matthias committed to
launch in his 2026-07-22 email to Cristian, so the decision is treated as made.

Launch gated on two Matthias deliverables (Cristian's 2026-07-22 email): (1)
suppression list, (2) product naming (TreasuryCentral lead / OnePilot platform).
Cristian confirmed naming done 2026-07-25 and is waiting on the suppression list.

**Definition SET BY DIRK 2026-07-27** (email to Matthias): suppress a pool
contact if they are IN THE CRM or IN THE MAILBOX ("if they are not in our CRM,
and maybe also not in my e-mail box then we should be fine"). This supersedes
the earlier customer-only Standard cut.

**Suppression list REBUILT 2026-07-27 to Dirk's rule**, read-only, deduped to
2,377 emails + 77 customer domains at
`context/lead-generation/outreach-assets/suppression-list.csv` (cols
value,kind,reason,source). Verified: 0 dupes, 0 malformed, 0 brisken.com leak.
- crm (1,396): every live Zoho CRM Contact email (not just customers).
- active-thread (907): both-mailbox Graph 90d scan (inbound aggregate + Sent
  Items), external human counterparties in the mailbox but not in the CRM.
- opt-out (73) + bounce (1): Rome master Tier=STOP/ANON + stop=X +
  sponsor_opt_in=No; send-log fails.
- customer domains (77): Zoho customer companies (Active/Churned/Blocked),
  domain-level so the whole company is suppressed.
- LIMITATION: Zoho **Leads** module returns 401 (the refresh token's OAuth
  scope covers Accounts/Contacts, not Leads). If Brisken keeps prospects as
  Leads, those are NOT covered; USER ACTION = re-auth the Zoho app with
  ZohoCRM Leads read scope, then rebuild.
- GAP (carried): no local Instantly unsubscribe export; historical opt-outs
  from the old ~2M-send lists are NOT included (matters only if the 834
  overlaps those lists).
- Rebuild: `.scratch/build_suppression_lean.py` (Graph result cached in
  `.scratch/active_threads.json`; Zoho pulled live each run).
- SENT 2026-07-27 to cristian@getken.ai (Graph, reply-in-thread "RE: Cristian
  Out of Office", CSV attached). VERIFIED in Sent Items (isDraft=false,
  hasAttachments=true). Ball now in Cristian's court: dedup the 834, confirm
  the count, launch. Cristian also uses cristian@ken.com.co on a separate thread.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Shadow-integration report (issue #1) | done | 71% / N=41; schema-marked; validated | Publish on a Brisken property | Dirk publish decision (gate 3) | `deliverables/lead-generation/aeo-outreach/shadow-integration-report.html` |
| AEO Q&A cluster pages (MDH, Remittance, Migration, Bank Fee) | done | FAQPage-schema-marked; validated | Publish + Store-review seeding | Dirk publish decision | `deliverables/lead-generation/aeo-outreach/` |
| LinkedIn page rewrite + 4-post batch | done | Ready for Dirk look | Approve + go live | Dirk page go-live (gate 4) | `context/lead-generation/outreach-assets/linkedin-reposition.md` |
| Research channel (series + hub + AEO wiring) | done | Spec ready | Stand up on publish | Publish decision | `context/lead-generation/outreach-assets/research-channel.md` |
| Forwardable proof (Calvin / Remittance) | in-progress | Best forwardable proof asset kept | Build the forwardable clip brief | none | `deliverables/lead-generation/aeo-outreach/mdh-forwardable-colgate.html` |
| Cold-email sending infra | paused | Retired as a channel 2026-06-12 | None (dormant) | none | `project_brisken_outreach_domains` memory; spec p2 last_changes |

## Open decisions / gates

The gates that block THIS workstream (sending identity + green-light for the
LinkedIn motion, publish-the-research to warm the outreach, SAP partner-cockpit
access for the badge + Terms-link fix) are group gates. Current state is
maintained in `context/lead-generation/dirk-go-live-sheet.md` (indexed in
`status/p2-lead-gen-general.md`), not restated here.

## Pointers

- Deliverables: `deliverables/lead-generation/aeo-outreach/`
- Context: `context/lead-generation/outreach-assets/`
- Gate index: `context/lead-generation/dirk-go-live-sheet.md`
