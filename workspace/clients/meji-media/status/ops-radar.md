---
project: meji-media
workstream: ops-radar
group: ""
spec: ""
state: active
updated: 2026-08-25
---

# Meji Media / Opportunity Radar

The repeatable method for finding leaks, gaps, and ROI opportunities from live
state with slight weekly effort. This file is the durable, value-free anchor:
it names where every part of the method lives so a fresh session (or machine)
can rediscover it without prior context. The method's content and all client
data live in the gitignored `context/`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Lens catalog + scoring rubric | live | sec J of `context/weekly-review-blueprint.md` (J1 lenses, J2 rubric, J3 cadence) | recalibrate rubric at first deep sweep | - | 12 lenses capped, one-in-one-out |
| Candidate ledger | live | `context/opportunity-radar.md`, seeded 2026-07-20; RAD-29 added 2026-08-25 | prune rejected/promoted rows at next sweep | - | states: candidate / promoted / rejected / watch |
| Engine `--radar` mode | live | `context/analysis-scripts/` weekly-review engine, radar flag off the cron path | fold into `--scheduled` after 2 clean weeks | - | deterministic feeds; verified on live data 2026-07-20 |
| Weekly light pass | dormant | never ran; ledger `last_light_pass` still reads the 2026-07-20 seed | restart Mon 2026-08-31 or retire the cadence | Aug was the unbilled observation month | always-on lenses + one rotating deep lens |
| Deep-sweep workflow | dormant | one run only (`weekly-reviews/2026-07-20-deep-sweep.md`); the planned 08-01 and 08-15 editions did not run | the 09-01 pre-gate edition is the one that matters, ahead of the September judgment point | - | client-parameterized; adversarial verify stage mandatory |

## Invocation

- Weekly: `/comd_radar meji-media light`
- Biweekly: `/comd_radar meji-media deep` (next: the 09-01 pre-gate edition)

Monday auto-review (the scheduled task) is separate and DID keep running
unattended through August; `weekly-reviews/` holds 07-26, 08-10, 08-16 and 08-23,
and the daily reply-SLA flags ran to 08-21. The radar cadences that lapsed are the
judgment passes that ride on top of that output, not the automated pull itself.

## Live state at 2026-08-25

The engine is healthy (all four scenarios green, zero errors) but capacity-capped:
the Make org burned 9,036 of 20,000 credits in the first 4.2 days of the 20 Aug
cycle, exhausting ~29 Aug with grace to ~5 Sep against a 20 Sep reset. Owner is
executing a 20k -> 40k tier move plus auto-purchase, with a client objection window
to Wed 2026-08-26 evening (comms-log Block 31). P1's Instantly list is DEPLETED
(0 fresh leads); P2 corporate copy is approved and locked, B5-gated for the
September go.
