---
name: warn-transient-queue-phrasing
enabled: true
event: stop
action: warn
message: Your last message parked work behind a transient block instead of retrying it.
source: 2026-05-11 agent-deferred (memory feedback_active_retry_on_transient_blocks)
created: 2026-09-17
pattern: '(?i)\bqueued\b.{0,80}\bwill (apply|run|land|go through)\b.{0,30}\bwhen\b|\bwill retry when\b.{0,60}\bunlock'
---
On 2026-05-11 eight edits failed with EBUSY and the turn ended on "8 queued edits will apply when the file unlocks". Nothing retried them until the user re-prompted. stop-b1-gate's passive-queue pattern does not match that sentence shape, which is why this rule exists.

A file lock, a 429, a 503 or a build still running is transient. If that work is still pending, start the retry now: a background `until` loop, or a Monitor watching for the release signal, then re-run the operation and report the result.
