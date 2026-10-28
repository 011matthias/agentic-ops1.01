---
name: warn-recon-drive-dom-remove
enabled: true
event: file
action: warn
message: A browser drive is deleting a React-owned DOM node (the recon feedback hint). React later unmounts it, throws removeChild 'not a child of this node', and the page shows 'This page didn't load', which reads as an app crash. Seed localStorage 'erc-fb-hint-seen'='1' before load instead, or close it with its own button.
source: 2026-10-07 verification-theater (receipt overview drive: hand-removed hint dialog crashed the local SPA after a popover close)
created: 2026-10-07
pattern: '(?i)(data-fb-widget|role=dialog)[^\n]{0,160}\.remove\(\)'
---
Explain what went wrong, when, and what to do instead.
