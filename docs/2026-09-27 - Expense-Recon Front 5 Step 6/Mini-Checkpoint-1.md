# Mini-Checkpoint: Expense-Recon Front 5 Step 6

**Date:** 2026-09-27
**Status:** Item 222 complete (steps 1-6 live); two new feedback notes filed as items 225 and 226
**Type:** mini

---

## Summary
Item 222 step 6 shipped and is live: a card-named EXACT pair whose merchant disagrees now waits in review when a same-amount receipt is left unmatched (PR #1479, merge `be01b686`, Fly v263). It was measured first and moves 0 pairs on any live month or bundle. Feedback notes #91 and #92 had no item, so they are now backlog items 225 and 226, and they are the next session's queue.

## What Was Done
- `MatchingConfig.exact_vendor_lookalike_guard` (asset key, default on) in `matching/deterministic.py`. It runs after the pass-2 assignment, because only then is it known which receipts are left over. The public helper `same_amount_receipts_waiting` lets the attribution tool read the same rule. `review_code: exact_vendor_disagrees`. The pair keeps its assignment, as D5 does.
- `service.review_cause_for_row`: the new code maps to cause `merchant_disagrees` plus `cause_detail.same_amount_receipt`. `docs/lovable-review-cause-prompt.md` (still unpasted) gains the key `merchant_disagrees_waiting`, because its no-card sentence would be wrong for these rows. `docs/api-contract.md` has a new section appended.
- Measured on a fresh read-only DB copy (flyctl ssh `sqlite3.backup` + sftp):
  - **Attribution tool:** July, August and the six bundles are byte-identical before and after. July reads 30 right / 0 wrong, August 6 / 2, bundles 70/95.
  - **Direct probe:** over those datasets plus September, two chosen pairs sit under 0.5 with a card: July Network Solutions 7.98 at 0.46 (labelled right) and September SendGrid 89.95 at 0.32. Neither has a same-amount receipt left over, so 0 fire.
  - **Differential:** one planted 7.98 USD receipt dated 2026-05-20 moves exactly Network Solutions and nothing else.
  - **Accuracy:** scorer 76.0, guard PASS x4, CI accuracy no diff.
- Tests: `tests/test_exact_vendor_lookalike_222.py` has 10 tests, 2 of them route-level through `rematch_month`. `regress_check` bit: disabling the call reddens the matcher test and the route test. The suite ran 3,971 passed, 2 skipped (14 min).
- Deployed via `deploy.py` from a detached origin/main worktree (v263; healthz commit `be01b686`). The live API on July / August / September is unchanged before and after, and 0 rows carry the code. August's Matching page was driven cold in headless Chrome: login 200, "35 of 143 charges paired, 5 to review", no fallback text, 0 writes. The SPA has no renderer for `same_amount_receipt` yet, so the drive proves no regression, not the new sentence.
- Read `/feedback.jsonl` (92 notes). #86-#90 already had items (185, 213, 217). #91 and #92 did not, so they are filed as items 225 and 226 in PR #1479. PR #1482 records the PR, release and live check.

## What Did NOT Work (and why)
- **CI monitor that only polled `gh pr checks`:** it sat silent for 30 minutes. The PR had turned CONFLICTING when a sibling's checkpoint landed on main, and a conflicting PR never gets CI, so "no checks" read as pending. The re-armed monitor reads `mergeable` and flags "no checks after 3 min".
- **Planting the differential receipt on 2026-07-27:** it found its own 7.98 charge in July (matches went 45 to 46), so it was never left over. A planted receipt must be dated outside every charge's window (2026-05-20 worked).

## Current Status
Item 222 is closed: steps 1-6 are live on v263. Its SPA half (`docs/lovable-review-cause-prompt.md`) waits on the owner. Items 225 and 226 are open and not investigated beyond the verbatim note. PR #1482 (the record) was in CI at checkpoint time.

## Next Steps
1. Item 226 (note #92): remove the statement Download links on the Matching page's Statements drop-down. SPA only, as a Lovable prompt, with item 141 as the precedent. First confirm the original file stays reachable some other way.
2. Item 225 (note #91): the "Save corrections to memory" list is not tangible. Open April's dialog read-only and compare each line to its correction. Follow-up to item 163.
3. Owner: paste `docs/lovable-review-cause-prompt.md`.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 225 and 226 (end of Open)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

---

## Continuation prompt

````
/comd_resume brisken

# Feedback notes #92 and #91: items 226 and 225

## Where it stands
Item 222 is closed. Step 6 shipped 2026-09-27 (PR #1479, merge be01b686, Fly v263; record PR #1482): `exact_vendor_lookalike_guard` sends a card-named same-currency EXACT pair with merchant below 0.5 to review (`review_code: exact_vendor_disagrees`, cause `merchant_disagrees` + `cause_detail.same_amount_receipt`) only when a same-amount receipt is left unmatched. Measured on July, August, September and the six bundles, it moves 0 pairs. A planted receipt moves exactly the one pair. The live API is unchanged and August's Matching page was driven cold. Waits on the owner: pasting `docs/lovable-review-cause-prompt.md` (now carrying `merchant_disagrees_waiting`). Waits on Criss: nothing.

Reading `/feedback.jsonl` (92 notes) found #91 and #92 with no item; they are now backlog items 225 and 226 (end of Open in `workspace/clients/brisken/status/p1-improvement-backlog.md`).

## The queue, in order
1. **Item 226 (note #92, operator 2026-09-25 16:23 UTC, on `/runs/0603bb0e6f38` = April 2026): "remove these statement download buttons".** The Matching page's "N statements" drop-down lists each statement file with a Download link (April has 3 files; August shows Download on August2026.xlsx and the Chase1176 SharePoint xlsx). SPA only: write `docs/lovable-{slug}-prompt.md`, add a PROMPT-STATUS Pending row, and hand the whole prompt over. Item 141 (note #68, the month page's repeated download buttons) is the shape precedent. Before removing, check that another route still serves the statement original (grep the SPA API client / `web/app.py` for the statement file route) so nothing becomes unreachable.
2. **Item 225 (note #91, operator 2026-09-25 16:15 UTC, on `/expenses/0603bb0e6f38`): "make sure the corrections displayed to user when 'Save corrections to memory' button is clicked are tangible, dirk and i had trouble understanding it".** A follow-up to item 163 (note #81; `lovable-memory-journal-prompt.md`, published 2026-09-23). Open the dialog on April read-only with every non-GET aborted, write down each line against the correction behind it, then make each line read as a concrete change. The owner's D4 ruling says to explain memory rules by example, account -> card -> count. Backend fields only if the payload lacks what the sentence needs.

## How to work
Protocol: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`.
- **Worktree.** Work in your own worktree off origin/main (`git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-item-226 C:\Users\neuma_p1qrsic\Repo\agentic-ops1-item226 origin/main`).
- **Shared files.** Append, never reflow.
- **After a push.** Merge origin/main and expect to renumber a Shipped row. Run `gh pr merge` as its own call. A CI watch must read `mergeable`, because a CONFLICTING PR never gets checks and sits silent.
- **Deploy.** Only via `deploy.py` from a detached origin/main worktree. flyctl may not find its token: pass `FLY_API_TOKEN` read from `~/.fly/config.yml`.
- **Drive.** Cold, with headless Playwright `channel="chrome"` (PEP 723 `playwright>=1.49`, `uv run --python 3.12`). Log in through the form after networkidle with `EXPENSE_RECON_OPERATOR_CODE` from the main clone's `workspace/clients/brisken/context/.env`. Click the feedback hint dialog's "Got it" before navigating. The month's charges are the "Matching" link (`/runs/{id}`); `/expenses/{id}` is the receipts grid. Abort every non-GET except `/api/login`.

Rules that do not bend:
- No live writes on Criss's months without a per-action AskUserQuestion.
- The matching program is closed.
- Each fix gets a route-level test through the caller and one `regress_check` proof.
- B4 applies.

Suite: `uv run --directory <worktree>/workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q -p no:warnings` (3,971 on 2026-09-27, about 14 min; no xdist).

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
