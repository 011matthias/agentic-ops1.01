# Lead Desk worker runbook (Windows glue)

The worker is the "hands": it claims due sends from the Lead Desk app
(the "brain" on Fly), fires them through Outlook COM, polls the
matthias + dirk inboxes for replies/bounces, and reports back. It never
decides who gets mailed - the app re-checks every stop condition at claim
time. This directory is dockerignored: none of it reaches the Fly image.

## Install

1. Pin a worktree for the task (never the dev checkout):
   `git worktree add C:\Users\neuma_p1qrsic\Repo\agentic-ops1-leaddesk-runner main`
2. Create the state home (gitignored, main clone):
   `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\clients\brisken\context\lead-desk-worker\worker.env`
   with: `LEAD_DESK_URL`, `LEAD_DESK_WORKER_SECRET`, `LEAD_DESK_INGEST_SECRET`,
   optional `ALERT_TO` + `RESEND_API_KEY`.
   Set the matching Fly secrets: `flyctl secrets set LEAD_DESK_WORKER_SECRET=... -a brisken-lead-desk`.
3. Verify readiness (read-only): `uv run --extra web --extra worker lead-desk-worker status --home <home>`
4. Rehearse: `... tick --dry-run` (peek, mutates nothing), then
   `... tick --draft-to-self` (full COM pipeline into our own Drafts, no ack).
5. Register the task: `powershell -ExecutionPolicy Bypass -File install-task.ps1`
   (from the pinned worktree's `worker/` dir).

## Kill switches (three, independent)

1. App UI: Campaigns page -> "Stop all sending" (works with the PC off).
2. Local file: create `<home>\KILL` (works with Fly unreachable).
3. `schtasks /Change /TN LeadDeskWorker /DISABLE`.

## Stuck / stalled sends

A lease that expires without a result shows as **stalled** on the board
and campaign page. The worker's reconcile searches Sent Items for
evidence on the next tick; genuine ambiguity stays stalled for a human:
campaign page -> Retry (re-queue) or Mark sent (assert it went out).
Never resolve ambiguity by resending from the mail client without
marking it sent first - the app cannot see manual sends.

## Logs

- `<home>\task.log` - raw scheduled-task output
- `<home>\runs\YYYY-MM-DD.jsonl` - per-tick counters + aborts
- `<home>\journal.jsonl` - per-send state machine (crash evidence)

## Known blind spot

If this machine is off or Outlook is closed, nothing sends (queue drains
next window - no burst) and nothing captures replies. The app-side
heartbeat staleness shows on the daily digest; log replies by hand on
the contact page if the worker is down for days.
