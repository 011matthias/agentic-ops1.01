---
name: warn-gh-repo-slug-missing-01
enabled: true
event: bash
action: warn
message: This repo's GitHub slug is 011matthias/agentic-ops1.01; without .01 gh fails (No commits between main and ..., Head sha can't be blank).
source: 2026-09-17 missed-memory-recall (PR #974 create failed on the short slug)
created: 2026-09-17
pattern: '011matthias/agentic-ops1(?!\.01)(?![\w-])'
---
Explain what went wrong, when, and what to do instead.
