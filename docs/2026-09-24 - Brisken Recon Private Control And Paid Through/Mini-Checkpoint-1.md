# Mini-Checkpoint: Brisken Recon Private Control And Paid Through

**Date:** 2026-09-24
**Status:** Item 176 shipped, deployed and verified live. Items 175 and 174 both scoped to one unpasted Lovable prompt. No backend work left in the private-expense area.
**Type:** mini

---

## Summary

`can_mark_private` told every confirmed private row it could still be marked
private; it no longer does, and the route that writes the private flag now
lets an already-private row correct who gets reimbursed. The cold drive that
verified the deploy also found what operator note #75 actually captured: the
doubled "Private (Dirk Neumann)" is the Paid Through cell rendering its value
twice, not the flag.

## What Was Done

- **Item 176 shipped** (PR #1258, merge `43305aea`, deployed to
  `brisken-expense-recon`). `can_mark_private` is `not private and (...)` in
  `resolve_batch_row_cards`; `_paid_by_conflict` skips its company-card
  refusal on a row that is already private. Five route-level tests in
  `tests/test_private_not_reoffered_item_176.py`, both wires regress-checked
  green to red to green. Module suite 3176 passed / 2 skipped.
- **Verified live, read-only.** Both private rows in the estate (September
  0046 Luigi Buchholz, July 0028 Brauhaus Kühler Krug) now read
  `can_mark_private: false`; all 15 `suggested_private` rows across the three
  months still read true, so the flag was narrowed and not flattened.
  September's split moved 28/47 to 27/50 on 77 rows.
- **Cold Chrome drive of September row 0046.** Badge and "Undo private card"
  both still render, which was this change's one real risk. The doubled label
  is two elements in cell index 7: a static
  `div.px-1.text-sm.text-foreground` and the `span` inside the account
  select's `role="combobox"` trigger. One row in 80 doubles, and it is the
  private one.
- **Follow-up shipped** (PR #1260, merge `80dffabb`, docs only).
- **Items 175 and 174 scoped from the published bundle**, both SPA-only, both
  in `docs/lovable-private-reimburse-prompt.md` (not pasted). 175's real half
  is that the `reimburse_to` dialog lives inside the card picker, which
  returns null once the row is private, so there is no way to correct who
  gets reimbursed short of undoing the mark. 174's "From email" is
  `months.origin.intake` on the months list, off `created_by`, rendered in
  the statement badge's cell.

## What Did NOT Work (and why)

- **The item's own diagnosis of 176.** It said the flag "is what renders the
  label the note captured twice". The SPA reads `can_mark_private` in one
  helper whose two callers already escape a private row for other reasons
  (the chip needs `suggested_private`, false there; the picker opens with
  `if (row.private) return null`), so the flip changes nothing on screen.
  Correct fix, wrong stated cause.
- **The first bundle scan, which reported the field absent everywhere.** The
  probe was validated (it found `suggested_private` and `reimburse_to`); the
  corpus was not. Chunk names were harvested with
  `chunk-[A-Za-z0-9_-]*\.js`, which cannot match
  `chunk-expenses._batchId-7cO7KDYP.js` because of the dot, so the one chunk
  holding the grid was never downloaded. A validated probe over an incomplete
  corpus still returns a confident absence.
- **`card_source` as item 174's cause.** That field never produces the string;
  "From email" appears once in the whole bundle, as `months.origin.intake`.

## Current Status

Fly `brisken-expense-recon` serves `43305aea`. September `51a22ad72864` 77
rows, August `074a7b8905d7` 25, July `50622baec444` 54; nothing was written to
Criss's months (the change applies at read time in `build_expense_view`, so no
re-match was needed). brisken platform ops status: unknown plan, last assessed
unknown. comms-log 16 days stale.

## Next Steps

1. Hand the owner `docs/lovable-private-reimburse-prompt.md` (items 175, 174
   and the Paid Through duplicate). Nothing else in this area needs backend
   work.
2. Item 108 needs statements for cards 9693 and 1176; it is an ask, not a fix.
3. Waiting on Criss or the owner: writing card 3645's `zoho_account` (item
   172), and the two August rows where her card pick contradicts the
   confirmed statement charge.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 174,
  175, 176)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-private-reimburse-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`resolve_batch_row_cards`)
