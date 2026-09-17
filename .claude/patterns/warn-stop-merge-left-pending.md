---
name: warn-stop-merge-left-pending
enabled: true
event: stop
action: warn
message: This closing message leaves a PR waiting on CI. The ship chain merges, deploys and verifies in the SAME turn: wait on gh run list --branch filtered by the head SHA, merge on green, deploy, then close. A merge promised for later does not happen once the turn ends.
source: 2026-09-17 skipped-gate: PR #971 sat green and unmerged while the owner published the SPA prompt that needed it
created: 2026-09-17
pattern: '(?i)(\bCI is (still )?running\b|\bmerge (it )?(on|once|when) (CI )?(is |goes |turns )?green\b|\b(once|when|after) CI (is |goes |turns )?green\b|\bI''?ll merge (it|the PR)? ?(on|once|when|after)\b)'
---
Explain what went wrong, when, and what to do instead.
