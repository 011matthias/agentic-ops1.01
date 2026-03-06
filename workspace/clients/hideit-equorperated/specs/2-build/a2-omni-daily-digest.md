---
id: a2
name: Daily Digest
type: automation
stage: build
orchestrator: trigger-dev
version: 1.0
created: 2026-03-05
updated: 2026-03-05
trigger:
  type: cron
  schedule: "0 8 * * *"
systems: [omniboard-api, macos-notifications]
last_changes: Initial spec
next_steps: Implement daily_digest.py, write TS wrapper
---

# A2: Daily Digest

8am daily cron. Summarizes yesterday's completions + today's workload as a macOS notification. Also appends to `digest.jsonl` for persistence.

## Flow

```
1. initialize  → validate OMNIBOARD_API_URL
2. fetch_data  → GET /api/board-state
3. transform   → compute digest:
                   - completed_yesterday: cards in 'completed' column, updatedAt between yesterday 00:00-23:59
                   - in_progress: cards in 'in-progress' column (count)
                   - todo_today: cards in 'todo' column (count)
                   - backlog: cards in 'backlog' column (count)
                   - overdue: stats.overdue (count)
4. execute     → fire macOS notification with digest summary
               → append JSON line to digest.jsonl
5. finalize    → log digest summary
```

## Notification Format

```
Title:   "OmniBoard — Good morning!"
Message: "Yesterday: 3 completed. Today: 2 in progress, 5 todo, 1 overdue."
```

## Digest Log (`digest.jsonl`)

Each line is a JSON object:
```json
{"date": "2026-03-05", "completed_yesterday": 3, "in_progress": 2, "todo": 5, "backlog": 12, "overdue": 1, "ts": "2026-03-05T08:00:00Z"}
```

Stored at `python/automations/digest.jsonl` (relative to automations/ root).

## Environment Variables

```
OMNIBOARD_API_URL=http://localhost:3001/api
```

## Acceptance Criteria

- [ ] Task runs at 8am daily
- [ ] Notification shows correct counts
- [ ] `digest.jsonl` grows by one line per day
- [ ] "completed yesterday" only counts cards updated yesterday (not older)
