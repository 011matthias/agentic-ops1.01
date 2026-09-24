# Checkpoint: Recon Paid Through Asks For The Card Twice

**Date:** 2026-09-24
**Status:** Diagnosis done; SPA prompt handed to owner, not yet pasted

---

## Summary
Owner asked why an Expenses row seems to ask for the paying card twice. It does not: the card pick in the company column already resolves Paid Through, and the Paid Through dropdown is a leftover manual override that looks like a second required field when no card is set. A Lovable prompt that hides or collapses that override was written against the live bundle and handed over in the reply.

---

## What Was Done This Session
### Diagnosis
1. Traced the two controls. The card pick (item 87) sets card, entity, person and `posting_paid_through` through one chain (`docs/api-contract.md` ~4071). The Paid Through select (`expx.review.paid.useAuto`) predates card-driven resolution (checkpoint 2026-07-28) and survives as an override that outranks the card and does not re-match (backlog ~6363-6365, Criss's row 0004).
2. Read the live cell source: function `Ct` in `assets/chunk-expenses._batchId-BZt6ewgZ.js`. It always renders the select, and on `source === "unassigned"` it adds an amber placeholder and a "needs a card" badge next to it.

### Prompt status
3. Checked `lovable-private-reimburse-prompt.md` (items 175/174) on the live bundle: **already pasted.** `expx.reimburse.edit` and `expx.private.editTitle` are present, and "From email" is replaced by "Receipts by email". `docs/PROMPT-STATUS.md` line 372 still says "not pasted", so that row is out of date.
4. Wrote a new Paid Through prompt (in the reply only, not saved to disk) with three states: no card → no select, badge `expx.review.paid.pickCardFirst`; resolved → select behind an "Override account" button; override set → as today. Guard: when `row.card` is non-null, the row always stays state 2.

### System
5. Added the pattern rule `warn-hand-rolled-spa-bundle-crawl`, which points a curl of expenses.brisken.com at `tools/lovable-bundle-audit.py`. Tested: it matches the SPA crawl and does not fire on `api.expenses.brisken.com`.

---

## Key Decisions Made
### Fix is SPA-only, override kept
- **Choice:** Hide the override select while there is no card and nothing to override; collapse it otherwise. Do not remove it.
- **Rationale:** Criss uses the override on real rows (August 0004). The confusion comes from where the control sits, not from the capability, and no backend field is missing.

---

## What Did NOT Work (and why)
- **Hand-rolled bundle crawl, round 1:** reported 0 hits for the control keys `expx.reimburse.undo` and `expx.privateCard.mark`, so the instrument was blind. The index-page asset grep went through `grep` on binary output ("Binary file matches"), and only 1 entry asset was followed. A transitive crawl of 45 files fixed it. `tools/lovable-bundle-audit.py` already does this and was not used.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/patterns/warn-hand-rolled-spa-bundle-crawl.md` | created | Point hand-rolled SPA crawls at the audit tool |
| this checkpoint + ledger rows | created | Session continuity |

---

## Current Status
Paid Through prompt is with the owner, not pasted. Item-175 prompt is live, but PROMPT-STATUS.md says otherwise. brisken ops: unknown plan, not assessed (`infrastructure.yaml` has no platform section for this FastAPI app).

---

## Next Steps
1. After the owner pastes the Paid Through prompt: `uv run tools/lovable-bundle-audit.py` with `NEW` = `expx.review.paid.pickCardFirst`, then a browser drive of one no-card row (consumer gate).
2. On a `client/brisken/...` branch: flip PROMPT-STATUS.md row 372 to applied (evidence in step 3 above) and save the Paid Through prompt as `docs/lovable-paid-through-follows-card-prompt.md` with its own status row.
3. File it as a backlog item in `p1-improvement-backlog.md` (owner's question 2026-09-24).
4. Stale status files: `p2-product-decks.md` (63d), `p2-targeting.md` (64d). Update or delete.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (row 372)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (~6363, items 175/176)

### Open Questions
- Should the "needs a card" badge also move to the company column, next to the picker, rather than only changing its text?

### Working Notes
Cell states key off `posting_paid_through.source` (`card` | `override` | `default` | `unassigned` | `private`), plus `row.paid_through` (the override) and `row.card`. The select's reset sentinel is `__auto__`.

### Reference Materials
- Live bundle: `https://expenses.brisken.com/assets/chunk-expenses._batchId-BZt6ewgZ.js`

---

## How to Continue
Wait for the owner to paste the prompt, then run next steps 1 and 2 together.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live component source before writing the prompt. That surfaced the `row.card != null` guard, and without it the prompt would have left known-card rows with no way to set an account.

### Suggestions
- Before hand-rolling a probe, grep `tools/INDEX.md` for the surface ("bundle", "SPA"). The tool existed, and a same-day register row already described this failure.

### System Health
- Autonomy: 0 human interventions beyond the owner's three prompts. The blind probe was caught by the controls, not by the user.
