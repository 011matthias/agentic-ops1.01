# upwork-independence-portfolio-no-cold — run summary

**Result: 1,610.55 → 1,864.34 kEUR net won-client value (+253.79), 1 kept
round + 2 boundary probes, converged.** Cold email retired by owner order
2026-09-05 (u1 plan deleted in PR #667); this run re-derived the acquisition
mix with `cold_email_b2b` pinned at 0.0 rather than hand-editing the locked
asset.

## The question this run answered

The leadgen-portfolio run (2026-07) found the optimal mix WITH cold email as
the volume engine (0.378 effort, 3,013.27 kEUR). The owner retired that
channel; the asset still carried 0.378 on it. This run answers: given the
retirement, how do the freed acquisition hours re-split across the four
surviving owned channels?

## The winning mix (`acquisition-portfolio.json`)

| Channel | Effort | Clients won | Value | Role |
|---|---|---|---|---|
| linkedin_outbound | **0.3683** (~663 h) | 30.0 | EUR 0.90M | pool-saturated |
| demo_first_local | **0.2992** (~539 h) | 18.4 | EUR 0.07M | takes the freed hours (re-entered the mix) |
| content_aeo_inbound | **0.1778** (~320 h) | 25.0 | EUR 0.50M | pool-saturated |
| referral_partnership | **0.1547** (~278 h) | 15.0 | EUR 0.45M | pool-saturated |
| cold_email_b2b | **0.0** | 0 | 0 | retired (owner order 2026-09-05) |

88.4 clients, value EUR 1.92M, net EUR 1.86M. The acquisition-hours budget
binds (1,800 of 1,800 used); the serviceable cap does NOT anymore (88.4 of
110). Structure of the optimum: saturate every surviving channel whose
marginal value-per-hour beats demo's (~144 EUR/h), then give demo the whole
remainder, because even demo beats the EUR33/h reinvestment rate.

## Journal

| r | change | kEUR | verdict |
|---|---|---|---|
| baseline | prior winner with cold zeroed, nothing redistributed | 1610.55 | — |
| 1 | saturate linkedin/referral/content pools, freed hours to demo | 1864.34 | keep +253.79 |
| 2 | probe: drop demo, hours idle | 1807.20 | discarded as predicted |
| 3 | probe: linkedin 0.45 past its pool, at demo's expense | 1843.10 | discarded as predicted |

## What the retirement costs (for the owner)

The prior winner netted 3,013.27 kEUR with cold email; the best no-cold mix
nets 1,864.34. The model prices the owner's retirement decision at **~1,149
kEUR over the 30-month horizon**, almost exactly cold email's modeled channel
value (50 clients x EUR30k minus its costs). The all-Upwork status quo nets
847 kEUR, so the owned no-cold portfolio still roughly doubles the status
quo. These are ASSUMPTION-tagged planning numbers, not measurements.

## Dead ends

Two boundary probes, both discarded as predicted. A later run against this
model should not re-derive them:

- **Dropping demo-first-local no longer wins (r2: demo to 0, 1807.20).**
  Demo's ~144 EUR/h marginal beats the 33 EUR/h reinvestment once cold email
  no longer consumes the budget. This REVERSES leadgen-portfolio's r2
  verdict ("demo does not earn budget", 2735.75 there); the reversal is
  constraint-driven, and both runs are correct under their own constraints.
  Do not inherit either verdict without checking which constraint regime
  applies.
- **Overshooting a surviving pool wastes hours (r3: linkedin 0.3683 to
  0.45, 1843.10).** Pools still cap each channel; 0.3683 is linkedin's knee,
  not a peg-to-max.

## Sensitivities

- **`cold_email_b2b` = 0.0 is an OWNER ORDER, not a model verdict.** The
  model would put 0.378 back if allowed (worth ~1,149 kEUR to it). A later
  run must not silently re-add the channel; reversing the retirement is the
  owner's call, priced above.
- **The serviceable cap no longer binds** (88.4 won vs 110 deliverable), so
  ~22 delivery slots sit idle. Any lift in a surviving pool (LinkedIn 30,
  referral 15, content 25, demo 33) converts directly to value; validating
  those ASSUMPTION-tagged pools is worth more than it was under the old mix.
- **Demo's 0.2992 is the budget remainder, not an independently optimized
  lever.** It inherits whatever the saturated channels do not use; if any
  pool assumption moves, demo's share moves mechanically with it.
- **Per-client values and pools remain ASSUMPTION-tagged from GTM-v2** (B2B
  ~EUR30k, local ~EUR4k, content ~EUR20k). The ranking is more stable than
  the exact split, as in every prior run on this project.
