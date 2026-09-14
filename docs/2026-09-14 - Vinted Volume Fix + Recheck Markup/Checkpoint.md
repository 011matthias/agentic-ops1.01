# Checkpoint: Vinted Volume Fix + Recheck Markup

**Date:** 2026-09-14
**Status:** Both fixes shipped and verified live on 09-11. Collection has been down since 09-14T19:35Z behind a new API wall.

---

## Summary

Two defects fixed and proven on the running watcher: the send bar was ranking each morning's finds against the previous day's finished field (9 pushes on 09-10, none loud), and the recheck had been reading every item page as a wall since 09-09 because Vinted reshaped the page. The owner's "everything is too expensive" was then answered with measurement rather than a config change. Since tonight's restart the API refuses this client entirely, which is the one thing that has to be settled before any of it produces data.

---

## What Was Done This Session

### PR #794 — the send bar (merged 09-10, `708ca10a`)
1. Ranking pool is the local day, not a rolling 24 hours, and `notify_failed` rows never enter it. The 08:20Z pool held 528 rows, 470 from the previous day; 147 more were messages ntfy had refused.
2. Budgets recalibrated against the real 09-09 stream (957 scored candidates): `SEND_BUDGET_PER_DAY` 60, `RING_BUDGET_PER_DAY` 15 to 6. A day-scoped rank with budget 60 yields ~202 pushes, not 60, because early candidates pass while the field is small.
3. `HARD_SEND_CEILING = 250` as a flat cutout on real pushes since local midnight.
4. Catch-up gate: the count condition removed entirely; the gap decides whether to screen, `CATCH_UP_FRESH_MIN` decides what survives.
5. `alerts.country` now travels in `ctx` instead of being read off `rec`; 1194 of 1226 rows had been NULL while the gate used a real country.
6. Country gate reads criterion 5 as written (`foreign_advantage_basis: median`), strict reading kept as `deal_gate`.
7. ntfy: status *and* body logged; code 42908 latches sends until the UTC rollover; held candidates record `ntfy_quota`, not `notify_failed`.
8. Volume instrumentation: per-cycle `pool_n / send_bar / ring_bar / pushes_today`, and a `--status` row for today / yesterday / 7-day mean with the loud share.

### PR #809 — the recheck parser (merged 09-11, `72b3bed0`)
1. Found by differential probe: a known-sold page against a known-live one through the watcher's own session. Vinted sorted each plugin object's keys alphabetically, so `data` (carrying the theme) precedes `name`, and live pages dropped `item_status` in favour of `buy` / `make_offer` / `ask_seller`.
2. The reader finds a plugin's flat data block by the adjacent name, on either side, so a third reordering will not blind it. Sold = `buyer_item_status` theme SUCCESS; alive = `buy` plugin present; reserved without a buy button = closed.
3. Both page shapes pinned as real-byte fixtures in `tools/fixtures/vinted-item-page/`.
4. Second defect in the same queue, visible only once the reader worked: tier 1 had no `last_seen` guard, so it would have re-bought the same 25 oldest alerted rows every hour while ~1,100 waited.

### The price-band question (analysis only, no config changed)
Four adversarial refuters plus a completeness critic over the read-only DB copy. Findings in `status/watcher.md`; the three questions it raised are unanswered.

### Outage diagnosis (tonight)
Probed the API directly after finding 16 consecutive dead cycles.

---

## Key Decisions Made

### Budgets 60 / 6 rather than the brief's 60 / 15
- **Choice:** Ring budget cut to 6.
- **Rationale:** Replayed on 09-09, ring 15 produces 47 loud alerts against the owner's satisfied 27; ring 6 produces 25.

### Calibrated against the stream *with* the country give-back
- **Choice:** Treat the two changes as one stream, not two.
- **Rationale:** The brief expected the country give-back to change which offers arrive, not how many. Measured, it does both: 479 to 957 candidates, 167 to 202 pushes. The bar absorbs most of it, not all.

### A1 binds, A4 does not
- **Choice:** Keep 140-220 pushes/day as the acceptance criterion and treat A4's 0.35 pass-rate as superseded.
- **Rationale:** 0.35 of 957 candidates is 335 pushes, far above A1's ceiling. The 0.35 came from the pre-country stream, where 09-09 lands at exactly 0.35.

