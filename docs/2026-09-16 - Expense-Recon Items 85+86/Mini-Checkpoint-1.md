# Mini-Checkpoint: Expense-Recon Items 85+86

**Date:** 2026-09-16
**Status:** Items 85 + 86 prompt written (PR #938), pending the owner's paste; item 88 next
**Type:** mini

---

## Summary
One SPA-only prompt turns the month pages' text-looking controls into outline small buttons, makes each fold toggle name what it shows, and makes the booked fold name the statement file with the yellow / grey rule. No backend change.

## What Was Done
- The inventory was read from the SPA repo at head `dcd875a7` and anchored by i18n key, because the brief's line numbers had already drifted by 3 to 14. It covers 10 controls in `RunWorkbench.tsx` and 10 in `ExpensesReviewGrid.tsx`. Two listed entries are not in it: `wb.credits.tip` is a card's `title` attribute, and the NEEDS PERSON Settings link belongs to the item-84 boxes prompt.
- Fold toggles: "Show 48 booked rows" (July, Charges without a receipt: 72 charges, 24 open), "Show 5 groups" (duplicates panel). The booked fold reads "{n} rows marked yellow in {file}, already booked" from `statements[].file` (`July2026.xlsx`, `August2026.xlsx`).
- Every new i18n key across the three pending prompts (`wb.reason.*`, `expx.box.*`, `wb.decided.showBooked`, ...) is checked absent from the published dictionary, so the bundle-audit names are unique.

## Current Status
Three SPA prompts pending the owner's paste, in PROMPT-STATUS Not applied: `lovable-unmatched-reasons-prompt.md` (83 + 75), `lovable-expense-boxes-prompt.md` (84), `lovable-controls-as-buttons-prompt.md` (85 + 86). Backend live at Fly v141.

## Next Steps
1. Item 88: find what "month sign-off" is in code, then save the month's corrections to memory there automatically (Memory page = undo).
2. Item 87: read July's card-review strip first.
3. Item 82: simulate ECB monthly rates with the S1 scorer before building.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-controls-as-buttons-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 87, 88, 82)
