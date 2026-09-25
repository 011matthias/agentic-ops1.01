# Mini-Checkpoint: Brisken Recon Copy Suggestion And Account Index Speed

**Date:** 2026-09-25
**Status:** Three p1 changes merged, deployed and verified; live on Fly at `7a67f7ee`
**Type:** mini

---

## Summary
The briefed item shipped (no `card_suggestion` on a decided copy). Verifying it exposed two live defects from build 4's billing-account index: every month page took ~35 s and failed in the SPA, and once the index built, it lent July's decided Lovable copy a card its twin's charge contradicts. Both are fixed and verified.

## What Was Done
- **#1388 (Shipped row 130):** `build_expense_view` passes `copy=r.document_id in grid_copies` into `card_suggestion.case9_row_fields`, which then returns only `waits_for_statements`. Test `test_a_decided_copy_gets_no_suggestion`, regressed red. Live: 3 suggestions, 0 on copies. The brief expected 4; May's original `0000` now holds 3645 via `settled_charge`, which ends its own suggestion.
- **#1397 (row 131):** live timing on v239: May read in 37 s, September 33 s, April 9 s, January 2.6 s, settings 1.3 s. The health check failed 01:43-01:46 UTC, the proxy returned 503 ("no known healthy instances") and the SPA's May page read "Failed to fetch". Cause: `billing_account.build_account_index` ran `month_evidence` over all seven months on every request. Fix: per-process reuse keyed on the new `RunStore.run_inputs_digest(run_id)` (the run's rows in runs, decisions, duplicate_resolutions, expense_field_overrides and expense_edits). The run is re-read under the digest, and a result is cached only when the digest matches before and after the read. After the fix: May 1.6 s then 0.3 s, September 0.5 s, April 0.4 s. Test `test_a_month_is_re_derived_only_after_its_own_rows_change`, regressed twice (cache never hits; constant digest).
- **#1404 (row 132):** once the index built, July's copy `0044` (Lovable 200.00, `50622baec444`) read `card-1176` via `account` while its twin `0043` is settled on `card-2838`. `decide` now returns None when the judged purchase already names a different card through another copy; it still never votes for itself. Test `test_a_copy_of_a_settled_purchase_is_not_lent_another_card`, regressed red. Live: 2 account rows (May Anthropic 99.95 / 90.00 on 3876), July `0044` blank.
- Cold SPA drive after the last deploy (fresh agent-browser session, login, July): the page renders in 4 s. The copy row shows "copy 2 of 2 · not in total", "Waiting for the statement of Apple Credit Card - 0113, Credit Card - 6013, Credit Card - 8311" and "Pick the card that paid", with no 1176.
- Memory `project_brisken_recon_case9_plan.md` gained the build 4 follow-up lesson.

## What Did NOT Work (and why)
- **Reading the live months list with the login cookie:** `POST /api/login` returns a bearer `token`, not a cookie, so `GET /api/expense-batches` answered 401. The census then read "0 suggestions", a blind negative. Send `Authorization: Bearer <token>`.
- **A whole-database fingerprint (file mtime/size) as the index cache key:** not built. `client_errors`, `jobs` and `login_failures` share the SQLite file, so the SPA's own error posts would invalidate the cache constantly. It would also not spare Criss the rebuild after each edit. Per-run digests replace it.
- **Mutating `h.update(text...)` to `pass` to regress the digest:** stayed green, because the per-row `h.update(b"\x00")` still counts rows and the pick adds an override row. Mutating `return h.hexdigest()` to a constant bites.
- **Clicking the month label text on the SPA months list (`find text "July 2026" click`):** does not navigate. Click the row's `link` ref from `snapshot -i`.

## Current Status
p1 live on `7a67f7ee` (Fly, after siblings' v240-v243). Month reads are sub-second on a quiet app. Copies carry no suggestion and no disputed account card. platform: unknown plan (infrastructure.yaml has no ops figures); comms-log: none for brisken.

## Next Steps
1. PROMPT-STATUS row `lovable-case9-status-prompt.md` still reads "Written 2026-09-25, not pasted", but the live SPA renders `waits_for_statements` (seen 02:40 UTC in July). Check whether `cardSuggest.chip` and `cardVendor.offer` render too, then correct the row.
2. Backlog items 211 (owner decision: the borrow window under calendar-month exports) and 212 (reference-rate conversion on a neighbour-settled receipt), both from item 204 step 3; 213-215 are recorded and owned by sibling sessions.
3. After any change that adds a per-request derivation across months, time one month read twice on a quiet app before calling the deploy verified.

## Loop status
This session's queue is empty: the briefed item plus the two defects it exposed are shipped. Per SESSION LOOP step 9, no continuation prompt. Waiting on the owner or Criss: the item 211 ruling and D7 (close day per card). D2/D3 history was loaded by a sibling session (#1402).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/billing_account.py` (`_month_rows`, `decide`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/store.py` (`run_inputs_digest`)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` Shipped rows 130-132
