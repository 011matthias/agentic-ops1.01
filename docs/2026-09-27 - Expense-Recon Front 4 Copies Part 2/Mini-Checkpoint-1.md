# Mini-Checkpoint: Expense-Recon Front 4 Copies Part 2

**Date:** 2026-09-27
**Status:** item 223 steps 4, 5 and 7 shipped and live (PR #1480, merge `382b2a35`); step 6 open
**Type:** mini

---

## Summary
The last three buildable copies steps landed as one PR. The receipt reader says what a document calls itself. A reference that another month shows as a billing account no longer twins two bills. An operator route previews and re-applies the duplicate rules on a matched month.

## What Was Done
- **Step 4 (built here):** `document_kind` added to the extraction schema only (last property, instructions byte-identical). The kept copy reads it first, then the printed numbers, then the file name. A reminder is never kept, and on its own it reads `reads_as_reminder`. The extraction fingerprint was re-pinned to `41f094df...`.
  - A/B on the owner's yes: USD 2.32 on Dirk's key, the 251 stored documents of the 09-25 backup, two passes per arm, cache off.
  - Moves: 53 of 3,366 readings that were stable in both arms moved, against about 6.5% pass-to-pass noise.
  - Key fields: date, total, document_type and card 0. Currency 1: August 0053 read BRL -> null. That slip prints "VALOR 6,00" and no currency; the owner chose to ship.
  - invoice_number: 26 moves, 24 of them Stripe files that now read the number they print.
  - Kind accuracy: right on all 57 Invoice/Receipt files, and Redis 0070 reads as a reminder. The printed numbers call 33 real receipts invoices, hence kind first.
- **Step 5 (builder subagent):** billing-account keys across months. The same reference or digit core, the same money and dates at least 20 days apart. Stored as snapshot `duplicate_account_keys` at re-match and at a no-statement receipt add, and never loaded at read. A `cross_month_copies[]` advisory. 27 bite proofs.
- **Step 7 (builder subagent):** `POST /api/runs/{id}/duplicates/reapply` with a typed confirm and a required boolean `dry_run`. The dry run writes nothing (tested on both DBs). A real run is the ordinary re-match with trigger `duplicates_reapply`. 15 bite proofs.
- **Suite and live checks:**
  - Merged suite: 4015 passed, 2 skipped. CI green.
  - Deployed via deploy.py; `/healthz` answers on `382b2a35`.
  - Live route probe: 400 `reapply_confirm_required`.
  - Live dry runs: September 0 groups move; July 1 group (E A Locações 0054 -> kept 0091, BRL 340.00).
  - Cold CDP drive: September and July render their totals with no failure text. The only non-GET calls were Lovable analytics beacons, all blocked.
- **Backlog:** item 223 updated; Shipped rows 148-150; new item 227: `llm/cost.py` has no gpt-5-mini price, so every photo reading is recorded at USD 0 (the tracker said USD 0.21 against USD 2.32 at list price).
- **SPA prompt:** `lovable-copies-kind-prompt.md` gains the trigger label.

## What Did NOT Work (and why)
- **Sizing the A/B from the app's cost tracker ("USD 0.02 per pass"):** the tracker prices gpt-5-mini (the vision model) at USD 0, so the real cost was about USD 0.58 per pass. The subagent stopped at the USD 1 gate and the owner re-approved.
- **Numbers-first kind rule:** the printed numbers call 33 real receipts invoices (NFC-e slips, OpenAI receipts). With the new schema, Stripe receipts also read their invoice number, so the kind is asked first.
- **Chaining `gh pr merge` after a CI wait loop:** the no-auto-commit gate reads CI once, before the whole command runs, so it saw CI pending and refused. Run the merge as its own call.
- **Conflict resolver followed by `;`:** a failed assertion still let `git add`, `commit` and `push` run, and `f2c56eb4` carried conflict markers until the fix in `139c82ff`. Use `set -e` or `&&`.
- **"The next re-match re-bills the whole history" (pin docstring):** false. Only arrival paths call the reader, and a re-match reuses stored readings. Docstring corrected.
- **Expecting September's 12 swaps from a reapply:** a receipt arriving on 2026-09-26 at 21:06 had already re-matched September. 15 pairs keep the receipt and 7 keep the invoice a charge holds.

## Current Status
- Live on Fly at `382b2a35`. No live row moved at deploy.
- July: the owner chose "leave July", so 0054 (BRL 340.00) leaves the count at July's next natural re-match. 0076 and 0083 sit in pending review pairs.
- Not pasted: `docs/lovable-copies-kind-prompt.md`.
- Step 6 is open.

## Next Steps
1. Step 6: `intake_provenance.twin_of` at arrival (`web/intake_mail.py` part filter ~560-600), and the ladder starts from it.
2. Optional small item 227: the gpt-5-mini price plus a test that every configurable model has one.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 223 (steps 4, 5, 7 paragraphs; Open list)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`: the last three sections (items 223 steps 4, 5 and 7)
- A/B outputs, until the scratchpad is cleaned: `old_pass{1,2}.jsonl`, `new_pass{1,2}.jsonl` and `compare_out.txt` under this session's scratchpad `ab\`.

## Continuation prompt

````
/comd_resume brisken

# FRONT 4 of 5, part 3: copies and double counting (step 6, the last)

## Where it stands
Steps 4, 5 and 7 shipped 2026-09-27 in PR #1480 (merge 382b2a35), deployed via deploy.py (/healthz on 382b2a35), live-verified: route probe 400 reapply_confirm_required, dry runs on September (0 groups move) and July (1 group), cold CDP drive of September and July rendering their totals with no failure text.
- Step 4: `document_kind` (invoice / receipt / reminder / statement / other) is the LAST property of `_EXTRACT_SCHEMA` (llm/client.py), instructions byte-identical; `payment_document_kind` (duplicates.py) reads it first, then receipt_number / invoice_number, then the file name; `kept_member` never keeps a reminder; `_expense_review` gives a lone reminder `reads_as_reminder`. Fingerprint re-pinned 41f094df. Owner-approved A/B (USD 2.32, 251 stored docs of the 09-25 backup): 53 of 3,366 stable readings moved; 0 date/total/type/card; 1 currency (Aug 0053, a slip printing no currency, BRL -> null; owner chose ship); invoice_number 26 (Stripe Receipt-* files now read the paired invoice number, e.g. Receipt-2247-1655-6392 -> HMVWDWIL0029); document_kind right on all 57 Invoice/Receipt files, Redis 0070 = reminder. Only arrivals from the deploy on carry it (a re-match reuses stored readings).
- Step 5: `duplicate_account_keys` on the snapshot (computed in rematch_month and in a no-statement receipt add; page views never load another month), `account_keys` threaded through reference_keys / document_number_cores / find_duplicate_receipt_groups / decide_receipt_groups / lending_groups; `cross_month_copies[]` advisory (0 live). Keys Railway 77H7ITO0, Rize 5ZK1BCDG, 0 groups moved.
- Step 7: `POST /api/runs/{id}/duplicates/reapply` (confirm = label or run id, `dry_run` a required boolean; refusals run_not_found, not_an_expense_batch, reapply_no_statement, month_published, rematch_running, reapply_confirm_required / _mismatch, reapply_dry_run_required). September needs nothing (re-matched naturally 2026-09-26 21:06; 15 copy pairs keep the receipt, 7 the charge-held invoice). July: 0054 E A Locações (BRL 340.00) leaves at July's next natural re-match; owner said leave July, no write.
- Backlog: item 223 steps 1-5 and 7 shipped, Shipped rows 148-150; new item 227 (llm/cost.py has no gpt-5-mini price; the tracker records every photo reading at USD 0). Pending paste: `docs/lovable-copies-kind-prompt.md` (three basis labels + `mh.rematch.trigger.duplicates_reapply`). Nothing waits on Criss.

## Queue, in order
6. Intake decides once: an Invoice-*.pdf and a Receipt-*.pdf naming one invoice number in one mail -> `intake_provenance.twin_of` (web/intake_mail.py part filter ~560-600); the ladder starts from it (duplicates.find_duplicate_receipt_groups / decide_receipt_groups, which now take `account_keys`); nothing counts differently. Signals available at arrival: both parts' `invoice_number` (a Stripe receipt now reads its invoice's number) and `document_kind` (invoice / receipt). Predict per row on fresh payloads first; live rows carry no twin_of, so expect 0 moves.
7. Optional, small: item 227, the gpt-5-mini price in llm/cost.py (input, cached input, output incl. reasoning) and a test that every model the config can name has a price.

## How to work
Protocol: workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main (own worktree off origin/main, append-never-reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session). Siblings merge into main every few minutes: before `gh pr merge`, read `gh api repos/011matthias/agentic-ops1.01/pulls/N -q .mergeable_state` (dirty = merge origin/main, keep both sides, renumber backlog items / Shipped rows a sibling claimed); run `gh pr merge` as its own Bash call (the gate reads CI once, before the command); conflict-resolver scripts run under `set -e`, never `;` before `git add`. Module suite ~9-10 min, no xdist: redirect to a log and read pytest's summary line. Live-check scripts in the main clone's .scratch: `recon-reapply-dryrun.py` (login via the vault's `operator_code:` line, route probe + dry runs) and `recon-cold-drive-months.py` (raw CDP, headless Chrome :9361, login typed key by key, month route /expenses/{run_id}, non-GET aborted). An extraction schema or prompt change needs the A/B (the pin test's protocol); cost it at list price, not from the app's tracker.

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


## Addendum (after the checkpoint, same session)

- **Lovable prompts, published-bundle audit (2026-09-27):**
  - 13 prompts that `docs/PROMPT-STATUS.md` still called "not pasted" are live. Their rows were corrected in PR #1494.
  - Still to paste:
    - `lovable-attach-month-filter-prompt.md` (item 215)
    - `lovable-statement-colour-prompt.md` (item 162)
    - the one `mh.rematch.trigger.duplicates_reapply` line of `lovable-copies-kind-prompt.md` (its three basis labels are live)
  - All three were handed to the owner in chat.
- **Feedback note #98 (Settings > Email intake, "add nicolas@expenses.brisken.com to this list"):** DONE on the owner's yes. One PUT of the `intake` group added alias `nicolas` -> "Nicolas Neumann" (the person on card 3876). A whole-settings diff before and after shows only `intake.aliases.nicolas` changed.
- **Feedback note #97 (September Expenses, the summary / filter area): OPEN, not itemized.** "These filters inside months need to show the postive things ("categorized", "ready") small, and formatted with the obvious intent of enabling distinguishment from the stuff that needs user's attention". It needs an SPA prompt: read the published filter component and the payload counts first, then itemize it in the backlog and write `lovable-*-prompt.md`.
- Every other note in `/feedback.jsonl` (98 in total) is already cited in the backlog.

**Queue for the next session, in order:**
1. Note #97: itemize it and write the Lovable prompt.
2. Item 223 step 6.
3. Optional: item 227.
