# Checkpoint: August Posted Through The Unified Runner

**Date:** 2026-09-23
**Status:** Two months posted and readback-verified in TEST-BTS. The engine is proven; what remains is per-org routing, production mapping sign-off, and the Criss handoff.

---

## Summary

Built `reconcile_month`, the one-command month-end runner, then used it to
post August to the sandbox: 19 of 19, USD 2,758.91, readback clean, card
delta measured. Finding the month's real blocker took a detour through a
fix of mine that passed its own tests and failed on live data.

---

## What Was Done This Session

### The runner (PR #1201, `3d0eec34`)

1. `zoho/reconcile_month.py` composes six stages over existing proven
   functions: ingest, occupancy, live chart, plan, send-by-id assertion,
   guarded post, readback, summary. No stage re-derives resolution order,
   conversion math, the envelope or a guard.
2. Sandbox-only by assertion before a client exists; per-org card and
   currency config in `ORG_PROFILES`.
3. 42 runner-level tests through `run_month` / `main`, three regress
   bites, and a July known-answer dry run reproducing 0 / 41 / 3 / 2.

### The synthetic-reference collision (PR #1206, `33f8280c`)

1. August's OpenAI purchase refused against a July row. Both are real and
   different; both are called `0003__rendered-body.pdf`, because the
   export falls back to the archive filename and those filenames are
   per-batch indexes that restart monthly.
2. `period_scoped_reference` scopes only the filename fallback. The
   durable ledger was migrated (backup first): one row, 41 before and
   after, confirmed against the stored expense's own date.
3. `plan_reset` gained `only_ids` so a single stray row can be pulled
   without destroying the July rehearsal.

### The August run and the scorecard (PR #1207, `5f659e80`)

1. After the owner ran the purge, occupancy read `CLEAR`; 19 posted, 19
   readback clean, stored total MATCH, 0 rejected, 0 ambiguous.
2. Card census before and after: 60,482.18 to 63,241.09 USD, delta
   exactly 2,758.91. The card reconciles to the cent.
3. Closed the batch-page question with evidence: 25 documents, 20
   charges, five second copies carrying `counts_in_total: False`.

---

## Key Decisions Made

### Migrate the ledger; do not fall back to the bare key

- **Choice:** rewrite July's pre-scoping ledger key, with the month
  confirmed by reading the stored expense's `date` back from Zoho.
- **Rationale:** the bare key carries no month, so a read-time fallback
  cannot say which month's purchase it names. From August it finds
  July's row, which is the collision being removed.

### Confirm the month by stored date, not by the export in hand

- **Choice:** the migration compares the stored expense's `date` against
  the group's own `Expense Date` cell.
- **Rationale:** exact, because the payload's date is the CSV cell
  verbatim, and unlike a period-window test it does not trip over July's
  three legitimate June-dated rows.

### Targeted sandbox reset rather than a full one

- **Choice:** `plan_reset(only_ids=...)`, with `ok` comparing
  `expected_remaining` instead of demanding an empty org.
- **Rationale:** TEST-BTS holds 60 rows the ledger records as posted. A
  full reset would desynchronise the ledger from Zoho and destroy the
  July rehearsal.

---

## What Did NOT Work (and why)

- **A read-time fallback from the scoped reference to the bare one:**
  passed its unit tests, then reported "ledger holds 1 of 20" on the live
  August dry run. The test seeded the ledger with the SCOPED July key
  (`2026-07_0003__rendered-body.pdf`); the real ledger held the RAW key,
  so the test exercised a shape that did not exist.
- **The migration's first draft:** re-keyed July's row to `2026-08_...`
  when run from August, because it assumed the month from the export
  being processed. Caught by its own test before it ran on real data.
- **Reading credential scopes via a hand-rolled OAuth POST:** refused by
  the auto-mode classifier. Rebuilt on the app's own `ZohoClient`, which
  passed.
