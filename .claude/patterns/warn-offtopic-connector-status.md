---
name: warn-offtopic-connector-status
enabled: true
event: stop
action: warn
message: Connector/MCP status is off-topic unless the task depends on it (owner, 2026-09-17). Cut the line, or say why this task needs that connector.
source: 2026-09-17 scope-creep: a closing message relayed Google Calendar / Vercel / n8n status the task never used
created: 2026-09-17
pattern: '(?i)(google calendar|vercel|n8n|context7|firebase)[^.\n]{0,60}(need(s)? (to be )?authoriz|failed to connect|not connected|unavailable for this session)'
---
Explain what went wrong, when, and what to do instead.
