# Mini-Checkpoint: Expense-Recon Notes 99-106 Matching Header

**Date:** 2026-09-27
**Status:** Queue empty; one SPA prompt written, not pasted
**Type:** mini

---

## Summary

Feedback notes #99-#106 (all on September's Matching page, all SPA strings) became backlog items 232-235 and one Lovable prompt, `docs/lovable-matching-header-prompt.md`, merged as PR #1511 (`386394a6`). No backend change, no deploy. The feedback store ends at #106, and note #98 was already done by a sibling.

## What Was Done

- Read the eight notes with their anchors from `GET /feedback.jsonl`, then found the owning component for each in the SPA at `1446588`. Six sit in `RunWorkbench.tsx` (header, `StatementLoadedLines`, `StatusLine`) and two in `CardScope.tsx`, which the Expenses page shares.
- #99's "card's 4 ending digits": the PDF upload carries `card_key` "" and `account_id` "", but `coverage[].statements` holds each upload's `file` under its card(s), filled by `service.py` `_statement_card_identities`. So the SPA joins two served fields, and the attribution stays the backend's own. Replaying the join over one live read gave exactly 9693 (Aug 05 to Sep 04, 32), 1176 (Sep 01 to Sep 10, 4) and 9693 (Sep 04 to Sep 14, 15).
- Items: 232 (#102, opening sentences go), 233 (#99 + #103, statements behind "View all statements loaded (N)", digits then period and count, file name in the tooltip), 234 (#100 + #101, blue card box, amber no-statement box with its Add button), 235 (#104-#106, uncovered cards behind an amber button, open amounts in amber boxes with the amount bold). PROMPT-STATUS gained a "Not applied" row.

## What Did NOT Work (and why)

- **Ending the turn with PR #1511 still in CI and promising the merge for later:** `warn-stop-merge-left-pending` flagged the closing message. The merge happened only because the background CI watcher's notification woke the session again. Watch CI in the foreground (`gh pr checks N --watch`) and merge in the same turn.

## Current Status

PR #1511 merged; main has items 232-235 and the prompt. Nothing to deploy. The recon loop's queue is empty and no feedback note is open. Sibling PR #1505 (the months list shows the picked card's own figures) is still open and titled "item 231"; it has to renumber past 235 at its merge. Criss's months were not written to (0 writes; two reads: the notes and one September run).

## Next Steps

1. Owner pastes, SPA only, each with its verify steps in the prompt file and a row in `docs/PROMPT-STATUS.md`: `lovable-matching-header-prompt.md` (232-235), `lovable-quiet-done-tiles-prompt.md` (231), `lovable-was-line-off-prompt.md` (228, reported pasted but not in the bundle; re-paste), `lovable-duplicate-reasons-gate-prompt.md` (223). PROMPT-STATUS records 221, 225, 226 and the copies-kind `mh.rematch.trigger.duplicates_reapply` key as PUBLISHED (bundle audit 2026-09-27), although their backlog headings still read "not pasted". Sibling PR #1505 adds `lovable-months-card-figures-prompt.md` when it merges.
2. Owner decisions: item 223 step 7's reapply per month; item 230 (receipt-day FX, measured).
3. After a paste: crawl the bundle for the new keys, then drive September Matching cold with replayed payloads (`feedback_recon_drive_replay_payloads`), after first running the same drive against the pre-paste app and seeing it fail.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-matching-header-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 232-235
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` "Not applied"
