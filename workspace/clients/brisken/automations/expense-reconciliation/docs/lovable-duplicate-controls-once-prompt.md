# Lovable prompt: one set of duplicate controls per unit, and say which copy is the real expense (item 216)

> **NOT PASTED.** SPA delta on top of item 209 (published 2026-09-25, the
> "Suggested duplicate" units). Answers the owner's notes #89 and #90, left on
> September's Pressmaster pair on 2026-09-25 at 03:45 and 03:47 UTC.
>
> **Backend half ships separately (item 216, no SPA dependency):** a re-match
> now keeps the payment RECEIPT as the real expense and sets its INVOICE aside,
> except where a charge already holds a copy. The page needs no new field for
> that: the main row is still the member with `duplicate.is_extra !== true`.
>
> **Proven before handover:** applied by hand to a scratch clone of the
> Lovable repo at `e1459f5`, `vite build` green, run locally and driven
> headless against one read of each live payload, every write aborted (none
> attempted). Results are in PROMPT-STATUS.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No backend change and no new request.

## Why

The owner, on the Expenses tab of September, on a "Suggested duplicate" unit:

- *"now you have so many buttons on each duplicate that its going to confuse the user."*
- *"compare copies should only appear once, as should the delete this copy/not a copy/compare copies button. the real expense should be big and duplicate should be small so they should effectively switch places and that should also be portrayed evidently to the user."*

Today each unit shows the same three controls twice: once under the vendor of the full row (Compare copies, Delete this copy, Not a copy) and again on the folded copy line (Compare copies, Delete the extra, Not a copy). A September month with 19 units renders 38 of each. Nothing on the page says in plain words which copy counts and which does not; the badges read "1 of 2" and "duplicate · copy 2 of 2".

The swap itself (which copy is the real expense) is the backend's job and is already done: the full row is always the member with `duplicate.is_extra !== true`, so this prompt only changes what the unit shows.

## Scope

Only `src/components/ExpensesReviewGrid.tsx` (the Expenses tab), `src/components/CompareCopies.tsx` (the Compare copies dialog) and `src/lib/i18n.tsx`. Do NOT change the Matching tab (`RunWorkbench.tsx`): its copy lines already show one set of controls each. Do NOT change how units are built, sorted or filtered (item 209).

## 1. The unit's header band carries the ONE set of controls

`BoundGroupHeader` (the amber "Suggested duplicate" band above each unit) gets `runId`, the unit's `copies` and an `onDelete(documentId)` callback (pass the grid's existing `setDeleteDoc`, so deleting still goes through the existing delete confirmation dialog). On the right of the band, in this order:

1. **Compare copies**: the existing `CompareCopiesButton`, `openedFrom` = the main's `document_id`, with the new `onDeleteCopy={onDelete}` prop (section 3) and the footer action "Not a copy" only.
2. **Delete the duplicate** (`expx.dup.deleteDuplicate`): shown only when the unit has exactly one copy (every live unit today). Opens the existing delete confirmation for that copy's `document_id`. Same rose outline style as today's delete buttons.
3. **Not a copy** (`expx.dup.notDuplicate`): the existing `resolveDuplicateGroup(runId, { group_id, action: "ignore" })` mutation, the existing toast and query invalidation.

Keep the band's existing text (label, vendor, date, amount, "2 copies", hint). Let the controls wrap on narrow screens.

## 2. The rows say what they are, and carry no controls

- **Full row (the main):** where `ExpenseRowView` renders `DuplicateCell` for a row that is part of a unit (`bound` is set), render ONE small emerald badge instead: **Real expense** (`expx.dup.role.real`), `title` = `expx.dup.role.realHint`. No buttons, no "1 of 2". Keep `DuplicateCell` for any duplicate row that is not inside a unit (should not occur, keep it as the fallback).
- **Folded copy line (`CompressedCopyRow`):** remove `DuplicateCell` (its badges and its three buttons). In its place ONE small amber badge: **Duplicate, not in the total** (`expx.dup.role.copy`). Keep the date, amount, the file-name link that opens the preview, the state badge and "Not on this card".

The full row stays full size and the copy stays one small line, so the real expense is the big one and the duplicate the small one.

## 3. The Compare copies dialog: role and delete per column

`CompareCopiesButton` and `CompareBody` get an optional `onDeleteCopy?: (documentId: string) => void`.

- In each column header, next to "Copy N of M", a small role chip read from that column's expense row: `duplicate.is_extra === true` -> **Duplicate** (`dup.compare.role.copy`, amber); otherwise, when `duplicate` is set -> **Real expense** (`dup.compare.role.real`, emerald). No chip when the row has no `duplicate`.
- When `onDeleteCopy` is given, under each column header a small rose outline button **Delete this copy** (`dup.compare.deleteThis`): close the dialog, then call `onDeleteCopy(column id)`. This keeps item 188's rule (either copy can be deleted) now that the grid shows only "Delete the duplicate".
- Every other caller (the Matching tab) passes no `onDeleteCopy` and sees no change beyond the role chip.

## 4. Strings (EN, then PT)

```
"expx.dup.role.real": "Real expense",
"expx.dup.role.realHint": "This one counts in the total",
"expx.dup.role.copy": "Duplicate, not in the total",
"expx.dup.deleteDuplicate": "Delete the duplicate",
"dup.compare.role.real": "Real expense",
"dup.compare.role.copy": "Duplicate",
"dup.compare.deleteThis": "Delete this copy",
```

```
"expx.dup.role.real": "Despesa real",
"expx.dup.role.realHint": "Esta entra no total",
"expx.dup.role.copy": "Duplicada, fora do total",
"expx.dup.deleteDuplicate": "Excluir a duplicada",
"dup.compare.role.real": "Despesa real",
"dup.compare.role.copy": "Duplicada",
"dup.compare.deleteThis": "Excluir esta cópia",
```

Leave the old keys (`expx.dup.deleteThis`, `expx.dup.deleteExtra`, `expx.dup.badge.*`) in place; `DuplicateCell` still uses them as the fallback.

## 5. Checks

On September 2026 (`/expenses/51a22ad72864`), which has 19 units:

1. Each unit's band shows exactly one Compare copies, one Delete the duplicate and one Not a copy: 19 of each on the page, not 38.
2. The rows themselves carry no Compare / Delete / Not a copy buttons: 0 "Delete this copy" and 0 "Delete the extra" buttons outside dialogs.
3. 19 "Real expense" badges on full rows and 19 "Duplicate, not in the total" badges on copy lines.
4. On the Pressmaster FZCO unit (2026-09-23, 135.00 USD), Compare copies opens the dialog with "Real expense" on one column and "Duplicate" on the other, a "Delete this copy" button under each column, and "Not a copy" + "Close" in the footer. Close it with Escape.
5. Switch to PT: "Despesa real", "Duplicada, fora do total", "Excluir a duplicada", "Não é cópia", "Comparar cópias". No raw `expx.` or `dup.` key anywhere.
6. The Matching tab is unchanged: its copy lines still read "Presumed copy of the receipt above" with their own controls.
````
