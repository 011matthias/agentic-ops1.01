---
name: block-merge-chained-after-any-command
enabled: true
event: bash
action: block
message: Run 'gh pr merge' as its own Bash call: no-auto-commit-gate reads CI once before the whole command, so anything chained ahead of the merge is invisible to it. Promoted from warn after four recurrences (2026-09-25, 09-27, 09-28 x2).
source: 2026-09-28 skipped-gate (a gh api read chained ahead of the PR 1533 merge in one call; warn rule did not hold)
created: 2026-09-29
pattern: '(?:;|&&|\|\||\bthen\b|\bdo\b)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*gh\s+pr\s+merge\b'
---
Explain what went wrong, when, and what to do instead.
