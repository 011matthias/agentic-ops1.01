---
name: warn-relayed-client-ask
enabled: true
event: prompt
action: warn
message: Relayed client ask: open that contact's last logged mail or draft and restate your reading of the ask before producing anything (2026-10-30: 'Testmail' meant a test-mail recipient, two rounds lost).
source: 2026-10-30 intent-misalignment
created: 2026-10-30
pattern: '\b(hat|haben|has|have)\s+(nach|um|for)\b[^.\n]{0,80}\b(gefragt|asked)\b'
---
Explain what went wrong, when, and what to do instead.
