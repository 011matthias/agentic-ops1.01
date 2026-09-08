# Vinted Reselling

Internal project: optimize clothes reselling on Vinted, starting from scratch.
The operating thesis: at Vinted margins, sourcing speed + a proprietary
price/demand database beat per-item finesse. Buying, listing, and messaging
stay manual; automation covers watching, comparing, calculating.

## Folder map

| Path | What |
|---|---|
| `STRATEGY.md` | Leverage assessment, economics, calibration plan |
| `api-notes.md` | Verified Vinted API surface, session mechanics, incident log |
| `improvement-prompt.md` | Ready-to-paste prompt for the next optimization round |
| `watcher/vinted_watcher.py` | The watcher (poll, score, alert, gone-detection) |
| `watcher/searches.yaml` | Tunable config: searches, price caps, thresholds |
| `watcher/run-hidden.vbs` | Task wrapper; waits and propagates the real exit code |
| `status/watcher.md` | Element-level status roll-up |
| `data/` (gitignored) | `vinted.db` (the asset), cookies, lock. Never delete the DB |
| `context/.env` (gitignored) | `NTFY_TOPIC=<topic>` for phone alerts |

Tests: `tools/tests/test_vinted_watcher_session.py` (offline, mock transport;
runs in the CI hooks job).

## Runtime

Windows scheduled task **VintedWatcher**, every 5 minutes, this machine:
`wscript watcher\run-hidden.vbs "<uv> run <watcher> --cycle"`. It reads
`searches.yaml` fresh every cycle, so config edits need no restart. Only runs
while the PC is on.

```powershell
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --status       # health + counts
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --cycle        # manual cycle
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --test-notify  # push test
```

`--status` shows `health: OK/STALLED`, token expiry, and any active backoff.
A stall (>45 min without a successful poll) pushes a "Vinted watcher steht"
alert to the phone, re-nagging every 6 h while the outage lasts.

## Alert gate (order matters)

Backlog guard (>15 new per search per cycle = catch-up, data only) → max 3
alerts per search per cycle → per-listing filters (min price, per-search
price cap, garment class != other, no kids items, no junk titles, brand +
condition known) → comp scoring: total price <= `deal_ratio` x median of
comps sharing search tag + brand + condition tier + garment class (min
`min_comps`, window `comp_window_days`, kids excluded from pools).

## Session + outage hardening (v2, 2026-09-08)

Vinted's anonymous token lives 24 h and is only reissued to a cookie-less
request. v2 therefore: clears the jar before every refresh, renews 45 min
before expiry, treats 401 (short backoff) differently from 403/429 (hard,
escalating, Retry-After-aware), aborts the whole cycle on a wall via
SessionWall, and never lets `recheck_gone` write verdicts unless the session
proved itself with a real API success in the same cycle. Batches reading
>40% gone are discarded as systemic. Details + incident: `api-notes.md`.
