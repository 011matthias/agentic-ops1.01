# Vinted Reselling

Internal project: optimize clothes reselling on Vinted, starting from scratch.
Strategy basis: sourcing speed + a proprietary price/demand database beat
per-item finesse at Vinted margins (assessment 2026-09-05; feasibility probe
same day confirmed the anonymous catalog JSON surface works).

## Watcher (v1, live)

`watcher/vinted_watcher.py` polls the Vinted catalog API for the saved
searches in `watcher/searches.yaml`, records every listing into
`data/vinted.db` (gitignored), scores new listings against accumulated
comps (same search tag + brand + condition tier, 45-day window), and
pushes deal alerts via ntfy.sh (topic in `context/.env`, gitignored).

- Runs as Windows scheduled task `VintedWatcher` every 5 minutes on this
  machine (registered via `wscript watcher/run-hidden.vbs`). No server.
- First cycle per search seeds ~190 listings as a comp baseline (marked
  `seed=1`, never alerted on).
- Hourly recheck pass revisits stale listings to detect sold/removed
  (`gone_at`, `sold_flag`). This is the sell-speed dataset. The sold
  marker on 200 pages is a heuristic (UNVERIFIED against a known-sold
  fixture yet); 404/redirect detection is exact.
- Anti-bot posture: anonymous session cookie, ~1 request per 2-3 s with
  jitter, one-hour backoff on 401/403, lock file against overlapping runs.
  Buying, listing, and messaging stay manual by design (ToS and account
  risk sit with the operator).

Ops:

```powershell
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --status
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --test-notify
uv run workspace/projects/vinted-reselling/watcher/vinted_watcher.py --cycle
```

Tuning lives entirely in `searches.yaml` (searches, price caps, deal
ratio). `context/.env` holds `NTFY_TOPIC=<topic>`.

## Later (not built)

Photo-to-listing pipeline (vision LLM drafts titles/descriptions),
markdown scheduler for own listings, inventory P&L ledger, Fly.io move
if 24/7 coverage starts mattering (datacenter-IP treatment by Vinted is
unverified; today's surface was probed from a residential IP).
