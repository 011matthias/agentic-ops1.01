# Session — brisken p1 recon: the matcher-v2 call

**Date:** 2026-07-23
**Scope:** brisken / expense-reconciliation (p1) · matcher
**Branch:** `client/brisken/matcher-v2-eval` (code, PR #418) · `docs/recon-matcher-v2-ledger` (this ledger)

## The question
Build matcher v2 (vendor/context signals) for the ~14 date+amount-inseparable
`no_charge` coincidences left by `brisken-recon-tuning-v1`, or accept them as
review-queue noise? v2 only if a signal generalizes without regressing the
55/95 deterministic wins or the 0-wrong floor, measured on the SAME pinned
scorer + guard.

## The call: YES — but the winning signal is CARD, not vendor
The 14 were not review noise; they were silent false-positive AUTO-matches
(-2.0 each). A generalizing signal exists, so build it — as a structural gate,
not a config edit and not a vendor matcher.

## What decided it (measured on the pinned scorer fixture, all 6 bundles)
- The 14 concentrate entirely in the travel months (9 Rome, 2 Copenhagen, 3
  Lisbon); the 3 BRL admin months are clean. Every one is a receipt whose Zoho
  `payment_mode` names a card ABSENT from the statement, coincidentally
  base-matching an unrelated same-vendor / same-day charge.
- **Vendor is NOT separable:** 26/55 true deterministic pairs score < 0.2
  vendor-sim (banks truncate foreign strings to aggregators); some coincidences
  score 1.00. A vendor gate loses more true pairs than it kills at every
  threshold. Vendor v2 = dead, exactly the killer risk the brief named.
- **Card is a clean split:** 14/14 coincidences `card_score` 0.0, 0/55 true
  pairs. Not circular: `payment_mode` is an independent Zoho field, never an
  E1-E4 labeling tier.

## The fix
A structural gate in `matching/deterministic.py`: a clean bilaterally-unique
`FX_BASE_AMOUNT`/`FX_REFERENCE` pair also forfeits auto-resolution when the
charge's card and the receipt's `payment_mode` name different cards
(`card_signal == 0.0`, behind the `card_scoping` trust switch). Demotes to
`FX_JUDGMENT`, never drops. Same class as PR #405's uniqueness gate; NOT a
`/comd_optimize` run, because the gate is binary and there is nothing to
hill-climb — the "not a hand-tuned edit" discipline is met by measuring a
structural change on the LOCKED scorer/guard.

## Result (pinned scorer + guard, both untouched)
- train 31.5 -> 49.5, all-6 37.2 -> 65.2; determ_ok 55/95 UNCHANGED (0 recall
  cost); determ_wrong 0; nc_matched 14 -> 0; guard 4/4 PASS (holdout 5.7 ->
  15.7).
- Full module suite 783 green + 3 new pinning tests. Hosted parity holds
  (defaults-only score == tuning-file score, 65.2), so the fix ships to the
  src-only Docker image with no config change.

## Residual (open)
Handles the dominant absent-card `no_charge` variety. A future `no_charge`
receipt paid on a PRESENT card whose charge is outside the export window keeps
`card_score` 1.0 and stays review noise. The ADOBE/ANTHROPIC receiptless-charge
FX-false-pairing is a distinct open WS3 item.

Detail: `automations/expense-reconciliation/ANNEALING.md` (Resolved 2026-07-23)
+ the p1 status WS3 rows.
