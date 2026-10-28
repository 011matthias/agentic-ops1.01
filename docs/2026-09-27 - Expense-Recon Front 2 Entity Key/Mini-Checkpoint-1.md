# Mini-Checkpoint: Expense-Recon Front 2 Entity Key

**Date:** 2026-09-27
**Status:** Item 220 steps 1-5 live (step 5 = Fly v268); steps 6-7 and item 211 open
**Type:** mini

---

## Summary
Two spellings of one company ("Corporate Services" / "Brisken Corp Services, LLC") are now one company everywhere a comparison happens, and the picker offers each company once. Shipped as PR #1495 (merge `49cc1638`), Fly v268, recorded in PR #1499; live exactly as predicted per month.

## What Was Done
- New `expense_recon/entity_keys.py`: a label's key is its org's single provisioning spelling, else the label itself. Not org-only, because live settings give "Brisken Holding, LLC" GmbH's org id 696750461 (Zoho's Holding org is 813627567).
- Wired: `MatchingConfig.entity_keys` (handed in by `rematch_month` and the folder ingest through `service.match_cfg_with_entity_keys`; `pair_in_scope` only, no scoring touched), hand-match guard (`validate_manual_match(..., settings)`), `entity_mismatch_advisory` (by company, plus per row: a receipt naming a company no card belongs to), `available_entities(..., carried=)` (five names; a month keeps a spelling its own rows hold so a Radix select never renders blank), `tools/recon-match-attribution.py`.
- 8 route-level tests (`tests/test_entity_key_220.py`); two regress proofs bit (rematch hand-in, guard settings argument); module suite 4046 passed / 2 skipped; CI 8/8 incl. the accuracy job.
- Attribution replay on the 2026-09-25 03:35Z SharePoint backup, origin/main vs branch: August 1 of 55 rows moves (0008 Lovable invoice `entity_mismatch` -> `rival_won_greedy`: it reaches its labelled charge LOVABLE 15.00 on 3645 and loses it to 0009, its receipt copy); July 0 of 82; no match changes.
- Live after v268: settings `entity_options` 8 -> 5, July 6, August 6, September 5; no row holds a company its month's list lacks; waiting/need-charge counts unchanged (Sep receipt 0096 Chili's arrived by intake between pulls). Cold Playwright drive of August Expenses: 55/55 rows, Lovable row reads "Brisken Corp Services, LLC", Moghul Mahal "Brisken GmbH", dropdown = blank + six names, 0 writes.
- Sibling finding picked up: `lovable-receipt-waits-prompt.md` is PUBLISHED (#1494).

## What Did NOT Work (and why)
- **A per-row advisory that flags every receipt whose company no charge in the month carries:** measured on live payloads, it would flag 28 September rows that are only waiting for the 2838 statement. Built the narrower rule instead (company no registered card belongs to: live 1 row, Aug 0017 Brisken GmbH).
- **Heredoc-written Python edits:** refused by the heredoc gate (triple quotes; >80 lines). Used Edit / Write.

## Current Status
Step 5 live and verified (API per month + SPA drive). The matcher half reaches August at its next natural re-match; no live re-match was run. Open for the owner: the Holding org id in settings (a live settings write, not made).

## Next Steps
1. Item 220 step 6 + item 211 (adjacent borrow keyed by source batch + document id; carry the resolved card; 3-day start-edge widening).
2. Item 220 step 7 (confirmed-private with no company: `categorize.py` ENTITY_MISSING, read-time for the two live rows).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 220 (step 5 + deploy paragraphs) and item 211
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- main clone `.scratch/front2-item220/` (scripts listed in the continuation)

## Continuation prompt

````
/comd_resume brisken

# FRONT 2 of 5, continued: receipts with nothing to land on (item 220 steps 6-7, item 211)

## Where it stands (2026-09-27 evening)
- Item 220 steps 1-5 LIVE. Step 5: PR #1495 (merge 49cc1638), Fly v268 via deploy.py; record PR #1499. New `expense_recon/entity_keys.py` (`entity_key`, `entity_key_map`, `entities_same`, `company_labels`, `norm_entity`): a company label's key is its org's single provisioning spelling, else the label itself (not org-only: live settings give "Brisken Holding, LLC" GmbH's org id). Wired: `MatchingConfig.entity_keys` (handed in by `rematch_month` and the folder ingest through `service.match_cfg_with_entity_keys`; `pair_in_scope(..., entity_keys)`), `validate_manual_match(..., settings)`, `service.entity_mismatch_advisory` (by company, plus per row: a receipt naming a company no card belongs to), `available_entities(settings, extra, carried=)` (five names, a month keeps a spelling its rows hold), `tools/recon-match-attribution.py`. Live as predicted: settings entity_options 8 -> 5, Jul 6, Aug 6, Sep 5; no row renders blank; August Expenses driven cold (Lovable row "Brisken Corp Services, LLC", dropdown blank + six). The matcher half reaches August at its next natural re-match (replay: 1 of 55 August rows moves, 0008 entity_mismatch -> rival_won_greedy against its receipt copy 0009; July 0 of 82).
- `lovable-receipt-waits-prompt.md` is PUBLISHED (sibling bundle audit, PR #1494); that owner wait is closed.
- Harness in the main clone's `.scratch/front2-item220/`: fetch.py (GET-only, 15 s gaps, 45 s brake), diff_live.py (row diff of two pulls), predict3.py / predict_step5.py (models against live waits / entity_options), fetch_backup.py (newest SharePoint backup `ExpenseTool` on site MARKETING via the module's app-only GraphDrive, extracts the SQLite files; run with `uv run --directory <module> --extra web python fetch_backup.py <outdir>`; this is the DB route that avoids `flyctl ssh`), diff_attr.py (per-receipt diff of two attribution --json outputs; edit its W path), drive_step5.py (cold Playwright drive with system Chrome, one grid read replayed on both API hosts, non-GETs aborted), settings_write.py (do not re-run). Payloads: before-step5-/after-step5-2026-09-27. A replay needs `EXPENSE_RECON_COA_PROVISION` = main clone `workspace/clients/brisken/context/coa-provision.json`, else no company keys join. The "before" tree for an A/B: `git archive origin/main <module>/src | tar -x -C .scratch/base`, then `RECON_MODULE_SRC=<that src>`.
- Newest SharePoint backup is 2026-09-25T03:35Z; none since. Check whether the backup job still runs before relying on it (read-only: GraphDrive list_folder, or the app's own backup status).

## Remaining queue, in order (code pointers on origin/main after #1499; line numbers drift, search by name)
6. Adjacent borrow: `adjacent_pool_for_month` skips `doc in own_doc_ids or doc in origins`, so a colliding `NNNN__rendered-body.pdf` is never borrowed; key borrowed receipts by (source batch, document id) end to end (consumption set, claims via `receipt_source_run`, view lookup `rec_by_id`). Carry the receipt's resolved card into the borrow (`bake_card_scope`; `CARD_SCOPE_SOURCES` in deterministic.py gains the borrowed source only when the home row's source is scoped). Item 211 (owner YES 2026-09-25): eligibility `lo - 3 days <= date <= hi` at the start edge only; August has 5 receipts dated 08-31 of that shape. Bundles 70/95. Measure before and after with `tools/recon-match-attribution.py --live <backup DB> --run-id <id> --labels <by-month labels.csv> --json` (both July 50622baec444 and August 074a7b8905d7), and report every row that moves. This is a matcher item: budget ~150-250k.
7. Confirmed-private with no company: `categorize.py` refuses ENTITY_MISSING before any private input; take `private` as an input and read `private_no_company` (or drop the refusal); `recategorize_moved_companies` sweeps only rows showing a company, so handle the two live rows at read time only (Jul 0028 Brauhaus Kühler Krug, Sep 0024 DB Fernverkehr AG). Front 3 owns the posting account: add a local helper, do not widen theirs.
Do not build: bills with no payment words (D2), the 5-day windows, the FX bands, anything in deterministic.py scoring, a month-named-workbook declaration, org-only company keys, a per-row advisory on "company carried by no charge" (flags 28 Sep rows that only wait for 2838).
For siblings, not front 2: August 0008 (Lovable invoice) and 0009 (its receipt) are one purchase the duplicate ladder does not collapse (front 4); `matching/judgment.py` `judge_unmatched` still compares raw entity strings (front 5).
Open questions for the owner (ask only if they block): should front 1's Publish warning (`summary.cards_uncovered`) honour `statement_expected=false`? Should Aug 0002/0033 keep waiting on 0340?
Waits on the owner: live settings `entities["Brisken Holding, LLC"].org_id` is 696750461 (GmbH's); `context/expense-reconciliation/zoho-entity-card-map.md` gives Holding 813627567. Correcting it is a live settings write: put it as a decision with a recommendation (AskUserQuestion) only when it blocks something, never write it unasked.

## How to work
Read workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main first and follow it to the letter (own worktree off origin/main, append never reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session `recon-front2`, checkpoint in a docs worktree, cleanup proof). Siblings: fronts 1 (chase), 3 (posting account), 4 (copies), 5 (reconciled clicks). No live writes on Criss's months. Every read-time change predicted per row on fresh payloads before deploy and checked after (diff_live.py). TEST- fixtures only, removed in the session. No message to Criss or Dirk. Every fix: a route-level test through the caller it changed and one tools/regress_check.py proof (Windows paths in --test, run from your worktree). B4: "not measured" is an answer. Traps: repo slug is 011matthias/agentic-ops1.01; PowerShell variable names are case-insensitive ($r clobbers $R); PowerShell here-strings do not feed `git commit -F -` (use a message file); a Python triple-quote block inside a Bash heredoc, or any heredoc over 80 lines, is refused by a hook (write the script with Write, append to CRLF docs through a small script); pytest-xdist is not installed (no `-n`); the module suite takes ~8-14 min, log it to a file and read its exit line; tests import shared helpers as `from tests.test_x import ...`; flyctl needs `FLY_API_TOKEN` exported from ~/.fly/config.yml; the live DB for a replay comes from the SharePoint backup (fetch_backup.py), since `flyctl ssh console` is refused by the auto-mode classifier; agent-browser `open` on the SPA never returns, so the drive is a Playwright script with system Chrome (drive_step5.py); the Expenses route is /expenses/{id}; run `gh pr merge` as its own call; a PR whose branch conflicts with main gets NO CI checks at all (mergeStateStatus DIRTY), so merge origin/main before waiting on CI; wait for CI inside the turn (`gh run watch <id> --exit-status` or an until-loop on `gh pr checks`), never close a turn with a merge pending; local `test_smtp_starttls.py` fails for lack of openssl on this box (CI is the reference).

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
