---
name: warn-mutate-shared-primary-clone
enabled: true
event: bash
action: warn
message: Mutating git on the shared primary clone. Re-read its state in the same step; a read from minutes ago is not current.
source: 2026-09-17 skipped-gate (ECC batch 2 live activation)
created: 2026-09-17
conditions:
  - field: command
    operator: regex_match
    pattern: 'agentic-ops1(?![-\w])'
  - field: command
    operator: regex_match
    pattern: '\bgit\s+-C\s+"?(\S*agentic-ops1(?![-\w])|\$\{?\w+\}?)"?\s+(merge|pull|checkout|switch|reset|rebase)\b'
  - field: command
    operator: not_regex_match
    pattern: 'session_registry'
---
The primary clone is shared by every session started in it. On 2026-09-17 a fast-forward was attempted on the strength of a check taken about twenty minutes earlier (clean tree, idle siblings). By then a brisken session was mid-build: 11 dirty files, three sessions active within 80 seconds, and one file the merge would have changed was locally modified. The auto-mode classifier denied the command.

Re-check in the same step you act: `git status --porcelain` must be empty and `tools/session_registry.py --check` must show no active sibling. Better, poll check-then-act in one loop so the condition and the mutation cannot drift apart. rule_behaviors B2, instrument validity: freshness beats recall.
