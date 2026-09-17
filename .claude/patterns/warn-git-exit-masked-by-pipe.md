---
name: warn-git-exit-masked-by-pipe
enabled: true
event: bash
action: warn
message: A pipe after a mutating git command hides its exit status, and the `&&` after it then runs anyway.
source: 2026-09-17 slow-path (this session, ECC port batch 2)
created: 2026-09-17
pattern: '\bgit\s+(-C\s+\S+\s+)?(rebase|merge|pull|cherry-pick|commit|push|reset|checkout|stash)\b[^|;]*\|[^;]*&&'
---
A shell pipeline reports the LAST command's status, so `git rebase ... | tail -1 && git branch -f ...` runs the second command even when the rebase stopped on a conflict. On 2026-09-17 that moved a branch ref mid-rebase, in a session that had just pushed the branch it was about to reset.

Run the mutating git command on its own and check what it did, or wrap it: `if git rebase origin/main > log 2>&1; then ...; else ...; fi`. Pipe only the read-class commands (`log`, `status`, `diff`).
