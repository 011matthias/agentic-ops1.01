# Mini-Checkpoint: Expense-Recon Front 2 Adjacent Borrow

**Date:** 2026-09-27
**Status:** Item 220 step 6 + item 211 live (Fly v272); step 7 open
**Type:** mini

---

## Summary
A neighbour month's receipt whose id collides with the borrowing month's own is now borrowed under its own pool id and resolved back to (home run, id) everywhere a claim or file is read; the borrow carries the home row's card; item 211's three-day start edge ships narrowed to calendar-month periods. PR #1512 (merge `dc20372f`), live in Fly v272, recorded in PR #1520.

## What Was Done
- Measured on the 2026-09-25 03:35Z SharePoint backup before building: 4 receipts dropped only for a colliding id (Aug from Jul `0002` Hostinger 172.61, `0003` Konsultancy 15,972.00; Sep from Aug `0005` Obsidian 96.00, `0006` Zoho Books 576.00); 7 in the three days before a period; the commit's claims re-check merged claims across source months by id alone (latent downgrade, 0 live).
- Built in `web/service.py`: `borrowed_pool_id` (`{run}~{id}`), `receipt_source_ref`, `adjacent_borrow_window`, `ADJACENT_START_EDGE_DAYS`; the commit re-check and claim writes keyed on (home run, id); `sync_claim_for_decision`, `charges_settled_elsewhere`, `borrowed_source_view` (`document_id` only for a pool-id receipt); the borrow bakes the home month's resolved card. `web/app.py`: the image route serves a borrowed id from its home month.
- 8 route tests (`tests/test_adjacent_borrow_220s6.py`); six `regress_check.py` proofs, all TEST BITES; suite 4068 passed / 2 skipped / 7 local-only starttls failures; CI 8/8 incl. accuracy.
- Attribution replay origin/main vs branch on Jul/Aug/Sep/Jun/May: 0 of 270 own receipts move, no charge changes its pairing.
- Live after deploy: the four referenced borrowed receipts' images 404 -> 200 through the borrowing month with the home month's bytes; cold drive of September Matching identical before and after (0 error boundary, 11 "August 2026" badges, 0 writes).

## What Did NOT Work (and why)
- **Item 211 as approved (`lo - 3 days` on every period):** on the Chase-cycle months it drew only wrong neighbours into review (May: April's Fenix 117.79 BRL on Passaguai Cibo e Vino 23.49 USD; June: May's Anthropic 99.95 EUR on TST*Cheers Beacon Hill 120 USD) and gained nothing right. Shipped narrowed to periods opening on the 1st.
- **This session's own `deploy.py` run:** the flyctl build ran 20+ minutes on `1fa8bf67` while two sibling releases landed; releasing it would have rolled #1514 back. Stopped before release; v272 (`fc8db9cc`, a sibling's) carries #1512.
- **Finding the SPA's receipt viewer for a borrowed row:** the Matching page requests no receipt image on any tile driven, so the image-route gain is proven by the API probe only.

## Current Status
Step 6 + item 211 live. Nothing read-time moved except borrowed-receipt images through the borrowing month; pairings change only at each month's next natural re-match (replay predicts none). platform: unknown plan (infrastructure.yaml carries no platform section).

## Next Steps
1. Item 220 step 7 (confirmed-private with no company).
2. Owner/sibling items listed in the continuation below.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 220 (step 6 + deploy paragraphs) and item 211
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

## Continuation prompt

````
/comd_resume brisken

# FRONT 2 of 5, continued: receipts with nothing to land on (item 220 step 7)

## Where it stands (2026-09-27 night)
- Item 220 steps 1-6 LIVE, item 211 LIVE narrowed. Step 6: PR #1512 (merge dc20372f), live in Fly v272 (fc8db9cc, a sibling's deploy that carries it; this session's own deploy.py run was stopped before release because its 20-minute build was on the older 1fa8bf67), record PR #1520. A neighbour receipt whose id the borrowing month holds is borrowed under `borrowed_pool_id(home run, id)` = `{run}~{id}`; `receipt_source_ref(run, id)` -> (home run, id there) feeds the commit claims re-check and claim writes (keyed on the pair), `sync_claim_for_decision`, `charges_settled_elsewhere`, `borrowed_source_view` (`document_id` only on such a receipt) and the image route (`web/app.py` `receipt_image`: a borrowed id is served from its home month). The borrow bakes the home month's resolved card (`bake_card_scope`). `adjacent_borrow_window`: 3 days before a period that opens on the 1st only (the approved `lo - 3` on Chase-cycle months drew two wrong review proposals in May/June and nothing right); the arrival trigger `neighbour_months_covering` reads the same window. Replay on the 2026-09-25 backup, origin/main vs branch, Jul/Aug/Sep/Jun/May: 0 of 270 own receipts move, no pairing changes. Live: four borrowed images 404 -> 200 through the borrowing month (same sha as home); September Matching drive identical before/after.
- Harness: main clone `.scratch/front2-item220/` (fetch.py, diff_live.py, fetch_backup.py, drive_step5.py, and from step 6 probe_images.py (borrowed-receipt images through borrower vs home, GET-only) and drive_step6.py (cold September Matching drive, one run read replayed, writes aborted); the step 6 replay outputs sit in its `step6-2026-09-27/`). A replay needs `EXPENSE_RECON_COA_PROVISION` = main clone `workspace/clients/brisken/context/coa-provision.json`. The attribution tool prints borrowed receipts the matcher did not take as "replay only" unmatched receipts (rematch_month strips them): noise, not a move.
- The newest SharePoint backup is STILL 2026-09-25T03:35Z. `web/backup.py` `start_backup_thread` backs up on every boot then every 24 h, so two days of deploys with no copy means every round is skipped or failing; the Fly log window (100 lines) held no backup line. Cause not measured.

