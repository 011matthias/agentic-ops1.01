---
tag: upwork-independence-gtm-v2-confirm
project: upwork-independence
goal: >
  Test whether `upwork-independence-gtm-v2` was actually converged when it
  journaled "all levers confirmed at optimum", by re-climbing its own winning
  plan against the BYTE-IDENTICAL v2 scorer. Score = total blended contribution
  SURPLUS (kEUR above the ~EUR33/hr hourly-work opportunity cost) over a
  30-month horizon, exactly as in v2, so the two runs' scores are directly
  comparable. Baseline is v2's winner as-is (2123.84 kEUR): any keep falsifies
  v2's convergence claim, and zero keeps is a publishable confirmation rather
  than a failed run. Hard floor that must not break: the plan's PESSIMISTIC-case
  total surplus stays >= 0.
scorer: tools/scorers/gtm-roi-v2.py
scorer_args:
  - workspace/projects/upwork-independence/gtm-plan.json
direction: maximize
assets:
  - workspace/projects/upwork-independence/gtm-plan.json
guards:
  - uv run tools/gtm-plan-validate.py workspace/projects/upwork-independence/gtm-plan.json
  - uv run tools/gtm-stress-guard-v2.py workspace/projects/upwork-independence/gtm-plan.json
guard_files:
  - tools/gtm-plan-validate.py
  - tools/gtm-stress-guard-v2.py
budgets:
  rounds: 12
  wall_clock_minutes: 60
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 5
---

# Upwork-independence GTM: was v2 converged? (same model, same scorer)

## Why this run

`upwork-independence-gtm-v2` closed with the journal line "all levers confirmed
at optimum (4 keeps ... 4 boundary probes discarded)". That claim is the thing
under test here. A run that stops climbing has not necessarily found an optimum;
it may have run out of ideas, and v2's four probes all pushed in the same
direction (upward) from levers it had just moved. This run re-climbs v2's own
winner and reports whether the claim holds.

## This is NOT a v3, and that is the point

The metric is unchanged. This run uses `tools/scorers/gtm-roi-v2.py` byte for
byte, at its existing pin (`PINS.json` sha `b6e0e17b...`, pinned 2026-07-21).
No re-pin, no `SCORER_LOCK_ALLOW`, no parameter edit, no change to the horizon,
the elasticities, the channel set, or the bounds. **v2's final score and this
run's final score are therefore directly comparable numbers on one ruler.**

v2's own SUMMARY had to open with "Not comparable to v1's score" because v1 and
v2 measured different things. That gap is precisely what made v2's result hard
to audit, and it is not repeated here. If this run concludes the MODEL needs to
change, that is a v3, it goes through the scorer-authoring PR path, and its
scores start a new incomparable series; nothing in this manifest anticipates
doing that mid-run.

## Baseline: option (a), v2's winner as-is

The asset on `main` IS v2's winner (capacity 32, alloc 0.24/0.76, handwerk,
build 1200, care 200, UK/cold_email, retainer 2500) and re-scores to exactly
**2123.84 kEUR**, matching v2's journaled final. So the baseline needs no
reconstruction, and the run answers the sharper question: *was v2 converged?*

