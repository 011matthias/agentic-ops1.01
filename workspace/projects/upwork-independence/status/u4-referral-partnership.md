---
project: upwork-independence
workstream: u4-referral-partnership
group: uwi
spec:
state: active
updated: 2026-07-22
general_ref: status/uwi-general.md
---

# uwi / u4 — Referral partnership (+ the supply validation probe)

True from-zero build (0.154 effort, ~275h, pool 15 ASSUMPTION, conv 0.12
SOURCED, 3-mo ramp, zero cash). Doubles as the program's highest-value
validation: the ledger (written 2026-07-22) enumerates 7 first-degree
names collapsing to 5 independent sources, of which 3-4 are honest warm
referral supply, plus 5 second-degree names reachable only via Dirk —
vs the model's pool-15 with ~4 warm intros/month. The gap gtm-v2-confirm
flagged is confirmed at enumeration time. Scope per owner decision
2026-07-22: **ledger + offer definition only; no outbound drafts** until a
separate go.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Partner ledger | done | Written 2026-07-22: 7 first-degree names (Dirk, Jochen, Gurmej, Jess, Irina, Tobias, Dzmitry) = 5 independent sources; 5 second-degree SI-ecosystem rows via Dirk; 0 subcontractors. Pool-15 is ~3x the enumerable first-degree reality | Keep current as relationships change | — | `../context/referral-ledger.md` |
| Offer definition | done | Recommendation written: no upfront commission for the client network; defined post-conversion thank-you; Jochen routed to partnership/subcontract track (u7); commission reserved for arm's-length future partners | Owner call on the recommendation | owner | ledger §offer-definition |
| Asks (10-20, register A) | blocked | Drafting GATED by owner decision; ledger row-count alone already tests pool-15 plausibility | — | drafts gate | `rule_human_communication` §1 |
| Validation loop | not-started | Track named-referrer count, intro rate, intro->client conv vs pool-15/conv-0.12; falsified pool feeds a SCORER_LOCK_ALLOW re-pin PR + portfolio re-run | Metrics rows once asks begin | asks gate | `rule_optimize_loop` seams |
| Source attribution | not-started | Which client came from which channel/referrer — required to ever score channel actuals | Convention decision with first live channel | — | — |

## Open decisions / gates

- DRAFTS GATE: no outbound without a separate explicit go.
- Offer economics (commission vs reciprocity) — owner call, informed by ledger.

## Pointers

- Message-shape precedent (client work, transfers): Brisken partner-SAP
  outreach pack (1:1 personal note, single two-week nudge, no pitch);
  Ashok/Accenture referral-handling (`project_brisken_ashok_accenture_referral`).
- Model economics: leadgen-portfolio scorer lines 108-123.
