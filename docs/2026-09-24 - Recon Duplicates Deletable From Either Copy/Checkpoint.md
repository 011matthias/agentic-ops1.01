# Checkpoint: Recon Duplicates Deletable From Either Copy

**Date:** 2026-09-24
**Status:** Items 188 + 189 live and driven (EN + PT); nothing pending in this thread

---

## Summary
The owner asked for two things: a duplicate should be deletable from either copy, and there should be a filter for duplicates. Both turned out to be SPA-only. The backend already handled deleting the first copy correctly, and now has tests pinning that. The filter already existed but did not look like a control. Two Lovable prompts (188 duplicates, 189 Paid Through) were pasted by the owner, then audited and driven cold on September.

---

## What Was Done This Session
### Backend (PR #1284)
1. Two tests in `tests/test_duplicate_rows.py`. Deleting the FIRST copy leaves the other as an ordinary row (`duplicate: null`, counted, USD 135.00). On a statement month, the re-match triggered by the delete hands the released charge to the surviving copy (`n_receipts_matched` 1, `n_unmatched_tx` 0, `copies_set_aside` empty). Both passed on existing code: no product change was needed.
2. Backlog items 188 (duplicates) and 189 (the Paid Through override reads as a second card question), with prompts `docs/lovable-duplicates-either-copy-prompt.md` and `docs/lovable-paid-through-follows-card-prompt.md`.
3. PROMPT-STATUS: the item-175 prompt moved to Applied on bundle evidence.

### Verification (PR #1285)
4. `tools/lovable-bundle-audit.py`, run from a scratch copy with the four new keys: all 5 controls and all 4 keys present.
5. Cold Playwright drive of September `/expenses/51a22ad72864`, login read from `.env` (never printed), one click (the filter). Results: 19 pairs = 38 badged rows; "Delete this copy" 19 and "Delete the extra" 19; "Show duplicates (38)", which after the click reads "Showing 38 duplicates"; "Pick the card that paid first" on 27 rows, matching the "No company or person 27" tile; `(paid-through - assign)` 0 times. PT gave identical counts.

---

## Key Decisions Made
### Delete from either copy is SPA-only
- **Choice:** No backend change; pin the existing behaviour with tests.
- **Rationale:** Duplicate groups are rebuilt from the effective (post-delete) receipts, so a group of one dissolves. Tested, not assumed.

### Surface the existing filter instead of building one
- **Choice:** Re-present the bundle's hidden `row.duplicate` filter (the amber "{n} copies set aside" text) as a "Show duplicates (N)" button with a filter icon.
- **Rationale:** The predicate and the clear control were already live; only the affordance was missing.

---

## What Did NOT Work (and why)
- **Python triple-quoted edit inside a bash heredoc:** blocked by heredoc-size-gate. The Edit tool was the right path, and the same block is in the 2026-09-23 checkpoint.
- **Drive round 1:** the filter click timed out. The feedback widget's first-visit hint dialog (`aria-labelledby=fb-hint-title`) intercepts pointer events. Dismissing it with Escape first fixed it.
- **First draft of the statement-month test:** used `summary.n_matched`, which does not exist. The run view has `n_receipts_matched` / `n_unmatched_tx`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/tests/test_duplicate_rows.py` | edit | Pin deleting the first copy (#1284) |
| `.../expense-reconciliation/docs/lovable-duplicates-either-copy-prompt.md` | create | Item 188 prompt |
| `.../expense-reconciliation/docs/lovable-paid-through-follows-card-prompt.md` | create | Item 189 prompt |
| `.../expense-reconciliation/docs/PROMPT-STATUS.md` | edit | 175, 188, 189 to Applied (#1284, #1285) |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | Items 188, 189 |

---

## Current Status
Items 188 and 189 are live in both languages. September still has 19 copies set aside (USD 1,882.21 kept out of its total), which is Criss's to clean with the new buttons. brisken ops: unknown plan, not assessed.

---

## Next Steps
1. When Criss uses "Delete this copy" on a first copy, read the month back: the survivor should count, and it should hold the charge once a statement exists.
2. Stale status files `p2-product-decks.md` (63d) and `p2-targeting.md` (64d): update or delete.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Applied rows for 188/189)

### Open Questions
- None open.

### Working Notes
Drive helper pattern: `.env` `EXPENSE_RECON_OPERATOR_CODE` read inside the script, Escape to clear the fb-hint overlay, `localStorage brisken.lang=pt` for PT, and a vendor string on the page as the language-independent control.

### Reference Materials
- PRs #1280, #1284, #1285

---

## How to Continue
Nothing is pending in this thread; pick up from the backlog.

---

## Strategic Feedback

### What Worked Well This Session
- Testing the "delete the original" behaviour before writing any fix. It showed that the whole request was SPA work, and that the filter existed already, which halved the prompt.

### Suggestions
- `warn-hand-prompt-as-text` fires on the NEXT prompt, after the user has already read a path instead of a prompt. As a Stop-event rule it would catch this before the message is sent.

### System Health
- Autonomy: 0 corrective interventions (the owner's prompts were directives plus "done"). Two same-day recall misses were caught by gates, not by recall.
