---
name: warn-cdp-before-browser-limitation
enabled: true
event: stop
action: warn
message: Before declaring browser automation unavailable: scan the CDP ports first. curl -s http://127.0.0.1:9222/json/version and :9333 — the user often has Chrome open with remote debugging (MEMORY.md reference_user_edge_cdp_9222). Driving it takes two calls (/json/new needs PUT on Chrome 111+); agent-browser hanging is not the same as no browser. Sibling rule warn-attach-busy-cdp-9222 covers the next step, which port to attach to.
source: 2026-09-24 missed-tool
created: 2026-09-24
pattern: '(?i)(LIMITATION|unavailable|could not|cannot)[^.]{0,80}(browser|agent-browser|playwright)|(browser|agent-browser|playwright)[^.]{0,60}(hung|unavailable|failed to connect)'
---
Explain what went wrong, when, and what to do instead.
