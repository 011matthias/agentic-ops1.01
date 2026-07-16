---
description: Log Brisken hourly-agreement hours since the last entry into the local hours tracker (both engagement tabs)
argument-hint: "[--tab lead|time] [--since YYYY-MM-DD] [--dry-run] [--yes]"
---

# Brisken Hours Log

Append the Brisken **hourly-agreement** work done since the last logged entry
into the current month's workbook under `workspace/hours-tracker/` (one dated
file per month, `hours-tracker-YYYY-MM-<month>.xlsx`; the tool auto-resolves the
latest month). This command is specific to the Brisken EUR 14/hr engagement and
its two billing tabs:

- **Lead Generation** (table `LeadGenLog`) -> p2 lead-gen / OnePilot / Rome
- the expense-recon tab (table `HoursLog`) -> p1 Brisken Expense Reconciliation
  Tool. Its sheet title varies by month (June `Timesheet`, July
  `Expense Reconciliation`); the tool resolves it by table name, so pass the
  `--tab time` alias rather than a literal title.

The mechanical, gotcha-safe write is done by `tools/log-brisken-hours.py`. THIS
command is the judgment layer: find the boundary, gather the evidence since it,
turn that into honest scope-based session rows, then hand them to the tool.

Entries are **scope-based estimates grounded in git history + session
checkpoints**, not a per-commit dump (see `feedback_hours_tracker_format`). The
hours are billed to a real client; estimate conservatively and never invent a
session that has no evidence.

Arguments ($ARGUMENTS):
- `--tab lead|time` — only log that engagement (default: both).
- `--since YYYY-MM-DD` — override the boundary (default: each tab's last entry).
- `--dry-run` — build and print the manifest, write nothing.
- `--yes` — skip the confirm and write directly (default: show manifest first).

## Context

- Today: !`date +%Y-%m-%d`
- Tracker status (the live boundary per tab): !`uv run tools/log-brisken-hours.py --status`
- Lead-gen commits since 2026-06-20: !`git log --since="2026-06-18" --pretty=format:'%h %aI %s' --no-merges -- 'workspace/clients/brisken/*' | head -40`

## Step 1 — Find the boundary

Read the `--status` block above. For each in-scope tab, the `last logged` line
gives the cutoff datetime. Everything after it is candidate work. Honor
`--since` if the user passed it.

If the status reports `LOCKED`, the workbook is open in Excel. Close just that
workbook without disturbing the user's other windows, then re-run:

```powershell
$p=(Get-ChildItem "C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\hours-tracker\hours-tracker-20*.xlsx" | Sort-Object Name | Select-Object -Last 1).FullName
[Runtime.InteropServices.Marshal]::BindToMoniker($p).Close($false)
```

## Step 2 — Gather the evidence since the boundary

Two sources, both read-only:

1. **Git** — commits Matthias authored that touch Brisken, after the boundary:
   ```bash
   git log --since="<boundary date>" --pretty=format:'%h%x09%aI%x09%s' \
     --no-merges -- 'workspace/clients/brisken/*'
   ```
   Use commit timestamps as the spine for Start/End (commits cluster at the END
   of a work block, so the block usually starts before the first commit).
2. **Session checkpoints** — `docs/<YYYY-MM-DD> - Brisken *` folders dated at or
   after the boundary. Read each `Checkpoint.md` / `Mini-Checkpoint-*.md` for
   "What Was Done", the file mtime (block end time), and work that produced NO
   commit (lists sent, emails, live deploys, research, calls). Commit-less work
   is still billable; the checkpoints are where you find it.

## Step 3 — Bucket each work block to the right tab

- **Lead Generation (p2):** `deliverables/*onepilot*`, `deliverables/lead-generation/**`,
  `context/lead-generation/**`, `onepilot-site/**`, Rome campaign, AEO Q&A pages,
  prospect lists, cold outreach. Commit subjects `brisken onepilot:`,
  `brisken lead-gen:`, `brisken p2:`.
- **Timesheet (p1):** `automations/expense-reconciliation/**`, the expense-recon
  app / web review workbench, Zoho export, receipt reader, categorizer, COA.

A block touching both is split by where the bulk of the work landed.

## Step 4 — Cluster into scope-based session rows

Group the evidence into coherent work sessions (one row each), not one row per
commit. For each row:

- **Date** = the day the work happened.
- **Start / End** = a conservative window grounded in the commit times and the
  checkpoint mtime. Never overlap an already-logged row (check the prior rows in
  `--status` / the tab).
- **Task** = COMPACT, lowercase, ~4 to 8 words, human voice, like
  "expandable cards, bigger hero, dns recon" — NOT a 15-word laundry list.
  No em-dashes, no `--`, no `->`, no parenthetical pile-ups, no slash-runs
  (`feedback_hours_tracker_format`, `feedback_human_voice_in_deliverables`).
- **billable** = "Yes" unless there is a clear reason otherwise.

## Step 5 — Show the manifest, then write

Unless `--yes`, print the manifest first (it is billing data the user may want
to adjust):

```
Brisken hours to log (since <boundary>):
  [Lead Generation]
    2026-06-21  12:30-14:00  (1.5h)  expandable cards, bigger hero, dns recon
  Total new: N.Nh = EUR M.MM
```

Write the rows JSON to `.scratch/brisken-hours-rows.json` and append:

```bash
uv run tools/log-brisken-hours.py --add .scratch/brisken-hours-rows.json
```

(Use `--dry-run` for a no-write preview.) The tool is idempotent (skips a row
whose date+start+task already exists), copies the cell styles + Hours/Earnings
formulas, extends the table ref, keeps the B4 period stamp live, and refreshes
the gitignored CSV mirrors. It self-verifies and prints `verified.` on success.

## Step 6 — Verify the behavior, not just the write

openpyxl leaves the formula cache blank (normal resting state); confirm the
numbers actually compute by reopening through Excel and checking the totals tie:

```powershell
$p=(Get-ChildItem "C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\hours-tracker\hours-tracker-20*.xlsx" | Sort-Object Name | Select-Object -Last 1).FullName
$xl=New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false
$wb=$xl.Workbooks.Open($p,$false,$true); $xl.CalculateFull()
foreach($ws in $wb.Sheets){$s=$ws.Name; if($s -notin @("_meta")){
 "[$s] "+$ws.Range("B4").Text+" | "+$ws.Range("K3").Value2+"h / EUR "+$ws.Range("L3").Value2+" | "+$ws.Range("K14").Value2}}
$wb.Close($false); $xl.Quit()
```

`K14` (the Control check cell) must read `ties to table` on every tab
written. `K13` is the week-of SUMPRODUCT for the last pre-anchored Monday
and reads `0` when that week has no work, so don't probe it. Report the new
per-tab total and the EUR figure logged this run.

## Notes

- Scope is the Brisken hourly agreement only. Other clients/projects are out of
  scope (the abandoned `tools/sync-hours.py` git-clustering approach is not used).
- The workbooks are local and gitignored (`workspace/hours-tracker/`, one dated
  file per month); they live only in the main clone.
- Safe to re-run: idempotency means a second run with overlapping rows is a
  no-op, so running it again after adding a forgotten session just adds the new one.
- If the user only says "log my lead-gen hours", run with `--tab lead`.
