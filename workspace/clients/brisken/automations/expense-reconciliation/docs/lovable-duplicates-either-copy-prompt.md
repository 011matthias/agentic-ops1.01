# Lovable prompt: delete a duplicate from either copy, and a filter that says it is one (item 188)

> **NOT PASTED.** SPA only. The backend already does the right thing when the
> FIRST copy is deleted, pinned 2026-09-24 by two tests in
> `tests/test_duplicate_rows.py`: the other copy becomes an ordinary row with
> no marker that counts in `n_expenses` and `totals_by_ccy`, and on a month
> with a statement the re-match the delete triggers hands the charge to it.
>
> Written against the published bundle of 2026-09-24
> (`assets/chunk-expenses._batchId-BZt6ewgZ.js`). The duplicates filter this
> prompt surfaces is already in that bundle: clicking the amber
> "{n} copies set aside" text keeps only rows whose `duplicate` is set. It just
> does not look like a filter.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No backend change and no new request: both changes use fields and calls the Expenses page already has. Render defensively; a row without `duplicate` renders exactly as today.

## Why

The owner, on a pair of duplicate rows: *"Duplicate should be able to be deleted from original and copy. also there should be a filter to see all the duplicates."*

Today only the row with `duplicate.is_extra === true` gets the red "Delete the extra" button. The first copy has none, so a reviewer who wants to keep the second copy (the cleaner scan, the one with the right file name) has no way to do it. "First" is only the order the group lists its members, not a judgement about which copy is better.

The page already filters to duplicate rows when the amber "{n} copies set aside" text is clicked. Nothing tells the reviewer that it is a filter, so for them it does not exist.

## 1. Every copy can be deleted

In the duplicate strip under each row (the component that renders the `expx.dup.badge.original` / `expx.dup.badge.extra` badge, "Compare copies" and "Not a copy"):

1. Render the delete button on EVERY row whose `duplicate` is set, not only when `duplicate.is_extra` is true.
2. Label: on an extra copy keep `expx.dup.deleteExtra` ("Delete the extra"). On the first copy use the new key `expx.dup.deleteThis` ("Delete this copy"). Same red outline style on both.
3. Both call the same delete handler the extra's button calls today (`DELETE /api/runs/{runId}/expenses/{documentId}`), with the same confirmation, if any, and the same refetch afterwards. Do not add a second code path.
4. The same rule applies inside the "Compare copies" dialog: its actions for a copy offer the delete button whether that copy is first or extra, with the same two labels.

After the first copy is deleted the backend returns the other copy as an ordinary row with `duplicate: null`, counted in the total. The refetch shows that; nothing on the client has to promote it.

## 2. The duplicates filter looks like a filter

The page keeps a boolean that, when on, keeps only rows where `row.duplicate` is set. Today it is toggled by the amber banner button whose label is `expx.dup.count` / `expx.dup.count_one` ("{n} copies set aside"), and `expx.dup.filter.clear` ("Show all rows") appears while it is on. Keep that state and that predicate; change how it is offered:

1. **When it shows.** Show the banner whenever at least one row in `expenses` has `duplicate` set. Today it is gated on `summary.n_duplicate_copies > 0`, which is the same population in practice; count rows, so the number the button shows is always backed by rows the filter will show.
2. **The button.** Its label becomes `expx.dup.filter.show` with `{n}` = the number of rows whose `duplicate` is set (both copies of each pair count, because the filter shows both). Give it a leading filter icon (the same lucide `Filter` icon family the page already imports, or `ListFilter`) so it reads as a control.
3. **Beside it**, as plain muted text, keep the existing set-aside sentence (`expx.dup.count` / `expx.dup.count_one`, from `summary.n_duplicate_copies`), so the "how many are left out of the total" fact is still on screen.
4. **While the filter is on**, the button renders in its active (pressed) state and its label becomes `expx.dup.filter.active` with `{n}` = rows currently shown. `expx.dup.filter.clear` ("Show all rows") stays exactly as today.
5. The filter still combines with the other filters as it does now (vendor, card, box tiles, not-in-report).

## 3. Do not change

"Not a copy" and what it posts. The badges, their text and colours. "Compare copies" apart from the delete button in section 1. The "not in total" chip. The totals tile and its copies-set-aside line. Every count in the summary tiles.

## New and changed strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.dup.deleteThis` (new) | Delete this copy | Excluir esta cópia |
| `expx.dup.filter.show` (new) | Show duplicates ({n}) | Mostrar duplicadas ({n}) |
| `expx.dup.filter.active` (new) | Showing {n} duplicates | Mostrando {n} duplicadas |

`expx.dup.deleteExtra`, `expx.dup.count`, `expx.dup.count_one` and `expx.dup.filter.clear` keep their text.

## Checking it landed

Do not delete anything: open the page and read it only.

1. A month with a duplicate pair (September has Fireflies.ai Corp, 2026-09-15, twice): the row badged "1 of 2" shows a red "Delete this copy" button, and the row badged "duplicate · copy 2 of 2" still shows "Delete the extra".
2. "Compare copies" on either row: the dialog offers a delete button for that copy.
3. Above the list: a "Show duplicates (N)" button with a filter icon, next to the muted "N copies set aside" text. Clicking it leaves only rows that carry a duplicate badge, the button reads "Showing N duplicates", and "Show all rows" brings the full list back.
4. Portuguese: "Excluir esta cópia", "Mostrar duplicadas (N)".
5. Bundle: `expx.dup.deleteThis`, `expx.dup.filter.show` and `expx.dup.filter.active` present in the i18n chunk; `expx.dup.deleteExtra` and `expx.dup.filter.clear` still present.
````
