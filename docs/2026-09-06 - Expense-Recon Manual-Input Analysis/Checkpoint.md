# Checkpoint: Expense-Recon Manual-Input Analysis

**Date:** 2026-09-06
**Status:** Read-only analysis complete; findings surfaced, nothing changed on the live app

---

## Summary

Read-only audit of the Brisken expense tool (p1) answering "where does it need
the most manual input". The live state changed materially since 2026-08-28:
every month batch has been deleted, 23 real receipts sit pooled waiting for
July/August/September, and 7 more are stranded in "month deleted" state, so
the whole intake stream is currently parked behind the manual month-open
action.

---

## What Was Done This Session

### Live audit (read-only, GETs only)
1. Loaded the p1 memory set + status/backlog/loop-brief files.
2. Wrote `manual_input_audit.py` in the `%TEMP%/claude/recon-probe/` scratch
   home (reuses `api.py` vault auth) and swept the live API: expense-batches,
   per-batch views, inbound log (+detail), settings, `/api/cards`,
   `/api/memory`, operator state.
3. Cross-checked recent commits (latest p1 commit is #659, 2026-08-29 round;
   nothing shipped in September).

### Findings (the ranked answer)
1. **Month lifecycle is the gate.** 0 months open; 23 pooled receipts
   (Aug 12, Jul 5, Sep 6); 7 real receipts stranded from deleted months, each
   needing per-archive re-ingest once a month exists. Opening a month is
   manual by owner ruling AND requires a manual first-receipt upload
   (`create_expense_batch` refuses an empty batch) even though the pool knows
   which months are wanted.
2. **Card registry data entry (item 26) still undone.** Live `/api/cards`:
   4 of 5 cards entity-less (0113/6013/9693/8311), 0340 card absent, all rows
   `source: "legacy"`. Measured cost: 29 of 40 April rows in MISSING ENTITY.
3. **Receiptless statement charges dominate Mode B.** Jan 78/80, Apr 57/94
   receiptless; learned memory covered 3/78 cold; heals one descriptor at a
   time as Criss categorizes.
4. **Exception review rows** (date flags 13/38 on April, duplicates,
   set-asides, generic tenders) are the intended manual work; the unknown-card
   strip still inflates it (verbatim-spelling grouping, item 35 server half
   open).
5. **Curation untouched:** 103/103 learned category rows unvalidated;
   merchant registry dup pairs + mislabels pending; no multi_category flags
   set.
6. **Intake is now fine:** known_senders lists Dirk's iCloud (ack gap
   closed), held 0, duplicates auto-park. Noise finding: n_refused=55 (7d) is
   all spammer relay probes (`*@flyio.net`), so a real refused submission
   would be invisible in the counter.

---

## Key Decisions Made

None (analysis-only session; user asked for assessment, no fixes applied).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `%TEMP%/claude/recon-probe/manual_input_audit.py` | created (scratch) | reusable read-only manual-input sweep |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | updated | live-state note (months deleted, pool 23) + `updated:` bump |
| `docs/2026-09-06 - Expense-Recon Manual-Input Analysis/Checkpoint.md` | created | this checkpoint |

---

## Current Status

Live app healthy (v98-era backend, API answering). No months exist; pool is
the only live state. Three stale unpublished July test runs remain
(94 charges, 20 matched). brisken platform: unknown plan (no platform section
in infrastructure.yaml for p1; FastAPI/Fly, not an orchestrator drift issue).
Comms-log 5 days stale at checkpoint time.

---

## Next Steps

1. Surface the ranked analysis to the owner; the two cheap unlocks are a
   **create-month-from-pool affordance** (owner call needed — the 2026-08-24
   "pre-creating intrudes" ruling covers the agent acting, arguably not a UI
   affordance Criss clicks) and **item 26 card data entry** (ten minutes in
   Settings > Cards: entities for 0113/6013/9693/8311, create 0340).
2. Consider splitting spam relay probes out of `n_refused` so a real refusal
   is visible (small backend change, ranks low).
3. When months reopen: the 7 "month deleted" archives need per-archive
   re-ingest clicks (only mail stamped `batch_deleted` qualifies).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the loop brief)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (the one list)
- This checkpoint

### Open Questions
- Does the owner want a create-month-from-pool affordance, or does the
  "pre-creating intrudes" ruling extend to it?
- Item 23 layer-2 product question still parked: GL code-level classification
  in the documents, or categories only?

### Working Notes
- `/api/expense-batches` genuinely returns `{"batches": []}` — first suspected
  a parse bug, confirmed against the raw response. All six 08-28 months were
  deleted after the demo test.
- Probe shapes: `/api/memory` returns
  `{categories, aliases, fx, entities, field_corrections, counts, total}`
  (not table-name keys); operator state `feedback` is `{count: N}` (31 total),
  not a list.
- Pooled mail carries `month: null` at the top level; the waiting month lives
  in `status_label` ("Waiting for August 2026").
- Fly machine is scale-to-zero; first API call takes ~30-60s.

### Reference Materials
- Live API: `https://brisken-expense-recon.fly.dev` (operator code: vault
  "Brisken recon operator code matthias")
- SPA: `brisken-reconcile-dash.lovable.app`
- Probe helpers: `%TEMP%/claude/recon-probe/` (`api.py`,
  `manual_input_audit.py`)

---

## How to Continue

`/resume brisken`, read the loop brief, then either hand the owner the two
unlocks (affordance decision + item 26 data entry) or start the next code
round from the backlog ranking (item 27 wrong-day residue leads on the
wrong-money rule; item 35 server-side canonical card grouping is small and
demo-visible).

---

## Strategic Feedback

### What Worked Well This Session
- The `recon-probe/api.py` + vault pattern made the whole audit autonomous:
  zero questions to the user, all claims backed by live reads (B4 clean).
- Suspecting my own parsing before asserting a live change (B3) caught the
  real story: the empty batches list was true, not a bug.

### Suggestions
- `manual_input_audit.py` is worth keeping in the probe home and re-running at
  the start of every p1 session: it turns "what's waiting on a human" into one
  command. If the loop continues, consider promoting it into the module's
  `docs/` or `tools/` with a row in tools/INDEX.md.

### System Health
- Autonomy score: 0 human interventions (fully autonomous session).
- The friction register is over 200 KB and the archiver only frees ~1.7 KB
  (3 resolved rows); the bulk is unresolved rows. At some point the register
  needs an unresolved-row triage pass, not just archiving.
