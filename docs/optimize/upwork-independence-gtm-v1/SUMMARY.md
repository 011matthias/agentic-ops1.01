# upwork-independence-gtm-v1 — run summary

**Result: 36.88 → 200.37 EUR/hr (+443%), 5 rounds, converged.** Score = blended
contribution-margin per working hour above the ~EUR33/hr hourly-work fallback, over
a 30-month horizon. The winning plan cleared the pessimistic stress floor on every
kept round (engine-enforced), so it is robust, not optimism-only.

## Winning plan (`gtm-plan.json`)

| Decision | Baseline | Winner |
|---|---|---|
| capacity / week | 40 h | **15 h** |
| route split (local / b2b) | 0.5 / 0.5 | 0.5 / 0.5 |
| Route-1 segment | handwerk | handwerk (largest reachable pool) |
| Route-1 build price | EUR 2000 | **EUR 1200 (floor)** |
| Route-1 care price | EUR 100 | **EUR 300 (ceiling)** |
| Route-2 geo / channel | UK / cold_email | UK / cold_email |
| Route-2 retainer | EUR 1200 | **EUR 2400 (ceiling)** |

## Kept changes (the journal)

| r | change | score | delta |
|---|---|---|---|
| 1 | retainer 1200 → 2400 | 81.88 | +45.00 |
| 2 | capacity 40 → 15 h/wk | 121.79 | +39.91 |
| 3 | care price 100 → 300 | 186.32 | +64.53 |
| 4 | build price 2000 → 1200 | 200.37 | +14.05 |
| 5 | allocation 0.45/0.55 (probe) | 194.37 | DISCARD |

## The three strategic insights (robust across the caveats)

1. **B2B is service-capacity-limited, not acquisition-limited.** Cold email produces
   far more qualified prospects than a solo can service, so the binding constraint is
   delivery hours, not lead flow. The lever that matters is therefore *price per unit
   of service capacity* — charge the top retainer the capacity can hold (r1).
2. **Work fewer hours, not more.** Route 1 saturates its reachable pool quickly; hours
   beyond saturation add only opportunity cost, so cutting capacity 40→15 h/wk raised
   margin/hr by a third (r2). This is a per-hour-efficiency result, see caveat 3.
3. **Loss-lead the build, monetize the annuity.** Recurring care (EUR5,400/client over
   18mo) dwarfs the one-time build, so pricing the build at the floor to maximize
   conversion and client count beats charging more per deal (r3+r4). Run Route-1 local
   as a recurring-care business, not a per-project one.

## Model limitations the winner leans on (validate before acting)

The optimizer pegged three levers to their bounds, which is a tell that the model has
no resistance there — the number is sensitive to exactly these:

- **Care price hit the EUR300 ceiling** because the model has NO care-price elasticity.
  Real SMB care retainers resist; EUR300/mo is unvalidated. HIGHEST-sensitivity input.
- **Build price hit the floor, retainer hit the ceiling.** The answer is only as good as
  where those bounds were set (build 1200–4000, retainer 500–2500). A different real
  market ceiling moves the result.
- **"Work 15 h/wk" is a single-period artifact.** The model charges full opportunity cost
  on every hour and does not let freed hours be reinvested; in reality you would redeploy
  them. Read insight 2 as "don't over-invest hours in a saturated channel", not "cap the
  business at 15 h/wk".
- Conversion funnels (R1 demo→client 0.22; R2 cold 3%×35%×22%) are ASSUMPTION-tagged;
  the absolute EUR/hr scales with them, though the *ranking* of decisions is more stable.

## What a human should review

The strategic direction is trustworthy: **commit to B2B lead-gen as the scalable core,
price it at the top of what delivery capacity allows, and run Route-1 local as a
loss-leader-build + recurring-care annuity.** Before acting on the specific numbers,
pressure-test the three pegged bounds above — especially whether SMB care sustains
EUR300/mo and whether the real lead-gen retainer ceiling is 2400 or higher.

Next iteration (`-v2`) worth building: add care-price elasticity and a reinvestment
term for freed hours, which would move the winner off the care-ceiling and off the
15h/wk floor toward a more realistic interior optimum.

---

*The two sections below were retrofitted 2026-07-22 so `optimize_overview.py
--prior-art upwork-independence` can read this run. They transcribe findings
already recorded above and in `results.tsv`; the only additions are two
cross-references to what `-v2` later did to these findings, so a reader of the
machine-readable path is not handed a superseded conclusion as if it still held.*

## Dead ends

- **Allocation away from 50/50 (r5, discard).** 0.45 local / 0.55 b2b scored
  194.37 vs the 200.37 winner and reverted. Do NOT inherit this as "50/50 is
  correct". v1's own reading is that Route 2 was capped by solo delivery hours,
  and `upwork-independence-gtm-v2` overturned the result outright (winner
  0.24 / 0.76) once subcontracting lifted that cap. Superseded, not a boundary
  that held.
- **The other four levers were grid-swept, not sampled** (journal stop row:
  "grid-swept + r5 allocation probe reverted"). The keeps are the v1 model's
  optimum for those fields: retainer 1200 to 2400, capacity 40 to 15, care 100
  to 300, build 2000 to 1200. A later run re-deriving them against the v1 model
  will land in the same place; the reason to move any of them is a model change,
  which is what v2 was.

## Sensitivities

- **Three levers pegged to their declared bounds; the run's own tell.** Care
  price at the EUR300 ceiling (the model has NO care-price elasticity, so care
  revenue scaled freely: highest-sensitivity input), build price at the EUR1200
  floor, retainer at what v1 called the ceiling. The answer is only as good as
  where those bounds were set. v2 confirmed the tell was right: adding care
  elasticity moved care to an interior EUR200.
- **v1's retainer "ceiling" label is wrong and should not be inherited.** The
  winner table reads "EUR 2400 (ceiling)", but the v1 scorer's declared bound is
  500-2500 (`tools/scorers/gtm-roi.py` BOUNDS), so 2400 was interior, not pegged.
  v2 subsequently moved retainer to 2500, which IS that ceiling.
- **"Work 15 h/wk" is a single-period artifact, not a recommendation.** The model
  charges full opportunity cost on every hour and cannot reinvest freed ones.
  Read insight 2 as "do not over-invest hours in a saturated channel". v2 added
  reinvestment and the same lever settled at 32 h/wk.
- **Conversion funnels are ASSUMPTION-tagged** (R1 demo to client 0.22; R2 cold
  3% x 35% x 22%). The absolute EUR/hr scales with them; the RANKING of decisions
  is more stable than the level.