- **`uv run python .scratch/purge_august_trial_row.py --go`:** refused by
  the classifier at the destructive call; the dry run passed. The owner
  ran it in PowerShell instead.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/zoho/reconcile_month.py` | created | the six-stage runner |
| `tests/test_zoho_reconcile_month.py` | created | 44 runner-level tests |
| `src/expense_recon/zoho/expense_post.py` | modified | period-scoped references, ledger migration |
| `tests/test_zoho_synthetic_references.py` | created | detector + migration contract |
| `src/expense_recon/zoho/sandbox_reset.py` | modified | `only_ids`, `expected_remaining` |
| `tests/test_zoho_sandbox_reset.py` | modified | targeted-reset guards |
| `docs/zoho-month-end-posting.md` | modified | runner, collision, August sections |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | modified | posting-engine element row |

---

## Current Status

TEST-BTS (822116290) holds 69 expenses; 68 sit on the dummy card at USD
63,241.09. The durable ledger records 60 posted rows (41 July + 19
August). Both duplicate defenses verified re-armed on a re-run: occupancy
`ALREADY_OCCUPIED`, all 19 refusing as `already_in_ledger`.

Suite 3016 passed / 2 skipped, up from 2967. Three PRs merged: #1201,
#1206, #1207.

brisken platform: unknown plan, last assessed unknown. comms-log 15 days
stale (last touched 2026-09-08).

---

## Next Steps

1. **Refuse `(paid-through - assign)` / `(entity - assign)`** in
   `plan_expense_post`. Both columns are cosmetic today (the card comes
   from `ORG_PROFILES`, the entity only reaches `audit_note`), which is
   exactly why the guard belongs in before multi-card routing uses them.
   Expect both months' known answers to shift.
2. **Resolve the two USD 576.00 Zoho charges** of 2026-08-30 on card
   2838. Read-only; the statement is the arbiter.
3. **Criss's five residual rows**: August `H0LHY2WQ-0032`; July's three
   unmapped accounts and two date exceptions.
4. **Production GL mapping sign-off** for the 5 cards and 5 legal
   entities, which blocks any production org joining
   `CATEGORY_ACCOUNT_CODES`.
5. **Agree the manual-entry freeze date** with Criss.
6. `p2-product-decks.md` (62d) and `p2-targeting.md` (63d) remain stale
   past threshold, carried from the previous checkpoint.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`
- `.../src/expense_recon/zoho/reconcile_month.py`
- `.../src/expense_recon/zoho/expense_post.py`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Should the ledger check run before build-time refusals? For an
  already-posted row, `already_in_ledger` is the more informative answer
  and a placeholder refusal is noise.
- Are the two 576.00 rows two subscription tiers or one charge with two
  receipts? The app does not flag them, and its duplicate suppression
  demonstrably works elsewhere in the same batch.
- Transaction date or statement period as the production selection rule?
  Zoho coerced nothing, so the choice is still ours.

### Working Notes
August batch is `074a7b8905d7`, export at `.scratch/august-expenses.csv`
(20 rows, 20 purchases, 16 USD + 4 EUR). July is `50622baec444` at
`.scratch/july-expenses.csv`. Scratch drivers that will be wanted again:
`migrate_july_synthetic_ref.py`, `purge_august_trial_row.py`,
`card_census.py`, `preview_august_plan.py`, `august_batch_breakdown.py`.
Ledger backup from the migration is
`.scratch/zoho-post-ledger-testbts.20260923-155119.bak.sqlite`.

The card's full reconciliation: 4,297.74 (2026-09-22 trial) - 156.00
(purged) + 56,340.44 (July) + 2,758.91 (August) = 63,241.09.

### Reference Materials
- Vault entry `Zoho API Brisken Sandbox` (fullaccess, reaches exactly one
  org, so it cannot touch production books)
- PRs #1201, #1206, #1207

---

## How to Continue

`/resume brisken`, read the runbook's 2026-09-23 sections (the
synthetic-reference one carries the lesson worth not repeating), then
take Next Step 1. The two rehearsed months are now the known-answer
instruments: re-run both as dry runs after any posting-path change and
report the refusal mix rather than assuming it.

---

## Strategic Feedback

### What Worked Well This Session

- **Running the real thing caught what the suite could not.** The live
  August dry run is what exposed the bad fallback; 3002 green tests had
  just passed over it. The habit of driving the actual runner against
  live data after every change is what made this session's defect a
  20-minute detour instead of a wrong month in Zoho.
- **The second instance of the same mistake was caught by its own test.**
  Having just been burned by assuming the month from context, I wrote
  `test_migration_does_not_touch_augusts_different_purchase` before
  trusting the migration, and it went red immediately.
- **Measuring the card delta rather than summing intent.** 60,482.18 to
  63,241.09 is evidence; "we sent 2,758.91" is not.

### Suggestions

- **A fixture standing in for persisted state should be built from that
  state's real shape, not from what the new code would write.** My test
  seeded the scoped key because that is what the new code produces; the
  ledger held the old one. A cheap discipline: when a change concerns
  existing persisted state, read one real row and mirror its shape in the
  fixture before writing the assertion.

### System Health

- Deny-by-default held throughout: every refusal this session was
  correct, and the two that looked like bugs (August's false
  `already_in_ledger`, the abort after migration) were the guards
  reporting real problems.
- **Autonomy: 1 human intervention** (a re-scoped re-run adding the July
  baseline first; an addition, not a correction). Two destructive calls
  had to be handed to the owner because the auto-mode classifier refuses
  them.
