# 2026-07-23 — Brisken expense-recon: date+amount matching accuracy program

Owner directive: "the matching has to be done with the date and time and the
amount spent at that point; those are the most important; this should be the
most accurate." Plan-mode session (3 explorers + 2 designers + adversarial
review), full program approved and executed end to end.

## The time-of-day finding (owner accepted date+amount)

Verified, not assumed: NO source carries time-of-day. Chase activity CSV
columns are `Card, Transaction Date, Post Date, Description, Category, Type,
Amount, Memo` (Memo empty on all 94 April rows); the statement PDF charge
regex captures MM/DD only; the Zoho ER PDF's only HH:MM tokens are two
report-level trip-window header fields outside the parsed region; the vision
schema asks for `YYYY-MM-DD` only; every domain type is `datetime.date`.
Receipt-photo till-times exist but have no bank-side counterpart — owner
chose date+amount only.

## What shipped (PRs #404, #405, #406 — all merged, deployed Fly)

**#404 — the metric first.** Pinned scorer `tools/scorers/
recon-match-accuracy.py` (+1.0 determ-correct / +0.3 deferred-correct /
−2.0 determ-wrong or no_charge false positive over the 6 labelled months,
95 confirmed pairs; SCORE = train composite, four 2025-26 months) + pinned
guard `tools/recon-accuracy-guard.py` (invariant on all 6 bundles, holdout
floor on the two 2024 months, no-new-holdout-wrongs, wrong-ceiling;
PASS/FAIL output only — numeric leak control; imports the scorer by path so
the two cannot drift). Pre-change baseline: determ_ok 3/95, SCORE 14.4 all /
8.9 train / 5.5 holdout; tier table E3 0/92 = the entire headroom.

**#405 — structure.** `MatchType.FX_BASE_AMOUNT` (deterministic off the ER
report's own per-receipt conversion — the E3 signal the matcher never read;
works even when the printed total failed to parse); self-derived per-run
reference rates (statement-FX-line median n≥1 wins, else receipt-rate median
n≥3, clamped to the static band; configured rates overlay); band candidates
scored by amount agreement under the best rate (configured > learned >
derived > midpoint) instead of midpoint distance; **review-zone deferral +
bilateral-uniqueness gate**; sort key gains the amount+date blend;
`contested_receipts` counter in calibrate. 775 tests green (17 new).

**Measured iteration, recorded honestly:** the ladder's first cut scored
89/95 deterministic but auto-matched 38 of the 46 no_charge-labelled
receipts (coincidences live INSIDE the clean 2% band in dense months —
June-2025: 26/31). Review-zone deferral alone barely helped (34). The fix
was the fixture's own criterion: `labeling.auto_pairs` never treated
base-amount as conclusive alone — clean rate-derived evidence now resolves
deterministically only when bilaterally unique; contested pairs demote to
judgment with scores + reasons intact. Result: determ 54/95, wrong 0,
nc false positives 14, train 30.8, holdout 5.7 (no regression, 13/22).

**#406 — tuning (optimize run `brisken-recon-tuning-v1`).** 7 rounds +
baseline, PLATEAU stop, guards held every scored round. One winner:
`fx_base_amount_match_pct` 0.02→0.01 (+0.7; tightening demoted a
coincidental rival, making a TRUE pair bilaterally unique — the gate
converts precision into recall). Knee bracketed (0.005 loses / 0.01 wins /
0.02 loses); dead ends journaled (date-window narrowing, reference-path
tightening — it needs its 3% headroom by construction); inert levers named.
Tuned value promoted into the `MatchingConfig` dataclass default (the
Docker image ships only `src/`; acceptance: EMPTY-asset score == tuned-file
score, 31.5 with identical counts). Race note: the drift-test CI failure on
#406 was fixed by cherry-picking the promotion into the same PR so file +
code moved atomically.

## The arc (all scorer-measured)

| | pre-code | post-#405 | tuned #406 |
|---|---|---|---|
| train composite | 8.9 | 30.8 | **31.5** |
| holdout composite | 5.5 | 5.7 | **5.7** |
| deterministic correct (all 6) | 3/95 | 54/95 | **55/95** |
| deterministic WRONG | 0 | 0 | **0** |
| no_charge false positives | 0 (nothing matched) | 14 | 9 train + 5 holdout |

## Live verification (deployed to Fly, same day)

April re-run on the hosted app, NO LLM, stored settings rates: 94 tx →
**20 reconciled clean (18 fx_base_amount + 2 fx_reference) + 13 teed-up
review**, invariant OK, 0 parse errors — **byte-identical to a local
replay of the same raw inputs** (20/13/61). Context: the same files scored
0/94 on 2026-07-22 before this program, and yesterday's 31 "reconciled"
included the imprecise review-zone auto-matches this program abolished.

## Open / next

- The ~14 bilaterally-unique no_charge coincidences are the precision
  frontier; vendor/context signals are the next structural idea if needed.
- New labelled months would sharpen everything; the labeling flow exists.
- fx tuning file and code defaults must keep moving together (CI drift
  test now enforces).
