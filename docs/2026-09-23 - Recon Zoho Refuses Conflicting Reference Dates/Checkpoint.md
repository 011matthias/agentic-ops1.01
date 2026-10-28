# Checkpoint: Recon Zoho Refuses Conflicting Reference Dates

**Date:** 2026-09-23
**Status:** Shipped and merged (PR #1219, `028a26b6`). Sandbox only; nothing deployed, nothing written to either month.

---

## Summary

`group_by_reference` read a shared `Reference#` as one purchase split
across accounts, which let Hostinger's reused invoice number merge two
documents 25 days apart into a single USD 345.22 expense. That is now the
hard refusal `conflicting_reference_dates`. Two of the brief's predicted
numbers did not survive measurement, and catching both is the session's
more durable result.

---

## What Was Done This Session

### The guard

1. `REFUSAL_CONFLICTING_DATES` fires from `build_expense_payload` when a
   group's readable `Expense Date` values span more than
   `MAX_REFERENCE_DATE_SPREAD_DAYS` (2).
2. `reference_date_spread` returns min/max over READABLE dates only, and
   `None` below two of them, so an empty or unparseable cell stays with
   `date_precedes_period_window`, which names that problem better.
3. Placed first inside the build and ungated by `period`; the #1211
   ledger-first order still outranks it.
4. 15 new cases: 8 through `run_month` per the test file's docstring,
   plus a 7-case parametrized unit test of the spread helper.

### Verification

1. Wiring regressed via `regress_check.py` (`spread` to `None`): 4
   caller-level tests red, restored green.
2. Intra-build order regressed by physically moving the guard below the
   stale-date check: exactly one test red,
   `test_conflicting_dates_outrank_a_stale_date`. Backed up and restored
   with `cp`, never a git restore.
3. Both months re-run as dry runs against the durable ledger, and both
   re-planned against a throwaway sqlite for the fresh-ledger case.
4. A differential probe (guard disabled, same source, re-planned) to
   establish WHY the fresh-ledger count did not move.

### Handover

1. `.scratch/undo_testbts_double_counts.py` written and dry-run, for the
   USD 748.61 the owner may or may not want corrected. Not executed.

---

## Key Decisions Made

### A hard refusal, not compound keying

- **Choice:** refuse a date-disagreeing group rather than key the ledger
  on reference + date so the two become separate purchases.
- **Rationale:** compound keying would POST BOTH, and one of Hostinger's
  two documents matches no statement line on either month, so it converts
  a silent merge into a silent duplicate. It also re-keys the ledger for
  every reference, the migration pain the runbook's synthetic-reference
  section already documents. Recorded in the code comment so it is not
  re-litigated.

### Tolerance of 2 days rather than 0

- **Choice:** `MAX_REFERENCE_DATE_SPREAD_DAYS = 2`.
- **Rationale:** a genuine split is one receipt, so its rows share a date
  exactly. The 2 days absorb a statement-vs-transaction-date nuance if the
  export ever starts writing per-row dates. Hostinger's spread is 25, so
  the tolerance costs nothing on the real case.

### First inside the build, and ungated by period

- **Choice:** ahead of the stale-date guard, and not conditional on
  `period` the way that guard is.
- **Rationale:** the stale check reads `group.cell("Expense Date")`, which
  is row[0] only, so while the rows disagree WHICH date it judges is an
  accident of CSV order. And a reference whose rows span a month is not
  one purchase regardless of which month is being posted.

---

## What Did NOT Work (and why)

- **The brief's predicted fresh-ledger effect (July 30 to 29 postable):**
  measured 30 either way. `H_46243348` also carries an unassigned card, so
  `card_or_entity_unassigned` was already holding it; the guard moved it
  between refusal buckets (unassigned 11 to 10, conflicting 0 to 1) rather
  than out of postable.
- **The brief's carried-forward suite floor (">= 3055"):** measured 3054
  passed / 2 skipped on `f3ecd6bc`. The prediction that #1210's FX tests
  had raised it above `b4186a7a`'s 3055 was wrong in direction.
- **`resolve_profile(None)` as a sandbox default:** raises `OrgRefused`.
  The CLI passes `args.org`, which DEFAULTS to `SANDBOX_ORG_ID`; the
  function itself has no default. Fixed by passing the id explicitly. The
  guard behaved correctly.
- **`uv run tools/regress_check.py --file <repo-root-relative>`:** the
  tool resolves `--file` against `--cwd`, not the process cwd, so the path
  must be relative to the app dir. One retry, the error named it exactly.
- **`uv run ruff` from either the worktree root or the app dir:** ruff is
  not a project dependency; `uvx ruff check` is the working path.
- **`gh pr merge` local cleanup:** failed with "'main' is already used by
  worktree", the known false-FAIL. The remote squash-merge succeeded;
  confirmed `state: MERGED` before doing anything else.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/zoho/expense_post.py` | edit | the refusal, the constants, `reference_date_spread`, the wiring |
| `automations/expense-reconciliation/tests/test_zoho_reconcile_month.py` | edit | 8 cases through `run_month`, incl. both ordering tests |
| `automations/expense-reconciliation/tests/test_zoho_expense_post.py` | edit | 7-case parametrized unit test of the spread helper |
| `automations/expense-reconciliation/docs/zoho-month-end-posting.md` | edit | new 2026-09-23 section; Hostinger + Still-open rows updated |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | element row with the measured figures |
| `.scratch/undo_testbts_double_counts.py` | create | owner's USD 748.61 correction, dry-run only (gitignored) |

---

## Current Status

Merged at `028a26b6`, all 8 CI checks green, remote and local branches
deleted, worktree removed. Verified by reading the merged file off
`origin/main` rather than trusting the merge report.

Suite 3069 passed / 2 skipped, measured twice locally (once on the settled
tree after all probe mutations were restored) and once by CI's `test` job
on a clean checkout of the merge commit.

brisken platform: unknown plan, `~?/?` ops/mo, last assessed `?`.

Both rehearsed months remain byte-identical against the durable ledger,
which is the signal that the ledger-first ordering survived: July 56/46
with 41 / 3 / 2 and 0 postable, August 20/20 with 19 / 1 and 0 postable,
ledger 60 posted.

---

## Next Steps

1. **Owner decision on the USD 748.61** in TEST-BTS. Dry-run line is in
   the session transcript; `--go` applies it. Note the new consequence:
   after the Hostinger delete a re-run will REFUSE rather than re-post.
2. **13 unassigned cards still gate the production run** (11 of July's
   46, carrying USD 54,235.71, 96% of the month; 2 of August's 20).
   Read PR #1214's attribution measurement before proposing a
   card-inference fix.
3. **Production GL mapping sign-off** for the 5 paid-through cards and 5
   legal entities, which blocks any production org joining
   `CATEGORY_ACCOUNT_CODES`.
4. **Manual-entry freeze cutoff** with Criss, an agreed date.
5. brisken comms-log is 15 days stale; owner confirmed nothing to log
   this session, so it is a watch item rather than a gap.
6. Two p2 status files are past the 21d threshold and were NOT touched
   here (`p2-product-decks` 62d, `p2-targeting` 63d). They belong to a
   p2 session; updating them from this session's knowledge would be
   invention.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`, the 2026-09-23 section "a reference whose rows disagree on the date"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/expense_post.py`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions

- Does Brisken want either double-count corrected, and if the Hostinger
  one is, who re-exports the batch with the 2026-07-28 document set aside
  as a copy?
- Are the production orgs on a paid Zoho tier? TEST-BTS is FREE, which is
  why foreign rows post converted at the CSV's own Exchange Rate.
- Per-org routing for the 5 cards across separate organizations is still
  unexercised; both rehearsed months went to ONE sandbox card in one org.

### Working Notes

The fresh-ledger measurement needs a throwaway sqlite plus the live chart,
because the runner aborts at the occupancy stage on an empty ledger by
design. `.scratch/fresh_ledger_plan.py` in the (now removed) worktree did
this by calling `plan_expense_post` with the runner's own `_plan_kwargs`,
so currency policy and the period window cannot drift from a real run. It
needs `resolve_profile(SANDBOX_ORG_ID)`, not `resolve_profile(None)`.

Fresh-ledger figures after the change: July 30 postable (USD 2,104.73),
10 `card_or_entity_unassigned`, 3 `account_unresolved`, 2
`date_precedes_period_window`, 1 `conflicting_reference_dates`. August 17
postable (USD 2,452.87), 2 unassigned, 1 account.

The guard changes no counts today. It becomes load-bearing the moment
someone assigns Hostinger's card, which is exactly when the merged 345.22
would otherwise have posted against a single 172.61 statement line.

### Reference Materials

- PR #1219, merge `028a26b6`
- PR #1211 (the ledger-first + unassigned ordering this builds on)
- PR #1214 / `docs/2026-09-23 - Attribution Measured Card Entity Person And Category`

---

## How to Continue

The code half of the Hostinger case is closed. What remains is owner
input, not engineering: the 748.61 decision, the 13 card assignments, the
production GL sign-off and the freeze date. Re-run either month as a dry
run to re-measure before acting on any of them; the ledger and occupancy
guards make that safe.

---

## Strategic Feedback

### What Worked Well This Session

- The brief's "MEASURE rather than assume" instruction earned itself
  twice in one session, on the suite floor and on the fresh-ledger count.
  Both predictions were plausible, and both were wrong.
- Regressing the two properties SEPARATELY was worth more than one
  combined check: the order mutation reddening exactly one test is what
  proves the ordering test tests ordering, rather than merely passing
  alongside a working guard.
- Treating a count that failed to move as suspicious rather than as
  confirmation. A differential probe turned "the change did not land" into
  "the row changed buckets", which is the opposite conclusion.

### Suggestions

- Backgrounding a command whose stdout is piped through `tail` makes its
  `.output` file empty until exit, so the sanctioned "Read it for interim
  output" does not work and polling is pure waste. Either do not pipe a
  backgrounded command, or treat piped-and-backgrounded as
  wait-for-notification only. `warn-tail-task-output-file` catches the
  bash half; the Read half has no event to hook.

### System Health

- Autonomy: 0 human interventions. Fully autonomous session; the only
  user input was the initial brief and the checkpoint request, plus one
  comms-staleness answer this skill required.
- The auto-mode classifier's refusal of destructive calls worked as
  designed: the Zoho DELETE was never attempted, and the user got a
  ready-to-run line instead.
