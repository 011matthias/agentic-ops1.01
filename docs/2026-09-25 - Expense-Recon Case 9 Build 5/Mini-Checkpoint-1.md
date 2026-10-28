# Mini-Checkpoint: Expense-Recon Case 9 Build 5

**Date:** 2026-09-25
**Status:** Build 5 (item 204 steps 1 and 5) merged (#1372, `6a4c7490`) and live on Fly v233; SPA prompt written, not pasted
**Type:** mini

---

## Summary
A receipt that names no card now says which cards' statements it is waiting for instead of asking for a company, carries a recurring-charge card suggestion it never applies, lets one picked card reach the vendor's other card-less rows on an explicit click, and a statement upload names the month its charges belong to.

## What Was Done
- `card_suggestion.py`: coverage by date read across every month (an upload that printed one card covers its whole `parent` family for its span), lever-E scan (first vendor word of 3+ characters, amount within 3% in the receipt's currency, 45 days, all on one named card), by-vendor target selection, `month_suggestion`.
- `expenses[].waits_for_statements` + review `waits_for_statement` in `needs_entity`'s place; `unmatched_receipts[].reason_code` `card_statement_not_loaded` for a no-card receipt; `expenses[].card_suggestion`; `POST /api/expense-batches/{id}/cards/by-vendor {vendor, card_key[, dry_run]}`; `statements[].month_suggestion` + advisory `statement_month_differs`.
- The view builders have no store, so `build_expense_view` / `build_view` each gained one trailing kwarg (`statement_evidence`, a lazy `EvidenceSource`) passed from `app.py`, and `build_statement_entry` an `attached_month` passed at its two calls. Named in the PR as the only lines outside the round's "You own" list.
- `tests/test_case9_status_c9.py` (11, route-level), contract pins, three older tests widened to the new code; six wiring points proven RED with `tools/regress_check.py`. Suite on the PR head 3571 passed / 2 skipped; accuracy replay no differences. Four merges from main (builds 1, 2, 3 and item 207/208 landed meanwhile), each conflict an append on both sides, kept both; Shipped row renumbered to 127.
- Live after deploy (read-only): every open card-less row in every month reads `waits_for_statement` (Sep 19, Aug 1, Jul 10, Jun 6, May 10, Apr 4; September was 22 `needs_entity` before, builds 1 and 3 resolved 3). Suggestions: Network Solutions 2.76 -> 3645 and Proton 9.99 -> 3876 as predicted, plus Fireflies 18.00 -> 3876 (June), Lovable 200.00 -> 3645 (May, x2) and -> card-2838 (July). July's run payload: 5 `card_statement_not_loaded`. Cold SPA drive (agent-browser `--session recon-c9-5`, access-code gate): September renders the backend's English fallback on exactly 19 rows, no raw `expx.review.reason.*` key, no "No legal entity yet", no fallback strings.

## What Did NOT Work (and why)
- **regress_check on the attach call's `attached_month=` line:** the 12-space literal is a substring of the 16-space re-read call, so it matched twice and the tool refused; proven on the single `_c9.month_suggestion(transactions, attached_month)` line instead.
- **`recon_accuracy_check.py ci` with no arguments:** `ci` needs `--fixtures` and `--expected`; copy them from `.github/workflows/expense-recon-tests.yml`.
- **Full suite beside other pytest runs:** `test_drop_speed_item_148` (0.7 s wall-clock budget) failed at 0.74 s under the load; 3/3 green alone.

## Current Status
Live v233 (`6a4c7490`). Two of the six live suggestions sit on decided copies (May and July Lovable 200.00): correct card, wrong row to offer it on. Network Solutions 173.98 (predicted) carries no suggestion. Build 4 (#1366) is open in its own session; item 206 (#1376) merged after this build. Platform/ops status for brisken: unknown plan (no `platform` section; not relevant to the Fly app).

## Next Steps
1. Owner: paste `docs/lovable-case9-status-prompt.md`; then bundle-audit and cold-drive it (see the prompt's section 6).
2. Follow-up (continuation prompt below): no `card_suggestion` on a decided copy.
3. After build 4 lands, re-read September: its waiting count should drop where the billing account names the card.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/card_suggestion.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (section "A receipt that names no card")
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 204, paragraph "Build 5 (steps 1 and 5)"

---

## Continuation prompt

````
/comd_resume brisken

# Brisken p1 expense-recon: no card suggestion on a decided copy (follow-up to item 204 build 5)

## Where it stands
Case 9 build 5 shipped 2026-09-25: PR #1372 (merge `6a4c7490`), Fly v233, cold SPA drive passed. Every open card-less row in every month reads `waits_for_statement`; `card_suggestion` is live on 6 rows. Builds 1 (#1362), 2 (#1367) and 3 (#1364) are merged; build 4 (#1366, billing-account card) was still open at checkpoint time and belongs to its own session. The SPA half `docs/lovable-case9-status-prompt.md` is written and NOT pasted (PROMPT-STATUS Not applied row).

## The one item
Two of the six live suggestions sit on DECIDED COPIES, rows that are out of the totals (`counts_in_total: false`): May 2026 (`86929f2a909a`) Lovable 200.00 dated 05-05 -> 3645 (the original row carries the same suggestion), and July 2026 (`50622baec444`) Lovable 200.00 dated 07-19 -> card-2838 (its evidence is the same-day July LOVABLE 200.00 charge its twin settled). The card is right; the row is the wrong place to offer it, and a click there would write an override on a copy.

Fix: `build_expense_view` already knows the copies (`grid_copies`, computed before the row loop). Pass `r.document_id in grid_copies` into `_c9.case9_row_fields` (the call at the END of the row dict) and return no `card_suggestion` for a copy. Keep `waits_for_statements` on copies (the review stays honest; copies carry `boxes: []` and move no count). Test route-level in `tests/test_case9_status_c9.py`: two identical-reference receipts after a charge on one card in the previous month; the counting row gets the suggestion, the copy does not. Regress the wiring with `tools/regress_check.py` (single-line mutation; run from the worktree that holds the change, `--test` with WINDOWS paths). Live after deploy: 4 suggestions, none with `counts_in_total: false`.

## How to work
- Branch `client/brisken/p1-c9-5b-copy-suggestion` in worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-c9-5b` off origin/main; `git -C`, `uv run --directory`, absolute paths; never `git stash`; MSYS_NO_PATHCONV=1 for colon or leading-slash args (never for flyctl paths: `cygpath -w` them).
- `docs/PARALLEL-ROUND-PROTOCOL.md` in the module governs merge, deploy (detached `agentic-ops1-deploy-c9-5b`, `--build-arg GIT_COMMIT`, skip if `/healthz` `server.commit` already contains your merge) and verify. Accuracy replay: `uv run tools/recon_accuracy_check.py ci --fixtures <module>/tests/fixtures/accuracy --expected <module>/tests/fixtures/accuracy/expected.json`. Do not run the full suite beside other pytest batches (`test_drop_speed_item_148` is wall-clock).
- Live API read-only (`POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`, never printed); read receipts through `GET /api/expense-batches/{id}`.
- Backlog: one dated line appended to item 204's "Build 5" paragraph's end; Shipped row at the top with the next free number after your last merge from main; status file one paragraph at the top.
- Waits on the owner or Criss, unchanged: the Lovable paste; D2 (weekly Chase export, view access to 9693 / 1176); D3 (load the 9693 history and the April to June 3876 / 0340 sheets); D7 unruled.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
