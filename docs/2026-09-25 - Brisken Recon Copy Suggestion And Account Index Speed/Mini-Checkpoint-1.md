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
Follow-up 2026-09-25 ~03:00 UTC, on the owner's question: the case-9 SPA prompt WAS pasted (Lovable commit 3b13259, 01:15 UTC) and IS published (bundle audit: controls valid, 8/8 renderer fields live; month_suggestion is a type-only field erased at build). Its PROMPT-STATUS row is stale. Owner asked for a fresh-chat prompt; it is appended below.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/billing_account.py` (`_month_rows`, `decide`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/store.py` (`run_inputs_digest`)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` Shipped rows 130-132

## Continuation prompt

````
/comd_resume brisken

# Brisken p1 expense-recon: record the case-9 SPA prompt as live, run its after-publish checks, then item 212

## Where it stands
Shipped 2026-09-25 by the previous session, all live at Fly `7a67f7ee`: #1388 (a decided copy gets no `card_suggestion`, Shipped row 130), #1397 (the billing-account index re-derives a month only when that month's rows change; month reads 37 s -> 0.3-1.6 s, row 131), #1404 (a purchase's own card vetoes a different account card; July's Lovable copy `0044` is blank again, row 132). Checkpoint: `docs/2026-09-25 - Brisken Recon Copy Suggestion And Account Index Speed/Mini-Checkpoint-1.md`.

The case-9 SPA prompt (`workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-case9-status-prompt.md`) WAS pasted and IS published, but its PROMPT-STATUS row still says "Written 2026-09-25, not pasted". Evidence found 2026-09-25 ~03:00 UTC:
- Lovable commit `3b13259` (2026-09-25 01:15 UTC) in `011matthias/brisken-expense-review` added all four parts (`cardSuggest`, `cardVendor`, `reason.waits_for_statement`, `statement_month_differs`).
- `tools/lovable-bundle-audit.py`, run from a scratch copy with `NEW` set to the case-9 fields: controls valid, 8/8 renderer fields present in the live bundle (`waits_for_statements`, `waits_for_statement`, `card_suggestion`, `cardSuggest`, `cards/by-vendor`, `cardVendor`, `dry_run`, `statement_month_differs`). `month_suggestion` reads ABSENT only because it is a TypeScript type (`src/lib/api.ts:653`) and types are erased at build; the renderer reads `advisory_detail.code` -> `adv.statement_month_differs`. Leave it out of NEW.
- Cold SPA drive of July: the copy row renders "Waiting for the statement of Apple Credit Card - 0113, Credit Card - 6013, Credit Card - 8311." (EN).

## The queue, in order

1. **Record the prompt as live.** In `docs/PROMPT-STATUS.md` (module docs, line ~392, the `lovable-case9-status-prompt.md` row) replace the status cell with Applied + the evidence above (commit, audit result, the type-erasure note). In `tools/lovable-bundle-audit.py` set `NEW` to the eight case-9 renderer fields (the tool's docstring says to edit NEW per round; leave CONTROLS alone) and run it: exit 0 expected. Ship both in one PR (`client/brisken/p1-case9-prompt-live`).
2. **Run the prompt's section-6 checks, read-only** (Playwright MCP or agent-browser with a fresh `--session`; log in by reading `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` into a shell variable, never printed; on the months list click the row's `link` ref from `snapshot -i`, clicking the label text does not navigate):
   - (1) The waiting line in EN and in PT (the EN/PT toggle in the header), muted styling, on a card-less row.
   - (2) The suggestion chip on the three live rows that carry `card_suggestion`: June `a5f97a85b1d0` row `0020` Namecheap 11.88 -> 3876; September `51a22ad72864` rows `0049` Network Solutions 2.76 -> 3645 and `0086` Proton 9.99 -> 3876. Open the popover and assert the evidence lines. Do NOT click "Use this card": that is a card pick on Criss's live month (memory `feedback_recon_no_live_writes_criss_acts`).
   - (3) The by-vendor offer appears only after a pick, so it cannot be driven on live months without a write. Either drive it in a synthetic `TEST - ` batch created and deleted in the same session, or record it as not checkable live. Do not pick on a real month.
   - (4) `statement_month_differs`: look for a `statements[]` entry whose `advisory_detail.code` is `statement_month_differs` via `GET /api/runs/{id}` over every month (bearer auth, see How to work). If one exists, check that the SPA renders the localized sentence; if none does, record it as not checkable live.
   Record the results in the same PROMPT-STATUS row, or in a follow-up line if the PR already merged.
3. **Backlog item 212** (untaken as of 2026-09-25 03:00 UTC; check `gh pr list --state all --search 212` first): "A receipt settled by a neighbour month converts at the reference rate, not at the charge's amount". Brief at `workspace/clients/brisken/status/p1-improvement-backlog.md`, heading `### 212.` (~line 10877). `settled_charge_amounts` / `export_settled_amounts` (item 98) read only the month's own settled charges and skip receipts borrowed through item 204 step 3's neighbour claim; they feed the Zoho CSV `Exchange Rate` column (`single_currency_for_export`) and the month report. Read the brief fully before building; it says what the fix reads (the same claim `cards_settled_elsewhere` reads). Route-level test plus `tools/regress_check.py`.

## How to work
- One worktree per item off origin/main (`C:\Users\neuma_p1qrsic\Repo\agentic-ops1-<name>`); `git -C`, `uv run --directory`, absolute paths; never `git stash`. MSYS_NO_PATHCONV=1 for colon or leading-slash args, but never for flyctl paths: `cygpath -w` them.
- Merge on green CI; deploy per the module's `docs/PARALLEL-ROUND-PROTOCOL.md` §7 (fresh detached `origin/main` worktree, `--build-arg GIT_COMMIT`, skip if `/healthz` `server.commit` already contains the merge; `FLY_API_TOKEN` read from `~/.fly/config.yml` if flyctl cannot find its token). Accuracy replay: `uv run tools/recon_accuracy_check.py ci --fixtures <module>/tests/fixtures/accuracy --expected <module>/tests/fixtures/accuracy/expected.json`. Run focused test files, not the full suite beside siblings.
- Live API is read-only: `POST /api/login {"code": ...}` returns `{token}`, so send `Authorization: Bearer <token>` (no cookie; a cookie-only client gets 401 and reads a blind zero). Months list: `GET /api/expense-batches` -> `batches[]`; one month: `GET /api/expense-batches/{batch_id}`.
- After any change that adds a per-request derivation across months, time one month read twice on a quiet app before calling a deploy verified (May and September are the heavy ones; expect under 2 s).
- Backlog: a dated line under the item, Shipped row at the top of `## Shipped (loop history)` with the next free number (find it in THAT table; the file's first `| N |` row is the notes table), status file one paragraph at the top. These files mix CRLF and LF: edit byte-wise with per-anchor line-ending detection.
- Waits on the owner or Criss, unchanged: the item 211 ruling (borrow window under calendar-month exports); D7 (close day per card) unruled. D2/D3 history is loaded (#1402).

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
