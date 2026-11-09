---
name: block-msys-noconv-git-c-posix-path
enabled: true
event: bash
action: block
message: With MSYS_NO_PATHCONV=1, git.exe gets '/c/Users/...' verbatim and fails 'cannot change to'; a '> file' redirect then leaves an EMPTY file that looks like a copy. Pass git -C 'C:/Users/...' when the prefix is needed for a rev:path argument.
source: 2026-11-05 slow-path (66 empty copies, caught by a blob-hash check)
created: 2026-11-09
pattern: 'MSYS_NO_PATHCONV=1[^\n]*\bgit\s+-C\s+[\x27\x22]?/[a-zA-Z]/'
---
Explain what went wrong, when, and what to do instead.
