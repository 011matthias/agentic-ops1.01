---
name: warn-grep-config-for-mcp-connector
enabled: true
event: bash
action: warn
message: claude.ai connectors (Zapier, Claude Docs, ...) live on the account, not in ~/.claude.json or .mcp.json, so a config grep is blind to them. Use 'claude mcp list': it shows account connectors and their health. A connector connected mid-conversation shows Connected there but does not load into the running session; a new conversation is needed.
source: 2026-10-07 missed-tool (Zapier connector check grepped config files)
created: 2026-10-07
pattern: '\bgrep\b[^|;&]*\.claude\.json'
---
Explain what went wrong, when, and what to do instead.
