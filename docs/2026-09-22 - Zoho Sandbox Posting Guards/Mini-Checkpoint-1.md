# Mini-Checkpoint: Zoho Sandbox Posting Guards

**Date:** 2026-09-22
**Status:** Guards merged (PR #1189, `0e4beb95`). `expenses.CREATE` granted, `expenses.DELETE` not. July rehearsal is unblocked; the payload builder is the remaining gap.
**Type:** mini

---

## Summary

Second slice of the Zoho month-end work. Built the two pieces that decide whether the books end up correct (numeric `account_id` resolution, month-occupancy guard) plus the sandbox reset, then fixed a flaw the owner's "starting with July" request exposed in the guard written an hour earlier.

## What Was Done

- **`zoho/accounts.py`**: resolves a reference to a real `account_id` or returns a refusal naming why. No third branch, no default. Refuses on empty reference, export placeholder, reference absent from the org's chart, a chart with no ids at all (the `from_csv` case, which would otherwise post a null id), inactive account, DO-NOT-USE account.
- **`posting_common.resolve_ref`**: `_resolve_account` split so the file exports and the API poster share one resolution order and cannot disagree about which account a reference meant. `test_cards.py` unchanged is the proof.
- **`zoho/occupancy.py`**: refuses a month someone else already entered, by asking Zoho rather than our own ledger. `LOCKED_PERIOD` (production-only), `ALREADY_OCCUPIED` (every org including the sandbox), `UNVERIFIABLE` (a failed query never shares a branch with an empty month), `ok` true only for `CLEAR`.
- **`zoho/orgs.py`**: org identity as a leaf module so the guard need not import the ledger. TEST-BTS `822116290` joins `DEFAULT_ORG_ALLOWLIST`; config can only intersect, never extend.
- **`zoho/sandbox_reset.py`** + `client.delete_expense` / `client._delete`: guarded reset, blocked on scope.
- **Grant exchanged**: the owner's grant code traded for a refresh token, old token preserved as a comment in the gitignored `.env`, grant-code script deleted.

### The July correction

The first cut locked `2026-07` globally. The owner then asked to rehearse real months starting with July, which that lock would have forbidden. The lock's justification was always production-specific: what makes July dangerous is 118 rows a human typed, and those exist only in the real orgs. In a clone July is empty and is the *best* rehearsal month, because a full month is the shape the tool has to survive. A global lock there protects nothing while blocking the thing that de-risks the real run. Now scoped by `is_production_org(org_id)`, which is a positive list rather than "anything that is not the sandbox", so a typo'd or newly-cloned org cannot inherit production's protections.

### The grant came back partial

Granted: `accountants.READ`, `expenses.READ`, `expenses.CREATE`, `contacts.READ`. **Not granted: `expenses.DELETE`**, so the sandbox cannot be emptied. Also dropped `settings.READ`, `bills.READ`, `documents.READ`; nothing in the posting path uses them. Verified by calling, not by reading the scope string: the three needed reads return rows, `bills` and `settings/currencies` both 401.

**The deletion turned out not to be on the critical path.** July in TEST-BTS is already `CLEAR` — all 10 existing rows are dated 31 Aug to 21 Sep, so they occupy September and leave July empty. The reset matters before a *September* rehearsal, not a July one.

## What Did NOT Work (and why)

- **Deleting the TEST-BTS rows, as asked:** the re-consented grant carries no `expenses.DELETE`. Checked rather than assumed, since the owner had said they were widening the grant. Dry run is built and enumerates all 10 by id; it runs the moment the scope exists.
- **The first `is_production_org` design, a global July lock:** would have blocked the sandbox July rehearsal the owner asked for. Rewritten as a production-scoped rule.
- **Two full-suite runs launched against an already-stale tree:** started before later edits landed, so both were killed via `TaskStop` and re-run rather than read. Launch the suite after the last edit, not during.
- **`gh pr merge --delete-branch` from a worktree (again, second time today):** fails on `fatal: 'main' is already used by worktree`. Merge without the flag and delete the remote branch separately.

## Current Status

PR #1189 merged (`0e4beb95`), 8/8 CI green, suite **2860 passed / 2 skipped** (from 2801). Three regress checks each green to red to green: the placeholder refusal, the `UNVERIFIABLE` branch, the production-org refusal in the reset. Ruff clean. Branch and worktree pruned.

Driven live against real Zoho, read-only: occupancy gave three distinct verdicts across four cases (TEST-BTS 2026-07 `CLEAR`, 2026-09 `ALREADY_OCCUPIED`, 2026-10 `CLEAR`, Corporate Services 2026-07 `LOCKED_PERIOD`); resolution found 196 of 196 TEST-BTS accounts carrying ids, the trial's four references resolving to four distinct ids, and three references correctly refusing.

brisken platform: unknown plan, last assessed unknown. Run `/ops-audit brisken`.

## Next Steps

1. **Open question for the owner, and it changes the build:** which July data feeds the rehearsal? The app's own July batch (`50622baec444`, 32 receipts, no statement) is the faithful month-end path; production July's 108 rows are the fuller shape. Pick before building the reader.
2. Payload builder: reconciled expense to Zoho POST body with a resolved `account_id`, plus an expense-CSV reader (the ledger's `entries_from_rows` reads the JOURNAL csv) and an `ExpenseEntry` reusing `PostLedger`.
3. Wire both new guards into the posting CLI pre-flight.
4. `expenses.DELETE` on the grant, needed before a September rehearsal.
5. Per-org routing for the 5 cards, and BRL/EUR/USD.
6. brisken comms-log 14 days stale.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`
- `src/expense_recon/zoho/accounts.py`, `occupancy.py`, `orgs.py`, `sandbox_reset.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 23, reversal block)