### Price-band complaint: no lever pulled
- **Choice:** Report the measurement and ask three questions instead of capping prices.
- **Rationale:** A cap changes the mix, not the volume (the pool refills), and it would end the Agolde and Mother searches the owner added himself on 09-08. Which knob is right depends on what he means by "20 EUR".

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/vinted-reselling/watcher/vinted_watcher.py` | edit | Both fixes: day-scoped ranking, budgets, ceiling, catch-up, country in ctx, ntfy quota latch, volume logging, plugin reader, tier-1 guard |
| `workspace/projects/vinted-reselling/watcher/searches.yaml` | edit | `foreign_advantage_basis` with the 622-row measurement at the line |
| `tools/tests/test_vinted_watcher_session.py` | edit | 170 to 189 tests |
| `tools/tests/test_vinted_outcomes.py` | edit | 26 to 36 tests |
| `tools/fixtures/vinted-item-page/item_{sold,alive}_v2.snippet.html` | add | Real bytes of the 2026-09-11 page shape |
| `workspace/projects/vinted-reselling/status/watcher.md` | edit | Both fixes, the price-band section, the outage |

---

## Current Status

**Collection is dead.** Two separate things happened after 09-11T18:11Z:

1. The machine was off for 73 hours (no log lines at all on 09-12 or 09-13). `WakeToRun=False` is a standing owner decision, not a fault. The liveness alert fired correctly on restart: `no successful poll for 4404 min; operator alerted`.
2. Since the 09-14T19:35Z restart, every cycle fails. 16 cycles, all 12 searches, 100% refused. The session mints fine (token valid to 09-15T19:35Z) and the homepage answers 200, but `/api/v2/catalog/items` and `/api/v2/items/{id}` both refuse.

The refusal has a shape worth knowing: **403 with an HTML block page for a plain request, 404 when `Accept: application/json` is sent** — which is exactly what `api_get` sends. So the 403 branch never fires, no backoff is ever set, and the watcher has been putting 12 requests every 5 minutes into a wall for over an hour (~190 refused requests). That is the same failure shape as the 147 ntfy retries fixed in #794, on the other side of the system.

Ops status: `vinted-reselling` has no `infrastructure.yaml` and no comms log; neither applies to an internal project.

**What did land before the lights went out.** The 09-11 acceptance run, first clean day: 204 pushes, 28 loud, 66 pushes and 8 loud in the 08-12Z morning. A1 (140-220) pass, A2 (15-35) pass, A3 (>=25 and >=3 loud) pass, A6 one `notify_failed` rather than zero, A7 both halves pass (713 of 869 alert rows carry a country; `listings.country` at 2,568 and growing). A4 reads 0.24, which is the criterion this session argued should be restated.

**First outcome data on alert candidates, ever.** Three recheck runs on 09-11 resolved 37 of them: 32 sold. By buy-price band the sell-through shows no gradient (<10 1/1, 10-15 9/9, 15-20 7/10, 20-30 5/7, 30-50 7/7, 50+ 3/3). Two caveats that matter more than the numbers: the "~69h to sale" figure is an artifact of when the recheck ran, not a velocity measurement, and suppressed candidates sold at 9/10 against pushed at 23/27, which is the first hint that the ranking is not demonstrably picking winners. 3,022 alerted rows remain unresolved.

---

## Correction, same evening

The "API wall" reading above is wrong, and the status file carries the corrected
version. The 403s came from probe requests that omitted `Accept:
application/json`; Vinted renders an HTML error page to a browser-shaped request
to an API path. With the header `api_get` actually sends, the picture is:
`/api/v2/catalog/items` returns 404 with the app's own JSON error
(`code 104, not_found`) for every parameter shape tried, while
`/api/v2/catalog/filters` on the same `search_text`, `/api/v2/users/{id}`, and
the web item page all return 200. Nonsense API paths return Vinted's HTML 404
page, so the JSON-versus-HTML difference proves the route still exists and is
refusing the query at application level.

So the client is not blocked and the session is healthy: the catalog endpoint is
retired. Three consequences replace next steps 1-3:

- Treating 404 as a wall would be the wrong fix. Nothing is being walled; a
  backoff would only quiet the retries, which at 12 requests per 5 minutes is
  the smaller problem.
- The recheck path works end to end (verified: a live item page read as `sold`
  with the correct price). It is blocked solely by `recheck_gone`'s
  `session_proven` gate, which only a successful catalog poll can set. That
  gate's premise, "a wall on the catalog means a wall everywhere", is falsified
  here, and 3,022 rows of perishable outcome data sit behind it against a 09-16
  cliff. This is now the most urgent item and it is independent of the catalog.
- The search page `/catalog?search_text=` is server-rendered and carries every
  field the watcher needs, but at 7.2 MB per search (5.7 MB for the RSC
  variant); no lighter payload was found. At the current cadence that is ~1 GB
  an hour, 250x today, which breaks the politeness constraint. The mobile app's
  API base and headers are the next lead before that parser is considered.

## Next Steps

1. **Decide whether to pause the scheduled task** while the wall stands. It is currently firing 144 refused requests an hour. Reversible either way; the cost of pausing is no collection, the cost of not pausing is hammering a wall that may be behaviour-scored.
2. **Diagnose the wall.** Homepage 200 and API 403/404 with a valid token points at a client-level block rather than an expired session. Compare the browser's own request headers against `new_client()`'s (UA, `x-anon-id`, `x-csrf-token`, `Accept-Language`); the Edge CDP path in `reference_user_edge_cdp_9222` gives the ground truth cheaply. See also `reference_vinted_blocks_datacenter_ips` (403 on the first request from datacenter IPs) — this is the home line, so it is behaviour or a flagged home IP, not IP class.
3. **Treat a 404 on the catalog as a wall in `api_get`.** Whatever the cause, a refusal that dodges the backoff branch and lets the cadence continue at full rate is a defect on its own. Same latch shape as the ntfy 42908 fix.
4. **Resume the outcome drain once polling works.** 3,022 alerted rows at 25/h. `RECHECK_MAX_AGE_D = 10` means the 09-06/07/08 cohorts (184/174/180 rows) lose the sold-versus-gone distinction from 09-16, i.e. this is already partly lost.
5. **Answer the three price-band questions** (below) before touching `price_max` or the margin term.

---

## Context for Next Session

### Files to Read First
- `workspace/projects/vinted-reselling/status/watcher.md` — the price-band section and the element table
- `workspace/projects/vinted-reselling/watcher/vinted_watcher.py` — `api_get` (the 404 gap), `item_page_verdict`, `alert_priority`
- `workspace/projects/vinted-reselling/data/watcher.log` — tonight's 16 dead cycles

### Open Questions
- Does "items over 20 EUR" mean the buy total including the buyer fee (what the push shows) or the resale value?
- Is the 15 EUR floor net or gross? Both of the owner's accepted flips net 8-12 EUR, below his stated floor.
- Which day shaped the impression? 09-09 and 09-10 were heavier on loud expensive pushes than 09-11.
- Is the wall temporary (rate-scored, decays) or a durable client block? Unanswerable until step 2.

### Working Notes
- **The wall, precisely.** `Accept: application/json` to `/api/v2/catalog/items` returns 404 regardless of parameters (with, without `order`, `search_text` only, no params at all). The same path without that header returns 403 plus an HTML page. `/api/v2/items/{id}` behaves identically, so the recheck is walled too, not only the catalog. `/` returns 200 and mints a token. Probe script kept at `.scratch/catalog_probe.py`.
- **Why the volume numbers are trustworthy.** The simulation harness replays the real alerts rows through the proposed send path (`.scratch/sim.py`, `sim2.py`, `replay_levers.py`) and reproduced the live 184/25 for 09-11 exactly before being used to choose budgets.
- **Lever replay, already done, do not redo.** Price cap on today's pool: 20 EUR gives 174 pushes and 0% expensive, 25 gives 170 and 21%, 30 gives 175 and 31% — the mix moves, the volume does not, because the pool refills with cheap candidates. A net-margin floor is the wrong direction entirely: it removes 79 of 103 cheap pushes and 8 of 81 expensive ones (net is gross minus a constant, r = 0.9997). Lowering the margin cap in `alert_quality` barely moves the loud tier (cap 30 still leaves 15 of 28 loud above 20 EUR).
- **Two structural findings not yet acted on.** The comp query has no `size_class`, which inflates the expensive bands' medians by 6-8% (p25 9-19%) relative to the cheap ones. The literal country gate cannot fire above an 18 EUR comp median, because `total <= 0.55 * median` already implies it; today it suppressed 3 alerts, all under 10 EUR.
- **Dead ends.** `views` is 0 on all 90k rows. Raw `last_seen - first_seen` as a velocity proxy is a search-volume artifact (the newest_first window is 2 polls deep for nike/adidas/tnf, 3-6 for the rest). The 2.99 EUR camelCase amount in the item payload is not yet tied to a shipping quote; the `shipping` plugin carries only the item id.

### Reference Materials
- PR #794 https://github.com/011matthias/agentic-ops1.01/pull/794
- PR #809 https://github.com/011matthias/agentic-ops1.01/pull/809
- Workflow journal (four refuters + critic): `subagents/workflows/wf_8b989873-482/journal.jsonl`

---

## How to Continue

Start at the wall: read tonight's log tail, then run `.scratch/catalog_probe.py` to see whether the refusal persists. If it has decayed, the first job is the `api_get` 404 gap so the next one backs off instead of hammering, then let the recheck drain the 3,022 open rows. If it has not, compare headers against a real browser session over CDP before changing anything else. The price-band work is blocked on the owner's three answers, not on code.

---

## Strategic Feedback

### What Worked Well This Session
- Every fix was regressed at its wiring point and watched go red before shipping: 8 mutations for #794, 4 for #809, including the exact one-line trap the brief warned about (`rec["country"] = country`, which would have silently stopped filling `listings.country`).
- Diagnosing the recheck by fetching a known-sold page against a known-live one, rather than reasoning about the parser. Two requests settled what three days of "wall" log lines had obscured.
- Measuring the brief's own premises instead of implementing them: the country give-back does add pushes, and A4 conflicts with A1. Both were reported with numbers rather than quietly absorbed.

### Suggestions
- Generalize the ntfy 42908 latch. The pattern "a refusal that does not stop the asking" has now caused three separate incidents in this project: 147 ntfy retries, 39 discarded recheck batches, and tonight's ~190 refused catalog requests. A single helper that records a refusal class with a cooldown, applied at every outbound boundary, would have caught all three.

### System Health
- The liveness alert is the one guard that worked unaided tonight: it detected 4,404 minutes of silence on restart and told the operator. Everything else in the failure path was silent.
- Autonomy: 0 human corrections across three user-initiated tasks (build, analyse, checkpoint). No intervention was needed to unblock work.
