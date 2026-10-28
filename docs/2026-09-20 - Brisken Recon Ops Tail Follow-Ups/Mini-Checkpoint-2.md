# Mini-Checkpoint: Brisken Recon Ops Tail Follow-Ups

**Date:** 2026-09-20
**Status:** Ops-tail fence complete; item 123 is now a measured question awaiting one owner decision
**Type:** mini

---

## Summary

Follow-ups to the third ops pass, across 2026-09-19 and 2026-09-20. Rescued an
abandoned session's uncommitted ledger work, then corrected my own item 123
finding twice as real data arrived: the cron does fire, and its cadence is worse
than the first correction said. Three PRs, all merged, all docs only. No code
and no deploy.

## What Was Done

- **Rescued the second pass's orphaned ledger work** (PR #1115, `28bd3b51`).
  Three edits sat uncommitted in `agentic-ops1-ops-fr` for ten hours with nothing
  in the object store behind them, after that session stopped mid-edit. Committed
  as it left them, then main merged in cleanly with both sides of the session log
  preserved. The content was its own `skipped-gate` row: its checkpoint ran end to
  end and merged as PR #1108, the closing reply never said so, so the work read as
  not having happened and the user re-asked for a checkpoint that already existed.
- **Corrected "the cron has never fired"** (PR #1116, `18497295`). It fires. The
  first scheduled run landed 2026-09-18T17:42:18Z, **46 minutes after the poll
  that concluded it never would** and 3h30m after the workflow reached main. The
  scheduler was never broken; it was slow to adopt a new workflow, and 2h13m of
  polling was not long enough to say otherwise.
- **Replaced that correction's own estimate with 44 hours of data** (PR #1121,
  `fed2d912`). 15 scheduled runs 2026-09-18T17:42Z to 2026-09-20T13:50Z, all
  green, no `recon-uptime` issue opened. 14 gaps: mean 3h09m, shortest 1h39m,
  longest **4h46m**, against the ~265 a `*/10` asks for, so 5.3% delivered. The
  delivery rate I estimated (about 6%) held; the cadence I estimated (about every
  2h15m) did not, and for a monitor the load-bearing number is the worst gap,
  because that is how long an outage sits unseen.
- **Repaired a row a sibling reverted.** PR #1111 merged an older copy of
  `p1-expense-reconciliation.md` after #1112 had edited it, silently reverting the
  item 123 status row. Only that row was lost; the item 125 and 129 rows in the
  same file survived and the backlog and PROMPT-STATUS were untouched.
- **Reframed the resume YAML's first next-step** so a resuming session does not
  re-derive "the cron never fires" from yesterday's wrong conclusion.
- State re-read at 2026-09-20T14:17Z: feedback log still 70 notes, nothing new
  from Criss; no open `recon-uptime` issue, so the app has been up throughout.

## What Did NOT Work (and why)

- **Concluding "the cron never fires" from 2h13m of polling.** 16 polls across
  one window, then a re-read, all zero, reported as a finding with three options
  attached. The first real run came 46 minutes later. A zero only ever measured
  inside one window is a statement about the window, not about the system. This is
  the same failure as the three blind instruments recorded in PROMPT-STATUS,
  approached from the other side: there a probe could not see something present,
  here the wait was too short to see something that had not happened yet.
- **Characterising the cadence from four runs.** The replacement finding said
  "roughly every 2h15m". Over 44 hours the mean is 3h09m and the worst gap 4h46m,
  so the first number understated the blind window by more than half. Four samples
  of a best-effort scheduler describe the four samples.
- **Assuming a merged PR stays merged in a shared file.** #1112's status-row edit
  was on main and then was not, because a PR opened earlier merged later carrying
  an older copy. Nothing warns about this; the loss was found only by an anchor
  failing to match during an unrelated edit.

## Current Status

`main` at `fed2d912`. All five fenced items (123, 125, 127, 128, 129) shipped and
verified. Nothing in the fence is mine to advance further.

The uptime monitor works and is the one item still carrying a decision: it detects
an outage, but on GitHub's best-effort scheduling an outage starting just after a
run can go unseen for nearly five hours.

Two `p2` status files remain stale (`p2-product-decks.md` 59d, `p2-targeting.md`
60d). Outside this fence; untouched and flagged for a third checkpoint running.

## Next Steps

1. **Owner decides whether a five-hour blind window is acceptable.** If yes,
   nothing to build: the monitor already runs. If not, the free external monitor
   on `/healthz` (option 3 in backlog item 123) is the only option whose vantage
   point shares a failure mode with neither GitHub nor the laptop. This is now a
   measured trade-off rather than an open question.
2. **Owner decides when to fire item 123's real alert path.** Still never run for
   real; not fired unattended because the mail subject reads "expenses.brisken.com
   is down" and would land as a false alarm.
3. **Item 125 closes itself** on the first mail arriving after Fly v187
   (2026-09-18T14:46:41Z): read `submitted_by.transport_tls` on the newest
   mail-sourced receipt. A `false` names a sender still delivering in the clear.
4. **Owner note #70 needs assigning to a session** (2026-09-18 10:19Z, run
   `af8936c6b05a`): "add receipts function just opens receipt view in new tab but
   does not really add it". Untriaged and outside the ops fence.
5. Residues, owner's call: 127's per-month verdict tally, 128's reader-version
   stamp, 129's per-file "matched with X" line, 125's CA certificate, 123's
   Brisken-mailbox recipient.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 123 carries
  the 44-hour measurement and the three options; items 125 and 129 below it)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (rows for 123,
  125, 129)
- `docs/2026-09-18 - Brisken Recon Ops Tail Third Pass/Mini-Checkpoint-2.md` (the
  pass these follow-ups correct)
