---
name: block-flyctl-deploy-posix-path
enabled: true
event: bash
action: block
message: flyctl on Windows cannot chdir into a Git-Bash /c/... path when MSYS_NO_PATHCONV=1 keeps it verbatim (it tries C:\c\Users\...). Pass the WINDOWS path (C:\Users\...) for both the build dir and --config.
source: 2026-09-25 slow-path (recurrence of the 2026-09-24 brisken deploy row)
created: 2026-09-25
pattern: '(?s)(?:=/[a-zA-Z]/Users/\S*.*MSYS_NO_PATHCONV=1\s+flyctl\s+deploy|MSYS_NO_PATHCONV=1\s+flyctl\s+deploy\s+"?/[a-zA-Z]/)'
---
Explain what went wrong, when, and what to do instead.
