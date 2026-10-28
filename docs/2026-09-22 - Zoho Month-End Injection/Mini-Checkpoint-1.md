# Mini-Checkpoint: Zoho Month-End Injection

**Date:** 2026-09-22
**Status:** Write path restored and merged (PR #1187, `c04740b1`); live posting blocked on an owner scope grant
**Type:** mini

---

## Summary

Dirk needs the reconciled month imported properly into Zoho Books at month end, which reverses his own 2026-08-22 "no ties to Zoho" directive; the owner chose API injection over a CSV hand-off. The deleted write path is restored and re-gated, and a read-only probe overturned two premises the scoping summary and this repo both held.

## What Was Done

- **Caught a deletion about to run.** Backlog item 23 rounds 4 and 5 were queued and unblocked (delete the journal artifact and the `/runs/{id}/zoho.csv` route; rename `zoho_expense_export.py`). Either would have removed the machinery the new requirement needs. Both marked OFF, with the reversal at the top of the item.
- **Restored from `5e2ff99e^` rather than rewritten:** `zoho/client.py`, `zoho/idempotent.py` (the 4.8 no-double-post ledger: write-ahead intent, deny-by-default on ambiguity), `zoho_post_cli.py`, the `zoho-post` dispatch. Repointed at post-#881 homes (`output/posting_common.py`); `_zoho_config_from_env` returned as `zoho.client.zoho_config_from_env` with its DC default corrected `eu` to `com`.
- **Added `create_expense` + `list_contacts`.** An accepted-but-unconfirmable create raises instead of returning success, because without an `expense_id` a re-run could post the same charge twice. Contact filtering is client-side, since a filter Zoho silently ignores answers for the whole workspace.
- **Replaced the guard instead of deleting it.** `test_no_zoho_connection.py` gives way to `test_zoho_posting_is_gated.py`, keeping the two guarantees that survive: the hosted web layer holds no Zoho import or credential (so no deploy can write into Criss's months), and a run config still cannot pull a chart mid-run. `test_the_import_guard_discriminates` pins both directions so the guard cannot silently stop matching.
- **Live read-only probes** (see Summary of findings below), plus a COA refresh across all 8 orgs.
- **Runbook** `docs/zoho-month-end-posting.md`; memories `project_brisken_zoho_books` and `reference_brisken_zoho_expense_orgs` corrected, MEMORY.md index line updated.

### Findings that change the design

- **There is no bank feed.** 0 of 39 sampled expense rows carry `imported_transactions`. This repo's own "charges from the card feed" note was an inference the record contradicts. Rows are hand-entered weeks late: Corporate Services' 108 July rows were created across 13 days ending 09-08, 45 on that last day. August 5, September 9. The duplicate hazard is Criss's entry, not a feed. **July must never be injected.**
- **The token is read-only** (`documents/expenses/bills/accountants/settings .READ`). Nothing posts until the owner grants `ZohoBooks.expenses.CREATE` plus contacts scope.
- **TEST-BTS = org `822116290`**, and its test is real and readable. Confirmed to the cent: 9 rows, 4,297.74, the AWS split across two COGS lines, vendor blank 9 of 9. Two summary claims fail: the audit string is on **7 of 9** (missing on the split row, which writes a different description format) and **6 of 9 rows fell back to `Office Infra and Admin`**, because an account passed as a name rather than a numeric `account_id` silently defaults.
- **The chart is stable**: all 8 orgs refreshed, identical to the June snapshot in 7; the only delta was the account the sandbox test created, which is the control proving the probe sees change.

## What Did NOT Work (and why)

- **Reading pytest's result off a backgrounded `pytest -q | tail -25`:** the pipeline reports `tail`'s status, so the harness announced "exit code 0" for a run that was actually 3 failed / 2792 passed, and the output file stays empty until exit so it cannot be polled either. Re-run unpiped; the exit code is then pytest's.
- **A `python - <<PY` heredoc carrying a triple-quoted block:** refused by `heredoc-size-gate` (the documented "unexpected EOF" shape). Used the Write tool plus `python <file>` instead.
- **The first `test_the_web_layer_does_not_import_the_posting_modules` pattern (`[.\w]*zoho[.\w]*`):** matched `output.zoho_export`, which the web layer legitimately imports to serve the CSV download. Narrowed to the posting modules and pinned both directions.
- **`gh pr merge --delete-branch` from the worktree:** printed `fatal: 'main' is already used by worktree at ...` because the sibling session holds `main`. The merge itself succeeded (`MERGED`, `c04740b1`); only the local checkout and branch cleanup failed. Remote branch deleted separately.
- **An Edit whose `old_string` spanned the "Owner direction" paragraph:** silently dropped it from backlog item 23, caught by grepping for the quoted directive afterwards and restored.

## Current Status

PR #1187 merged at 12:42 UTC, all 8 CI checks green, suite 2801 passed / 2 skipped (from 2795, minus the 4-test guard removed, plus 5 replacement and 5 client tests). Both real fixes regress-checked `TEST BITES` (green to red under mutation to green). Ruff clean. Branch and worktree pruned.

**Not deployed, deliberately.** The change is CLI-only and dormant: the hosted app never imports it and the token has no write scope, so a Fly deploy would carry no behavior change. The next slice, which does change behavior, deploys.

brisken platform: unknown plan, ~?/? ops/mo, last assessed ?. Run `/ops-audit brisken`.

## Next Steps

1. **Owner:** widen the Self Client grant to `ZohoBooks.expenses.CREATE` plus contacts scope. Verify by reading the `scope` field off the token response, never by attempting a write.
2. **Criss handoff:** agree who enters which month before any real post. September (9 rows) is the clean first candidate; July (108) is permanently off limits.
3. Numeric `account_id` resolution, which kills the 6-of-9 fallback.
4. A month-occupancy guard that refuses to post into an org, card and month already holding rows, turning "never inject July" from remembered into refused.
5. Per-org routing for the 5 cards across separate organizations, and the BRL/EUR/USD cases.
6. brisken comms-log is 14 days stale (last touched 2026-09-08).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 23, reversal block at the top)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/idempotent.py`
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_zoho_posting_is_gated.py`
