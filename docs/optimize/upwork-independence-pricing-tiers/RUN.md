---
tag: upwork-independence-pricing-tiers
project: upwork-independence
goal: >
  Maximize the total contribution surplus (kEUR over a 30-month horizon, above the
  owner's opportunity cost) of a good/better/best PRICING MENU for the B2B
  lead-generation service, by choosing each tier's {price, scope}. The question:
  once GTM-v2 fixed the delivery economics and leadgen-portfolio fixed how clients
  are won, what exactly do we sell, and at what price? A heterogeneous prospect
  population self-selects into the menu (second-degree price discrimination). Hard
  floor that must not break: the menu's PESSIMISTIC-case surplus stays >= 0 (the
  clients who buy are worth more than the cost of serving them, even in the bad case).
scorer: tools/scorers/pricing-tiers.py
scorer_args:
  - workspace/projects/upwork-independence/pricing-tiers.json
direction: maximize
assets:
  - workspace/projects/upwork-independence/pricing-tiers.json
guards:
  - uv run tools/pricing-tiers-validate.py workspace/projects/upwork-independence/pricing-tiers.json
  - uv run tools/pricing-tiers-stress-guard.py workspace/projects/upwork-independence/pricing-tiers.json
guard_files:
  - tools/pricing-tiers-validate.py
  - tools/pricing-tiers-stress-guard.py
budgets:
  rounds: 12
  wall_clock_minutes: 60
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 6
---

# Upwork-independence pricing-tier menu (good / better / best)

## Why this run

Third and final GTM-family run. GTM-v2 optimized the delivery + pricing of ONE
retainer (~EUR2500/mo); leadgen-portfolio optimized how clients are acquired.
Neither priced the OFFER itself. This run designs the packaging: a three-tier menu
where each tier is a {price, scope} pair, sold to a prospect population that spans
very different willingness to pay. The whole reason to offer tiers instead of one
flat price is that a flat price forces a bad trade-off, either excluding low-value
prospects or leaving money on the table with high-value ones. The loop finds the
menu that resolves that trade-off.

## Baseline

A naive even ladder (good EUR1000/0.33, better EUR2000/0.66, best EUR3000/1.0):
evenly-spaced prices, evenly-spaced scope. It leaves the premium segment badly
underpriced and prices the entry tier just above the low segment's willingness to
pay, so the low segment buys nothing. The loop climbs from there.

## What is locked vs free

- **Free (the asset):** each tier's `price` (EUR/mo) and `scope` (0..1, normalized
  service intensity), for good / better / best.
- **Locked (scorer + guards):** the three prospect segments (size + value curve),
  the scope->value and scope->cost curves, owner oversight, delivery capacity, and
  the 30-month horizon + 14-month client lifetime carried from GTM-v2. Hash-pinned;
  re-verified every round.

## Honest-number caveat (read before trusting the output)

The SCORE is only as real as the locked segment economics, which are
ASSUMPTION-tagged planning estimates for the B2B prospect willingness-to-pay
distribution (reviewed on PR #311). The run does not discover the true market; it
finds the menu the model rewards and surfaces which assumptions the answer leans on.
The RANKING (spread the tiers, how much to differentiate them, which segment each
tier serves) is more stable than the absolute EUR. Treat the result as "given this
prospect distribution, this is the efficient menu", then validate the segment sizes
and value curves against real quotes.

## Guards (both must pass every round)

1. `pricing-tiers-validate.py` — schema + a valid non-decreasing good/better/best
   price+scope ladder + no tier priced below its own delivery cost (no loss-making
   recurring tier).
2. `pricing-tiers-stress-guard.py` — pessimistic-case surplus >= 0 under adverse
   haircuts (segment sizes x0.7, value x0.8, delivery x1.25, oversight x1.25,
   capacity x0.8, plus a EUR150/mo buy threshold). Anti-optimism lock.

## Action catalog (hypothesis menu, prioritized)

1. Widen the entry tier: drop good's price and scope so the numerous low-WTP
   segment actually buys (a cheap thin plan), adding volume the flat baseline lost.
2. Capture the premium segment, but note the coupling: raising best's price alone
   makes the high segment DEFECT down to the better tier (it gets more surplus
   there). Best-capture only works if the better tier is thinned/repriced in the
   SAME move so the high segment still prefers best. These two levers are
   incentive-coupled and move together.
3. Do not over-scope the entry tier: a fat good tier cannibalizes better (the mid
   segment trades down). Keep good deliberately thin.
4. Confirm the optimum is an interior peak, not a bound: probe best-price too high
   (segment defects), good-scope too high (cannibalization), and folding the menu
   to two tiers (loses either the entry-volume or the premium-capture).

## Reviewer focus at ship time

Baseline vs final surplus, the final menu (the three price+scope pairs), which
segment self-selects each tier, and the headline: the tiering LIFT over the best
single flat price (the money versioning captures over one-size-fits-all pricing).
Plus how the result reconciles with GTM-v2's single ~EUR2500 retainer (which
segment that was) and leadgen-portfolio's serviceable-capacity ceiling.
