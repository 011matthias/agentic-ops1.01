---
name: warn-lovable-prompt-file-first
enabled: true
event: prompt
action: warn
message: A Lovable prompt is being asked for. For the Brisken recon SPA, write it to workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-<slug>-prompt.md with a Not-applied row in PROMPT-STATUS.md in the same turn, and hand the body in a four-backtick fence naming that file. Check component names against the SPA repo origin/main first.
source: 2026-10-07 skipped-gate (recon confirm-button prompt handed without its ledger file; the stop-time rule caught it a turn late, 3rd time)
created: 2026-10-07
pattern: '(?is)\bprompt\w*\b.{0,80}\blovable\b|\blovable\b.{0,80}\bprompt'
---
Explain what went wrong, when, and what to do instead.
