# Mini-Checkpoint: Expense-Recon Notes 91-92

**Date:** 2026-09-27
**Status:** items 225 + 226 done; notes #93-#96 read and itemized (227-229), not started
**Type:** mini

---

## Summary
Feedback notes #91 and #92 answered. Item 226 (Matching statement download buttons) is a SPA prompt, merged in PR #1484. Item 225 (the memory-save dialog is not tangible) has its backend live (PR #1487, Fly v265) plus a SPA prompt for the Save dialog. The store grew to 96 notes during the session; #93 is covered by 226, and #94-#96 became items 227-229.

## What Was Done
- **226 (note #92):** the anchor is the Downloads row, not the Statements drop-down. The backend serves no raw statement upload, only `statement-categorized.xlsx`, and that stays reachable from the Expenses statements table. Prompt `docs/lovable-statement-downloads-off-matching-prompt.md`, PR #1484 (75012308).
- **225 (note #91):** lesson sentences now say what the next receipt gets. Cards are named by their Settings label and person; merchant-list card lessons carry the receipts the learner observed (`service.registry_card_observations`, shared with the card learner). PR #1487 (672c7ddf), Fly v265. Tests in `tests/test_memory_plan_tangible_item_225.py` (3), `regress_check` red on 3 wires, suite 3986/2 skipped. Prompt `docs/lovable-memory-plan-sentences-prompt.md` (dialog lists `lessons[]`, "Save {n} changes"). Record PR #1488.
- **Live:** April's memory-plan reads 18 lessons in sentences with 0 `card-` keys. The published Publish checklist renders them (cold drive, 0 non-GET). The Save dialog still shows the old table until the paste.
- **Notes #93-#96** (2026-09-26 23:51-23:55 UTC) read off `/feedback.jsonl` after the ship and itemized.

## What Did NOT Work (and why)
- **Reading the continuation brief's "statements drop-down" for note #92:** the note's anchor was the Downloads row; the drop-down has shown no download on Matching since item 141 (`showDownload={active !== "matching"}`). Read the note's `anchor` before designing.
- **`read f r w` with Windows backslash paths in the regress_check loop:** bash `read` ate the backslashes ("no such file"); use `read -r` and relative `--file` paths.
- **Ending a turn while the local suite ran:** it left the ship chain for a later wake-up. Arm a Monitor on the PR verdict and keep the chain in one turn.

## Current Status
- Backend: Fly v265 at 672c7ddf, healthz on the commit.
- Pending paste (owner): `lovable-statement-downloads-off-matching-prompt.md`, `lovable-memory-plan-sentences-prompt.md`, plus the older Not-applied rows in PROMPT-STATUS.
- PR #1488 (record) merges on green.
- Waits on Criss: nothing.

## Next Steps
1. Item 227 (note #94): drop the "Was: …" line (`category.stamped.was`, SPA `GlAccountPicker.tsx` ~223). SPA prompt; check whether the CSV/PDF read the field before touching the backend.
2. Item 228 (note #95): the FX judge's model prose ("The converted amount of 104.00 USD is close to …"). Read which field carries it and whether item 222's structured `review.cause` (prompt `lovable-review-cause-prompt.md`, not pasted) already replaces it.
3. Item 229 (note #96): measurement only. Would a receipt-day FX rate (the charge-day rung is `MatchingConfig.daily_rate`, `matching/deterministic.py:698`) settle more pairs? Labelled bundles plus live months, read-only; the matching program is closed.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 225-229)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

## Continuation prompt

````
/comd_resume brisken

# Feedback notes #94, #95, #96: items 227, 228, 229

## Where it stands
Notes #91 and #92 are answered (2026-09-27):
- **Item 226** (Matching statement download buttons): SPA only. `docs/lovable-statement-downloads-off-matching-prompt.md`, PR #1484. Note #93 (the same ask on September) is covered by it.
- **Item 225** (the memory-save dialog is not tangible): backend live (PR #1487, merge 672c7ddf, Fly v265; record PR #1488). Memory-plan lessons now say what the next receipt gets, name cards by Settings label and person, and a merchant-list card lesson names the receipts it was seen on (`service.registry_card_observations`, shared with the card learner). April reads 18 lessons in sentences with 0 `card-` keys, and the published Publish checklist renders them. The Save dialog still shows the old table until `docs/lovable-memory-plan-sentences-prompt.md` is pasted.

Waits on the owner: pasting those two prompts (plus the older Not-applied rows in PROMPT-STATUS, among them `lovable-review-cause-prompt.md`). Waits on Criss: nothing.

`/feedback.jsonl` held 96 notes at the end of the session; #94-#96 are backlog items 227-229 (end of Open in `workspace/clients/brisken/status/p1-improvement-backlog.md`). Re-read the store first: diff the count against 96.

## The queue, in order
1. **Item 227 (note #94, operator 2026-09-26 23:53 UTC, September Matching `/runs/51a22ad72864`): "remove this "was..." line, no need for that".** Anchor: "Was: IT: Computer and Internet Expenses (suggested)". The line is item 224's `category.stamped.was`, rendered in the SPA's `src/components/GlAccountPicker.tsx` (~line 223, keys `category.stamped.*`; read it with `gh api repos/011matthias/brisken-expense-review/contents/src/components/GlAccountPicker.tsx`). SPA prompt: `docs/lovable-{slug}-prompt.md` + a PROMPT-STATUS Not-applied row. Before touching the backend field, check whether the CSV or the PDFs read `stamped`.
2. **Item 228 (note #95, operator 2026-09-26 23:54 UTC, April Matching `/runs/0603bb0e6f38`): "ai slop remove or improve".** Anchor: "The converted amount of 104.00 USD is close to the transaction amount, but the vendors ar…", which is the FX judge's model-written reason (item 222; judge in `matching/deterministic.py` + `llm/client.py`). Read which field carries it (`review.reason` vs item 222's structured `review.cause` / `cause_detail`) and whether the unpasted `lovable-review-cause-prompt.md` would already replace it. If the structured cause covers every judged pair, stop showing the prose rather than rewriting it.
3. **Item 229 (note #96, operator 2026-09-26 23:55 UTC, April Matching): "look if certainty gets significantly improved if fx rate from date of receipt is used".** Anchor: "12.90 EUR x 1.17064 = 15.10 USD · difference +1.02 USD (+6.75%)". Measurement only; the matching program is closed. The daily rung reads the CHARGE day (`MatchingConfig.daily_rate`, `matching/deterministic.py:698`, nearest day within 4). Measure, read-only, on the labelled bundles and the live months, which pairs' gap and band change on the RECEIPT date, counting right and wrong crossings. Report before proposing.

## How to work
Protocol: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`.
- **Worktree.** Work in your own worktree off origin/main (`git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-item-227 C:\Users\neuma_p1qrsic\Repo\agentic-ops1-item227 origin/main`).
- **Shared files.** Append, never reflow.
- **After a push.** Merge origin/main and expect to renumber a Shipped row (the next free row is 148). Run `gh pr merge` as its own call.
- **CI watch.** Arm a Monitor on a script that reads `mergeable` as well as checks: a CONFLICTING PR never gets checks and sits silent. Keep merge, deploy and live check in the same turn.
- **Deploy.** Only via `deploy.py` from a detached origin/main worktree (`agentic-ops1-deploy` exists). flyctl may not find its token: export `FLY_API_TOKEN` read from `~/.fly/config.yml`.
- **Drive.** Cold, with headless Playwright `channel="chrome"` (PEP 723 `playwright>=1.49`, `uv run --python 3.12`).
  - Log in through the form after networkidle with `EXPENSE_RECON_OPERATOR_CODE` from the main clone's `workspace/clients/brisken/context/.env`.
  - Click the feedback hint dialog's "Got it" before navigating.
  - The month's charges are the "Matching" link (`/runs/{id}`); `/expenses/{id}` is the receipts grid.
  - Abort every non-GET except `/api/login` and cache the two heavy month reads (45 s brake).
  - On an unpublished month, Publish -> "Publish anyway" only opens the checklist.
- **regress_check.** Pass a Windows path to `--directory` inside `--test`, a relative `--file`, and use `read -r` in any loop.

Rules that do not bend:
- No live writes on Criss's months without a per-action AskUserQuestion.
- The matching program is closed.
- Each fix gets a route-level test through the caller and one `regress_check` proof.
- B4 applies.

Suite: `uv run --directory <worktree>/workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q -p no:warnings` (3,986 passed / 2 skipped on 2026-09-27, about 9 min; no xdist).

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
