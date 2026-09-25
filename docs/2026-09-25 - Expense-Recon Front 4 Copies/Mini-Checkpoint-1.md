# Mini-Checkpoint: Expense-Recon Front 4 Copies

**Date:** 2026-09-25
**Status:** steps 1-3 of 7 shipped and live (backlog item 223, PR #1470, merge `0b9200b8`, Fly v261); steps 4-7 open
**Type:** mini

---

## Summary
Front 4 of the 2026-09-25 parallel round: the BENCH files traced (real receipts, not a load to delete), and two copy shapes the duplicate ladder never saw now decided by the tool: one number read two ways (`reference_digits`, `misread_digit`) and the rendered mail body (`body_twin`).

## What Was Done
- **Step 1, BENCH origin (read-only).** The 50 `CARD-nnn_..._BENCH-nnn.pdf` files (July 27, August 23) are not mail (no inbound archive, `submitted_by` empty). Two web uploads with an operator code: July 2026-09-23T23:56:27Z (28 files), August 23:58:38Z (30 files); the upload route records no operator label. PDFs built by FPDF 1.7 / MuPDF on 08-30 and 09-01; names encode each receipt's statement line, so the maker had already paired them. 16 of July's 27 embed the byte-identical photo of one of Criss's uploads; 12 July + 19 August BENCH rows are the ONLY receipt a charge holds. Deletion not recommended, so the owner decision in the brief did not arise.
- **Steps 2-3 (`duplicates.py`).** `document_number_cores` (longest digit run >= 6 of reference / invoice_number / receipt_number, account-id filter), `vendors_agree` (`merchant_identity.identity_key`, one key the start or end of the other), `find_duplicate_receipts_by_number` + rungs 3a/3b before `distinct_reference`, `body_twin_partners` + body groups (partners first, body last; decided only when the partners are one document), `kept_member` document-over-body, `with_kept_first` follows another group's kept doc. 13 route tests in `tests/test_duplicate_front4_copies.py`; three regress proofs bite.
- **Attribution replay** (subagent, labels + live DB + six bundles, origin/main vs branch): no labelled-right pair moved, July resolved_clean 26 -> 30, bundles 70/95 both. It caught `misread_digit` merging ER-00181 #016/#017 (7-ELEVEN 446525 / 446528, two purchases); fixed: a difference in the last two digits never counts.
- **Live after deploy (per row, fresh GET before/after):** August 1 row out (Zoho Books body, USD 2,150.95 -> 1,574.95), September 4 bodies out (USD 4,758.14 -> 4,498.14), July 7 groups changed exactly as predicted but 3 of 5 predicted rows left (BRL 3,222.46 -> 2,869.66). Cold Playwright drive of expenses.brisken.com: new totals render on August and September, old ones gone, no fallbacks, 0 non-GET.

## What Did NOT Work (and why)
- **Predicting July's read-time count from `rows[].chosen_document_id`:** 0076 and 0083 are candidates of two PENDING review pairs (SUPERMEC SAO JOSE 8.48 / 8.29, fx_judgment); `decided_copies` drops only copies in `effective.unmatched_receipts`, so a copy a review pair holds stays counted. They leave at July's next re-match (with the E A Locações slip, BRL 340.00; BRL 424.97 in all).
- **`misread_digit` as first written (any one position):** merged two real 7-ELEVEN slips three numbers apart in labelled bundle ER-00181; consecutive till numbers differ in the tail.
- **Heredoc Python with backslashes / triple quotes:** refused three times by the heredoc gate (correctly); scripts go through the Write tool.

## Current Status
Merged and live: PR #1470 (`0b9200b8`), Fly v261, suite 3941 passed / 2 skipped after merging fronts 1, 2, 5. Backlog item 223 (renumbered twice at merge: fronts 2, 1, 5 took 220-222), Shipped row 143, status row, api-contract section "Three more duplicate rungs", PROMPT-STATUS Pending row. SPA prompt `docs/lovable-copies-kind-prompt.md` NOT pasted (new groups read "Decided by the tool" until then). No live write was made; no message to Criss or Dirk.

## Next Steps
1. Step 4: `document_kind` in the extraction response SCHEMA only, A/B x2 old vs new over the stored receipts, `kept_member` reads it before the file name, `reminder` -> read-time review note.
2. Step 5: cross-month billing-account guard (Railway `77H7ITO0`, Rize `5ZK1BCDG`) + cross-month advisory.
3. Step 6: `intake_provenance.twin_of` at arrival.
4. Step 7: `POST /api/runs/{id}/duplicates/reapply` built and tested, run on nothing; then ask the owner about September's re-match (12 invoice-over-receipt swaps + the new body groups settle).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 223
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/duplicates.py` (front-4 block after `reference_keys`)
- `.scratch/recon-matching-gaps-2026-09-25.md` "Copies and duplicates" (main clone)

## Continuation prompt

````
/comd_resume brisken

# FRONT 4 of 5, part 2: copies and double counting (steps 4-7)

## Where it stands
Steps 1-3 shipped 2026-09-25: backlog item 223, PR #1470 (merge 0b9200b8), Fly v261, cold-driven. New duplicate rungs `reference_digits` / `misread_digit` (not in the last two digits) and a `body_twin` key in duplicates.py (block after `reference_keys`); `kept_member` keeps a document over a rendered body unless a charge holds the body; `with_kept_first` makes a group with no stored choice follow another group's kept doc. Live moves: August Zoho Books body out (USD 1,574.95), September 4 bodies out (USD 4,498.14), July 3 slips out now (BRL 2,869.66) and 0076 / 0083 / E A Locações 0054 (BRL 424.97) at July's next re-match (0076/0083 sit in pending review pairs; `decided_copies` drops only copies in `effective.unmatched_receipts`). The BENCH files are real receipts (31 hold a charge): do not propose deleting them. Pending paste: `docs/lovable-copies-kind-prompt.md` (three basis labels). Checkpoint: docs/2026-09-25 - Expense-Recon Front 4 Copies/Mini-Checkpoint-1.md.

## Queue, in order
4. Kind from the document itself: add `document_kind` (invoice / receipt / reminder / statement / other) to the extraction response SCHEMA only (llm/client.py ~529-543, beside invoice_number/receipt_number; instructions byte-identical, per the 2026-09-16 trap), A/B twice old vs twice new over the stored receipts (pull `/data/runs/*/receipts` via tar + `flyctl ssh sftp get`; PDFs prepared SERIALLY, only API calls parallel; ~$0.02 per run on the OpenAI key that bills Dirk, smallest set). Then `payment_document_kind` (duplicates.py ~1000) reads it before the file name; a `reminder` gets a read-time review note (item 186's quarantine extended), never a deletion. Receipt field: `document_type` exists (types.py ~512) and is None on all live rows.
5. Cross-month guard: a reference seen in another month of the same company with the SAME total is a billing-account key (Railway 77H7ITO0 5.00 Jul + Sep, Rize 5ZK1BCDG 12.99 Jul + Aug): compute at re-match (read-time duplicate_decisions runs on every view; do not load neighbour months there), store in the snapshot, pass into `reference_keys` / `document_number_cores`; cross-month vendor/date/amount/currency pairs as an advisory (0 live).
6. Intake decides once: an Invoice-*.pdf and Receipt-*.pdf naming one invoice number in one mail -> `intake_provenance.twin_of` (intake_mail.py part filter ~560-600); the ladder starts from it; nothing counts differently.
7. `POST /api/runs/{id}/duplicates/reapply` (operator, typed confirm): ladder over the month's receipts, commit group membership + kept order, re-match. Live write: build, test, run on nothing. Then AskUserQuestion: order September's re-match (12 invoice-over-receipt swaps, the four body groups settle; recommend yes, no charge decision moves) and July's (0076/0083/0054 leave the count).

## How to work
Protocol docs/PARALLEL-ROUND-PROTOCOL.md on origin/main (own worktree `agentic-ops1-front4b` off origin/main, append-never-reflow on shared files, merge origin/main after any push + re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session). Predict every read-time change per row on fresh payloads first, and treat "held" as NOT in `effective.unmatched_receipts` (a review pair holds its candidate), not only `chosen_document_id`. Attribution replay recipe (subagent, ~220k of its own context): tools/recon-match-attribution.py `--live <db> --learning <learning db> --files <receipts> --run-id ... --labels ...` + the six bundles with `--asset config/match-tuning.json`, old vs new tree. The SPA login button stays disabled when the code is typed before hydration: type key by key and retry until enabled. Backlog numbers are claimed at merge; three siblings renumbered this front twice.

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
