---
name: warn-stop-next-item-handback
enabled: true
event: stop
action: warn
message: Before handing a what-comes-next choice back, read origin/main's backlog and status (git show origin/main:<path> | grep) for an item already planned or ruled; a sibling may have answered it since you last looked.
source: 2026-09-25 agent-deferred (handed back 'which card-attribution case comes next' while item 204 already planned case 9 on main)
created: 2026-09-25
pattern: '(?i)\b(decide|pick|choose)s?\s+(which|what)\b[^.\n]{0,60}\b(comes|goes|is|should be|to build)\s+next\b'
---
Explain what went wrong, when, and what to do instead.
