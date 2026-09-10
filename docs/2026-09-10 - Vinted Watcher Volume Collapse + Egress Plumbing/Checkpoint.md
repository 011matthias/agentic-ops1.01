# Checkpoint: Vinted Watcher Volume Collapse + Egress Plumbing

**Date:** 2026-09-10
**Status:** Watcher healthy and polling; alert volume collapsed 95% by my own send budget; diagnosis complete, fix handed to the owner as a prompt

---

## Summary

The owner reported "barely any notifications coming in". He is right and the
cause is mine: the send budget shipped on 2026-09-09 cut daily pushes from about
177 to 9. The budget's shape is wrong, not just its number; it ranks each
candidate against the best 60 of a trailing 24 wall-clock hours, which is not
the same thing as sixty a day and which lets one rich day set a bar the next
morning cannot clear. The session also closed the always-on-host question with a
single probe (Vinted answers 403 to a datacenter IP on the first request) and
shipped the plumbing for the residential egress the owner chose instead.

---

## What Was Done This Session

### The catch-up gate was discarding the wrong half (PR #783)

1. After the overnight sleep the watcher found a large batch and treated the
   whole batch as stale, on the assumption that a backlog is old. Page 1 of a
   `newest_first` catalog query holds the NEWEST 48 listings, so most of the
   batch was minutes old: 223 of them under a quarter hour.
2. Replaced the count-based assumption with the real posting time
   (`CATCH_UP_FRESH_MIN = 45`), with tests that enter the branch in both
   directions. The first draft of those tests never entered the branch at all
   (the gate needs a time gap AND more than 15 new listings; the fixture passed
   2 records), which is why they were rewritten around 20-record batches.

### The always-on host, answered by probe rather than by plan (PR #784)

1. Built a throwaway Fly machine in Frankfurt and sent exactly one request.
   `egress ip: 89.222.119.20`, `GET https://www.vinted.de/` returned **HTTP 403
   Forbidden**. Not the API, not after a burst, not a challenge page: the
   homepage, refused by address class. Machine destroyed, finding written to
   memory as `reference_vinted_blocks_datacenter_ips`.
2. That closes the standing open question "datacenter-IP treatment untested" as
   NO, for Fly, Railway, Hetzner and every other cloud host.
3. Shipped the plumbing for the residential egress the owner chose instead, and
   nothing more: `EGRESS_PROXY_URL` read from `context/.env`, absent by default,
   `redact_proxy()` keeping credentials out of the logfile added the day before.
   The three consequences of switching it on live in `searches.yaml` next to the
   switch rather than in a checkpoint nobody re-reads.

### The volume collapse, measured

Everything below is a query against the live database, not an estimate.

1. **What the old volume actually was.** `listings.alerted=1` per day:
   180 (09-06), 171 (09-07), 181 (09-08), 319 (09-09), 9 (09-10 by 09:46Z).
   The owner's "50+" was a floor he never came near needing; he was receiving
   about 177 a day and was content.
2. **What the budget does.** Replaying `alert_priority` over all 561
   quality-bearing rows shows the bar climbing monotonically through a day as
   the pool fills: 50.9 at 20Z on 09-08, 88.5 by 12Z, 108.4 by 16Z, 114.7 by
   19Z. Pushes per hour on 09-09 fell 40, 26, 19, 10, 13, 11, 3, 6, 1, 0, 0. The
   last two hours of that day sent nothing at all.
3. **Why the next morning inherited it.** The window is 24 wall-clock hours
   while the active day is about 13, so the pool always spans two active
   periods. At 09:37Z today the pool was 519 rows, of which 473 were yesterday's,
   and the bar stood at 114.8: the 88.5th percentile. Today's candidates average
   91.1. Deals at quality 112.4, 110.1 and 105.8 were discarded.
