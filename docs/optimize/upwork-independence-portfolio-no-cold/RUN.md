---
tag: upwork-independence-portfolio-no-cold
project: upwork-independence
goal: >
  Owner order 2026-09-05: the cold-email channel is retired (the u1 plan was
  deleted in PR #667). With cold_email_b2b PINNED at 0.0 effort for the whole
  run, maximize the net won-client VALUE (kEUR over the 30-month horizon) of
  the remaining four owned channels by re-splitting the fixed acquisition
  budget. Any round that puts effort back on cold_email_b2b violates the owner
  order and is discarded regardless of score. Hard floor unchanged: the
  portfolio's PESSIMISTIC-case net value stays >= 0.
scorer: tools/scorers/leadgen-portfolio.py
scorer_args:
  - workspace/projects/upwork-independence/acquisition-portfolio.json
direction: maximize
assets:
  - workspace/projects/upwork-independence/acquisition-portfolio.json
guards:
  - uv run tools/leadgen-portfolio-validate.py workspace/projects/upwork-independence/acquisition-portfolio.json
  - uv run tools/leadgen-portfolio-stress-guard.py workspace/projects/upwork-independence/acquisition-portfolio.json
guard_files:
  - tools/leadgen-portfolio-validate.py
  - tools/leadgen-portfolio-stress-guard.py
budgets:
  rounds: 10
  wall_clock_minutes: 45
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 4
---

# Re-split the acquisition portfolio with cold email retired

## Why this run

The leadgen-portfolio run (2026-07) found the optimal owned-channel mix WITH
cold email as the volume engine (0.378 effort, ~EUR1.5M modeled value). On
2026-09-05 the owner retired the cold-email channel and had the u1 plan
deleted (PR #667). The locked asset still carried 0.378 on a channel that no
longer exists as a plan; leaving it there fabricates strategy state, and
hand-editing the mix outside a run breaks the byte-stable convention. This
run re-derives the mix through the sanctioned machinery, with cold pinned to
0 as an owner constraint.

The score will land far BELOW the prior 3013 kEUR by construction: a channel
the model valued at ~EUR1.5M was removed by owner decision, not by the model.
The comparison that matters is baseline-no-cold vs optimized-no-cold, and the
run also documents the modeled cost of the retirement for the owner.

## Baseline

The prior winner with cold_email_b2b zeroed and every other effort untouched
(the honest "channel deleted, nothing redistributed" state; the freed 0.378
sits idle at the neutral opportunity rate). Committed before lock-on so the
run climbs among no-cold mixes only.

## Prior art inherited (optimize_overview.py --prior-art, read 2026-09-05)

- Inherited from leadgen-portfolio: all-in on one channel fails (pools are
  small; diversify); AEO/content earns its slots (fixed 200 h then compounds);
  the pools and per-client values are ASSUMPTION-tagged, ranking more stable
  than exact split.
- Deliberately RE-TESTED, not inherited: "demo-first-local does not earn
  acquisition budget" (r2 there). That verdict held while cold email
  saturated the hours budget and the 110-client serviceable cap bound. With
  cold gone, total reachable clients drop below the cap and acquisition hours
  free up, which is exactly the "move either constraint and the mix moves"
  sensitivity that run recorded. Demo-first as the marginal use of freed
  hours is this run's main open question.
- GTM-v2 / pricing-tiers economics stay locked inputs via the scorer, as
  before.

## What is locked vs free

- **Free (the asset):** channel_effort on the four remaining channels, and
  target_geos. cold_email_b2b stays 0.0 by owner order (agent-enforced per
  round; the engine scores, the manifest forbids).
- **Locked (scorer + guards):** unchanged from leadgen-portfolio, same
  pinned scorer and both guards.

## Action catalog (prioritized)

1. Saturate the high-value-per-hour survivors in order (content past its
   fixed threshold, referral, LinkedIn) up to their pools.
2. Spend the leftover hours on demo-first-local (marginal value per hour
   above the EUR33 opportunity rate in central AND stress cases; verify).
3. Boundary probes: drop demo again (expect KEEP of demo per the arithmetic,
   so a probe predicting discard-of-drop), push a survivor past its pool
   (expect discard).
4. Confirm effort sum stays <= 1.0 and the stress floor holds every round.

## Reviewer focus at ship time

Baseline vs final net value with cold retired, the modeled cost of the
retirement vs the 3013 kEUR prior winner (owner decision, priced), whether
demo-first re-enters the mix once cold is gone, and which pools now bind.
