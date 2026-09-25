# Lovable prompt: the duplicates filter shows each group together (item 208)

> **NOT PASTED.** SPA only, no backend change. Follows item 188, whose
> "Show duplicates (N)" button is live since 2026-09-24.
>
> Written against the Lovable repo `011matthias/brisken-expense-review` at
> `1081d57` (2026-09-24 21:00Z), `src/components/ExpensesReviewGrid.tsx`.
> With the filter on, the page still sorts the surviving rows into the three
> review-state tables, so a pair whose copies are in different states sits in
> two tables, and a pair in one table can have other rows between its copies.
> Measured read-only on the live months 2026-09-25: July 10 of 11 pairs are
> not side by side (2 split across tables, 8 with rows between), September
> 3 of 19, August 3 of 5, June 2 of 2. Every live group is a pair and every
> member is an `expenses[]` row.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No backend change and no new request: this uses only fields the Expenses page already loads. With the duplicates filter OFF, the page renders exactly as today.

## Why

The owner: *"a duplicate filter inside each month so the user can see all the expenses that were flagged as duplicated grouped together."*

The "Show duplicates (N)" button already keeps only rows whose `duplicate` is set. But those rows are still sorted into the three review-state tables ("Needs a look", "Assign a category", "Ready"). A pair whose copies are in different states lands in two different tables, e.g. July's Supermercado Fenix 803.11 BRL (2026-07-27): the first copy is under "Ready", the second under "Needs a look". Within one table, other rows can sit between the two copies. The reviewer has to hunt for the partner copy, which is what the filter was supposed to save.

## 1. With the filter on, one block per duplicate group

In `ExpensesReviewGrid`, when `dupFilter` is true, do NOT render the three review-state sections (`GROUP_ORDER.map(...)`). Render one section instead, with the same outer markup as a review-state section (`<section className="overflow-hidden rounded-lg border bg-card">`):

1. **Section header:** the same header strip and `Badge` as a review-state section, in the amber tone of `GROUP_TONE.check`, reading `t("expx.dup.group.section")` + ` · ` + the number of groups shown.
2. **One table**, with exactly the same column header row as the review-state tables (Date, Vendor, Amount, Currency, Tax, Category / Account, Legal entity, Paid through, Receipt, Actions). Moving that `TableHeader` into a small shared component is fine; its columns and widths must not change.
3. **For each group, a group header row:** a `TableRow` with one `TableCell colSpan={10}` on a muted background (`bg-muted/40`, `py-1.5`, `text-xs`). Content, from the group's FIRST copy (lowest `duplicate.copy`): `vendorDisplay(row.vendor)` · `fmtDate(row.date, locale)` · `fmtAmount(row.total, locale)` `row.currency`, then a small outline badge `t("expx.dup.group.copies", { n })` with `n = duplicate.n_copies` (fall back to the number of member rows).
4. **Under it, the group's rows**, sorted by `duplicate.copy` ascending, each rendered with the existing `ExpenseRowView` and the same props the review-state tables pass (`runId`, `row`, `options`, `onPreview`, `onDelete`, `onFilterVendor`). Nothing inside the row changes (the duplicate strip, "Compare copies", "Not a copy", the delete buttons all stay).
5. **Group order:** by the first copy's `date` ascending (ISO string compare), then by vendor display, then by `group_id`. Deterministic, so the list does not reshuffle on refetch.

## 2. The row says its review state

In the grouped view the table no longer tells the reviewer a row's state, so the row has to. Add an optional prop `stateBadge?: boolean` to `ExpenseRowView`. When true, render a small outline `Badge` (`text-[10px]`) with `t(GROUP_TITLE[state])` and the `GROUP_TONE[state]` classes, in the same flex wrapper that holds the `expx.review.manualTag` and `ccy?` badges. `state` is `row.review?.state` when it is `check`, `pick` or `ready`, otherwise `ready` (the same fallback the review-state sections use). Only the grouped view passes `stateBadge`; the normal view is unchanged.

## 3. Which groups show

1. Build the groups from ALL rows in `data.expenses` whose `duplicate` is set, keyed by `duplicate.group_id`.
2. A group shows when at least one of its members passes the other active filters, with the same predicates as today: vendor filter, "not in report", box tile, card scope (`inCardTab(cardTab, row.card_section)`).
3. When a group shows, ALL its members render, including a member those filters would hide. A pair is never shown half.
4. A member outside the selected card (a card is selected and `inCardTab(cardTab, row.card_section)` is false) gets a muted outline badge `t("expx.dup.group.otherCard")` beside its state badge. Pass it as an optional prop `outOfScope?: boolean` on `ExpenseRowView`. This is common: in several live pairs one copy names the card and the other names none.
5. If no group shows, render the same dashed empty box the page uses for `cardScope.emptyExpenses`, reading `t("expx.dup.group.empty")`.
6. The existing empty-state check (`data.expenses.length === 0 || (cardTab !== null && tabRows.length === 0)`) still runs first, unchanged.

## 4. The filter button's count

While the filter is on, `expx.dup.filter.active` ("Showing {n} duplicates") takes `n` = the number of rows the grouped view renders (every member of every shown group). With the filter off, `expx.dup.filter.show` keeps `n = dupRowCount` as today. `shownCount` for the box-filter caption keeps its current computation.

## 5. Do not change

The filter off state, everywhere on the page. The filter stays page-local state (not in the URL) and is still toggled by the same button; "Show all rows" (`expx.dup.filter.clear`) still turns it off. The duplicate strip on each row and everything it posts. The summary tiles and every count in them. The Matching tab. No new request.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.dup.group.section` | Duplicate groups | Grupos de duplicadas |
| `expx.dup.group.copies` | {n} copies | {n} cópias |
| `expx.dup.group.otherCard` | Not on this card | Fora deste cartão |
| `expx.dup.group.empty` | No duplicates match the filters in use | Nenhuma duplicada corresponde aos filtros em uso |

## Checking it landed

Read only. Do not click "Delete this copy", "Delete the extra" or "Not a copy".

1. September, Expenses tab: click "Show duplicates (38)". One section, "Duplicate groups · 19"; 19 group header rows, each followed by its two rows, the "1 of 2" row directly above "duplicate · copy 2 of 2". The "Needs a look" / "Assign a category" / "Ready" sections are gone while the filter is on. The button reads "Showing 38 duplicates".
2. September, Lovable Labs Incorporated 50.00 USD 2026-09-05: both copies under one header, the first badged "Needs a look", the second "Assign a category".
3. July: "Duplicate groups · 11". Supermercado Fenix 803.11 BRL 2026-07-27 shows both copies together, badged "Ready" and "Needs a look".
4. On `/months` select card 2838, open July, turn the filter on: Aposto Karlsruhe 80.00 EUR 2026-07-13 shows both copies, the no-card copy badged "Not on this card".
5. "Show all rows": the three review-state sections come back exactly as before, with no state badges on the rows.
6. Portuguese: "Grupos de duplicadas", "2 cópias", "Precisa olhar".
````
