---
name: warn-flyctl-console-large-payload
enabled: true
event: bash
action: warn
message: A long flyctl ssh console -C payload is silently dropped on this Windows flyctl (no output, nothing written), and ssh sftp put / stdin piping write EMPTY files. For a /data file, make a SHORT in-place edit on the machine to <file>.new, verify it, then mv.
source: 2026-09-24 slow-path (Consulting provisioning upload, 4 attempts)
created: 2026-09-24
pattern: 'flyctl ssh console[^\n]{0,80} -C [^\n]{1500,}'
---
Explain what went wrong, when, and what to do instead.
