---
name: block-stop-merge-left-pending
enabled: true
event: stop
action: block
message: This closing message leaves the ship chain waiting (a suite, CI, a merge or a deploy promised for later). Finish it in THIS turn: wait on the suite or on gh pr checks with an in-turn until-loop, merge on green as its own call, deploy, verify, then close. Promoted from warn after five recurrences (2026-09-28 x2, 10-02, 10-07 x2).
source: 2026-10-07 agent-deferred (5th recurrence; warn fired only on the next prompt)
created: 2026-10-07
pattern: '(?i)(\bCI is (still )?running\b|\bmerge (it )?(on|once|when) (CI )?(is |goes |turns )?green\b|\b(once|when|after) CI (is |goes |turns )?green\b|\bI''?ll merge (it|the PR)? ?(on|once|when|after)\b)'
---
Explain what went wrong, when, and what to do instead.
