# Mini-Checkpoint: Expense-Recon Item 76

**Date:** 2026-09-16
**Status:** Item 76 shipped + live (Fly v139); next item is 83 + 75
**Type:** mini

---

## Summary
Item 76 is live: every run row carries `turn` (decide / confirmed / rejected / posted / none) and a verdict names its author, and clean exact pairs (one candidate, category ready, vendor >= 75) confirm themselves after each re-match. With owner approval, July and August were refreshed and the five predicted pairs confirmed, with nothing else moving.

## What Was Done
- Feedback store read: still 51 notes, none new since #51 (16:16 UTC).
- Published prompts for items 73/74/77/80/81 verified. Bundle: 48 chunks, controls hit, 19/20 names; the absent `n_duplicate_groups_open` is never needed by the render rule. Cold drive of July + August (EN, PT on August): every check with a live case passed, 0 writes. The move offer has no live case on any of 6 batches. PR #924.
- Owner rulings (AskUserQuestion), recorded on the items in PR #924: item 76 floor 75; item 84 MISSING ENTITY + NEEDS PERSON become one box; item 88 corrections saved at month sign-off, Memory page as undo.
- Item 76, PR #925 (merge `a299174f`), Fly v139. `rows[].turn`, `decided_by`, `decided_rule`, `summary.n_self_confirmed`; `apply_self_confirmations` after every `rematch_month` commit; `RunStore.set_tool_decision` conditional upsert (never over a person's verdict); `decisions.decided_by` / `decided_rule` migrated in place. Suite 1907 -> 1929 passed / 2 skipped; three regress proofs bite (pass wiring, turn wiring, store guard). SPA half `docs/lovable-turn-prompt.md` (PROMPT-STATUS Pending).
- Live after deploy: turn on all rows, decide == n_undecided (July 3, August 10), 0 posted rows asking. Owner-approved refresh-master-data on both months: July confirmed ELEVENLABS 5.00 + ANTHROPIC 50.54 (undecided 3 -> 1), August LOVABLE 15.00 / 25.00 + ANTHROPIC 51.38 (10 -> 7); no other row moved, 0 master-data changes, 0 new model calls. SPA reads "Blocked · 1 row" / "7 rows to decide".

## Current Status
Items 73/74/77/80/81 verified live. Item 76 shipped; its SPA prompt awaits the owner's paste. Clean non-exact pairs still asking: 2, both August `fx_reference` (CLAUDE SUB 247.32 vendor 52, PETIT TRAIN 37.48 vendor 61). July WEB*NETWORKSOLUTIONS 7.98 (vendor 46, labelled right) still asks by ruling. brisken ops status: platform unknown (no infrastructure assessment); comms-log 8 days stale (not touched this session).

## Next Steps
1. Items 83 + 75, one branch: set-aside copies leave `unmatched_receipts` / `assignable_receipts` / the counts (live now July 2 of 13, August 11 of 21; July dropped from 4 because a reviewer ruled Hostinger 0000/0002 and Redis 0004/0070 "Not a copy" at 16:17 UTC, which the labels call copies: flag this to the owner); a `reason_code` on every unmatched receipt and charge; keep the invariant and the by-index pairing. Grep labels first.
2. Item 84: one per-row box field produced by the summary code; resolve Categorized 49 vs 51 rows and `has_receipt_image` vs `receipt_image_available` first; merge ENTITY + PERSON per ruling.
3. Items 85 + 86 prompt: the underlined-control inventory is already listed (RunWorkbench L179/1357/1655/2207/2362/2619/2630/3185/3283; ExpensesReviewGrid L670/725/789/1108/1374/1510/1691/1699/2171/2969/3002/3304), from the SPA repo read via `gh api`.
4. Item 88 (sign-off auto-save), then 87 (read July's card strip first), then 82 (ECB monthly rates, simulate with the S1 scorer first).
5. Hand the owner the turn prompt; after publish, bundle-audit (`n_self_confirmed`, `row.status.confirmedByTool`, `row.status.posted`) + cold drive.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 75, 83, 84, 85-88; item 76's shipped paragraph)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (the item 76 section, last)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
