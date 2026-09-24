---
name: warn-spa-write-button-click
enabled: true
event: file
action: warn
message: This script clicks a control whose OLD behaviour may be a live write. Gate the click on proof that the published bundle carries the new build (bundle-first), or the click writes to the live month (2026-09-23, run 51a22ad72864).
source: 2026-09-23 skipped-gate B2: a verification drive clicked Save corrections on the old build and wrote to the live September month
created: 2026-09-23
pattern: 'get_by_role\(\s*"button"\s*,\s*name=re\.compile\(\s*"[^"]*(Save|Commit|Refresh|Reset|Forget|Undo|Rematch|Delete)'
---
Explain what went wrong, when, and what to do instead.
