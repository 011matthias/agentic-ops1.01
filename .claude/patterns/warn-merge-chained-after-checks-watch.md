---
name: warn-merge-chained-after-checks-watch
enabled: true
event: bash
action: warn
message: Split it: run 'gh pr checks N --watch' in its own call, then 'gh pr merge' in the next. Chained, no-auto-commit-gate evaluates CI before the watch runs, sees pending, and forces a permission prompt on a PR that is about to be green.
source: 2026-09-24 agent-deferred
created: 2026-09-24
pattern: 'gh pr checks[^\n]*--watch[\s\S]*gh pr merge'
---
Explain what went wrong, when, and what to do instead.
