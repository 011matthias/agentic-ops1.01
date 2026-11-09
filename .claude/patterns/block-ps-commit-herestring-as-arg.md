---
name: block-ps-commit-herestring-as-arg
enabled: true
event: bash
action: block
message: In PowerShell a here-string after 'git commit -F -' is an ARGUMENT (read as a pathspec), not stdin: the commit fails and a chained push sends nothing new. Write the message to a file and use -F <file>, or -m per paragraph.
source: 2026-11-05 slow-path (ClientSense #3 commit; push sent a branch with no commit)
created: 2026-11-09
pattern: '\bcommit\b[^\n]*\s-F\s+-\s+@[\x27\x22]'
---
Explain what went wrong, when, and what to do instead.
