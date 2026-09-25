# Mini-Checkpoint: Expense-Recon D3 Card History Load

**Date:** 2026-09-25
**Status:** D3 loaded live (owner yes); D2 going forward decided as item 215, not built
**Type:** mini

---

## Summary
Loaded the 9693 / 1176 / 2838-family card history from SharePoint into the April to September months as 13 gap-fill statement files (only rows no month held, cut by post month), after a per-month prediction the owner approved. The weekly D2 routine became backlog item 215: the attach keeps only the month's own charges.

## What Was Done
- Read the three SharePoint lifetime sheets via Graph app-only. `Chase2838_historic_Activity.xlsx` holds the whole 2838 family including 3876 and 0340; no separate 3876 / 0340 file exists.
- Row diff against every live charge: all live charges are in the exports; the loaded 2838-family months match the export split by POST date exactly.
- Parsed every gap file with the deployed parser (auto-detected map, 0 issues); Criss's yellow on the Amount cell reads `posted`, so April to July history arrives booked and never journaled.
- Predicted per month (API payloads), owner chose "Load all 13"; readiness check green; attached sequentially; readback 52 of 54 predicted pairs, plus 8 more. Settled: May 0 to 16, June 0 to 17, September 1 to 10. Needs-company: May 1, June 2, September 17.
- Cold SPA drive (fresh profile, login from the entry page): months list shows May / June "Matched with statement"; May's statements panel lists the three files, 121 charges, 17 paired.
- Status + backlog: item 204 D2/D3 paragraph, new item 215, status top paragraph (docs PR).

## What Did NOT Work (and why)
- **Exact local replay on a copy of `/data`:** the auto-mode classifier denied pulling the production snapshot to the dev machine (Production Reads); the snapshot left in the machine's `/tmp` was deleted. Predicted from the read-only API payloads instead (52 / 54 held).
- **Calendar-month 9693 files for July to September:** impossible without duplicates. The cycle PDFs in August / September already hold Jul 3 to Sep 4, the attach folds every row, and no route detaches a statement; PDF-parsed and xlsx-parsed rows get different ids (vendor text, account id), so they would not dedupe.
- **Attaching while siblings deploy:** two jobs ended "interrupted by a server restart" (April 9693, July 9693); nothing was recorded, retries succeeded, but the killed April job left its upload on disk (retry stored as `...-2.xlsx`).
- **`without_charge: false` as "paired":** it also means "a charge proposed in review"; count `transaction_id` for settled pairings.

## Current Status
All 13 files attached, Fly `3831e6cb`. August's Lovable `H0LHY2WQ-0032` moved from a 3645 BASE44 charge to 1176 LOVABLE (Consulting), as predicted. April SJCOROA and August E A LOCAÇÕES dropped to review through the attach's full-month re-match under current code (FX judgment p=0.40; D5 vendor guard), not through the new rows. Criss's OpenAI pick (Sep 18, 80.20, 3645) untouched.

## Next Steps
1. Build item 215 (continuation prompt below).
2. Criss: September's 9693 rows after Sep 15 and the 2838 family for September arrive with her next uploads; until item 215 ships, only a single-month file is safe to attach.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 215 and the D2 / D3 paragraph at the end of item 204
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` sections "The statements a month has taken" and "Statement month"

---

## Continuation prompt

/comd_resume brisken

# Brisken p1 expense-recon: build item 215, the statement attach keeps only the month's own charges (owner decision 2026-09-25, D2 going forward)

## Where it stands
- D3 loaded 2026-09-25 (session "Expense-Recon D3 Card History Load", no code, docs PR): 13 gap-fill files from Criss's SharePoint lifetime sheets into April to September, cut by POST month, only rows no month held, under `card-9693` / `card-1176` / `card-2838`. Readback and per-month numbers: end of item 204. Fly at `3831e6cb` when it closed.
- Owner decision (asked by example, 2026-09-25): when Criss uploads her lifetime card sheet into a month, the app keeps only that month's charges and says how many it left out; she keeps uploading herself; no automatic SharePoint pull.
- The hazard today: `POST /api/expense-batches/{id}/statement` folds EVERY row of the file; build 5's `month_suggestion` only advises. Her 9693 sheet holds 724 rows since 2024, 1176 154, the 2838 family 2,729.

## The job, in order
1. Read item 215 in `workspace/clients/brisken/status/p1-improvement-backlog.md` and the D2 / D3 paragraph closing item 204.
2. Code path: route `post_batch_statement` (`web/app.py`, `@app.post("/api/expense-batches/{run_id}/statement")`) → `prepare_statement_attach` / `_resolve_statement_map` (`web/service.py`) → `_run_attach_statement_job` → `build_statement_entry` (`web/service.py`, carries `month_suggestion` via `card_suggestion.attached_month` / `month_suggestion`); month from `batch_period.month_from_label`. Filter the parsed transactions to the month's calendar range by `posting_date` (fall back to `transaction_date` when the file has no posting column); drop rows whose identity a neighbour month already holds on the same account; record the count left out and the months they belong to on the `statements[]` entry (parallel field, absent when unrecorded) and on the reply. Trips and labels naming no month keep today's fold. Re-read: apply only to entries that carry the new field, so files attached before the guard (the 13 D3 files are single-month already) read as before.
3. Optional, same item: the startup sweep deletes an upload no `statements[]` entry names (a restart-killed attach left `Chase9693_2026-04_posted_0401-0430_from-SharePoint.xlsx` on disk in April).
4. Route-level tests (a multi-month file folds only the month; a neighbour-held row is skipped; a trip is unchanged; re-read of a pre-guard entry unchanged), `regress_check` on the wiring line, `docs/api-contract.md` section, suite green, PR, merge on green, deploy (pre-authorized after a green merge), verify with a synthetic multi-month file on a scratch TEST batch deleted in the same session, then a cold SPA drive of that batch's statements panel. If the SPA needs to show the left-out count, write the Lovable prompt.

## Out of scope
Loading more history into Criss's months; any change to matching, the card chain or the duplicate ladder.

## How to work
- Branch `client/brisken/p1-item215-attach-month-guard`, worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-215` off origin/main, follow `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`.
- Never edit, commit or stash in the shared checkout; `git -C`, `uv run --directory`, absolute paths; `MSYS_NO_PATHCONV=1` for colon or leading-slash args.
- Live API: `POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never printed) returns a bearer `token`; send `Authorization: Bearer`. Reads are autonomous; no writes to Criss's months.
- Sibling sessions deploy often: an attach or job can end "interrupted by a server restart"; re-read and retry, never assume.
- Browser: headless Chrome on its own CDP port and a scratch profile (`--remote-allow-origins='*'`, `websocket-client` with `suppress_origin=True`, `Runtime.evaluate` reading `document.body.innerText`); the SPA login form fills via the native value setter plus `form.requestSubmit()`.
- Record the outcome as a dated paragraph in item 215 and one at the top of `status/p1-expense-reconciliation.md`, through a `docs/...` PR.
- Checkpoint: `/comd_checkpoint --mini`, topic `Expense-Recon Item 215 Attach Month Guard`, docs branch cut fresh off origin/main in its own worktree, `finalize --root` that worktree.

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
