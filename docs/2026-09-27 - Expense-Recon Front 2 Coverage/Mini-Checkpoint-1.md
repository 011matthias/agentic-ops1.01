# Mini-Checkpoint: Expense-Recon Front 2 Coverage

**Date:** 2026-09-27
**Status:** item 220 steps 3 + 4 shipped, deployed (Fly v267) and the owner-approved settings write done; steps 5-7 open
**Type:** mini

---

## Summary
Statement coverage now reads the period an upload declares for itself (a PDF's Opening/Closing Date, a SharePoint export's posted range) and covers a subcard only when the upload printed it or declares its period; `cards[].statement_expected=false` on 0113 / 6013 / 8311 stops every card-less receipt from waiting on three cards nobody can export. Every live row moved exactly as predicted.

## What Was Done
- Measured first (fresh GETs, harness `.scratch/front2-item220/predict3.py`, control 27/27 live waiting lists): step 3 alone moves 0 reason codes; with the flag, July moves 5 receipts, waiting 6 -> 1.
- PR #1491 (merge `b6f951b3`): new `statement_declared.py`; `statements[].period_declared_start/end` on attach and re-read (a stored workbook read off `upload_name`); `card_suggestion.statement_evidence` unions printed + declared span, family only on a declaration; `Card.statement_expected`, validated in the settings PUT, and a save that omits the key keeps a stored false (SPA erasure class); `reason_coverage` returns `no_statement` for a receipt on such a card -> `no_charge_on_any_loaded_statement`. 20 route-level tests, 6 regress_check proofs all TEST BITES; item 204 and item 213 fixtures now name a declared family export. Suite 4038 passed / 2 skipped after merging main; CI 8/8 green; accuracy bundles unchanged.
- Deployed via `deploy.py` from a detached origin/main worktree: Fly v267, `/healthz` on `b6f951b3`.
- Live after deploy, as predicted: 0 reason moves; Aug 0002 / 0033 gained 0340; Sep 0032 / 0083 dropped 9693.
- Owner-approved write (per-action yes 2026-09-25): read-only readiness check, then `.scratch/front2-item220/settings_write.py --go`; re-GET verified exactly three flags changed. After it, as predicted: July 0003 / 0053 / 0063 -> neighbouring, 0004 / 0070 -> no charge, waiting 6 -> 1 (0008), 9 Expenses rows now `needs_entity`; Aug 0002 / 0033 wait on 0340 only; Sep's 14 lose three labels; need-charge unchanged.
- Cold SPA drive (`agent-browser --session recon-front2`) of July's workbench and Expenses tab: the Why line and the completeness line match the payload; no waiting line on Expenses, `needs_entity` label renders.
- Record PR #1492 (status files: Fly v267, live checks, the write).

## What Did NOT Work (and why)
- **Pytest with `-n auto` on the module:** pytest-xdist is not installed in the module env, usage error; run it plain, logged to a file.
- **Guessing the SPA's Expenses route `/expense-batches/{id}`:** the SPA 404s it; the route is `/expenses/{id}` (read the workbench's own links).
- **`lovable-bundle-audit.py` as proof the receipt-waits prompt was pasted:** its signatures are item 204's; the reason words on screen come from the backend's labels, so the paste is not established.

## Current Status
Item 220 steps 1-4 live. August's two card-less rows (Perplexity 08-20, E A LOCACOES 08-18) wait on 0340 only, because `August2026.xlsx` printed no 0340 charge and declares no period (rule kept as written; widening it to month-named workbooks was measured and not built). Front 1's Publish warning still names 0113 / 6013 / 8311 as uncovered (unchanged by design: they have no statement).

