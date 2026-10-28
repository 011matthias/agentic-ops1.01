---
name: warn-pytest-or-true-masks-exit
enabled: true
event: bash
action: warn
message: pytest followed by '|| true' exits 0 whether the suite passed, failed or never started (2026-09-25: '-n auto' without xdist). Read pytest's own summary line ('N passed'), never the exit code, or drop the '|| true'.
source: 2026-09-25 verification-theater
created: 2026-09-25
pattern: 'pytest[^\n]*\|\|\s*(true|:)(\s|$|;)'
---
Explain what went wrong, when, and what to do instead.
