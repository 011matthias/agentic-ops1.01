---
project: meji-media
workstream: ops-radar
group: ""
spec: ""
state: active
updated: 2026-07-20
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
| Candidate ledger | live | `context/opportunity-radar.md`, seeded 2026-07-20 | weekly light pass updates | - | states: candidate / promoted / rejected / watch |
| Engine `--radar` mode | live | `context/analysis-scripts/` weekly-review engine, radar flag off the cron path | fold into `--scheduled` after 2 clean weeks | - | deterministic feeds; verified on live data 2026-07-20 |
| Weekly light pass | live | `/comd_radar meji-media light`, ~2h Monday ceiling | first full pass Mon 2026-07-27 | - | always-on lenses + one rotating deep lens |
| Deep-sweep workflow | live | `.claude/workflows/opportunity-radar.js` via `/comd_radar meji-media deep` | first run ~2026-08-01; then ~08-15 and a 09-01 pre-gate edition | - | client-parameterized; adversarial verify stage mandatory |

## Invocation

- Weekly: `/comd_radar meji-media light`
- Biweekly: `/comd_radar meji-media deep` (~Aug 1 / Aug 15 / Sep 1)

Monday auto-review (the scheduled task) is separate and unchanged; the radar
rides on top of its output.