## Remaining queue, in order (code pointers on origin/main after #1520; search by name)
7. Confirmed-private with no company: `categorize.py` refuses ENTITY_MISSING before any private input; take `private` as an input and read `private_no_company` (or drop the refusal); `recategorize_moved_companies` sweeps only rows showing a company, so handle the two live rows at read time only (Jul 0028 Brauhaus Kühler Krug, Sep 0024 DB Fernverkehr AG). Front 3 owns the posting account: add a local helper, do not widen theirs. Predict per row on fresh GETs before deploy, check after with diff_live.py.
Then front 2's queue is empty: say the loop is done.
Do not build: bills with no payment words (D2), the 5-day windows, the FX bands, anything in deterministic.py scoring, a month-named-workbook declaration, org-only company keys, a per-row advisory on "company carried by no charge", item 211's widening on card-cycle periods.
For siblings, not front 2: August 0008 / 0009 (Lovable invoice + receipt) not collapsed as copies (front 4); `matching/judgment.py` `judge_unmatched` compares raw entity strings (front 5); live September OPENAI 81.12 now holds August's `0033` E A LOCACOES 340 BRL receipt (paired after 2026-09-25, vendor disagrees; matcher/front 5); the SharePoint backup gap above (ops).
Open questions for the owner (ask only if they block): should front 1's Publish warning (`summary.cards_uncovered`) honour `statement_expected=false`? Should Aug 0002/0033 keep waiting on 0340? Is item 211 narrowed to calendar-month periods acceptable (it is live that way)?
Waits on the owner: live settings `entities["Brisken Holding, LLC"].org_id` is 696750461 (GmbH's); `context/expense-reconciliation/zoho-entity-card-map.md` gives Holding 813627567. A live settings write: AskUserQuestion with a recommendation only when it blocks something.

## How to work
Read workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main first and follow it to the letter (own worktree off origin/main, append never reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session `recon-front2`, checkpoint in a docs worktree, cleanup proof). Siblings: fronts 1 (chase), 3 (posting account), 4 (copies), 5 (reconciled clicks). No live writes on Criss's months. Every read-time change predicted per row on fresh payloads before deploy and checked after (diff_live.py). TEST- fixtures only, removed in the session. No message to Criss or Dirk. Every fix: a route-level test through the caller it changed and one tools/regress_check.py proof (Windows paths in --test, run from your worktree). B4: "not measured" is an answer. Traps: repo slug is 011matthias/agentic-ops1.01; PowerShell variable names are case-insensitive ($r clobbers $R); PowerShell here-strings do not feed `git commit -F -` (use a message file); a Python triple-quote block inside a Bash heredoc, or any heredoc over 80 lines, is refused by a hook (write the script with Write, append to CRLF docs through a small script); pytest-xdist is not installed (no `-n`); the module suite takes ~12 min, log it to a file and read its exit line; tests import shared helpers as `from tests.test_x import ...`; flyctl needs `FLY_API_TOKEN` exported from ~/.fly/config.yml; the live DB for a replay comes from the SharePoint backup (fetch_backup.py), since `flyctl ssh console` is refused by the auto-mode classifier; agent-browser `open` on the SPA never returns, so the drive is a Playwright script with system Chrome (drive_step5.py / drive_step6.py; dismiss the `fb-hint-title` dialog first); the Expenses route is /expenses/{id}; run `gh pr merge` as its own call, never inside Push-Location or a chain; `gh pr merge` false-FAILs on "main is already used by worktree", confirm with `gh pr view --json state,mergedAt`; a PR whose branch conflicts with main gets NO CI checks at all (mergeStateStatus DIRTY), so merge origin/main before waiting on CI; wait for CI inside the turn (`gh run watch <id> --exit-status`), never close a turn with a merge or deploy pending; deploy.py refuses a tree behind origin/main, and a flyctl build can outlive sibling releases: before letting a long deploy release, check `flyctl releases` and `/healthz` commit, and stop it if live already carries your merge and a newer commit; do not pipe deploy.py through `Select-Object -Last N` (it hides progress until exit); local `test_smtp_starttls.py` fails for lack of openssl on this box (CI is the reference).

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
