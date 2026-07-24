---
tag: brisken-recon-tuning-v1
project: brisken
goal: >
  Maximize the expense-recon match-accuracy composite on the TRAIN split of
  the human-labelled month fixture (four 2025-26 months, 73 confirmed pairs:
  +1.0 deterministic-correct, +0.3 deferred-correct, -2.0 deterministic-wrong
  or no_charge false positive) by tuning config/match-tuning.json, WITHOUT
  regressing the two held-out 2024 months and without new held-out wrong
  matches. The remaining precision frontier at baseline: 14 bilaterally-unique
  no_charge coincidences auto-matching (-28), and 22 review-zone true pairs
  sitting at +0.3 that tighter/looser thresholds might trade against them.
scorer: tools/scorers/recon-match-accuracy.py
scorer_args:
  - workspace/clients/brisken/automations/expense-reconciliation/config/match-tuning.json
direction: maximize
assets:
  - workspace/clients/brisken/automations/expense-reconciliation/config/match-tuning.json
guards:
  - uv run tools/recon-accuracy-guard.py workspace/clients/brisken/automations/expense-reconciliation/config/match-tuning.json docs/optimize/brisken-recon-tuning-v1/holdout-baseline.json
guard_files:
  - tools/recon-accuracy-guard.py
  - docs/optimize/brisken-recon-tuning-v1/holdout-baseline.json
budgets:
  rounds: 12
  wall_clock_minutes: 180
  score_timeout_seconds: 300
  guard_timeout_seconds: 600
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 5
---

# Brisken expense-recon match-tuning v1

## Why this run

First optimize run on project `brisken` (prior-art check: none to inherit).
Phase 3 of the approved date+amount accuracy plan. The structural code work
landed first (scorer + guard #404; base-amount path, self-derived rates,
band-scoring fix, review-zone deferral, bilateral-uniqueness gate #405) and
moved train 8.9 -> 30.8 and holdout 5.5 -> 5.7 with zero wrong deterministic
matches. This run tunes the NUMBERS the structure exposed.

## Baseline (at lock-on)

Train composite 30.8 (determ_ok 41/73, determ_wrong 0, deferred_ok 26,
nc_matched 9). Holdout 5.7 (determ_ok 13/22, wrongs 5) — enforced as the
guard floor via holdout-baseline.json; total-wrongs ceiling 17 (14 + 3
slack).

## Action catalog (priority order)

1. `fx_base_amount_match_pct` / `fx_base_amount_review_pct` — the precision
   dial on the dominant (E3) evidence path. Tightening match_pct may shed
   nc false positives (-2.0 each) at the cost of true cleans (+1.0 each);
   the composite prices the trade directly.
2. `fx_date_window_days` — coincidences spread across the +-5-day window;
   true pairs cluster tight. Narrowing may cut nc_matched cheaply.
3. `fx_reference_rates` per pair (BRL:USD, EUR:USD) — explicit month rates
   vs the self-derived medians; the holdout guard forces generalization
   (a 2026-era global rate that hurts 2024 months dies at the guard).
4. `fx_reference_match_pct` / `fx_reference_review_pct`.
5. `fx_band_score_span_pct` + `fx_rate_bands` lo/hi tightening.
6. `date_exact_window_days` / `date_probable_window_days` /
   `amount_probable_tolerance_pct` (same-currency paths).
7. `blend_*` weights incl. `blend_card_weight` (now accuracy-bearing via
   the score-aware sort key).

## Fixed by declaration

`card_scoping` stays true (owner-set behavior). `fx_self_derived_rates`
stays true (structural decision from #405; disabling it is a code-level
question, not a tuning move). The train/holdout split is hard-coded in the
pinned scorer. Everything outside the single asset glob is out of scope.

## Sensitivities to watch

- Per-evidence-tier table every round: a gain confined to E3 with E1/E2
  flat is the circularity smell — journal it, do not celebrate it.
- Pegged-at-bound tunables get named in SUMMARY.md as sensitivities.
- nc_matched trades at -2.0 vs determ_ok at +1.0: the optimizer must not
  be allowed to "win" by refusing determinism entirely — the +1.0 vs +0.3
  gap prices that, and the deferred_ok count is watched per round.
