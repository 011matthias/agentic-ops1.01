---
name: warn-git-write-after-script-semicolon
enabled: true
event: bash
action: warn
message: A script runs, then ';' lets git add/commit/push run even when the script failed. On 2026-09-27 a merge-resolver assertion failed and the unresolved conflict markers were committed and pushed (f2c56eb4). Chain with && or run under set -e.
source: 2026-09-27 skipped-gate
created: 2026-09-27
pattern: '(?:python|uv run)[^\n&|;]*\.py[^\n&|;]*;[^\n]*\bgit\b[^\n]*\b(?:add|commit|push)\b'
---
Explain what went wrong, when, and what to do instead.