Option (b) (start from v2's pre-run baseline, 687.58) was considered and
rejected: it would test whether the hardened harness rediscovers the same path,
which is a reproducibility check of the loop, not a check of the ANSWER. The
loop's mechanics are already covered by the hook and engine test suites. The
answer is not covered by anything.

## Inherited from `--prior-art upwork-independence` (do not re-open)

Read at Step 2.0 via `uv run tools/optimize_overview.py --prior-art
upwork-independence`, after backfilling the heading contract into the v1 and v2
SUMMARYs (its own docs PR, shipped first; before that the read path returned
nothing for this project). Inherited and NOT re-tested here:

- v2 r6: allocation to 1.0 b2b (drop local) is worse. Mixed beats the corner.
- v2 r7: build price 1200 to 1500 is worse.
- v2 r8: care price 200 to 250 is worse.
- v2's four keeps (care 200, capacity 32, allocation 0.76 b2b, retainer 2500)
  are the starting position, not hypotheses to re-derive.
- v1's allocation dead end is marked SUPERSEDED in the backfill and is
  deliberately not inherited: v2 overturned it.

Overridden, with reason: v2's `## Dead ends` present r7 and r8 as settling the
build and care levers. They settle only the UPWARD side of each. This run probes
the downward side of both, which is a different test, not a re-run.

## What the guards prove, and what they do not

Both guards are reused unchanged and are hash-pinned in `tools/guard-pins.json`
(2026-07-22); `start` refuses a guard that has drifted from its pin.

1. `gtm-plan-validate.py` (pin `97cb1c4b...`) is an independent instrument:
   schema, market/realism bounds, and the UWG Sec.7 legal fence rejecting
   DE + cold_email.
2. `gtm-stress-guard-v2.py` (pin `681bd883...`) requires the pessimistic-case
   total surplus to stay >= 0 under adverse haircuts.

**The stress guard is not a held-out generalization check, and this run will not
claim it is.** It re-runs the SAME self-authored model with pessimistic
parameters, so it tests robustness to bad assumptions inside one model; it
cannot detect that the model itself is wrong. RECIPES rule 3 (a held-out score
floor) genuinely cannot be satisfied for a planning model of a business that has
not run yet: there is no ground-truth slice to hold out, because there is no
ground truth. The honest position is that this run has an anti-optimism lock and
no anti-overfit lock, and its output is "the best execution GIVEN these
economics", never "the validated best execution". Standing caveat, already in
the friction register.

## Action catalog (prioritized; expected impact from an offline sweep)

The ordering below was set by sweeping the locked scorer offline over the
decision space before lock-on, so rounds are spent on tests whose outcome is
informative rather than on searching. The scorer is locked either way; the sweep
changes only the ORDER of hypotheses, and it is disclosed here so a reviewer can
discount the "predicted correctly" rate accordingly.

**Value hypotheses (expected keeps):**

1. **Route-2 acquisition `cold_email` to `referral`.** Neither v1 nor v2 ever
   listed the acquisition channel in a catalog or moved it in a round; it is the
   one decision field in the plan that no previous run touched. Route 2 is
   market-capped at 62.5 clients under both channels, but referral reaches that
   cap with far fewer acquisition hours, so productive hours (and therefore
   opportunity cost) drop with revenue unchanged. Expect a large keep.
2. **Route-1 build price 1200 to ~1225.** v2 probed only upward and concluded
   the floor is optimal. The revenue curve `clients(pb) x (pb + care)` has an
   interior maximum just above the floor. Expect a keep so small it is
   commercially meaningless, whose only value is falsifying the word "floor".

**Boundary probes (predicted discards; `--probe`, so they do not count toward
PLATEAU):**

3. Care price 200 to 175: closes v2's one-sided test from below.
4. Build price up off whatever r2 lands on: brackets the interior peak from
   above, so the claim is two-sided.
5. Route-1 segment `handwerk` to another niche: both v1 and v2 asserted
   "largest reachable pool" without ever probing it.
6. Allocation local 0.24 to 0.23: v2's winner sits where Route-2 oversight
   capacity only just covers the market cap, which is a constraint intersection
   rather than a smooth interior optimum. Probe the cheap side of the edge.
7. Route-2 geo UK to US: expect an EXACT tie, documenting that geo is
   score-neutral in `compute()` and is load-bearing only for the legal guard.

Explicitly NOT probed: retainer upward. It sits on its declared ceiling (2500 of
500-2500) and the model's gradient still points up, so a probe would only
re-measure the bound. It is named as the run's headline pegged-lever sensitivity
instead.

## Reviewer focus at ship time

The comparison section of the SUMMARY: baseline used and why, v2 final vs this
run's final on the same scorer with the delta as a number, a per-lever table of
v2's value vs this run's value and whether it moved, and a one-sentence verdict
on whether v2 was converged with the specific lever that proves it. Plus every
winning lever checked for the pegged-at-bound tell and named as a sensitivity,
and minutes per round from the new `timestamp` column (this is the first run to
populate it, so there is no prior run to compare the figure against).

If a keep lands, the reviewer's question is not "is the number bigger" but
"does the model support acting on it" (see the SUMMARY's sensitivities). If
nothing lands, the run ships as a confirmation: v2's optimum held under N
further hypotheses and M boundary probes.
