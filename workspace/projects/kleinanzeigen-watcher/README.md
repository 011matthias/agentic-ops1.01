# Kleinanzeigen watcher

Pushes a phone notification within about five minutes of a new 180x200 bed
being listed in the city of Karlsruhe on Kleinanzeigen (formerly eBay
Kleinanzeigen). It follows the Vinted watcher's pattern: it runs on the home
line, keeps a SQLite memory of every ad it has seen, pushes via ntfy.sh, and
is run by a hidden Windows scheduled task every 5 minutes.

## How it decides

Each cycle reads page 1 of both feeds in `watcher/searches.yaml`, newest
first: the whole Schlafzimmer category in Karlsruhe, plus a "180x200" search
across all categories. The size test runs in the script, not in
Kleinanzeigen's search box, so "180 × 200", "1,80 x 2,00", "180/200", "180er"
and "1,80 m breit" all count. Sellers who give the size only in the full
description get one fetch of their ad page. Mattresses, toppers, linen, bed
frames for other sizes, wardrobes and "Suche ..." ads stay quiet.

The first cycle only learns what is already listed and sends one push linking
the current list. After 30 minutes without data (blocked, offline, page
layout changed) it pushes a warning, and it pushes again once data flows.

## Where it runs

Task `KleinanzeigenBetten`, running from the pinned worktree
`C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher` (the same one the Vinted
task uses, detached on `origin/main`, so no session's branch switch can change
the running code). The live `data/` (database, log) and `context/.env` (push
topic) are real, gitignored folders inside THAT worktree's copy of this
project, not in the main checkout; a checkout of a new `origin/main` leaves
them alone. After a merge that touches the watcher:

```powershell
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin
git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1-watcher checkout --detach origin/main
```

## Commands

```powershell
uv run watcher/ka_watcher.py --status        # health, counts, last hits
uv run watcher/ka_watcher.py --dry-run       # a full cycle, writes and sends nothing
uv run watcher/ka_watcher.py --test-notify   # a test push
uv run watcher/ka_watcher.py --check "Polsterbett 1,80 x 2,00"
```

The log is `data/watcher.log`. The push topic is `NTFY_TOPIC` in
`context/.env` (gitignored); in the ntfy app, subscribe to that topic name on
ntfy.sh.

## Changing the search

Edit `watcher/searches.yaml`: the size (`width_cm` / `length_cm`), an
optional `price_max`, or the area (append `r10` to `l9186` for a 10 km radius).
Tests: `tools/tests/test_kleinanzeigen_watcher.py`.
