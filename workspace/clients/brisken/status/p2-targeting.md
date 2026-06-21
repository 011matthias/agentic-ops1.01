---
project: brisken
workstream: p2-targeting
group: lead-generation
spec: p2
state: active
updated: 2026-06-20
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Targeting (p2)

The spine of the engine: a trigger-detection radar that surfaces accounts with
proven data-vendor pain (Bloomberg/Refinitiv/360T/FXall/OANDA/CME + SAP), ranked
into tiers, feeding the precision-LinkedIn cohort. List-building is autonomous
(seat granted); only the send waits on Dirk. Shared lead-gen context is in
`status/p2-lead-gen-general.md`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Targeting radar (spine) | in-progress | Trigger-detection radar defined | Vendor-tag + trigger-verify the JOB-signal accounts; rank into tiers | none | `context/lead-generation/targeting/targeting-radar.md` |
| Sales Nav recipes + Wave-1 lists | in-progress | Recipes + Wave-1 ready to build in-seat | Build the lists in-seat | none | `context/lead-generation/targeting/sales-nav-targeting.md` |
| Weekly sweep runbook | done | Cadence runbook written | Run on go-live | Green-light to contact | `context/lead-generation/targeting/weekly-sweep-runbook.md` |
| Named accounts (Colgate, Corteva) | in-progress | Colgate/Corteva tagged A1 | Build the MDH teardown + ABM 1-pager (named logos cleared) | none | `context/lead-generation/accounts/account-colgate.md` |
| Co-sell + vendor matrix (enabler pack) | in-progress | Parts 1-2 ready | Hand to Dirk as the parallel workstream | Dirk vendor relationships | `context/lead-generation/accounts/dirk-enabler-pack.md` |

## Open decisions / gates

- Green-light to contact (group gate 2): the seat is granted and list-building is
  autonomous; only pressing send on the Wave-1 lists waits.
- Which vendor relationships are live (gate 6): routes the warmest channels.

## Pointers

- Context: `context/lead-generation/targeting/`, `context/lead-generation/accounts/`
- Spine: `context/lead-generation/targeting/targeting-radar.md`
