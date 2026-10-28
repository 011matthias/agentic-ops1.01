---
project: brisken
workstream: p2-targeting
group: lead-generation
spec: p2
state: dormant
updated: 2026-09-24
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Targeting (p2)

The spine of the engine: a trigger-detection radar that surfaces accounts with
proven data-vendor pain (Bloomberg/Refinitiv/360T/FXall/OANDA/CME + SAP), ranked
into tiers, feeding the precision-LinkedIn cohort. List-building is autonomous
(seat granted); only the send waits on Dirk. Shared lead-gen context is in
`status/p2-lead-gen-general.md`.

**Dormant since 2026-07-22 (checked 2026-09-24).** No file under
`context/lead-generation/targeting/` or `accounts/` has changed since July, and no
other workstream reads this one: the campaigns moved onto the Lead Desk, whose
critical path is Dirk's September review packet (memory
`project_brisken_campaigns_fully_on_lead_desk`). The rows below are the July state,
not work in flight. The one live instruction was Dirk's 07-22 reply on the Nestle
list (row below): the filing half is done, the Zoho rename is not.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Targeting radar (spine) | in-progress | Trigger-detection radar defined | Vendor-tag + trigger-verify the JOB-signal accounts; rank into tiers | none | `context/lead-generation/targeting/targeting-radar.md` |
| Sales Nav recipes + Wave-1 lists | in-progress | Recipes + Wave-1 ready to build in-seat | Build the lists in-seat | none | `context/lead-generation/targeting/sales-nav-targeting.md` |
| Weekly sweep runbook | done | Cadence runbook written | Run on go-live | Green-light to contact | `context/lead-generation/targeting/weekly-sweep-runbook.md` |
| Named accounts (Colgate, Corteva) | in-progress | Colgate/Corteva tagged A1 | Build the MDH teardown + ABM 1-pager (named logos cleared) | none | `context/lead-generation/accounts/account-colgate.md` |
| Co-sell + vendor matrix (enabler pack) | in-progress | Parts 1-2 ready | Hand to Dirk as the parallel workstream | Dirk vendor relationships | `context/lead-generation/accounts/dirk-enabler-pack.md` |
| Nestle StratiFy list (S/4 hypercare) | parked by Dirk | 214 recipients, tiered, sent to Dirk 07-22. **His answer the same day** (Graph read 2026-09-24, Matthias's inbox): "maybe not a high value activity right now", file the list under the lists in SharePoint with a comment on where it came from and the analysis, change "Ortega" to "Dorta" in Zoho, and move on. So the LinkedIn enrichment is off. **Filed 2026-09-24** (owner yes): `MARKETING/60_Campaigns/05 - Lists/NESTLE STRATIFY LIST 2026-07/` holds the exact xlsx Dirk was sent (pulled from the 07-22 Sent Items attachment; downloaded back and cell-identical on all 3 tabs, 59/216/20 rows) plus a README on source, method and his ruling. **Zoho rename NOT done:** the contact still reads "Daniel Ortega" (id 1343217000029348091, @es.nestle.com, no account linked; no "Dorta" exists), and the CRM token carries only `contacts.READ` + `accounts.READ`, so the API cannot write it | Rename Ortega to Dorta in the Zoho UI (and link the contact to the Nestle account) | LIMITATION: read-only CRM token; Dirk's same reply says Matthias's Zoho CRM access still needs fixing | `context/lead-generation/nestle-stratifi-analysis.md` + `nestle-stratifi-contacts.csv` |

## Open decisions / gates

- Green-light to contact: list-building is autonomous (seat granted); only
  pressing send on the Wave-1 lists waits.
- The group gates that block THIS workstream (green-light, and which vendor
  relationships are live) are maintained in
  `context/lead-generation/dirk-go-live-sheet.md` (indexed in
  `status/p2-lead-gen-general.md`), not restated here.

## Pointers

- Context: `context/lead-generation/targeting/`, `context/lead-generation/accounts/`
- Spine: `context/lead-generation/targeting/targeting-radar.md`
