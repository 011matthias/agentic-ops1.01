---
name: warn-git-exit-masked-by-pipe
enabled: true
event: bash
action: warn
message: A pipe after a mutating git command hides its exit status, so both the `&&` behind it and a `$?` read report the pipe's last command.
source: 2026-09-17 slow-path (ECC port batch 2), widened to `$?` after a 2026-09-17 recon session
created: 2026-09-17
pattern: '\bgit\s+(-C\s+\S+\s+)?(rebase|merge|pull|cherry-pick|commit|push|reset|checkout|stash)\b[^|;]*\|[^;]*(&&|\$\?)'
---
A shell pipeline reports the LAST command's status, so `git rebase ... | tail -1 && git branch -f ...` runs the second command even when the rebase stopped on a conflict. On 2026-09-17 that moved a branch ref mid-rebase, in a session that had just pushed the branch it was about to reset.

`$?` after the pipe is the same bug with a quieter ending. Later the same day a session ran `git merge origin/main --no-edit 2>&1 | tail -6` and then `echo "MERGE_EXIT=$?"` on the next line, and read `MERGE_EXIT=0` off a merge that had in fact stopped on a conflict. Nothing broke, because the conflict was obvious in the output above it, but the line that was supposed to be the check reported the opposite of the truth. The first version of this rule required a `&&` behind the pipe and so said nothing.

Run the mutating git command on its own and check what it did, or wrap it: `if git rebase origin/main > log 2>&1; then ...; else ...; fi`. Redirect rather than pipe when you intend to read `$?`, and put the exit-code read on its own line. Pipe only the read-class commands (`log`, `status`, `diff`).
