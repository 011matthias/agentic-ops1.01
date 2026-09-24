---
name: warn-chained-checks-watch-and-merge
enabled: true
event: bash
action: warn
message: Split them: run 'gh pr checks N --watch' in one call and 'gh pr merge N' in the next. no-auto-commit-gate reads the CI verdict per command and cannot see green through a chain, so a chained merge takes a permission stop Band 2 would have auto-allowed.
source: 2026-09-24 slow-path (recurred 3 sessions same day, documented fix did not hold)
created: 2026-09-24
pattern: 'gh pr checks[^\n]*--watch[\s\S]*gh pr merge'
---
Explain what went wrong, when, and what to do instead.
