# Lovable prompt: a suggested duplicate stays bound together until someone releases it (item 209)

> **NOT PASTED.** SPA only, no backend change. Replaces this file's first
> draft (the grouped duplicates filter, never pasted): the owner widened the
> ask the same day to "all suggested duplicates should live bound together
> inside the tool until released by a user's click (delete / not a copy)",
> asked for the copies to be compressed under their main, and extended it to
> the Matching tab. Design approved on screenshots of the real July data,
> 2026-09-25.
>
> **Backend already does both matching rules**, read live 2026-09-25: a
> presumed copy is never matched, offered as a candidate or pickable by hand
> (0 of 35 copies across July, August and September), and every receipt of a
> group ruled "Not a copy" is back in matching with no marker (all 6 from
> July's three released groups). After either release click the backend
> returns the rows without `duplicate`, so the binding needs no client state:
> it holds exactly as long as the marker does.
>
> **Proven before handover:** applied by hand to a scratch clone of the
> Lovable repo, `vite build` green, run locally against the live API and
> driven headless with every write aborted. Results are in PROMPT-STATUS.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No backend change and no new request: everything here uses fields both month pages already load.

## Why

The owner: *"all suggested duplicates should live bound together inside the tool until released by a user's click (delete / not a copy)"*, *"feel free to compress the copies under it, as they can be viewed with the compare button either way"*, and for the Matching tab: *"the duplicate pair stay bound together until a user separates them, even if in matching."*

Today the copies of one purchase are scattered: on the Expenses tab they sit in different review-state tables or with other rows between them, and on the Matching tab the presumed copy sits in a folded "copies set aside" list, away from the receipt it copies.

## Words used below

- **Suggested duplicate:** every row whose `duplicate` is set. Its members share `duplicate.group_id`.
- **Main:** the member with `duplicate.is_extra !== true` (copy 1). **Presumed copy:** a member with `duplicate.is_extra === true`.
- **Release:** after "Delete this copy" / "Delete the extra" or "Not a copy", the backend returns the rows without `duplicate`. The binding reads only that field, so a released pair comes apart on the refetch with no extra client code, and a pair nobody released stays bound.

## Part A. Expenses tab (`ExpensesReviewGrid`)

### A1. A bound unit

Every suggested duplicate renders as one unit, in this order, inside the table it belongs to:

1. **Binding strip** (`BoundGroupHeader`): one `TableRow` with a single `TableCell colSpan={10}`, `border-t-2 border-t-amber-400/60 bg-amber-500/10`, the cell `border-l-4 border-l-amber-400 py-1.5 text-xs`. Content in one wrapping flex line: lucide `Link2` icon (amber), `t("expx.dup.bound.label")` in amber medium weight, the main's `vendorDisplay(vendor)` in medium weight, then muted ` · {main.date} · {fmtAmount(main.total, locale)} {main.currency}` (print `date` as the Date column does, the ISO day; do NOT use `fmtDate`, which formats timestamps and prints a time such as "02:00 AM"), a small outline badge `t("expx.dup.group.copies", { n })` with `n = duplicate.n_copies` (fall back to the member count), and `t("expx.dup.bound.hint")` in muted italic `text-[11px]` right after the badge (not pushed to the far right: the table is wider than the screen and it would be off-screen).
2. **The main**, rendered with the existing `ExpenseRowView`, unchanged except for two new optional props: `stateBadge` (a small outline badge `t(GROUP_TITLE[state])` with the `GROUP_TONE[state]` classes, `text-[10px]`, placed in the same flex wrapper as the `expx.review.manualTag` and `ccy?` badges) and `bound` (the row gets `bg-amber-500/[0.04] hover:bg-amber-500/[0.07]`, its first cell `border-l-4 border-l-amber-400`; when it is the unit's last row also `border-b-2 border-b-amber-400/60`). `state` is `row.review?.state` when it is `check`, `pick` or `ready`, otherwise `ready`.
3. **Each presumed copy, folded to one line** (`CompressedCopyRow`), in `duplicate.copy` order: one `TableRow` (`id="exp-row-{document_id}"` so the existing jump-to-row still lands on it) with a single `TableCell colSpan={10}`, same amber tint as the main, the cell `border-l-4 border-l-amber-400 py-1 pl-8 text-xs`, muted text, `border-b-2 border-b-amber-400/60` on the unit's last row. Content in one wrapping flex line: lucide `CornerDownRight` icon, the copy's `date`, `fmtAmount(total)` + `currency`, its `receipt_name` as a truncated (`max-w-[18rem]`) button that opens the existing receipt preview (`onPreview`), its state badge (as in A1.2), the "Not on this card" badge when A4 applies, then the existing `DuplicateCell` unchanged (badge "duplicate · copy 2 of 2", "not in total", "Compare copies", "Delete the extra", "Not a copy"). Everything else about the copy is one click away in "Compare copies".

### A2. Where a unit sits (filter off)

Build the sections from `data.expenses` in payload order. A row without `duplicate` goes to its own state section as today. A suggested duplicate is placed once, when its first member is reached: the whole unit goes to the section of its MOST URGENT member (`check` before `pick` before `ready`), so nothing that needs a look is hidden under Ready. Each section's badge counts the rows it renders (a unit counts all its members), so the three badges still add up to every row of the month.

### A3. The "Show duplicates" filter

When the filter is on, do not render the three state sections. Render one section, same outer markup, its badge `t("expx.dup.group.section") · {units shown}` in the `GROUP_TONE.check` tone, holding the same units as A1, ordered by the main's `date` (ISO string compare), then vendor, then `group_id`. The filter button reads `expx.dup.filter.active` with `n` = the rows rendered. If no unit shows, render the page's dashed empty box with `t("expx.dup.group.empty")`. "Show all rows" (`expx.dup.filter.clear`) turns it off as today.

### A4. Other filters and the card scope

A unit shows when AT LEAST ONE member passes the other active filters (vendor, "not in report", box tile, card scope via `inCardTab(cardTab, row.card_section)`), and then ALL its members render: a pair is never shown half. A member outside the selected card gets a muted outline badge `t("expx.dup.group.otherCard")` (pass `outOfScope` to `ExpenseRowView` / `CompressedCopyRow`). This is common: in many live pairs one copy names the card and the other names none.

## Part B. Matching tab (`RunWorkbench`)

### B1. Copies by main

`copiesByMain`: a map from main id to its presumed copies, built from `data.copies_set_aside` keyed by `duplicate.of`, each list sorted by `duplicate.copy`.

### B2. Which row hosts a main

A main can show on the Matching tab in three places. Host each main exactly once:

1. The charge that HOLDS it: the first row whose `chosen_document_id` is the main.
2. Otherwise the charge that PROPOSES it: the first row whose `chosen_document_id ?? candidates[0].document_id` is the main (a "Needs review" row).
3. Otherwise, if the main is in `unmatched_receipts`, its own row in "Receipts without a charge".

(Live July: 7 mains held by a matched charge, 2 proposed by a Needs-review charge, 2 in Receipts without a charge.)

### B3. The copy line under its main

Directly under the hosting row, render one line per presumed copy: in `chargeTable` (open AND decided tables) after the host `RowView`, wrapping `RowView` and its lines in a keyed `Fragment`, `colSpan={9}`; in `receiptTable` for the `"open"` kind after the main's row, `colSpan={5}`, and give that main row `border-t-2 border-t-amber-400/60 bg-amber-500/[0.04]` with its first cell `border-l-4 border-l-amber-400` so the pair reads as one unit. The line: same amber tint, rail and closing bottom border as A1.3, content in one wrapping flex line: `CornerDownRight` icon, `t("wb.bound.copyOf")` in amber medium weight, the copy's date (`formatDate`), `formatAmount(total, currency)`, the existing `ViewReceiptButton` for the copy, `t("wb.bound.outOfMatching")` in italic, the existing `CompareCopiesButton` with `dupGroupActions(group_id)`, a red outline "Delete the extra" (`expx.dup.deleteExtra`) and a "Not a copy" (`wb.dups.notCopy`) that calls the existing `duplicates` mutation with `resolution: "ignore"`.

For "Delete the extra", export `DeleteExpenseDialog` from `ExpensesReviewGrid` and mount one instance in `RunWorkbench` driven by a `deleteCopy` state; it already calls `DELETE /api/runs/{runId}/expenses/{documentId}`, asks for confirmation and refetches. Do not add a second delete path.

### B4. The set-aside list

The folded "copies set aside" list in "Receipts without a charge" keeps only copies whose main is hosted NOWHERE by B2 (live July: none). A copy is never listed on its own while its main is on the page.

## Part C. Do not change

What any button posts. The Duplicates panel at the bottom of Matching. The summary tiles and every count in them. The "Compare copies" dialog. With no duplicate in a month, both pages render exactly as today.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.dup.bound.label` | Suggested duplicate | Duplicata sugerida |
| `expx.dup.bound.hint` | Kept together until you delete a copy or click Not a copy | Ficam juntas até você excluir uma cópia ou clicar em Não é cópia |
| `expx.dup.group.section` | Duplicate groups | Grupos de duplicadas |
| `expx.dup.group.copies` | {n} copies | {n} cópias |
| `expx.dup.group.otherCard` | Not on this card | Fora deste cartão |
| `expx.dup.group.empty` | No duplicates match the filters in use | Nenhuma duplicada corresponde aos filtros em uso |
| `wb.bound.copyOf` | Presumed copy of the receipt above | Cópia presumida do recibo acima |
| `wb.bound.outOfMatching` | kept out of matching until you release it | fora da conciliação até você liberar |

## Checking it landed

Read only. Do not click "Delete this copy", "Delete the extra" or "Not a copy" on a real month. Counts below were read 2026-09-25 and move as Criss works; the rules in brackets are what must always hold.

1. July, Expenses: 11 "Suggested duplicate" strips, each followed by a full main row and one folded copy line. [Every copy sits under its main; no "duplicate · copy" row appears outside a unit; the three section badges add up to every row of the month.] Supermercado Fenix 803.11 BRL (2026-07-27) sits whole under "Needs a look" (its copy needs a look, its main is Ready).
2. July, "Show duplicates": one section "Duplicate groups · 11", the same units, nothing else.
3. July, Expenses with card 2838 selected on `/months`: Aposto Karlsruhe 80.00 EUR shows its no-card copy folded under the main, marked "Not on this card".
4. July, Matching: 7 copy lines under charges in "Matched", 2 under charges in "Needs review", 2 under receipts in "Receipts without a charge", and none left alone in the set-aside list. [A copy line always sits directly under the row showing its main.]
5. Portuguese: "Duplicata sugerida", "Cópia presumida do recibo acima".
````
