---
name: block-grep-no-ignore
enabled: true
event: bash
action: block
message: --no-ignore is a ripgrep flag. GNU grep exits 2 on it, and with 2>/dev/null the search silently returns nothing, which reads as 'not found'. Use rg --no-ignore (or the Grep tool) instead.
source: 2026-10-12 verification-theater (regression of 2026-10-07 WW grep row)
created: 2026-10-12
pattern: '(^|[;&|(]\s*|\s)grep\s[^|;&]*--no-ignore'
---
Explain what went wrong, when, and what to do instead.
