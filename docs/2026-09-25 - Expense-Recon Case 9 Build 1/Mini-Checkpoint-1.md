# Mini-Checkpoint: Expense-Recon Case 9 Build 1

**Date:** 2026-09-25
**Status:** Shipped and live (PR #1362, merge `da4136f0`, Fly v229)
**Type:** mini

---

## Summary
Backlog item 204 step 2: an invoice that prints no card now takes the card its own payment receipt prints whenever the grid shows the two as one document. On September's live read the three predicted rows moved (`0008`, `0033` to 3645, `0029` to 9693) and `n_needs_entity` went 26 to 23.

## What Was Done
- `duplicates.lending_groups` (new): the reference groups plus every group behind `expenses[].duplicate` (not `ignore`, not `distinct`). `inherit_card_from_copies` walks it and takes optional `decisions`; with none it runs the ladder without file evidence (lends less, never more).
- `web/service.py`: only the three owned call lines (`# grid`, `# export`, `# before the card chain`) now pass `duplicate_decisions(run, receipts, resolutions)`. The Stripe pairs carry two numbers, so only rung 3 (the receipt printing the invoice's number, a file read) joins them; an evidence-free call would have lent nothing on the live rows.
- Guards unchanged, one added: a copy two shown groups would lend two different cards or entities gets neither.
- `tests/test_twin_card_c9.py` (9, route-level); `test_reference_duplicates.py`'s "a vendor/date pair lends nothing" unit test flipped in place; `docs/api-contract.md` section appended; backlog paragraph at the end of item 204, Shipped row 123, status paragraph.
- Four wiring points red under `tools/regress_check.py`: the group source in `inherit_card_from_copies` (7 of 70), grid line (3 of 9), export line (2 of 9), re-match bake line (1 of 9). Suite 3485 passed / 2 skipped. CI 8/8 green.
- Deployed from a detached `origin/main` worktree (fly.toml matched the live config); `/healthz` `da4136f0`; SPA driven cold over raw CDP: the three invoice rows render "Corporate Services from card · Credit Card Chase Visa - 3645 · Dirk Neumann - Corp Services" and "Cloud Services from card · Credit Card Chase Visa - 9693 · Brisken Cloud Services"; the three OpenAI 80.12 rows still read "No legal entity yet".

## What Did NOT Work (and why)
- **The plan's July Supermercado Fenix 803.11 prediction (copy 2 takes 3876):** copy 2 prints `CARTAO: xxxxxxxxxxxx3076`, which `_card_keys` reads as card 3076, so the pair names two cards and the kept guard lends nothing. Confirmed live after deploy: copy 2 still has no card.
- **`recon-match-attribution.py` as the before/after instrument:** 0 class moves and 0 row differences on all eight bundles, but every bundle receipt carries `payment_mode` None, so card lending cannot happen in bundle mode at all. A confident negative from a blind probe; the live API read was the measurement.
- **agent-browser `open` for the consumer drive:** hung past 150 s (fourth time on record). Raw CDP on port 9361 with a scratch profile drove it in three calls. The deploy-consumer gate does not recognise a CDP drive and kept advising "not driven".
- **`pytest -n auto`:** the module has no pytest-xdist; the run exits immediately having run nothing.
- **Inserting ledger lines with a CRLF-literal anchor after the merge:** a sibling's merged lines in `p1-improvement-backlog.md` are LF, so the anchor matched 0 times; the insert now reuses whatever ending sits at the anchor.

## Current Status
Live on v229. The three September invoices carry their twin's card, company and person. They still show a stale "no company yet, so no account was picked" category line (`review.refusal: entity_missing`): the GL categorization ran while they had no company and a card-chain company does not re-run the engine. That is open backlog item 206, not this build. Nothing was written to Criss's months; other rows move on read, the matcher scope at the month's next natural re-match.

## Next Steps
1. Builds 2 to 5 of the case-9 round run in their own sessions (no-card vendor guard; cross-month card flow-back; billing-account card memory, where the twin's printed card should outrank the account memory; honest status + suggestions + apply-to-vendor).
2. Item 206 (re-run the engine when a card gives a row its company) clears the stale category line on these three rows.
3. Owner / Criss: D2 (weekly Chase export, view access to 9693 / 1176), D3 (load the 9693 history and the April to June 3876 / 0340 sheets).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py` (`lending_groups`, `inherit_card_from_copies`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_twin_card_c9.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 204, "Build 1 (step 2)" paragraph


## Addendum (after the checkpoint, same session)

**Owner, 2026-09-25:** "D2 and D3 granted, both are in sharepoint." The files were found by name (not opened): 9693 `ADMINLLC9/Chase9693_Activity2024_Start.xlsx`, 1176 `admin_consulting/Chase1176_Activity_historicactivity_since202402.xlsx`, both with Aug/Sep cycle PDFs; no file names 3876 or 0340, candidates `admin_corp_services/Nicolas Neumann Monthly Expenses.xlsx` and `admin_corp_services/Chase2838_historic_Activity.xlsx`. The owner chose a fresh session that predicts per month and attaches only after a yes (prompt below).

**Note for item 206 (Prompt A in `docs/2026-09-25 - Brisken P1 Continuation Prompts For Items 206 207 And 180 181 183 172/Checkpoint.md`):** its live check expects 0 rows on July to September that show a company and still carry `entity_missing`. Live after v229 there are 3, all September and all from this build (`0008` Lovable 50.00 and `0033` Lovable 50.00 on Corporate Services, `0029` Anthropic 184.35 on Cloud Services). They gained their company at read time (twin card), with no edit and no re-match, so Prompt A's edit-route triggers never reach them and its re-match sweep only does at September's next re-match. Add a sweep that also runs on read or at deploy, and expect 3.

## Continuation prompt: D3 card history load (paste into a fresh chat)

````
/comd_resume brisken

# Brisken p1 expense-recon: load the D2 / D3 card histories from SharePoint into the months (backlog item 204, owner decisions D2 + D3; predict first, write only after a yes)

## Where it stands
- Case 9 build 1 shipped 2026-09-25: PR #1362 (`da4136f0`), Fly v229. An invoice takes the card its twin receipt prints. Checkpoint: `docs/2026-09-25 - Expense-Recon Case 9 Build 1/Mini-Checkpoint-1.md`. Builds 2 to 4 have open PRs (#1367 vendor guard, #1364 card flows back, #1366 billing-account card); build 5 runs in its own session. None of them is this session's work.
- Owner, 2026-09-25: "D2 and D3 granted, both are in sharepoint". D2 = the 9693 / 1176 statements as calendar-month Chase activity exports, pulled weekly, view access given (D1 already ruled the calendar-month form). D3 = load the 9693 history and Criss's April to June 3876 / 0340 sheets into the months. Owner chose (AskUserQuestion, 2026-09-25): a fresh session reads the files, predicts per month which rows move, and attaches ONLY after the owner's yes on that prediction.
- Files found by name 2026-09-25 (Graph app-only search, NOT opened):
  - 9693: site `ADMINLLC9`, `Chase9693_Activity2024_Start.xlsx` (modified 2026-09-23, 66,924 bytes); cycle PDFs `20260804-statements-9693-.pdf`, `20260904-statements-9693-.pdf`.
  - 1176: site `admin_consulting`, `Chase1176_Activity_historicactivity_since202402.xlsx` (2026-09-17, 30,870 bytes); cycle PDFs `20260804-statements-1176-.pdf`, `20260904-statements-1176-.pdf`.
  - 3876 / 0340 April to June: NO file names either number. Candidates on site `admin_corp_services`: `Nicolas Neumann Monthly Expenses.xlsx` (2026-09-23; Nicolas carries 3876) and `Chase2838_historic_Activity.xlsx` (2026-09-23; 3876, 3645 and 0340 are sub-cards under the 2838 account in the card registry, so this export may already hold them). Confirm by reading them; if neither holds 0340 rows for April to June, say so and ask, never guess.
- Live months: April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`.

## The job, in order
1. Read-only: download each file via Graph app-only (creds in `workspace/clients/brisken/context/.env`, never printed; `GET /sites?search=*` to find the site id by `name`, then `GET /sites/{id}/drive/root:/{file}:/content`), into `.scratch/` only, deleted at the end. Parse them: which card(s), which date span, how many charges per calendar month, currency. The cycle PDFs parse with `parse_statement_pdf_tolerant(path, legal_entity_id=...)`.
2. Read-only: for each month, what statements and cards it already holds (`GET /api/expense-batches/{id}` `coverage[]`, keys `card_key` / `statements` / `period_start` / `period_end` / `n_transactions`; empty for a receipts-only month), and read in the code and `docs/api-contract.md` how the statement attach route handles a file that spans many months (does it keep only the month's own dates, or take everything?) and how a second card's statement coexists with the first. If the attach would take out-of-month rows, split the file by calendar month locally first; never attach a multi-month file to one month unfiltered.
3. Predict, per month and per card: charges added; which receipts would newly match (the card-less 9693 rows on September, the Anthropic / OpenAI rows, July's and August's 9693 / 1176 rows); which rows change company or person; `n_needs_entity` before and after. Use the local replay where it can see cards (live-mode `tools/recon-match-attribution.py` needs a DB copy; the label bundles carry no payment modes and are blind to card changes, measured 2026-09-25). Say what the prediction cannot see.
4. Put the prediction to the owner through `AskUserQuestion`, one decision per month or one for the set, with the recommendation and the consequence (rows move at attach; Criss's own picks and rulings stay). No attach before a clear yes.
5. After the yes: run the read-only readiness check (right month, right card key and entity, right date span, no duplicate of a statement already attached), attach, then read each month back and compare against the prediction row by row. Drive the Expenses view cold for one month and assert the new card coverage renders.
6. D2 going forward: note where the weekly exports will land and whether Criss attaches them herself; do not build an automatic SharePoint pull in this session (ask first if it looks worth it).

## Out of scope
Any code change to matching, the card chain or the duplicate ladder (builds 2 to 5 own those); item 206; any write to Criss's months beyond the attaches the owner approved.

## How to work
- No code change is expected. If one turns out to be needed (the attach cannot filter by month, a parser gap), stop, describe it, and ask before building; if the owner agrees, branch `client/brisken/p1-d3-card-history`, worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-d3` off origin/main, and follow `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`.
- Never edit, commit or stash in the shared checkout; `git -C`, `uv run --directory`, absolute paths; `MSYS_NO_PATHCONV=1` for colon or leading-slash args.
- Live API: `POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never printed). Reads are autonomous; every attach is an owner-approved write.
- Browser: agent-browser has hung repeatedly; the working fallback is headless Chrome on its own CDP port and scratch profile (`--remote-allow-origins='*'`, `websocket-client` with `suppress_origin=True`, `Runtime.evaluate` reading `document.body.innerText`).
- Record the outcome as one dated paragraph at the end of item 204 in `workspace/clients/brisken/status/p1-improvement-backlog.md` and one paragraph at the top of `status/p1-expense-reconciliation.md`, through a `docs/...` PR.
- Checkpoint: `/comd_checkpoint --mini`, topic `Expense-Recon D3 Card History Load`, docs branch cut fresh off origin/main in its own worktree, `finalize --root` that worktree.

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
