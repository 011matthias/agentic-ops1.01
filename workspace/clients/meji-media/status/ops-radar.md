---
project: meji-media
workstream: ops-radar
group: ""
spec: ""
state: active
updated: 2026-08-27
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

## Live state at 2026-08-27

Engine healthy (all four Make scenarios green, zero errors) but capacity-capped:
12,529 of 20,000 credits burned by 08-27, exhausting ~3 Sep with grace to ~10 Sep
against a 20 Sep reset. Gurmej APPROVED the 20k -> 40k tier move plus auto-purchase
on 08-25 (comms-log Block 31); both are still UNEXECUTED as of 08-27 18:54 UTC
(`autoPurchasingActivated: false`, `operations: 20000`).

Instantly inventory, verified 08-27 via the `campaign` scoping field (NOT
`campaign_id`, which the API silently ignores and answers workspace-wide):

| Campaign | Total | Fresh | In-seq | Done | Bounced |
|---|---|---|---|---|---|
| P1 Warm Re-engagement | 907 | 1 | 0 | 876 | 31 |
| P2A Decision-Makers | 589 | 0 | 0 | 556 | 33 |
| P2B Organisers | 434 | 3 | 20 | 384 | 30 |
| P3 Christmas Cold | 569 | 0 | 0 | 564 | 5 |
| Christmas Bookers | 983 | 1 | 2 | 942 | 39 |
| Big Companies UK | 880 | 258 | 267 | 594 | 19 |

P1/P2A/P3 are spent. The open item is `Big Companies UK` (245913f7, status -2,
created 2025-11-12, pre-dates our engagement, in no routing doc): 267 leads still
in sequence and 258 never contacted, on the SAME three mejievent mailboxes the
September corporate wave launches from. Resolve before the wave loads.
