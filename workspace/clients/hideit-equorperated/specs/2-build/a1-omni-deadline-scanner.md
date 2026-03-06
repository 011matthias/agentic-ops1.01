---
id: a1
name: Deadline Scanner
type: automation
stage: build
orchestrator: trigger-dev
version: 1.0
created: 2026-03-05
updated: 2026-03-05
trigger:
  type: cron
  schedule: "0 * * * *"
systems: [omniboard-api, macos-notifications]
last_changes: Initial spec
next_steps: Implement deadline_scanner.py, write TS wrapper, test locally
---

# A1: Deadline Scanner

Hourly cron. Reads board state from Hono API. Fires macOS notifications for cards with a `Deadline` attribute due within 24 hours.

## Flow

```
1. initialize  → validate OMNIBOARD_API_URL env var
2. fetch_data  → GET /api/board-state → extract stats.dueSoon + stats.overdue
3. transform   → group: [overdue, due-today, due-soon], deduplicate
4. execute     → osascript notification per card
5. finalize    → log count: "Sent N deadline notifications"
```

## Notification Format

```
Title:   "OmniBoard Deadline"
Message: "[OVERDUE] Fix bug #102 (Work)" or "Due in 3h: Read chapter 5 (School)"
```

osascript command:
```bash
osascript -e 'display notification "{message}" with title "OmniBoard Deadline"'
```

## Magic Attribute

Card `attributes` array must contain `{ key: "Deadline", value: "YYYY-MM-DD" }` (or ISO datetime). The scanner parses this value as a date.

## Environment Variables

```
OMNIBOARD_API_URL=http://localhost:3001/api
```

## Acceptance Criteria

- [ ] Task runs on hourly schedule in Trigger.dev
- [ ] Cards with `Deadline` in the past are flagged as overdue
- [ ] Cards with `Deadline` within 24h are flagged as due-soon
- [ ] macOS notification fires for each flagged card
- [ ] No notification if no cards are due soon
- [ ] Handles date parsing errors gracefully (skips malformed dates)
