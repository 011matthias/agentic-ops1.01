---
tag: upwork-independence-gtm-v1
project: upwork-independence
goal: >
  Maximize blended contribution-margin per working hour (EUR/hr above the
  hourly-work opportunity cost) of the two-route Upwork-independence GTM plan
  over a 30-month horizon, by searching route mix, pricing, capacity, geo, and
  segment against a locked economic model. Hard floor that must not break: the plan's PESSIMISTIC-case
  margin/hr stays >= 0 (must beat grinding hourly even in the bad case).
scorer: tools/scorers/gtm-roi.py
scorer_args:
  - workspace/projects/upwork-independence/gtm-plan.json
direction: maximize
assets:
  - workspace/projects/upwork-independence/gtm-plan.json
guards:
  - uv run tools/gtm-plan-validate.py workspace/projects/upwork-independence/gtm-plan.json
  - uv run tools/gtm-stress-guard.py workspace/projects/upwork-independence/gtm-plan.json
guard_files:
  - tools/gtm-plan-validate.py
  - tools/gtm-stress-guard.py
budgets:
  rounds: 20
  wall_clock_minutes: 90
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 6
---

# Upwork-independence GTM ROI optimization (v1)

## Why this run

Owner's core 2026 goal is independence from Upwork via two service routes:
Route 1 (DE local-SMB sites + AEO, demo-first) and Route 2 (B2B lead-gen as a
service, cold-email UK/US). This run searches the *execution* decisions for the
configuration that earns the most per working hour, against a model whose reality
parameters are locked and human-reviewed at pin time.

## What is locked vs free

- **Free (the asset, `gtm-plan.json`):** capacity/week, route allocation, Route-1
  price_build + price_care + segment + geo + acquisition, Route-2 geo + acquisition
  + retainer. Nine decisions.
- **Locked (the scorer + guards):** every conversion funnel, build-hour cost,
  saturation cap, price elasticity, deliverability haircut, and the EUR33/hr
  opportunity rate. The agent cannot edit these during the run, so it cannot win
  by inflating conversion or price past reality.

## Honest-number caveat (read before trusting the output)

The SCORE is only as real as the locked parameters. Several are ASSUMPTION-tagged
planning estimates (build hours, conversion rates, retainer band), sourced where
possible (opportunity rate, UWG Sec.7 legal fence, verified-list bounce). The run
does not discover ground truth; it finds the decision configuration the *model*
rewards, and surfaces which assumptions the answer is most sensitive to. Treat the
result as "given these economics, this is the best execution", then pressure-test
the two or three parameters the winner leans on hardest.

## Guards (both must pass every round)

1. `gtm-plan-validate.py` — schema, market/realism bounds, and the UWG Sec.7 legal
   fence (DE + cold_email is rejected outright).
2. `gtm-stress-guard.py` — pessimistic-case margin/hr must stay >= 0. This is the
   anti-overfit lock: a plan that only wins under optimistic assumptions is discarded
   even if its central score is the new best.

## Action catalog (hypothesis menu, prioritized)

1. Shift Route-2 geo to UK/US cold-email vs DE referral (channel legality gates volume).
2. Tune Route-1 price_build against its conversion elasticity for the interior optimum.
3. Rebalance route_allocation toward whichever route's marginal hour clears EUR33/hr.
4. Pick the Route-1 segment with the largest reachable pool before saturation.
5. Find the capacity/week where marginal hours still beat the opportunity rate
   (more hours is not automatically better; each hour costs EUR33 of foregone work).
6. Set Route-2 retainer against its close-rate elasticity, and only as high as the
   service-hour budget can actually deliver.

## Reviewer focus at ship time

Baseline vs final margin/hr, the kept decisions and their deltas, and — most
important — the sensitivity note: which locked assumptions the winning plan depends
on, so the owner knows what to validate in the real world before acting on it.
