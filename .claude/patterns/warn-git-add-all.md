---
name: warn-git-add-all
enabled: true
event: bash
action: warn
message: Broad `git add` stages whatever else is dirty in this tree, including a sibling session's work.
source: feedback_worktree_for_concurrent_sessions (sibling-session-gate advisory)
created: 2026-09-17
pattern: '\bgit\s+(-C\s+\S+\s+)?add\s+(-A\b|--all\b|\.(\s|$|;|&|\|))'
---
Several Claude sessions routinely share one clone, and the sibling-session gate's standing advice is to commit with explicit pathspecs only. `git add -A`, `--all` and `.` sweep in unrelated dirty files, and on a shared tree that includes another session's uncommitted edits.

Stage the exact paths this change touched, then check `git diff --cached --name-only` before committing.
