---
project: vinted-reselling
workstream: watcher
group: ""
spec: ""
state: active
updated: 2026-09-08
---

Sourcing watcher + price/demand database. Polls Vinted catalog API for 9
staple-brand searches, records all listings to SQLite, alerts deals via ntfy.

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Poller + comp DB | live | v2 session-hardening shipped 2026-09-08; ~27k listings | Watch data quality | - | README, api-notes |
| Session management | live | Clean-slate refresh, proactive 45-min renewal, 401/403 split, SessionWall abort | - | - | api-notes incident section |
| Deal scoring | live | 0.55 ratio, 8 comps, 8 EUR floor, garment-class + kids-aware comps | Owner rates alert quality as weak; next round via improvement-prompt.md | - | searches.yaml |
| Gone/sold detection | live | Rebuilt: proven-session precondition, wall-redirect abort, 40% batch ceiling, gone_source provenance, re-sight clears verdicts | Accumulate trusted outcomes (~2 weeks) | - | 375 pre-v2 rows were fabricated + reset 2026-09-08 |
| Liveness | live | Stall alert to phone >45 min, 6h re-nag; vbs propagates real exit codes | - | - | tested live 2026-09-08 |
| Backtest calibration (/comd_optimize) | planned | Scorer design agreed | Wait for a few hundred gone_source events | outcome data | STRATEGY.md |
| Next optimization round (8 points: fake detection, feedback loop, sizes S/M/L, women's jeans, DE-first, brand rules, schema, hashtags) | queued | Owner-approved prompt ready | Owner pastes improvement-prompt.md in a fresh session | - | improvement-prompt.md |
| Fly.io 24/7 move | idea | Only if PC uptime proves limiting | - | datacenter-IP treatment unverified | STRATEGY.md |
