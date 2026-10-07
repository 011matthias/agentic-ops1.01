---
name: warn-poll-task-output-file
enabled: true
event: bash
action: warn
message: Polling a background task's .output file in a sleep/until loop: a task launched with its stdout piped through tail/head writes nothing until it exits, so the loop only waits for the exit and can burn the whole tool timeout (2026-10-07: 600 s). The harness notifies you when the task completes; wait for that, and use Read on the path for interim output.
source: 2026-10-07 slow-path (sibling of warn-tail-task-output-file, which misses a path held in a shell variable)
created: 2026-10-07
pattern: 'tasks[/\][A-Za-z0-9_-]+\.output.*\b(sleep|until|while)\b'
---
Explain what went wrong, when, and what to do instead.
