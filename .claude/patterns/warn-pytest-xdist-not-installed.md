---
name: warn-pytest-xdist-not-installed
enabled: true
event: bash
action: warn
message: pytest-xdist is not installed in the expense-recon module env: -n / --numprocesses is refused with a usage error. Run pytest plainly and read its own exit code (redirect to a log, do not pipe it through tail).
source: 2026-09-25 missed-memory-recall (item 204 build 3; same-day sibling row, documented fix did not hold)
created: 2026-09-25
pattern: 'pytest\b[^\n;&|]*\s(-n\s*(auto|\d+)|--numprocesses)\b'
---
Explain what went wrong, when, and what to do instead.
