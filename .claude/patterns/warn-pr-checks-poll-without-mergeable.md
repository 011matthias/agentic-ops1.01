---
name: warn-pr-checks-poll-without-mergeable
enabled: true
event: bash
action: warn
message: A PR with a merge conflict never gets CI, so 'no checks reported' can mean blocked, not pending. Read mergeable_state (gh api repos/.../pulls/N) before or inside the poll.
source: 2026-09-17 slow-path (PR #974 conflicted with a sibling's backlog append; watcher waited 30 min on checks that could not start)
created: 2026-09-17
pattern: '^(?![\s\S]*mergeable)[\s\S]*\bgh\s+pr\s+checks\b[\s\S]*\b(sleep|until|while)\b'
---
Explain what went wrong, when, and what to do instead.
