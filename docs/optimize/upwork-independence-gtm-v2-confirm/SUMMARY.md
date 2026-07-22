# upwork-independence-gtm-v2-confirm — run summary

**Result: 2123.84 → 2159.47 kEUR, 8 rounds, converged. v2 was NOT converged.**
Two levers moved off v2's winner, and the larger one is a decision field that no
previous run on this project ever touched.

## Comparison against `upwork-independence-gtm-v2`

### Baseline used, and why

Option (a): **v2's winning `gtm-plan.json` as-is.** The asset on `main` already
IS v2's winner, and it re-scored to **2123.84**, bit-identical to v2's journaled
final. So the baseline required no reconstruction and the run tested the sharp
question, "was v2 actually converged?", rather than the loop-reproducibility
question option (b) would have answered. The loop's mechanics are already covered
by the engine and hook test suites; v2's *answer* was covered by nothing.

### Scores are comparable, deliberately

Both runs used `tools/scorers/gtm-roi-v2.py` byte for byte, at the same
`PINS.json` pin (`b6e0e17b…`, pinned 2026-07-21). No re-pin, no
`SCORER_LOCK_ALLOW`, no parameter, bound, horizon, or channel-set edit.
`pin_scorer.py check` reported zero drift both before lock-on and after `stop`.

| | score (kEUR) |
|---|---|
| v2 final | 2123.84 |
| this run final | 2159.47 |
| **delta** | **+35.63** (+1.68%) |

v2's SUMMARY had to open with "Not comparable to v1's score". That is not
repeated here: these two numbers sit on one ruler and the delta is a real
measurement, not a re-scoring artifact.

### Per lever

| Decision | v2 | this run | Moved? |
|---|---|---|---|
| capacity / week | 32 | 32 | no |
| route split (local / b2b) | 0.24 / 0.76 | 0.24 / 0.76 | no |
| Route-1 segment | handwerk | handwerk | no (asserted by v1+v2, tested here) |
| Route-1 build price | 1200 | **1225** | **yes, +25** |
| Route-1 care price | 200 | 200 | no (one-sided in v2, bracketed here) |
| Route-1 geo | DE | DE | no (score-invisible) |
| Route-1 acquisition | demo_first | demo_first | no (score-invisible) |
| Route-2 geo | UK | UK | no (score-invisible) |
| Route-2 acquisition | cold_email | **referral** | **yes** |
| Route-2 retainer | 2500 | 2500 | no (pegged at ceiling) |

### Verdict

**v2 was not converged, and `b2b_lead_gen.acquisition` proves it: switching
Route-2 from cold email to referral is worth +35.62 kEUR, 99.97% of this run's
total gain, on a field neither v1 nor v2 ever moved or even listed in an action
catalog.**

### Minutes per round

**0.35 min/round** (≈21 s): 8 rounds spanning the baseline stamp 13:14:36 to the
final round stamp 13:17:23, 167 s total. The interval between consecutive rows
covers both the agent's edit and the engine's commit/score/guard cycle, so it is
end-to-end round latency, not engine time alone.

This is the first run to populate the `timestamp` column, so **no prior run has a
comparable figure** — `optimize_overview.py --scoreboard` reported
`minutes per round n/a (0/6 runs carry timestamps)` before this run. The number
is a baseline for future runs, not yet a comparison.

## Kept changes (the journal)

| r | change | score | delta |
|---|---|---|---|
| 1 | Route-2 acquisition cold_email → referral | 2159.46 | +35.62 |
| 2 | Route-1 build price 1200 → 1225 | 2159.47 | +0.01 |
| 3 | PROBE care 200 → 175 | 2157.64 | DISCARD (predicted) |
| 4 | PROBE build 1225 → 1300 | 2159.42 | DISCARD (predicted) |
| 5 | PROBE segment handwerk → beauty | 2125.16 | DISCARD (predicted) |
| 6 | PROBE allocation local 0.24 → 0.23 | 2153.86 | DISCARD (predicted) |
| 7 | PROBE Route-2 geo UK → DE | 2159.47 | DISCARD, exact tie (predicted) |
| 8 | PROBE capacity 32 → 30 under referral | 2025.26 | DISCARD (predicted) |

