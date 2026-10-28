# Checkpoint: Brisken Recon Confirm Button Under Account

**Date:** 2026-10-07
**Status:** Lovable prompt written and handed over; not yet pasted

---

## Summary

Dirk asked for the "Confirm {account}" button under the vendor name on the
Expenses grid to replace the amber "Suggested" line under the Category /
Account picker. The Lovable prompt for that is written against the live SPA
source, handed to the owner as a fence, and filed in the recon prompt ledger.

---

## What Was Done This Session

### Lovable prompt (SPA only)
1. Located the two pieces in SPA `011matthias/brisken-expense-review`
   `origin/main` `0ac4b07`: `KeepCategoryButton` (vendor cell) and
   `SuggestionLine` (under the account `Select`), both in
   `src/components/ExpensesReviewGrid.tsx`.
2. Read the backend (`web/service.py` `_row_categories`,
   `category_confirmable`) to confirm a posted category and a suggestion can
   coexist on one row (mixed lines), which is why the prompt keeps
   `SuggestionLine` as a fallback in two cases.
3. Handed the prompt as a four-backtick fence labelled "Paste into Lovable".
4. Filed it as `lovable-confirm-under-account-prompt.md` with a Not-applied
   row in `PROMPT-STATUS.md` (PR #1578), after the stop-time rule flagged the
   missing file.

### System
1. New prompt-time pattern rule `warn-lovable-prompt-file-first`: fires when
   the owner asks for a Lovable prompt, before the prompt is written.

---

## Key Decisions Made

### Italic reason line stays under the vendor name
- **Choice:** only the button moves; "The model suggested this account..."
  stays in the vendor cell.
- **Rationale:** Dirk asked about the button only, and with the "Suggested"
  badge gone that line is the one remaining cue that the account is a model
  guess.

### Suggested line kept as a fallback
- **Choice:** show `SuggestionLine` when there is a suggestion but no button
  (`category_confirmable` false), and under a "Keep" button on mixed rows.
- **Rationale:** deleting it outright would hide a suggestion on any row the
  backend does not mark confirmable.

---

## What Did NOT Work (and why)

- **Handing the prompt as text only:** the recon Lovable prompts have a
  tracked home and ledger (`expense-reconciliation/docs/lovable-*-prompt.md` +
  `PROMPT-STATUS.md`); handing a fence without filing it left no record of
  what was asked for. `warn-owner-publish-without-named-prompt` caught it one
  turn late, the third time this has happened (2026-09-24, 09-28, 10-07).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-confirm-under-account-prompt.md` | Created (PR #1578) | The prompt, as handed |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` | Edited (PR #1578) | Not-applied row |
| `.claude/patterns/warn-lovable-prompt-file-first.md` | Created | Prompt-time primer |

---

## Current Status

Prompt not yet seen pasted. No backend gate. brisken platform: unknown plan
(no `platform` section in `infrastructure.yaml`).

---

## Next Steps

1. After the owner publishes: verify by structure on a replayed month payload
   (writes aborted), per the prompt file's "Verify after publish", then move
   the PROMPT-STATUS row to Applied.
2. Stale status files flagged by `pre` and not touched this session:
   `p1-recon-loop-prompt.md` (22d), `p2-lead-gen-general.md` (22d),
   `p2-lovable-rebuild.md` (27d), `p2-rome.md` (22d).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-confirm-under-account-prompt.md`

### Open Questions
- None.

### Working Notes
- `KeepCategoryButton` has two variants: `Keep "{category}"` when a posted
  category exists, `Confirm {account}` when only a suggestion exists; it
  renders nothing unless `row.category_confirmable === true`.
- The card workbench (`RunWorkbench.tsx` `PostingCategoryCell`) has no
  confirm button, so the change is Expenses-grid only.

### Reference Materials
- SPA repo `011matthias/brisken-expense-review` (local clone
  `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-responsive\.scratch\spa`)

---

## How to Continue

Wait for the owner's publish, then run the structural verify and update the
ledger row.

---

## Strategic Feedback

### What Worked Well This Session
- Naming components from the live SPA `origin/main` and reading the backend
  payload rules before writing turned a one-line request into a prompt with
  its edge cases (mixed rows, non-confirmable suggestions) already handled.

### Suggestions
- The recon prompt ledger convention depends on recall; the new prompt-time
  rule moves the reminder to before the prompt is written. If it misses
  again, make the stop rule a block instead of a warn.

### System Health
- Autonomy: 0 human interventions (the miss was caught by a hook, not the
  user).
