# Lead Desk COM worker (RETIRED 2026-07-16; fallback only)

The local Windows Outlook-COM worker was the campaign engine's "hands"
(iteration 3, gate-passed 2026-07-13). The 4d build replaced it with the
in-app cloud worker on Fly (`src/lead_desk/cloud_worker.py`: Graph app-only
send + capture, same tick contract, no Windows session needed), per
rule_brisken_graph_first. The `LeadDeskWorker` scheduled task is DISABLED.

This directory stays ONLY as the validated fallback until the Graph send
path passes its own watched send-gate drill; delete it (and the `worker`
extra) after that drill. Do not re-enable the task while the cloud worker
is live: two workers double-capture harmlessly, but the retired path must
not quietly come back into duty.

## Re-enable (fallback drill only)

1. State home (gitignored, main clone):
   `workspace/clients/brisken/context/lead-desk-worker/worker.env`
   (`LEAD_DESK_URL`, `LEAD_DESK_WORKER_SECRET`, `LEAD_DESK_INGEST_SECRET`).
2. Readiness (read-only): `uv run --extra web --extra worker lead-desk-worker status --home <home>`
3. `schtasks /Change /TN LeadDeskWorker /ENABLE` (task runs from the pinned
   worktree `agentic-ops1-leaddesk-runner`, interactive session only).

## Kill switches (unchanged, three, independent)

1. App UI: Campaigns page -> "Stop all sending" (global kill switch; also
   halts the cloud worker).
2. Local file: create `<home>\KILL`.
3. `schtasks /Change /TN LeadDeskWorker /DISABLE` (current state).

## Stuck / stalled sends

A lease that expires without a result shows as **stalled** on the board and
campaign page; resolve there (Retry / Mark sent). Never resolve ambiguity by
resending from the mail client without marking it sent first.

## Logs

- `<home>\task.log` - raw scheduled-task output
- `<home>\runs\YYYY-MM-DD.jsonl` - per-tick counters + aborts
- `<home>\journal.jsonl` - per-send state machine (crash evidence)
