# Mini-Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Step 1 live; its SPA prompt written and handed over (not pasted); steps 2-4 with a fresh session
**Type:** mini

---

## Summary
Two Lovable prompts went to the owner as pasteable text: the new `model_picked_parent` refusal sentence (EN + PT), and item 218's bills-path prompt, which the previous closing had only named by path. The step-4 suggestion-label prompt waits for step 2's payload fields.

## What Was Done
- Read the SPA source (shallow clone of `011matthias/brisken-expense-review`, HEAD `ad43cef`). Refusal sentences come from `gl.refusal.<code>` in `src/lib/i18n.tsx` (EN and PT). `ExpensesReviewGrid.tsx` and `refusalText` in `GlAccountPicker.tsx` fall back to the backend's English `reason`. So the prompt adds one key and touches no component.
- Wrote `docs/lovable-model-picked-parent-prompt.md` (PT uses "conta sintética", the Brazilian chart-of-accounts term for a summary account) and a Not-applied row in `PROMPT-STATUS.md`. PR #1449 merged.
- Pasted the bills-path prompt body in the reply; the SPA source has no `payment_path`, so it is not pasted.
- `PROMPT-STATUS.md` is behind the Lovable repo. Five prompts it lists as not pasted have their decisive field names in the repo source at `ad43cef`: `account_check`, `default_keep`, `expx.cardFix.source.account`, `waits_for_statement_many`, `private_card_options`. That is repo source, not the published bundle, so the table was not changed. `month_filter` (attach-month filter) and `row.fills` (statement colour) are absent from the source.

## What Did NOT Work (and why)
- **Naming a Lovable prompt by its file path in a closing reply:** the stop hook flagged it (`warn-hand-prompt-as-text`); the owner then had to ask for the prompt. Paste the body in a four-backtick fence labelled "paste into Lovable".
- **`gh search code` on the SPA repo:** returned nothing for strings the source holds (the private repo is not indexed); a shallow clone and grep found them.

## Current Status
Step 1 live on Fly `2820e33c`; its SPA prompt and the bills-path prompt wait on the owner's paste. brisken ops: platform unknown plan; comms-log none.

## Next Steps
1. Owner: paste and publish the two prompts, then run a bundle audit (`tools/lovable-bundle-audit.py`) for `gl.refusal.model_picked_parent` and `payment_path`.
2. Fresh session: item 216 Build 2 steps 2-4 (continuation prompt in Mini-Checkpoint-1's session reply; the owner's labelled-suggestion ruling is in backlog item 216).
3. Re-audit `PROMPT-STATUS.md` against the published bundle: five rows marked not pasted look applied in the repo source.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-model-picked-parent-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied)
- `docs/2026-09-25 - Brisken Recon Item 216 Build 2/Mini-Checkpoint-1.md`
