# Lovable prompt: copies set aside leave the month's totals (item 94)

Paste into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`).

The app calls the FastAPI backend at `https://api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth is the existing `Authorization: Bearer <token>`.

## What changed in the backend

An invoice and its receipt for one purchase used to count twice. The tool
already decides the second document is a copy (the duplicate badge, "copy 2
of 2"), and now the backend leaves that copy out of the month's expense count
and its totals. The SPA renders those numbers as sent, so the Expenses tile,
the Totals tile and the months list correct themselves with no change. What
is new is saying what was left out, so nobody reads the lower total as money
gone missing.

New fields, all parallel (absent on an older backend, which means "nothing
set aside"):

| Payload | Field | Shape |
|---|---|---|
| `GET /api/expense-batches/{id}` | `summary.n_copies_set_aside` | int |
| same | `summary.copies_set_aside_by_ccy` | `{ "USD": "263.59", "EUR": "32.00" }`, formatted, `{}` when none |
| same | `expenses[].counts_in_total` | `false` on a copy set aside, ABSENT on every other row |
| `GET /api/expense-batches` | `batches[].summary.n_copies_set_aside` | int |
| `GET /api/cost-centers/totals` | `copies_set_aside` | `{ n_rows, n_batches, totals }`, same shape as `unassigned` |

`summary.n_receipts` keeps counting every row, so on the grid
`n_receipts == n_expenses + n_copies_set_aside`.

## 1. Types (`src/lib/api.ts`)

- `ExpenseBatchSummary`: add `n_copies_set_aside?: number` and
  `copies_set_aside_by_ccy?: Record<string, string>`.
- `ExpenseRow`: add `counts_in_total?: boolean`.
- `CostCenterTotalsResponse`: add `copies_set_aside?: CostCenterTotalsRow`.

Read defensively: `const nCopies = Number(summary?.n_copies_set_aside ?? 0) || 0;`
and treat `copies_set_aside_by_ccy` as empty unless it is a plain object whose
values are strings. A row is set aside only when `row.counts_in_total === false`
(strict; absent means it counts).

## 2. Review expenses grid (`src/components/ExpensesReviewGrid.tsx`)

**Totals tile.** Inside the Totals `Tile` value, below the currency chips and
beside the existing `n_amounts_unreadable` line, when `nCopies > 0` add one
muted line (same classes as the unreadable line):

`expx.copies.totalsLine.one` / `.many` with `{count}` and `{amounts}`, where
`{amounts}` is the entries of `copies_set_aside_by_ccy`, sorted by currency,
each `CCY amount`, joined with ` · `. Omit the colon part when the object is
empty.

**Expenses tile.** Pass `sub={t("expx.copies.tileSub", { count: nCopies })}`
when `nCopies > 0`, so "20" reads with "5 set aside as copies" under it and the
grid's 25 rows are explained.

**The row.** On a row with `counts_in_total === false`, render a small muted
badge next to the existing duplicate badge in `DuplicateCell`:
`expx.copies.rowBadge`, title `expx.copies.rowBadge.help`. Keep the row, its
duplicate badge and the "Not a copy" button exactly as they are: that
button is the undo, and after it the row counts again.

## 3. Spend by cost center (`src/components/CostCentersScreen.tsx`)

Under the table, beside the existing `cc.totals.undated` line, when
`(data?.copies_set_aside?.n_rows ?? 0) > 0` add one muted line:
`cc.totals.copiesSetAside` with `{count}` (`n_rows`), `{months}`
(`n_batches`) and `{amounts}` (its `totals`, formatted as above). No new table
row: copies are not a cost center.

## 4. Months list

No change. `summary.n_expenses` in the Receipts column now leaves copies out,
and the batch page tile shows the same number.

## i18n keys (`src/lib/i18n.tsx`, both dictionaries)

| Key | EN | PT |
|---|---|---|
| `expx.copies.totalsLine.one` | 1 copy set aside, not in this total: {amounts} | 1 cópia separada, fora deste total: {amounts} |
| `expx.copies.totalsLine.many` | {count} copies set aside, not in this total: {amounts} | {count} cópias separadas, fora deste total: {amounts} |
| `expx.copies.tileSub` | {count} set aside as copies | {count} separadas como cópias |
| `expx.copies.rowBadge` | not in total | fora do total |
| `expx.copies.rowBadge.help` | The tool decided this document repeats another expense, so it is left out of the count and the totals. "Not a copy" counts it again. | A ferramenta concluiu que este documento repete outra despesa, por isso fica fora da contagem e dos totais. "Não é cópia" volta a contá-lo. |
| `cc.totals.copiesSetAside` | {count} copies set aside across {months} months are not counted: {amounts} | {count} cópias separadas em {months} meses não são contadas: {amounts} |

The quoted button label in `rowBadge.help` is `expx.dup.notDuplicate` ("Not a
copy" / "Não é cópia"); keep them in step if that label changes.

## Do not

- No em-dashes in UI copy.
- Do not recompute totals or counts in the browser, and do not hide copy rows.
- Do not add a table row for copies on the cost-center screen.

## Verify after publish

Only after the backend round is deployed (the fields are absent before it).

1. The published bundle contains `n_copies_set_aside`,
   `copies_set_aside_by_ccy`, `counts_in_total` and `copies_set_aside`.
2. August 2026 (`/expenses/074a7b8905d7`), as of the 2026-09-17 read: the
   Expenses tile shows 20 with "5 set aside as copies"; Totals shows EUR 668.00
   and USD 2,033.86 with "5 copies set aside, not in this total: EUR 32.00 ·
   USD 263.59"; the five copy rows (Obsidian 96.00, Lovable 15.00, Anthropic
   100.00 and 52.59, Petit Train 32.00 EUR) carry "not in total". Same page in
   PT.
3. July 2026 (`/expenses/50622baec444`): 50 expenses, 2 copies set aside (EUR
   80.00 · USD 200.00).
4. `/cost-centers`: "17 copies set aside across 4 months are not counted: EUR
   112.00 · USD 1,425.01".
5. The months list shows 20 for August and 50 for July.