## Next Steps
1. Step 5: company labels through one `entity_key` (queue in the continuation prompt below).
2. Steps 6 (adjacent borrow by (source batch, document id) + item 211 start-edge widening) and 7 (confirmed-private with no company).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 220 (steps 3 + 4 paragraphs)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` last sections
- `.scratch/front2-item220/` in the main clone (fetch.py, predict3.py, diff_live.py, settings_write.py; payloads `now-`, `after-deploy-`, `after-write-2026-09-27`)

## Continuation prompt

/comd_resume brisken

# FRONT 2 of 5, continued: receipts with nothing to land on (item 220 steps 5-7, item 211)

## Where it stands (2026-09-27)
- Item 220 steps 1-4 LIVE. Steps 3+4: PR #1491 (merge b6f951b3), Fly v267 via deploy.py; record PR #1492. `statements[].period_declared_start/end` (PDF Opening/Closing Date; SharePoint export posted range from the name; stored workbooks read off `upload_name` at read time, stored PDFs gain it only on a new attach or re-read); coverage = printed span union declared span; a family's subcard is covered only when the upload printed one of its charges or declares its period. `cards[].statement_expected` (default true, stored only when false, 400 invalid_body on non-boolean, a PUT that omits the key keeps a stored false); nothing waits for such a card; a receipt on one reads no_charge_on_any_loaded_statement.
- Owner-approved write DONE 2026-09-27: statement_expected=false on card-0113 / card-6013 / card-8311, readiness-checked and re-GET verified. Live after it, every row as predicted: July waiting 6 -> 1 (0008), 0003/0053/0063 neighbouring, 0004/0070 no charge; Aug 0002 Perplexity / 0033 E A LOCACOES wait on 0340 only; Sep 45 waiting unchanged, labels lost the three cards.
- Harness in the main clone's `.scratch/front2-item220/`: fetch.py (GET-only, 15 s gaps, 45 s brake), predict3.py (steps 3/4 model; control against live waits), diff_live.py (row diff of two pulls), settings_write.py (the guarded write; do not re-run). Payloads: now-/after-deploy-/after-write-2026-09-27.
- Owner decisions already given 2026-09-25 (all YES): item 211 widen the adjacent borrow by 3 days at the start edge; the company picker offers only the five provisioning names.

## Remaining queue, in order (code pointers on origin/main b6f951b3; line numbers drift, search by name)
5. Company labels resolve through ONE `entity_key(label, settings)` (settings `entities` aliases + `coa_provision.provisioned_entity_labels()` + card entities). Wire: matcher entity scope `deterministic.pair_in_scope` (front 5 owns scoring: hand the key in via the matcher config or canonicalize at the rematch bake next to `card_res_bake`, never touch scoring), hand-match guard (`code="entity_differs"` in service.py), `entity_mismatch` advisory made per row, memory/account-map label keys. `available_entities` then offers the five provisioning names only (owner YES); rows carrying a long spelling keep it and resolve. Proof: August LOVABLE 15.00 on card-2838 vs receipt 0008__Invoice-HMVWDWIL-0029.pdf (override "Brisken Corp Services, LLC") gains its candidate on a local replay, `tools/recon-match-attribution.py --live <DB> --run-id 074a7b8905d7` (DB via flyctl ssh sqlite3 backup + sftp, read-only; note `flyctl ssh console` is refused by the auto-mode classifier, so plan the DB copy around it or ask; labels in the main clone's gitignored context/expense-reconciliation/expense-reports/csv/by-month/August-2026_live_*); six bundles stay 70/95, 0 labelled-right pairs move to wrong. No live re-match. Budget it as a matcher item (~200k).
6. Adjacent borrow: `adjacent_pool_for_month` skips `doc in own_doc_ids or doc in origins`, so a colliding `NNNN__rendered-body.pdf` is never borrowed; key borrowed receipts by (source batch, document id) end to end (consumption set, claims via `receipt_source_run`, view lookup `rec_by_id`). Carry the receipt's resolved card into the borrow (`bake_card_scope`; `CARD_SCOPE_SOURCES` in deterministic.py gains the borrowed source only when the home row's source is scoped). Item 211 (owner YES): eligibility `lo - 3 days <= date <= hi` at the start edge only; August has 5 receipts dated 08-31 of that shape. Bundles 70/95.
7. Confirmed-private with no company: `categorize.py` refuses ENTITY_MISSING before any private input; take `private` as an input and read `private_no_company` (or drop the refusal); `recategorize_moved_companies` sweeps only rows showing a company, so handle the two live rows at read time only (Jul 0028 Brauhaus Kühler Krug, Sep 0024 DB Fernverkehr AG). Front 3 owns the posting account: add a local helper, do not widen theirs.
Do not build: bills with no payment words (D2), the 5-day windows, the FX bands, anything in deterministic.py scoring, a month-named-workbook declaration (measured 2026-09-27: it would clear Aug 0002/0033, but April's 2838 CSV proved a file name does not guarantee its subcards).
Open questions for the owner (ask only if they block): should front 1's Publish warning (`summary.cards_uncovered`) honour `statement_expected=false`? Should Aug 0002/0033 keep waiting on 0340?
Waits on the owner: paste `docs/lovable-receipt-waits-prompt.md` (PROMPT-STATUS still "not pasted"; the words on screen today come from the backend's labels); then check its own signatures in the bundle (`lovable-bundle-audit.py` currently checks item 204's) and drive September's workbench.

## How to work
Read workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main first and follow it to the letter (own worktree off origin/main, append never reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session `recon-front2`, checkpoint in a docs worktree, cleanup proof). Siblings: fronts 1 (chase), 3 (posting account), 4 (copies), 5 (reconciled clicks). No live writes on Criss's months. Every read-time change predicted per row on fresh payloads before deploy and checked after (diff_live.py). TEST- fixtures only, removed in the session. No message to Criss or Dirk. Every fix: a route-level test through the caller it changed and one tools/regress_check.py proof (Windows paths in --test, run from your worktree). B4: "not measured" is an answer. Traps: repo slug is 011matthias/agentic-ops1.01; PowerShell variable names are case-insensitive ($r clobbers $R); PowerShell here-strings do not feed `git commit -F -` (use a message file); a Python triple-quote block inside a Bash heredoc is refused by a hook (write the script with Write); pytest-xdist is not installed (no `-n`); the module suite takes ~8 min, log it to a file and read its exit line; flyctl needs `FLY_API_TOKEN` exported from ~/.fly/config.yml; agent-browser `open` on the SPA never returns (background it, then read with `get url` / `eval` in the foreground), and navigate with `eval "location.assign('/expenses/<id>')"` (the Expenses route is /expenses/{id}, not /expense-batches/{id}); run `gh pr merge` as its own call; a PR whose branch conflicts with main gets NO CI checks at all (mergeStateStatus DIRTY), so merge origin/main before waiting on CI; wait for CI inside the turn (`gh run watch <id> --exit-status` or a Monitor on `gh pr checks`), never close a turn with a merge pending; local `test_smtp_starttls.py` fails for lack of openssl on this box (CI is the reference).

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
