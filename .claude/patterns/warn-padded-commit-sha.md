---
name: warn-padded-commit-sha
enabled: true
event: bash
action: warn
message: A commit SHA with a run of eight trailing zeros is padded, not real. Read it with git rev-parse and pass the full 40-char value; /healthz would otherwise stamp a commit that exists nowhere (B4).
source: 2026-09-23 skipped-gate B4: dedd7260...00000000 passed to a Fly build arg, caught before it landed
created: 2026-09-23
pattern: '[0-9a-f]{20,}0{8}'
---
Explain what went wrong, when, and what to do instead.
