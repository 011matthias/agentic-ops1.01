# upwork-independence-gtm-v2 — run summary

**Result: 687.58 → 2,123.84 kEUR total 30-month contribution surplus, 8 rounds,
converged.** Score = total contribution margin above the ~EUR33/hr hourly-work
fallback, over a 30-month horizon (v2 metric; see the note on comparability
below). The winner cleared the pessimistic stress floor on every kept round
(627.83 kEUR pessimistic surplus, engine-enforced), so it is robust, not
optimism-only.

**Headline: v1's strategic direction survives the more realistic model.** The
two levers v1 pegged to their bounds were artifacts, and both corrected to
interior values once the model resisted; a third finding (allocation) turned out
richer than v1 could see.

## Not comparable to v1's score

v1 scored EUR margin per working hour (winner 200.37). v2 scores TOTAL surplus
in kEUR, because under freed-hour reinvestment a per-hour metric rewards a
mono-channel corner and treats "reinvest at the hourly rate" (the Upwork grind)
as neutral. The two numbers are different metrics; compare the WINNERS by their
decisions, not their scores. (Metric change reviewed and signed off on PR #307.)

## Winning plan (`gtm-plan.json`)

| Decision | v1 winner | v2 winner | What moved and why |
|---|---|---|---|
| capacity / week | 15 h | **32 h** | v1's 15 was a no-reinvestment artifact; 32 is the knee that saturates both channels |
| route split (local / b2b) | 0.5 / 0.5 | **0.24 / 0.76** | subcontracting makes B2B scale; tilt hard, but keep local (see mixed-not-corner) |
| Route-1 segment | handwerk | handwerk | largest reachable pool (60/yr), unchanged |
| Route-1 build price | 1200 (floor) | **1200 (floor)** | loss-lead the build survives |
| Route-1 care price | 300 (ceiling) | **200 (interior)** | care elasticity un-pegs it from the ceiling |
| Route-2 geo / channel | UK / cold_email | UK / cold_email | legal + viable channel, unchanged |
| Route-2 retainer | 2400 | **2500 (ceiling)** | price at the top of what the channel bears |

Winner economics: 32 h/wk → 3,840 h over the horizon, of which **3,625 h are
productive and 215 h reinvest** (idle, neutral). Route 1 saturates its handwerk
pool at ~41 clients (EUR 167k). Route 2 saturates the **market cap** at 62.5
clients (EUR 2.19M revenue, EUR 105k subcontractor cost), delivered by
subcontractors under ~1.5 h/client/mo of oversight. Total surplus EUR 2.12M.

## Kept changes (the journal)

| r | change | score (kEUR) | delta |
|---|---|---|---|
| 1 | care price 300 → 200 | 716.39 | +28.81 |
| 2 | capacity 15 → 32 h/wk | 1386.8 | +670.41 |
| 3 | allocation 0.5/0.5 → 0.24/0.76 b2b | 2038.9 | +652.10 |
| 4 | retainer 2400 → 2500 | 2123.84 | +84.94 |
| 5 | PROBE capacity 32 → 40 | 2123.84 | DISCARD (identical: the knee) |
| 6 | PROBE allocation → b2b 1.0 | 1987.25 | DISCARD (mixed beats corner) |
| 7 | PROBE build 1200 → 1500 | 2123.11 | DISCARD (floor is optimal) |
| 8 | PROBE care 200 → 250 | 2116.48 | DISCARD (200 is a peak) |

The four value moves are all keeps; the four probes are all discards that map
the boundaries (the capacity knee, the mixed-not-corner allocation, the build
floor, the care interior peak).

## Does the v1 direction survive?

Yes, on all three conclusions, with the numbers corrected:

1. **Commit to B2B — survives and strengthens.** v1 kept 50/50 (its allocation
   probe to 0.55 b2b was discarded, because Route-2 was solo-service-capped at
   ~5 clients). Once subcontracting lifts that cap, B2B scales to the market
   ceiling (62.5 clients), and the optimum tilts to **76% B2B**. The insight
   sharpens: B2B is no longer service-capacity-limited by YOUR hours; subcontract
   delivery so the **market**, not your delivery time, is the binding constraint.
2. **Price at the top the channel bears — survives.** Retainer → 2500 (ceiling),
   as in v1. Retainer elasticity is mild, so pricing high still nets more.
3. **Loss-lead the build, monetize the annuity — survives.** Build → 1200 floor
   (probe up discarded). Route-1 remains a recurring-care business, not a
   per-project one.

## Two v1 artifacts, corrected

- **Care price: 300 (ceiling) → 200 (interior).** v1 had no care-price
  elasticity, so care pegged to the ceiling. With elasticity, uptake/retention
  falls faster than price past ~EUR200/mo. Both neighbours are worse (r1: 300
  worse; r8: 250 worse), so 200 is a true peak, not a bound.
- **Capacity: 15 (floor artifact) → 32 (knee).** v1 charged full opportunity
  cost on every hour with no reinvestment, so the per-hour metric drove capacity
  down. With subcontracting (added hours buy served clients) and reinvestment
  (idle hours are neutral, not a drag), capacity rises to the point that
  saturates both channels: ~32 h/wk. Beyond 32 is neutral (r5: cap 40 is
  identical), so read this as "work ~32 h to saturate; reinvest the rest," not
  "work exactly 32."

## One new nuance the richer model surfaces

**Mixed allocation beats the corner.** Dropping local entirely (b2b = 1.0) costs
~137 kEUR of surplus (r6 discard: 1987 vs 2124). Route-1's care annuity earns
above the opportunity rate up to its pool, so the optimum keeps ~24% of hours on
local. A per-hour metric would have gone to the all-B2B corner; total surplus
keeps the annuity. Concretely: run B2B as the scalable core AND keep a small
local-SMB care book on the side.

## Model limitations the winner leans on (validate before acting)

The absolute surplus scales with the ASSUMPTION-tagged params; the RANKING of
decisions is more stable than the EUR figure. The winner now leans hardest on:

- **The subcontracting economics (v2-new, highest new sensitivity).** The whole
  B2B scale-up rests on being able to subcontract delivery at ~EUR20/hr with
  only ~1.5 h/client/mo of your oversight (~4x leverage). If real oversight is
  heavier or good subcontractors cost more, Route-2's ceiling drops. Validate
  against an actual subcontracted delivery arrangement before assuming 62.5
  serviceable clients.
- **The Route-2 market cap (25 clients/yr, now the BINDING constraint).** The
  winner is market-capped at 62.5 clients over the horizon, so this input now
  sets the entire Route-2 revenue. v1's answer did not depend on it (it was
  service-capped far below); v2's does. This is the single highest-sensitivity
  input for the winner.
- **Retainer 2500/mo for ~6 delivered h/mo** is value-priced, not hourly. Mild
  elasticity keeps it at the ceiling; a harder real-world ceiling moves it.
- **Care 200/mo** assumes the elasticity shape (ref 150, k 0.6). The interior
  optimum is robust to the exact shape, but the LEVEL (200) tracks the reference.

## What a human should review

The direction is trustworthy and unchanged from v1: **commit to B2B lead-gen as
the scalable core (76% of hours), subcontract delivery so the market is the
limit, price at the top the channel bears, and run a smaller local-SMB
recurring-care book alongside (loss-lead the build).** Before acting on the
specific numbers, pressure-test the subcontracting arrangement (can you really
get 4x leverage on delivery?) and the UK/US solo market size (is ~25 qualified
clients/yr real?), since those two now drive the result.

Next iteration (`-v3`) worth building only if the subcontracting arrangement is
validated: make `acq_fraction` and a subcontract-intensity decision part of the
plan (currently locked), and add a management span-of-control cost so Route-2
scale has a diminishing return beyond a solo's oversight bandwidth rather than
stopping only at the market cap.