4. **The ntfy wall is at 319, not at 177.** 09-09 sent 319 and then failed 147
   times between 16Z and 20Z. The three preceding days sent about 180 each with
   no failures. The quota was blown by the flood, never by the normal day, which
   makes 60 a cure aimed at the wrong number.
5. **The country gate is a separate, pre-existing drag.** By real country
   (joined through `listings`, because `alerts.country` is never written):
   FR 415 candidates / 42 sent, IT 160 / 12, NL 86 / 11, BE 52 / 7, against
   DE 248 / 154. A flat `foreign_advantage_eur: 8` on a comp median of 25 to 35
   EUR demands roughly 25 extra percentage points of discount. A listing at
   11.20 EUR against a 32.73 median, 66% below, is refused.
6. **`alerts.country` is always NULL.** `record_alert` reads country from `rec`,
   while `score_and_alert` resolves it into a local from the seller profile and
   never writes it back. Five non-null rows exist against 726 resolvable through
   the join. The snapshot table was built to feed the backtest; on this
   dimension it feeds it nothing.
7. **Ruled out.** The 120 catalog 404s were confined to 09-09 10Z-11Z and did
   not recur. Listing intake is healthy at about 1000 per hour. The scheduled
   task is Ready, last result 0, next run on time.

---

## Key Decisions Made

### Cloud hosting is not available, and this is settled by evidence

- **Choice:** One probe, one refusal, no re-probe from other regions.
- **Rationale:** A 403 on the homepage from the first request is unambiguous,
  and repeat probing is exactly the hammering this project avoids by design.

### The residential proxy is plumbing only, and the decision stays the owner's

- **Choice:** Ship the switch, off by default, with the consequences written at
  the switch; pick no provider and hold no credentials.
- **Rationale:** It converts a polite anonymous reader on a home line into
  evasion of a control Vinted deliberately set, residential pools are detected
  by behaviour as well as address, and a detection plausibly lands on the
  owner's selling account rather than on the tool. That is a business decision.

### The send budget must be a counter, not a percentile

- **Choice:** Do not merely raise `SEND_BUDGET_PER_DAY`; replace the mechanism.
- **Rationale:** "Top 60 of the trailing 24 hours" starves the late hours of
  every day and couples each day to the one before it. A count of what has
  actually been sent since local midnight has neither property. The percentile
  idea stays where it belongs, on the ringing tier, which is about interruption
  rather than volume.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/vinted-reselling/watcher/vinted_watcher.py` | Edit | Catch-up freshness gate; `EGRESS_PROXY_URL` + `redact_proxy()` |
| `workspace/projects/vinted-reselling/watcher/searches.yaml` | Edit | Header block documenting the proxy switch and its three costs |
| `tools/tests/test_vinted_watcher_session.py` | Edit | 170 tests; catch-up branch entered in both directions, proxy default-off and credential-redaction pinned |
| `workspace/projects/vinted-reselling/status/watcher.md` | Edit | The volume collapse, measured |
| `~/.claude/.../memory/reference_vinted_blocks_datacenter_ips.md` | Create | The 403 finding, so no future session re-probes it |

---

## Current Status

The watcher is running and healthy: scheduled task Ready, last run 11:40 local,
`LastTaskResult 0`, about 1000 new listings an hour reaching the database. The
database holds 56,836 listings and 860 alert rows. Nothing is broken in the
collection half, which is the half that is the asset.

The delivery half is throttled to about 5% of its former rate by a control I
added. `vinted-reselling` has no `infrastructure.yaml` and no comms log, which
is correct for an owner-operated project.

---

## Next Steps

1. Owner runs the restore prompt in a fresh session: replace the percentile send
   budget with a real daily counter, set the ceiling near 180 with headroom
   under the observed ntfy wall at 319, make the country headroom proportional
   rather than a flat 8 EUR, and fix the `alerts.country` write.
2. Decide the overnight gap. `WakeToRun` is `False`, which is why the machine
   slept 671 minutes from 21:10Z. Waking a laptop every five minutes all night
   contradicts the owner's own preference for not making his laptop the 24/7
   host, so this is his call, not a silent flip.
3. Choose a residential proxy provider with audited consent, or decide against
   it. The plumbing is shipped and inert until a URL exists.
4. `WARN: recheck discarded, 25/25 pages carried no status plugin` recurs in the
   log and is unexamined. It is the source of the `gone` and `sold-flagged`
   data that the round-trip gate depends on.
5. Build the round-trip ledger and start the 30-trip run. `my_listings` is at
   0 rows and the comp median has never been checked against a realised price.

---

## Context for Next Session

### Files to Read First

- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\projects\vinted-reselling\status\watcher.md`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\projects\vinted-reselling\watcher\vinted_watcher.py` (`alert_priority`, `alert_quality`, `score_and_alert`, `record_alert`)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\projects\vinted-reselling\watcher\searches.yaml`

