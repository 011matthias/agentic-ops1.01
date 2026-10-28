# Lovable prompt: a booked row names its statement workbook and the colour rule (item 142, note #69)

> **NOT YET APPLIED.** SPA copy only, no backend change. Reads
> `statements[].file`, `statements[].account_id`, `statements[].writeback` and
> `rows[].account_id` on `GET /api/runs/{id}`, all live. Same wording as item
> 86's fold tooltip (`lovable-controls-as-buttons-prompt.md`, applied).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/RunWorkbench.tsx` and `src/components/RowStatusBadge.tsx`, plus strings in `src/lib/i18n.tsx`. No new field. Render defensively: `statements` may be absent or empty, and an entry may lack `account_id` or `writeback`.

## Why

A charge Criss colours yellow in the month's statement workbook is already booked; the colour is read when the statement is loaded. The booked fold already says so ("48 rows marked yellow in July2026.xlsx, already booked", with a tooltip for the colour rule). The rows under it do not: hovering a row's "Already booked" badge says "This charge is marked yellow in your statement workbook, so it is already booked. Nothing to decide here.", and the line under the vendor says "Marked yellow in your statement workbook, so already booked." The owner asked, on that row: "where do you get this information from?"

The fold also names too much when a month has more than one statement: August's reads "1 row marked yellow in August2026.xlsx, 20260804-statements-1176-.pdf, already booked", but only an Excel workbook carries colours.

## 1. One helper for the workbook's name

Add near `asArray` in `RunWorkbench.tsx`:

```ts
function bookedWorkbooks(statements: unknown, accountIds: (string | null | undefined)[]): string {
  const books = asArray<{ file?: string; account_id?: string | null; writeback?: boolean }>(statements)
    .filter((s) => typeof s.file === "string" && s.file !== "" && s.writeback !== false);
  const ids = new Set(accountIds.filter((a): a is string => typeof a === "string" && a !== ""));
  const own = books.filter((s) => !!s.account_id && ids.has(s.account_id));
  return [...new Set((own.length ? own : books).map((s) => s.file as string))].join(", ");
}
```

An empty string means "no file to name"; every caller below falls back to the wording without a file.

## 2. The fold uses it

In the fold label (the `foldBooked` branch that builds `files` today), replace the `files` expression with `bookedWorkbooks(data.statements, shownDecided.map((r) => r.account_id))`. Keys, tooltip and layout stay as they are.

## 3. The badge tooltip names the file

- `RowStatusBadge` takes an optional prop `bookedFile?: string`. When the resolved key is `posted`, the tooltip is `t("row.status.posted.tipFile", { file: bookedFile })` when `bookedFile` is non-empty, else `t("row.status.posted.tip")`. Every other key keeps `row.status.{key}.tip`.
- `RowView` takes an optional prop `bookedFile?: string` and passes it to `<RowStatusBadge ... bookedFile={bookedFile} />`.
- Where `<RowView ... />` is rendered, pass `bookedFile={bookedWorkbooks(data.statements, [row.account_id])}`.

## 4. The line under the vendor names the file

In `RowView`, where the charge reason line renders `t(`wb.reason.charge.${row.reason_code}`)`: when `row.reason_code === "already_booked"` and `bookedFile` is non-empty, render `t("wb.reason.charge.already_booked.file", { file: bookedFile })` instead. Same element, same classes. The other three reasons are unchanged.

## 5. Do not change

The badge label "Already booked", its colour, the fold's toggle button, the "{n} already booked" breakdown in the section caption, `wb.decided.foldBooked.tip`, and which rows are booked.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `row.status.posted.tipFile` | This charge is marked yellow in {file}, the statement spreadsheet uploaded for this month, so it is already booked. The colours are read when the statement is loaded. Nothing to decide here. | Esta transação está marcada em amarelo em {file}, o extrato enviado para este mês, por isso já está lançada. As cores são lidas quando o extrato é carregado. Nada a decidir aqui. |
| `row.status.posted.tip` (change) | This charge is marked yellow in the statement spreadsheet uploaded for this month, so it is already booked. The colours are read when the statement is loaded. Nothing to decide here. | Esta transação está marcada em amarelo no extrato enviado para este mês, por isso já está lançada. As cores são lidas quando o extrato é carregado. Nada a decidir aqui. |
| `wb.reason.charge.already_booked.file` | Marked yellow in {file}, so already booked. | Marcada em amarelo em {file}, portanto já lançada. |
| `wb.reason.charge.already_booked` (change) | Marked yellow in the statement workbook, so already booked. | Marcada em amarelo na planilha do extrato, portanto já lançada. |

## Checking it landed

1. July 2026 Matching (`/runs/50622baec444`), "Charges without a receipt", press "Show 48 booked rows": the fold still reads "48 rows marked yellow in July2026.xlsx, already booked". The ANTHROPIC* CLAUDE SUB row of Jul 28, 2026 (205.56 USD) reads "Marked yellow in July2026.xlsx, so already booked." under the vendor, and hovering its "Already booked" badge reads "This charge is marked yellow in July2026.xlsx, the statement spreadsheet uploaded for this month, so it is already booked. The colours are read when the statement is loaded. Nothing to decide here."
2. Same view: 47 rows carry the reason line with "July2026.xlsx", and no row anywhere on July's page says "your statement workbook".
3. July, "Matched": a booked row's badge tooltip names July2026.xlsx the same way.
4. August 2026 Matching (`/runs/074a7b8905d7`), "Credits on the statement", press "Show 1 booked row": the fold reads "1 row marked yellow in August2026.xlsx, already booked" (the PDF statement is no longer named), and the Payment Thank You-Mobile row of Aug 04, 2026 (-7,823.16 USD) names August2026.xlsx in its badge tooltip.
5. PT on July: the reason line reads "Marcada em amarelo em July2026.xlsx, portanto já lançada." and the tooltip "Esta transação está marcada em amarelo em July2026.xlsx, o extrato enviado para este mês, por isso já está lançada. As cores são lidas quando o extrato é carregado. Nada a decidir aqui."
6. Bundle: `row.status.posted.tipFile` and `wb.reason.charge.already_booked.file` in `chunk-runs._runId`; "your statement workbook" absent from `chunk-i18n`.
````
