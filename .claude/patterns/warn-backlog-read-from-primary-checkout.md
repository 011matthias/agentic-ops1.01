---
name: warn-backlog-read-from-primary-checkout
enabled: true
event: bash
action: warn
message: Reading the recon backlog from the primary checkout, which lags origin/main while siblings itemize notes. Read it with 'git show origin/main:workspace/clients/brisken/status/p1-improvement-backlog.md' (MSYS_NO_PATHCONV=1) before calling a feedback note new or unrecorded.
source: 2026-10-29 verification-theater (notes #126-#135 reported unrecorded; a sibling had itemized them as 258-262 on origin/main)
created: 2026-10-29
pattern: '^(?!.*origin/main)(?=.*Repo/agentic-ops1(?![-.\w]))(?=.*\b(grep|rg|sed|awk|cat|head|tail)\b).*p1-improvement-backlog\.md'
---
Explain what went wrong, when, and what to do instead.
