---
tag: upwork-independence-gtm-v2
project: upwork-independence
goal: >
  Maximize the total blended contribution SURPLUS (kEUR above the hourly-work
  opportunity cost) of the two-route Upwork-independence GTM plan over a
  30-month horizon, under the v2 economic model that adds care-price elasticity
  and a subcontracting / freed-hour-reinvestment term. The question this run
  answers: does v1's strategic DIRECTION (commit to B2B, price at service
  capacity, loss-lead the build) survive once the two pegged levers can breathe?
  Hard floor that must not break: the plan's PESSIMISTIC-case total surplus
  stays >= 0 (must beat grinding hourly even in the bad case).
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
  rounds: 14
  wall_clock_minutes: 60
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 6
---

# Upwork-independence GTM ROI optimization (v2)

## Why this run

v1 (`upwork-independence-gtm-v1`) converged 36.88 -> 200.37 EUR/hr but pegged
three levers to their bounds — a tell that the model had no resistance there.
The v1 SUMMARY flagged the two worth fixing: care price hit its ceiling (no
care-price elasticity) and capacity collapsed to a low-end artifact (freed
hours charged full opportunity cost, no reinvestment). This run climbs the same
decision plan against the v2 model (`tools/scorers/gtm-roi-v2.py`, PR #307),
which adds exactly that resistance, and reports whether the v1 direction holds.

## Baseline

The asset starts at the **v1 winner** (capacity 15, alloc 0.5/0.5, local
DE/demo/handwerk build 1200 care 300, b2b UK/cold_email retainer 2400). Starting
from v1's answer isolates precisely the levers that move once the model resists:
if care and capacity were real, they stay; if they were artifacts, the climb
moves them. (v2's SCORE is total surplus in kEUR, not v1's per-hour figure —
the two are not score-comparable; compare the WINNERS by their decisions.)

## What is locked vs free

- **Free (the asset, `gtm-plan.json`):** capacity/week, route allocation,
  Route-1 build + care + segment + geo + acquisition, Route-2 geo + acquisition
  + retainer.
- **Locked (scorer + guards):** every conversion funnel, build-hour cost,
  saturation cap, the three elasticities (build/care/retainer), the
  subcontracting economics (rate + oversight leverage), deliverability haircut,
  and the EUR33/hr opportunity rate. Hash-pinned; re-verified every round.

## Honest-number caveat (read before trusting the output)

The SCORE is only as real as the locked parameters. The v2-new ones
(`r1_ref_care`, `r1_care_elasticity`, `subcontractor_rate_eur_hr`,
`r2_oversight_hours_client_mo`) are ASSUMPTION-tagged planning estimates,
reviewed and signed off on PR #307. The run does not discover ground truth; it
finds the decision configuration the *model* rewards and surfaces which
assumptions the answer leans on. Treat the result as "given these economics,
this is the best execution", then pressure-test the parameters the winner
depends on hardest.

## Guards (both must pass every round)

1. `gtm-plan-validate.py` (reused, unchanged) — schema, market/realism bounds,
   and the UWG Sec.7 legal fence (DE + cold_email rejected). The v2 care optimum
   (~EUR200/mo) is interior to the existing EUR300 ceiling, so bounds are unchanged.
2. `gtm-stress-guard-v2.py` — pessimistic-case TOTAL surplus must stay >= 0
   (anti-overfit lock), under adverse haircuts incl. subcontractor rate x1.3 and
   oversight hours x1.5. A plan that only wins if subcontracting pays under
   optimism is discarded even on a central-score win.

## Action catalog (hypothesis menu, prioritized)

1. Drop Route-1 care price 300 -> its interior optimum (care elasticity now
   resists; expect ~EUR200/mo).
2. Raise capacity off 15 toward the market-saturating knee (subcontracting +
   reinvestment now reward productive hours; idle capacity is neutral, not a
   drag).
3. Tilt route_allocation toward B2B (subcontracting makes Route-2 far more
   scalable than in v1; test how hard to tilt without abandoning the Route-1
   care annuity — total surplus should peak at a MIXED allocation, not a corner).
4. Confirm build price stays at the floor (loss-lead the build) and retainer
   near the ceiling (price at service capacity) — the v1 findings not targeted
   by this run.
5. Re-check the Route-1 segment (largest reachable pool) and geo/acquisition
   channel legality.

## Reviewer focus at ship time

Baseline vs final total surplus, the kept decisions and their deltas, and — the
headline — whether the three v1 strategic conclusions survive: (1) commit to
B2B, (2) price at service capacity, (3) loss-lead the build. Plus the corrected
numbers (care off the ceiling, capacity off the floor) and any NEW nuance the
richer model surfaces (e.g. the mixed-not-corner allocation).
