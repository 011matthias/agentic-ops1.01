---
tag: upwork-independence-leadgen-portfolio
project: upwork-independence
goal: >
  Maximize the net won-client VALUE (kEUR over a 30-month horizon: client
  contribution won, minus the acquisition cost of winning them) of the
  client-acquisition portfolio, by splitting a fixed acquisition budget (hours +
  cash) across the five OWNED channels. The question: how are we going to win
  clients, once we stop renting lead flow from Upwork? Hard floor that must not
  break: the portfolio's PESSIMISTIC-case net value stays >= 0 (the clients you
  win must be worth more than the hours+cash spent winning them, even in the bad
  case).
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
  rounds: 14
  wall_clock_minutes: 60
  score_timeout_seconds: 60
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 6
---

# Upwork-independence client-acquisition portfolio

## Why this run

Independence from Upwork means replacing a rented lead source with owned
outbound. GTM-v2 optimized delivery + pricing and hit a MARKET-REACH ceiling
(Route-2 ~25 clients/yr): no single channel wins enough clients. This run
answers the acquisition question directly: given a fixed acquisition budget
(hours + cash) and the delivery capacity from GTM-v2, how should effort split
across the OWNED channels to win the most client value?

## Baseline

A naive even hedge (0.20 effort on each of the five owned channels). The loop
climbs from there toward the value-weighted portfolio.

## What is locked vs free

- **Free (the asset):** `channel_effort` per owned channel (fraction of the
  acquisition-hours budget), and `target_geos`.
- **Locked (scorer + guards):** the acquisition hours + cash budgets, the
  delivery serviceable cap, and each channel's cost-per-client, reachable pool,
  ramp, fixed setup, geo-legality, and per-client value (net of delivery, from
  GTM-v2). Hash-pinned; re-verified every round.

## Honest-number caveat (read before trusting the output)

The SCORE is only as real as the locked channel economics, which are
ASSUMPTION-tagged planning estimates (reviewed on PR #309). The run does not
discover ground truth; it finds the channel mix the model rewards and surfaces
which assumptions the answer leans on. The RANKING of channels is more stable
than the absolute EUR; treat the result as "given these channel economics, this
is the efficient acquisition mix", then validate the pools and costs.

## Guards (both must pass every round)

1. `leadgen-portfolio-validate.py` (reused) — schema, effort bounds, budget sum,
   geo-legality (cold_email_b2b needs UK/US; no DE cold email, UWG Sec.7).
2. `leadgen-portfolio-stress-guard.py` — pessimistic net value >= 0 under adverse
   haircuts (value x0.85, pools x0.6, hpc x1.25, ramp +2mo, cash x1.3,
   serviceable x0.8). Anti-optimism lock.

## Action catalog (hypothesis menu, prioritized)

1. Tilt effort to the high-value-per-client B2B channels (cold-email, LinkedIn,
   referral) up to their pools; the serviceable cap prioritizes value-per-client.
2. Fund AEO/content inbound past its fixed-cost activation threshold (it needs
   > ~200h to produce, then compounds cheaply).
3. Cut demo-first-local effort: it is the lowest value-per-acquisition-hour
   channel (a local client costs ~27h to win for ~EUR4k; a B2B client ~15h for
   ~EUR30k), so it earns few serviceable slots.
4. Confirm the portfolio stays diversified (no single channel reaches enough) and
   that the cash + serviceable constraints bind at the optimum.

## Reviewer focus at ship time

Baseline vs final net value, the channel mix and each channel's won clients, and
the headline playbook: which channels to invest in, in what proportion, to win
the most client value. Plus the cross-model tension with GTM-v2 (local is cheap
to DELIVER but expensive to WIN) and the contrast against the all-Upwork status
quo (the independence upside).
