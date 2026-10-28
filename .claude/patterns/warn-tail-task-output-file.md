---
name: warn-tail-task-output-file
enabled: true
event: bash
action: warn
message: Tailing a background task's .output file from Bash: the harness notifies you when the task exits, and Read on that path is the sanctioned way to check interim output. If the command was launched with its stdout piped through tail/head, the file stays EMPTY until it exits, so this check cannot show progress. Wait for the notification.
source: 2026-09-20 slow-path (3rd occurrence; 09-18 and 09-20 both fixed 'documented' and did not hold)
created: 2026-09-20
pattern: 'tail[^|;&]*tasks[/\][A-Za-z0-9_-]+\.output'
---
Explain what went wrong, when, and what to do instead.