All six probes discarded as predicted. Note the prediction rate is not evidence
of insight: the action catalog was ordered by an offline sweep of the locked
scorer before lock-on, disclosed in RUN.md. The sweep changed which rounds were
worth spending, not what the scorer would say.

## What the referral switch actually does, and why you should not act on it yet

The mechanism is narrow and worth stating exactly, because the headline number
is easy to over-read.

Route 2 is capped at 62.5 clients by `r2_market_cap_yr` under **both** channels,
so revenue is unchanged (EUR 2,187,500 either way; total revenue moved by +7 EUR,
all of it from the build-price change). Referral converts about 8x better per
prospect-hour (3 prospects/hr × 12% close vs 35 prospects/hr × 0.23%), so it
reaches the same cap using ~313 acquisition hours instead of ~1392. Productive
hours fall 3625 → 2545, and the entire +35.62 kEUR is the opportunity cost no
longer charged on those 1,080 hours.

Three reasons that is not yet a recommendation:

1. **The model has no referral-supply constraint.** `r2_prospects_per_hr_referral
   = 3.0` lets you generate referral prospects indefinitely at a fixed rate, with
   no dependence on an existing client base, network size, or reputation. For
   someone leaving Upwork *without* a book of clients, that is the least
   defensible assumption in the model. Cold email has no bootstrapping problem;
   referral is precisely the channel that does. The model rewards referral partly
   because it never charges for the thing that makes referral hard.
2. **The freed hours are stranded, not redeployed** (r8). `r2_acq_fraction` is
   locked at 0.55, and Route-2 hours are set by the 0.45 service share needing
   ~1313 oversight hours, so the 1,080 freed acquisition hours cannot be moved
   anywhere productive. They become idle, and idle is worth exactly zero surplus
   by construction. The gain converts to money only if those hours are actually
   redeployed outside the model.
3. **The win is an accounting effect, not new revenue.** Nothing about the
   business got bigger; the same 62.5 clients cost fewer of your hours.

The defensible reading is directional: **if referral supply can be made real, the
acquisition channel is worth more than any pricing lever v2 tuned.** Validating
referral supply is now the highest-value open question on this project, ahead of
the subcontracting arrangement v2 nominated.

One genuine side effect, confirmed in r7: DE + cold_email is rejected by the UWG
Sec.7 fence, but DE + referral passes both guards and scores identically. The
channel switch legally unlocks the DE market at zero modelled cost.

## Pegged-lever audit

Every winning lever checked against its declared bound:

- **Route-2 retainer 2500 is pegged at its ceiling (bound 500–2500).** The
  model's gradient still points up, so 2500 is an artifact of where the bound was
  set, not a discovered optimum. Deliberately not probed: a probe would only
  re-measure the bound. This is the run's headline sensitivity, unchanged from v2.
- **Capacity 32 is not pegged (bound 5–45) but sits at the left edge of a flat
  region.** Everything from 32 to 45 scores identically; 30 is much worse (r8).
  Read it as the minimum that saturates both channels, not a peak.
- **Allocation 0.24 / 0.76 is not pegged but sits at a constraint intersection**,
  where Route-1 hours saturate the handwerk pool and Route-2 oversight just
  covers the market cap. Both directions lose (r6 here, r6 in v2). It is an edge,
  not a smooth interior peak, so it will move if either constraint moves.
- **Build 1225 and care 200 are genuinely interior and now bracketed on both
  sides** (r3/r4 here, r7/r8 in v2).

## What the guards do and do not prove

`gtm-plan-validate.py` and `gtm-stress-guard-v2.py` both passed on every kept
round; the winner clears the pessimistic floor at 809.70 kEUR (v2's winner
cleared at 627.83).

**The stress guard is not a held-out generalization check and this run does not
claim it is.** It re-runs the same self-authored model with pessimistic
parameters, so it tests robustness to bad assumptions inside one model and cannot
detect that the model itself is wrong. RECIPES rule 3 (a mandatory held-out score
floor) genuinely cannot be satisfied for a planning model of a business that has
not run: there is no ground-truth slice to hold out because there is no ground
truth. This run therefore has an anti-optimism lock and **no anti-overfit lock**.
Its output is "the best execution given these economics", never "the validated
best execution".

