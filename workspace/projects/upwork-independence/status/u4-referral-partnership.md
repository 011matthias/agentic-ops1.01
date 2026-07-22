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
validation: the enumerable seed network today is ~4-6 named plausible
referrers vs the model's implied ~4 warm intros/month — that gap IS the
referral-supply question gtm-v2-confirm flagged. Scope per owner decision
2026-07-22: **ledger + offer definition only; no outbound drafts** until a
separate go.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Partner ledger | not-started | First artifact: enumerate every named plausible referrer — Dirk's SI ecosystem (Accenture, LeverX, SINVA, Target Networks, ICD/Tradeweb), Gurmej, Jochen, warme-wimmer, past Upwork relationships, future subcontractors | Write `../context/referral-ledger.md` | — | recon: ~4-6 named today |
| Offer definition | not-started | Commission / reciprocity / none; one-page asset shape decision | Define after ledger | — | — |
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
