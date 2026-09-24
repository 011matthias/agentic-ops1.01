---
name: warn-hand-rolled-spa-bundle-crawl
enabled: true
event: bash
action: warn
message: Probing the published recon SPA bundle? Use uv run tools/lovable-bundle-audit.py (transitive crawl + known-present controls, exit 2 = instrument invalid) instead of a hand-rolled curl/grep crawl.
source: 2026-09-24 missed-tool
created: 2026-09-24
pattern: 'curl[^|;&]*expenses\.brisken\.com(/assets|["'' ]|$)'
---
Explain what went wrong, when, and what to do instead.
