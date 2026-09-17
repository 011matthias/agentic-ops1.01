---
name: warn-attach-busy-cdp-9222
enabled: true
event: file
action: warn
message: Attaching to the user's main browser on :9222 hangs when it is busy (Chrome 227 procs, Edge 112 tabs: ws connects, then the target handshake times out). If the task needs no existing login, launch a second instance with its own --user-data-dir on another port (tools/launch-edge-cdp.ps1, or chrome.exe --remote-debugging-port=9333) and attach there; it is also the cold-drive seat.
source: 2026-09-17 missed-memory-recall: MCP, agent-browser x3, connect_over_cdp all hung on :9222
created: 2026-09-17
pattern: 'connect_over_cdp\(\s*["'']https?://(127\.0\.0\.1|localhost):9222|agent-browser\s+(--cdp\s+\S*9222|connect\s+\S*9222)'
---
Explain what went wrong, when, and what to do instead.
