# Mini-Checkpoint: Expense-Recon Note 97 Filters

**Date:** 2026-09-27
**Status:** Front 4 queue closed (step 6 and item 227 shipped by a sibling); notes #99-#106 open
**Type:** mini

---

## Summary
Note #97 became backlog item 231 with a Lovable prompt, and the check against the published bundle turned up a second SPA defect: the duplicate panel's `BASIS_KEYS` gate hides every front-4 reason label. Item 223 step 6 and item 227 were built here too, but a sibling had already shipped both, so that work was dropped unmerged.

## What Was Done
- **Note #97 → item 231** (PR #1503, merge `0aecc8b5`): `docs/lovable-quiet-done-tiles-prompt.md`. Built from `ExpensesReviewGrid.tsx` (repo head `0da12e6`) and one live read of September (`n_expenses` 69, categorized 32, needs category 37, ready 28, no company or person 18, private 2, missing image 0). The attention tiles go under an amber "Needs a look" label; Categorized / Ready / a zero Missing image / Private become small filter chips. SPA only. The published bundle carries today's 5-column grid and none of the new keys.
- **Duplicate reason gate** (PR #1507, merge `cf30a314`): `duplicateReason()` renders `wb.dups.basis.<basis>` only for a basis in `BASIS_KEYS`, and the published set is still the first seven. 12 live groups read "Decided by the tool": July 6 `reference_digits` + 1 `misread_digit`, August 1 `body_twin`, September 4 `body_twin`. `intake_twin` would read the same. `docs/lovable-duplicate-reasons-gate-prompt.md` adds the four names, plus the `intake_twin` key only if it is missing. Note written under backlog item 223.
- Live checks, read-only: `/healthz` on `987e0b52` (sibling's Fly v270, #1496 + #1500); 0 rows carry `twin_of` in July, August or September.

## What Did NOT Work (and why)
- **Building item 223 step 6 and item 227 from the queue without checking open PRs first:** sibling PR #1496 (step 6) was opened at 20:04 UTC, before this session started the item, and #1500 (227) at 20:15. Both merged while this session's suite ran (4064 passed). The overlap only showed at `merge origin/main`: conflicts in `duplicates.py`, `cost.py` and `service.py`. About 70k context went into work that was dropped. Before starting a queue item, run `gh pr list --state open --search "item N"` and grep `origin/main`'s backlog for the item's SHIPPED marker.
- **Python edit scripts in a bash heredoc with triple quotes:** `heredoc-size-gate` refused both (correct). Use Write / Edit.

## Current Status
- Item 231 and the gate prompt are on main. Neither is pasted.
- Sibling PR #1505 is also titled "item 231" (months list, open). Since #1503 already claimed 231, it has to renumber at its merge.
- Notes #99-#106 (September Matching `/runs/51a22ad72864`, 20:28-20:33 UTC) are not itemized. All eight are about the page header: the statements line (#99 card last-4 only, #103 a "View all statements loaded" dropdown), the no-statement line (#100 more evident, #104 a "View cards with no statement" dropdown), the card scope (#101 "Showing card 2838" more evident), the intro (#102 remove the first two sentences), and the totals (#105 "USD 7,496.60 still open", #106 "USD 1,467.27 booked without a receipt (11 charges)" more visible).

## Next Steps
1. Notes #99-#106 as one SPA item for the Matching page header. First check that no sibling has claimed them (open PRs, backlog on origin/main).
2. Owner pastes: `lovable-quiet-done-tiles-prompt.md`, `lovable-duplicate-reasons-gate-prompt.md`, and the `intake_twin` line of `lovable-copies-kind-prompt.md`.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 223, 231)
- SPA source: `gh repo clone 011matthias/brisken-expense-review` (`src/components/SummaryBar.tsx`, `RunWorkbench.tsx`, `StatementPanels.tsx` for notes #99-#106)

## Continuation prompt

````
/comd_resume brisken

# Notes #99-#106: September's Matching page header

## Where it stands
- Front 4 is closed. A sibling shipped item 223 step 6 (PR #1496: intake records `twin_of`, ladder rung 0 `intake_twin`) and item 227 (PR #1500: gpt-5-mini / gpt-5 priced), deployed as Fly v270 (`/healthz` commit `987e0b52`). 0 live rows carry `twin_of`.
- This session: note #97 became backlog item 231, `docs/lovable-quiet-done-tiles-prompt.md` (PR #1503). The duplicate panel's reason labels turned out to be gated: `duplicateReason()` in the SPA's `CompareCopies.tsx` renders `wb.dups.basis.<basis>` only for a basis in `BASIS_KEYS`, and the published set is still the first seven. So 12 live groups (July 6 `reference_digits` + 1 `misread_digit`, August 1 and September 4 `body_twin`) read "Decided by the tool". Fix: `docs/lovable-duplicate-reasons-gate-prompt.md` (PR #1507). Checkpoint: docs/2026-09-27 - Expense-Recon Note 97 Filters/Mini-Checkpoint-1.md.
- Waiting on the owner (Lovable pastes): `lovable-quiet-done-tiles-prompt.md`, `lovable-duplicate-reasons-gate-prompt.md`, and the `intake_twin` line of `lovable-copies-kind-prompt.md`. The PROMPT-STATUS Not-applied table has the full list. Re-check after a publish with `fetch_corpus` from tools/lovable-bundle-audit.py; for the gate, the decisive check is the `new Set([...])` literal holding `hash` in the ExpensesReviewGrid chunk.
- Sibling PR #1505 (months list) is also titled "item 231". #1503 already claimed 231, so #1505 renumbers at its merge.
- Owner's call, not queued: step 7's duplicates reapply per month (owner said leave July).

## Queue, in order
1. **Before anything: check claims.** Run `gh pr list --state open --search "brisken p1"`, then grep origin/main's `status/p1-improvement-backlog.md` for "note #99" ... "note #106". A sibling took items 223 step 6 and 227 in parallel with the last session (it opened #1496 at 20:04 UTC, before that session started the item), and about 70k context went into dropped work.
2. **Notes #99-#106, one SPA item** (operator, 2026-09-27 20:28-20:33 UTC, all on September Matching `/runs/51a22ad72864`, the page header):
   - #99: the statements line "Statement loaded: 20260904-statements-9693-.pdf, Aug 05, 2026 to Sep 04, 2026, 32 charges…" should show only each card's last 4 digits.
   - #103: the same line becomes a dropdown "View all Statements loaded".
   - #100: "· No statement loaded for this card" should be more evident.
   - #101: "Showing card 2838" should be more evident.
   - #102: the intro "51 charges from the bank statement, matched against this month's receipts. Confirm or rej…" loses its first two sentences.
   - #104: "7 cards have no statement for this month: Apple Credit Card - 0113, Credit Card - 2838, …" becomes a dropdown "View cards with no statement for this month".
   - #105 and #106: "USD 7,496.60 still open" and "USD 1,467.27 booked without a receipt (11 charges)" formatted more visibly.

   Read the published SPA source (`gh repo clone 011matthias/brisken-expense-review`; start at `src/components/SummaryBar.tsx`, `RunWorkbench.tsx`, `StatementPanels.tsx`, `CardScope.tsx`) and one September `/api/runs/51a22ad72864` payload. Itemize at the END of the backlog (numbers are claimed at merge), write `docs/lovable-<slug>-prompt.md` + its PROMPT-STATUS row, and hand the prompt over in a four-backtick fence. SPA only unless a field the design needs is missing. Before calling any prompt "copy only", grep the rendering component for a gate (the `BASIS_KEYS` lesson).
3. Any newer note in `GET /feedback.jsonl` (106 notes at 20:45 UTC).

## How to work
Protocol: workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md on origin/main (own worktree off origin/main, append-never-reflow on shared files, merge origin/main after any push and re-run the suite, deploy only via deploy.py from a detached origin/main worktree, own browser session). Siblings merge into main every few minutes: before `gh pr merge`, read `gh pr view N --json mergeable`. CONFLICTING means merge origin/main, keep both sides, and renumber backlog items / Shipped rows a sibling claimed. UNKNOWN right after a push is normal, and `gh pr merge` refuses on a real conflict. Run `gh pr merge` as its own Bash call. Write conflict-resolver scripts with the Write tool (heredoc-size-gate refuses a heredoc holding Python triple quotes) and run them under `set -e`. Module suite ~11 min, no xdist: redirect to a log, read the summary line. Live reads: log in via the vault's `operator_code:` line (`.scratch/recon-reapply-dryrun.py` in the main clone has the block); `GET /api/expense-batches/{id}` takes ~1 s per month, so read each once. Feedback store: `GET /feedback.jsonl` (bearer); the note text is the `comment` field. An extraction schema or prompt change needs the A/B; cost it at list price (now in llm/cost.py).

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
