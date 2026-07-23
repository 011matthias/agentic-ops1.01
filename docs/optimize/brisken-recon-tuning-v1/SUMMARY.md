# brisken-recon-tuning-v1 — SUMMARY

Run: 2026-07-23, 7 rounds + baseline, mode converge, stopped on PLATEAU
(5 consecutive non-keeps). Best **31.5** train composite (baseline at
lock-on 30.8; pre-code-fix baseline 8.9). Guard (holdout floor 5.7,
no-new-holdout-wrongs, wrong-ceiling 17) passed on every scored round —
no round was discarded by guard; every discard was a score loss.

## What won

One lever kept: **`fx_base_amount_match_pct` 0.02 → 0.01** (r2, +0.7).
Tightening the clean base-amount threshold demoted a coincidental rival to
the review zone, which made a TRUE pair bilaterally unique and promoted it
to a deterministic match — the uniqueness gate converts precision into
recall. Final asset = PR #405 defaults + this one change.

## Dead ends

- **fx_date_window_days below 5** (r1: 2 → 29.4; r4: 3 → 30.6). Narrowing
  promotes uniqueness (+7 determ at window 2) but drops day-3..5 true
  pairs out of deferral entirely AND lets more no-charge coincidences
  become unique claimants (nc 9 → 12). Net negative at both settings.
- **fx_base_amount_match_pct 0.005** (r3 → 29.8). Too tight: sheds true
  cleans. The knee is bracketed: 0.005 loses, 0.01 wins, 0.02 loses.
- **fx_reference_match_pct 0.015** (r5 → 25.7, the worst round). The
  derived-median reference path NEEDS its 3% headroom — a month median
  deviates 1-3% from each receipt's own rate by construction.

## Sensitivities

- **fx_base_amount_review_pct is inert above 0.13** (r6: 0.18 scored
  identically — no fixture pairs live in the 13-18% zone). Not evidence
  for any particular value; revisit only with new labelled months.
- **blend_card_weight is inert at 0.10** (r7: identical score — every
  judgment-slot assignment on the fixture was already correct). The card
  signal stays priced at 0 by default; nothing pegged at a bound.
- The composite's precision half rests on the 46 no_charge labels; 9
  train no-charge receipts remain bilaterally-unique coincidences
  (-2.0 each) that (date, amount) alone cannot separate. Vendor/context
  signals are the next structural idea if this must shrink further.

## Per-tier honesty check (final asset, --split all)

E2 3/3, E3 55/92 deterministic; holdout E3 12/21 with 0 wrong — gains are
NOT confined to the train subset or to the E3-circular signal alone
(holdout is E1-rich and improved from 5.5 pre-code to 5.7 with 13/22
deterministic).

## Where the tuned values go

Per the plan's Phase 4: promote `fx_base_amount_match_pct=0.01` into the
`MatchingConfig` dataclass default (the Docker image ships only `src/`,
so the hosted app never reads this tuning file), acceptance test =
defaults-only score equals tuning-file score.