## Dead ends

Six boundary probes, all discarded as predicted against this model. A later run
should not spend rounds re-deriving them:

- **Care price below the optimum loses (r3: 200 → 175, 2157.64).** With v2's r8
  (200 → 250) this brackets care on both sides. v2's "true interior peak" claim
  rested on a one-sided test; it is now two-sided and holds.
- **Build price above the optimum loses (r4: 1225 → 1300, 2159.42).** The peak is
  pinned inside [1200, 1300]. v2's r7 tested only the coarse 1200 → 1500 step.
- **A smaller Route-1 niche loses (r5: handwerk → beauty, 2125.16).** v1 and v2
  both carried "handwerk = largest reachable pool" as an untested assertion
  across every round. It is now tested and correct.
- **Shaving Route-1 allocation loses (r6: 0.24 → 0.23, 2153.86).** Strands
  Route-1 pool without buying anything on Route-2, which is already market-capped.
- **Route-2 geo is score-neutral (r7: UK → DE, exact tie 2159.47).** Three of the
  plan's decision fields are never read by `compute()`: `local_smb.geo`,
  `local_smb.acquisition` (both verified by direct scoring), and
  `b2b_lead_gen.geo` (verified in-run). They are constrained only by the legal
  guard. Do not spend a round moving them for score.
- **Capacity below 32 loses even after referral frees 1,080 hours (r8: 32 → 30,
  2025.26).** The knee is set by the locked 0.45 service share, not by
  acquisition, so a cheaper acquisition channel does not lower it.

Settled by construction and not worth a round: this run's score is directly
comparable to v2's (same pinned scorer) and directly INcomparable to v1's
(EUR/hr, different metric).

## Sensitivities

- **Referral supply is unmodelled, and the run's whole gain depends on it.**
  See the section above. Highest-priority validation on this project, ahead of
  subcontracting.
- **Route-2 retainer 2500 is pegged at its declared ceiling.** Inherited
  unchanged from v2 and still the single most bound-dependent number in the plan.
- **The Route-2 market cap (25 clients/yr) still binds both channels**, so it
  still sets all of Route-2's revenue. Inherited from v2; this run makes it more
  load-bearing, not less, because the channel switch does not relax it.
- **`r2_acq_fraction` is locked at 0.55 and now visibly distorts the answer.**
  It strands the hours referral frees. v2's SUMMARY already nominated making it a
  decision field in a v3; r8 turns that from a nice-to-have into the specific
  thing blocking the freed hours from earning anything.
- **The +0.01 kEUR build keep is real but commercially meaningless.** It is +7
  EUR on a 2.16M plan. Its only value is falsifying the word "floor" in v2's
  conclusion: the optimum is interior at ~1227, and the curve is flat within
  ±100 EUR. "Loss-lead the build" survives intact; "the floor is optimal" does not.
- **The subcontracting economics** (EUR20/hr, ~1.5 h/client/mo oversight, ~4x
  leverage) remain as assumed and unvalidated as in v2.

## What a human should review

The strategic direction is unchanged from v2 and does not depend on this run's
keeps: commit to B2B as the scalable core, subcontract delivery so the market
rather than your hours is the limit, price at the top the channel bears, and keep
a smaller local-SMB recurring-care book alongside.

What this run adds is a correction to v2's convergence claim and one new
question. v2 concluded "all levers confirmed at optimum" having never tested the
acquisition channel, the Route-1 segment, the downward side of two interior
optima, or three score-invisible fields. All are now tested. The open question is
whether referral supply can be made real for an operator without an existing
client base; if it can, the acquisition channel outranks every pricing lever v2
tuned, and if it cannot, cold email stays and v2's plan stands with the build
price nudged 25 EUR.

A `-v3` (new scorer, new incomparable series) is worth building when either the
referral-supply constraint or `r2_acq_fraction`-as-a-decision is ready to model.
Both are now better motivated than they were at the end of v2.
