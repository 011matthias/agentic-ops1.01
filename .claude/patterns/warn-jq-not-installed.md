---
name: warn-jq-not-installed
enabled: true
event: bash
action: warn
message: There is no jq binary on this machine: a pipe into jq fails on every run with the error on stderr, so a poll or Monitor loop built on it stays silent and reads as still waiting. Use gh's own --jq flag, or python -c, instead.
source: 2026-09-27 verification-theater
created: 2026-10-02
pattern: '\|\s*jq\b'
---
Explain what went wrong, when, and what to do instead.
