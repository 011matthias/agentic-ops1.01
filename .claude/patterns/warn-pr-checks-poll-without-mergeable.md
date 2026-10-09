---
name: warn-pr-checks-poll-without-mergeable
enabled: true
event: bash
action: warn
message: A PR with a merge conflict never gets CI, so 'no checks reported' / 'no runs' can mean blocked, not pending. Read mergeable_state (gh api repos/.../pulls/N or gh pr view --json mergeable) before or inside the poll.
source: 2026-09-17 slow-path (PR #974 conflicted with a sibling's backlog append; watcher waited 30 min on checks that could not start); widened 2026-10-09 after a `gh run list --commit` poll (no `gh pr checks` in the command, so the original regex missed it) waited ~1h on a conflicted PR whose CI could never start
created: 2026-09-17
pattern: '^(?![\s\S]*mergeable)[\s\S]*\bgh\s+(pr\s+checks|run\s+list)\b[\s\S]*\b(sleep|until|while)\b'
---
Explain what went wrong, when, and what to do instead.
