---
project: vinted-reselling
workstream: watcher
group: ""
spec: ""
state: active
updated: 2026-09-06
---

Sourcing watcher + price/demand database. Polls Vinted catalog API for 9
staple-brand searches, records all listings to SQLite, alerts deals via ntfy.

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Poller + comp DB | live | Deployed as scheduled task, 5-min cycle | Watch first week of data quality | - | README |
| Deal scoring | live | Ratio 0.62 vs comp median, min 6 comps | Recalibrate after 2 weeks of gone-data | - | searches.yaml settings |
| ntfy alerts | live | Topic in context/.env | User subscribes phone app | user-side | README ops |
| Gone/sold detection | live | 404/redirect exact; 200-page sold marker heuristic | Verify marker against a known-sold item | - | vinted_watcher.py recheck_gone |
| Fly.io 24/7 move | idea | Not started | Only if PC uptime proves limiting | datacenter-IP treatment unverified | README Later |