### Open Questions

- What is ntfy.sh's documented free-tier daily limit? The observed wall is
  between 181 (fine) and 319 (refused). The exact number decides the ceiling.
- Does a foreign listing actually resell worse, or is the country penalty an
  assumption? Only 3 trustworthy `gone` events exist; not yet measurable.
- Should the night gap be closed by waking the laptop, by accepting it, or by
  the residential proxy plus a second machine?
- `alerts.country` has been NULL since the table was created, so the backtest
  cannot separate domestic from foreign for any row already recorded. Is that
  worth a backfill from `listings.country`, or is forward-only enough?

### Working Notes

The replay script that produced the bar trajectory is the fastest way back into
this: read every `alerts` row with a non-null quality in time order, and at each
one recompute `sorted(pool_last_24h, reverse=True)[59]`. It reproduces the
production decision exactly, which is what makes it trustworthy as a
before-and-after instrument for any replacement budget.

The hypothesis that was wrong and cost a detour: that the collapse would
self-heal once yesterday's flood aged out of the 24-hour window. It partly does,
but the replay shows the bar climbing again within each day as that day's own
pool fills, so the late hours starve every day regardless. Measuring the
trajectory rather than the current value is what settled it.

`listings.alerted` is the only record of pushes before 2026-09-08T19:50Z, and it
agrees exactly with `alerts.sent` on the day both exist (319 and 319), which is
what makes the 180/171/181 series usable as the definition of "old volume".

### Reference Materials

- Memory `reference_vinted_blocks_datacenter_ips` (the 403 probe, do not repeat)
- Memory `reference_vinted_has_no_hashtags`
- `docs/2026-09-09 - Vinted Watcher Precision + Portability/Checkpoint.md`

---

## How to Continue

Read the status file, then run the owner's restore prompt in a fresh session
against a worktree cut from `origin/main`. The watcher itself runs from
`C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher`, pinned detached to
`origin/main`, so any merge that touches the watcher needs that worktree pulled
forward before the change is live.

---

## Strategic Feedback

### What Worked Well This Session

- The Fly probe. A question that had been open for days as "untested" was closed
  in one request, and the answer was the opposite of the plan everyone assumed.
  Probing beat planning by a wide margin here.
- Replaying the production decision over historical rows, rather than reading
  the current value of the bar. The current value looked defensible; the
  trajectory did not.

### Suggestions

- Every cap this project has added was verified as "the code does what the
  constant says" and never as "the constant produces the volume the owner
  asked for". A one-line daily counter printed by `--status` (pushes today,
  pushes yesterday, pushes per day over the last week) would have made this
  collapse visible the same morning instead of after the owner noticed. Build
  it as part of the fix, not after it.

### System Health

- Autonomy: 1 human intervention (the owner reporting the collapse). It should
  have been zero; the instrument to catch it does not exist yet, which is what
  the suggestion above is for.
- The `alerts` table was built so nothing about a scoring decision would be
  lost, and one of its columns has been silently NULL since creation. A snapshot
  table nobody reads back is a snapshot table nobody can trust.
