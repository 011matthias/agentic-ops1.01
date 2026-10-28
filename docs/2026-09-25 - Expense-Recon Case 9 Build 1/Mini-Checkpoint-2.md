# Mini-Checkpoint: Expense-Recon Case 9 Build 1

**Date:** 2026-09-25
**Status:** Build 1 live (v229); D3 load prompt written; the item-206 note in Mini-Checkpoint-1's addendum is superseded
**Type:** mini

---

## Summary
After build 1 shipped, the owner granted D2 and D3 ("both are in sharepoint") and chose a fresh session that predicts per month before any attach. Item 206 turned out to be built already by a sibling (PR #1376), so the note for its Prompt A in Mini-Checkpoint-1's addendum no longer applies.

## What Was Done
- Found the D2/D3 files by name via the Graph app, app-only, not opened: 9693 `ADMINLLC9/Chase9693_Activity2024_Start.xlsx`, 1176 `admin_consulting/Chase1176_Activity_historicactivity_since202402.xlsx` (both with Aug/Sep cycle PDFs). No file names 3876 or 0340; candidates `admin_corp_services/Nicolas Neumann Monthly Expenses.xlsx` and `admin_corp_services/Chase2838_historic_Activity.xlsx`.
- Owner decision (AskUserQuestion): the D3 load runs in a fresh session that reads the files, predicts per month which rows move, and attaches only after a yes. The prompt is in Mini-Checkpoint-1's addendum (PR #1373).
- Counted live rows on July to September that show a company but are still refused `entity_missing`: July 0, August 0, September 3 (`0008`, `0029`, `0033`, all from build 1's twin card).
- Memory `project_brisken_recon_case9_plan.md` records the D2/D3 grant, the file locations and build 1.

## What Did NOT Work (and why)
- **The item-206 note in Mini-Checkpoint-1's addendum ("add a sweep that runs on read or at deploy, expect 3"):** a sibling had already built 206 (PR #1376, merged 00:49 UTC). Its `recategorize_moved_companies` sweeps every row that shows a company while refused `entity_missing`, at the month's next edit, arrival or re-match. The three September rows clear at September's next such event once #1376 is deployed; no read-time sweep is needed. Caught by checking open and merged PRs before handing Prompt A over.

## Current Status
Live Fly `6a4c7490` did not yet contain #1376 at the check; deploying it is that session's step. The three September rows stay refused until then plus one September event. Item 207 is in flight (PR #1378, open). Case-9 builds 2 to 4: PRs #1367, #1364, #1366 (build 2's checkpoint merged as #1371).

## Next Steps
1. Paste the D3 load prompt (Mini-Checkpoint-1 addendum) into a fresh chat.
2. After #1376 deploys: confirm `0008` / `0029` / `0033` lose `entity_missing` at September's next arrival or edit (read-only).
3. Owner / Criss: name the file holding Criss's April to June 0340 activity if neither candidate has it; decide whether Criss attaches the weekly 9693 / 1176 exports herself.

## Files to Read First
- `docs/2026-09-25 - Expense-Recon Case 9 Build 1/Mini-Checkpoint-1.md` (build 1 and the D3 prompt)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 204 and 206
