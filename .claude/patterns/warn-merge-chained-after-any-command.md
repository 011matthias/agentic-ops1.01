---
name: warn-merge-chained-after-any-command
enabled: true
event: bash
action: warn
message: Run 'gh pr merge' as its own Bash call. no-auto-commit-gate reads CI once, before the whole command runs, so any wait chained ahead of the merge (a --watch, a poll script, an if on its exit code) is invisible to it and a PR about to go green takes a permission stop.
source: 2026-09-25 agent-deferred (custom wait script + merge in one call; the --watch rules did not match)
created: 2026-09-25
pattern: '(?:;|&&|\bthen\b)[^\n]*\bgh pr merge\b'
---
Explain what went wrong, when, and what to do instead.
