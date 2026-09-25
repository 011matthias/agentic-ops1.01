# Mini-Checkpoint: Expense-Recon Front 2 Receipts

**Date:** 2026-09-25
**Status:** Item 220 steps 1-2 in PR #1466 (CI running, not merged, not deployed); steps 3-7 queued; three owner decisions taken
**Type:** mini

---

## Summary
Front 2 of the five-front recon round. Unmatched receipts now name the statement they wait for: the reason reads the card before the date edge, a new `statement_not_loaded_for_date` code carries `waits_for_statements`, German cash and girocard words read as non-card payments, and the sign-off refusal counts waiting receipts apart from receipts with no charge.

## What Was Done
- Fresh GETs of July / August / September reproduced the map exactly (Sep: 44 neighbouring, 6 card not loaded, 1 not a card; Aug 8 neighbouring).
- Built on `client/brisken/p1-front2-receipts` (commit `f7c4fc44`, PR #1466): `unmatched_reasons.receipt_reason_code(coverage=...)`, `card_suggestion.reason_coverage`, `month_readiness.receipts_waiting_statement` + split `not_complete_detail`, service wiring, contract pins, `tests/test_receipt_waits_item_220.py` (19), api-contract section, `docs/lovable-receipt-waits-prompt.md` + PROMPT-STATUS row, backlog item 220 + Shipped row 140, status row.
- Prediction by the item-203 method, running the branch's own functions over the payloads: 0 control mismatches against live reason codes, 28/28 against live `waits_for_statements`. Moves: Jul 5 rows, Aug 0, Sep 49 (40 neighbouring + 6 card-not-loaded to not-loaded-for-date, 3 to not a card payment); `n_receipts_waiting_statement` 7 / 0 / 46.
- Two regress proofs bite (`coverage=_reason_cov` and `n_receipts_waiting_statement = _n_waiting`): 2 route tests red each, restored green. 172 tests in the touched files pass; local full suite and CI `test` still running at checkpoint time (CI accuracy job green).
- Owner decisions (AskUserQuestion, 2026-09-25): item 211 widen the borrow 3 days at the start edge = YES; `statement_expected=false` on 0113 / 6013 / 8311 in live settings = YES (per-action yes for that one write, after the field ships and a readiness check); picker offers only the five short company names = YES.

## What Did NOT Work (and why)
- **Coverage model keyed on `statements[].card_key`:** workbook entries carry the card in `account_id` with `card_key` empty; the model disagreed with 16 of 28 live waits lists until it read `card_key or account_id`.
- **`git commit -F -` fed by a PowerShell here-string:** PowerShell passed the message as a pathspec; use a message file.

## Current Status
PR #1466 open, CI `test` pending, everything else green. Nothing deployed; nothing written to Criss's months. The change is read-time: every month shows it the moment the backend deploys, no re-match needed. The SPA prompt is not pasted, so until then the workbench shows the new code through its fallback.

## Next Steps
1. Merge #1466 on green, deploy, verify the prediction, drive cold (continuation below).
2. Item 220 steps 3 to 7, plus item 211 (now decided yes) and the picker change.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 220
- `.scratch/recon-matching-gaps-2026-09-25.md` (main clone), sections named in the continuation
- `.scratch/front2-item220/` (main clone): `fetch.py`, `predict.py` (edit `SRC` to your worktree), `before-2026-09-25/` payloads

---

## Continuation prompt

````
/comd_resume brisken

# FRONT 2 of 5, continued: receipts with nothing to land on (item 220 steps 3-7, item 211, company picker)

## Where it stands (2026-09-25 evening)
- Item 220 steps 1+2 are in PR #1466 (branch client/brisken/p1-front2-receipts, commit f7c4fc44). An unmatched receipt's reason reads the card before the date edge (`card_suggestion.reason_coverage` -> `unmatched_reasons.receipt_reason_code(coverage=...)`), new code `statement_not_loaded_for_date` with `unmatched_receipts[].waits_for_statements`, German till words (`Bar`, `girocardOLV`, `Kartenzahlung erhalten`) read `not_a_card_charge`, `summary.n_receipts_waiting_statement` + `receipts_waiting_cards`, and the publish refusal splits "N receipts wait for a statement (cards ...)" from "M receipts have no charge on any loaded statement". Read-time only.
- At checkpoint: CI `test` pending, every other check green (accuracy job included); local full suite still running. NOT merged, NOT deployed.
- Predicted per row (fresh GETs, branch functions over the payloads, 0 control mismatches, 28/28 waits lists): Jul 5 rows move (0003/0053/0063 neighbouring -> card_statement_not_loaded, 0002 card_statement_not_loaded -> no_charge, 0008 -> statement_not_loaded_for_date), Aug 0, Sep 49 (40 neighbouring + 6 card_statement_not_loaded -> statement_not_loaded_for_date; 0031 Bar, 0044 girocardOLV, 0046 Kartenzahlung erhalten -> not_a_card_charge; 0024 private 3281 stays neighbouring). `n_receipts_waiting_statement` 7 / 0 / 46 against need_charge 14 / 8 / 49.
- SPA half `docs/lovable-receipt-waits-prompt.md` NOT pasted (PROMPT-STATUS Not applied row).
- Owner decisions 2026-09-25 (AskUserQuestion): item 211 widen the adjacent borrow by 3 days at the start edge = YES, build it; `cards[].statement_expected=false` on card-0113 / card-6013 / card-8311 in live settings = YES (per-action yes for that one settings write, after step 4 ships and a read-only readiness check); company picker offers only the five provisioning names = YES.

## Do first
1. `gh pr checks 1466 --repo 011matthias/agentic-ops1.01`. If a sibling merged first: `git merge origin/main` in the front2 worktree (C:\Users\neuma_p1qrsic\Repo\agentic-ops1-front2), keep both sides of shared-file conflicts, renumber backlog item 220 / Shipped row 140 only if taken, re-run the suite, push, poll. Merge on green with `gh pr merge 1466 --squash --delete-branch`.
2. Deploy per PARALLEL-ROUND-PROTOCOL.md §7: probe `summary.n_receipts_waiting_statement` on September first (present = a sibling's deploy carried it); else detached worktree agentic-ops1-deploy-front2 off origin/main, `uv run <it>/workspace/clients/brisken/automations/expense-reconciliation/deploy.py` (FLY_API_TOKEN from ~/.fly/config.yml).
3. Verify the prediction: `uv run .scratch/front2-item220/fetch.py .scratch/front2-item220/after` (main clone; GET only, 15 s gaps), then diff reason codes per row against the table above. Report every row that moves, never net it out. Drive the workbench cold in `agent-browser --session recon-front2` (or headless Playwright channel=chrome): September's unmatched receipts must not read "next or previous month" for 09-15..09-24 rows; the SPA key is not pasted, so assert no regression + the API field, and say so in those words.

## Remaining queue, in order (code pointers on origin/main 84a5e15e; service.py lines shift about +26 after #1466)
3. Coverage per card, declared. `ingest/statement_pdf.py:290-297 _parse_period` binds `_d1, _d2` and returns months/years only; keep the days. `service.build_statement_entry` (:12114, span from `_statement_period` :12075) gains parallel `period_declared_start/end`; for xlsx parse the requested range from the upload name (`Chase9693_2026-09_posted_0906-0915_from-SharePoint.xlsx`: that is a POSTED range, the file's own charges run 09-04..09-14). Stored entries have no declared fields until a re-read (a live write, not ours): derive the xlsx range at READ time from `upload_name` in `card_suggestion.statement_evidence` (:106-166, `_span` :184); PDFs gain it only on new attaches. Family rule (card_suggestion.py:12-18, :148-150, `_families` :169-181): a subcard counts as covered only when the upload printed one of its charges OR a declared span exists. Measure how many waiting rows move with `predict.py` before building on a guess.
4. `cards[].statement_expected` (default true, absent = true; validated in the settings PUT; cards.py:509 and :1211 are the active defaults). `statement_evidence` drops such cards from `active` for waits (keep them for labels), so `reason_coverage`/`waits_for` skip them and such receipts read `no_charge_on_any_loaded_statement`. Then the owner-approved write: read-only readiness check (the three cards exist, none has a statement anywhere, which rows move: 12 per the map, Jul 10 / Aug 2), then one settings PUT, then re-GET and verify.
5. Company labels resolve through ONE `entity_key(label, settings)` (settings `entities` aliases + `coa_provision.provisioned_entity_labels()` + card entities). Wire: matcher entity scope `deterministic.pair_in_scope` :1770-1789 (front 5 owns scoring: hand the key in via the matcher config or canonicalize at the rematch bake service.py ~15513-15528, never touch scoring), hand-match guard service.py :1661-1673, `entity_mismatch` advisory ~16036-16060 made per row, memory/account-map label keys. `available_entities` :496-534 then offers the five provisioning names only (owner YES); rows carrying a long spelling keep it and resolve. Proof: August LOVABLE 15.00 on card-2838 vs receipt 0008__Invoice-HMVWDWIL-0029.pdf (override "Brisken Corp Services, LLC") gains its candidate on a local replay, `tools/recon-match-attribution.py --live <DB> --run-id 074a7b8905d7` (DB via flyctl ssh sqlite3 backup + sftp, read-only; labels in the main clone's gitignored context/expense-reconciliation/expense-reports/csv/by-month/August-2026_live_*); six bundles stay 70/95, 0 labelled-right pairs move to wrong. No live re-match.
6. Adjacent borrow: `adjacent_pool_for_month` (~16289-16379) skips `doc in own_doc_ids or doc in origins` so a colliding `NNNN__rendered-body.pdf` is never borrowed; key borrowed receipts by (source batch, document id) end to end (consumption set, claims via `receipt_source_run`, view lookup `rec_by_id`). Carry the receipt's resolved card into the borrow (`bake_card_scope` ~7258-7277; `CARD_SCOPE_SOURCES` deterministic.py:1733 gains the borrowed source only when the home row's source is scoped). Item 211 (owner YES): widen eligibility to `lo - 3 days <= date <= hi` at the start edge only; August has 5 receipts dated 08-31 of the shape. Bundles 70/95.
7. Confirmed-private with no company: `categorize.py:958-959` refuses ENTITY_MISSING before any private input; take `private` as an input and read `private_no_company` (or drop the refusal); `recategorize_moved_companies` (~13885-13940) sweeps only rows showing a company, so handle the two live rows at read time only (Jul 0028 Brauhaus Kühler Krug, Sep 0024 DB Fernverkehr AG). Front 3 owns the posting account: add a local helper, do not widen theirs.
Do not build: bills with no payment words (D2), the 5-day windows, the FX bands, anything in deterministic.py scoring.

## How to work
Read docs/PARALLEL-ROUND-PROTOCOL.md on origin/main first and follow it to the letter (own worktree, append never reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session, checkpoint in a docs worktree, cleanup proof). Siblings: fronts 1 (chase), 3 (posting account), 4 (copies), 5 (reconciled clicks). No live writes on Criss's months beyond the one owner-approved settings write in step 4; every read-time change predicted per row on fresh payloads before deploy and checked after. TEST- fixtures only, removed in the session. No message to Criss or Dirk. Every fix: a route-level test through the caller it changed and one tools/regress_check.py proof (Windows paths in --test). B4: "not measured" is an answer. Traps from this session: statement entries carry the card in `account_id` (card_key is empty on workbooks); the repo slug is 011matthias/agentic-ops1.01; PowerShell here-strings do not feed `git commit -F -` (use a message file).

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
