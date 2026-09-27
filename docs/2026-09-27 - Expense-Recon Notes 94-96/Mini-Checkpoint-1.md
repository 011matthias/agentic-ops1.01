# Mini-Checkpoint: Expense-Recon Notes 94-96

**Date:** 2026-09-27
**Status:** Loop done: items 228-230 answered, queue empty
**Type:** mini

---

## Summary
Feedback notes #94-#96 became items 228-230. Item 229 (model prose) is live on Fly v269, item 228 is a Lovable prompt waiting on the owner, and item 230 was measured and left for an owner decision. No continuation prompt: every open note is claimed.

## What Was Done
- **Item 229 (note #95, "ai slop remove or improve"), PR #1497, merge `87bc8b77`, Fly v269.**
  - Where the sentence came from: the published review-cause prompt renders `cause_detail.model_reasoning`, which the backend cut at read time from the tail of `candidates[].reason` (`_fx_reason` appends the model's words). It was also wrong: April's SUPERMEC SAO JOSE row said 104.00 USD against the tool's 109.83 (-2.48%).
  - The fix: `matching/judgment.py` `without_model_prose` keeps the verdict, p and the tool's own conversion. It is applied to the run view, the Reconciled CSV and the Excel notes. `model_reasoning` is gone, the stored reasons and the CLI `--explain` sheet keep the text, and no SPA paste is needed.
  - Tests: route-level `tests/test_model_prose_item_229.py` (4). `regress_check` goes red on the served reason, the CSV and the Excel notes. Suite 4,042 passed, 2 skipped.
  - Live: 26 judged reasons short (April 14, July 9, August 2, June 1), 0 `model_reasoning`, `model_doubts` counts unchanged (April 12, August 2). A cold Playwright drive of April Matching FAILED before the deploy (12 cause lines, sentence present) and PASSED after it (12 lines, no sentence), with 0 writes.
- **Item 228 (note #94):** `docs/lovable-was-line-off-prompt.md`, SPA only. `StampedLine` renders in `RunWorkbench.tsx` and `ExpensesReviewGrid.tsx`. No backend reader of `stamped` exists. Today the line is on 19 September, 25 July and 51 August Matching rows.
- **Item 230 (note #96), measured and not built.** Full numbers are in the backlog under item 230.
  - The receipt day adds nothing: labelled bundles score 72 right / 0 wrong on either day, and 102 of 111 live FX pairs share the date.
  - The day's rate itself gives +2 right / 0 wrong over the shipped rungs, but the table starts on 2026-07-22 (OpenTickers history, differential probe).
- **PROMPT-STATUS:** the bundle crawl found 14 Not-applied prompts published. A sibling marked the same rows in #1494 during the same hour; I kept theirs and added the item 228 row and a note on the review-cause row.
- Memories updated: `reference_brisken_opentickers_fx_api.md` (history start, `first_day` vs `backfilled_from`) and `feedback_recon_drive_replay_payloads.md` (Matching opens on "Receipts without a charge"; a drive must FAIL before the change).

## What Did NOT Work (and why)
- **First probe of April Matching straight after load:** read 0 cause lines and "sentence absent" on the pre-deploy app. The review rows only render after the "Needs review N" tile is clicked. Caught because the drive was run before the deploy and a blind FAIL-less result was not accepted.
- **Stripping the Excel explain sheet too:** `regress_check` TEST DOES NOT BITE. That sheet is CLI `--explain` only and no route reaches it, so the change was reverted.
- **Receipt-day FX rate as the certainty lever:** no gain (see item 230).

## Current Status
Item 229 is live on v269. Item 228 waits on a paste. Item 230 waits on an owner decision. Note #97 is item 231 in sibling PR #1503, item 227 is in sibling PR #1500, and note #98 is done by a sibling. The feedback store held 98 notes at 20:30 UTC. Two ledger races this session: #1494 (PROMPT-STATUS) and #1495 (Shipped row 152; mine renumbered to 153).

## Next Steps
1. Owner pastes: `lovable-was-line-off-prompt.md` (228), `lovable-attach-month-filter-prompt.md` (215), `lovable-statement-colour-prompt.md` (162), and the `mh.rematch.trigger.duplicates_reapply` key of `lovable-copies-kind-prompt.md`.
2. Owner decision (230): fill the daily FX table before 2026-07-22 from the ECB SDMX daily series. Recommended: yes. It gave +2 right and 0 wrong on the labelled bundles and moves 11 of April's 12 review pairs into the 2% band (those are unlabelled).
3. The next session re-reads `/feedback.jsonl` first and diffs it against 98.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 228-230, Shipped row 153)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied)
