# Lovable prompt: one download button per output file on the Matching page (item 141, note #68)

> **NOT YET APPLIED.** SPA only, no backend change. Every route used here is
> live: `reconciliation-report.pdf`, `report.xlsx`, `reconciled.csv` and
> `statement-categorized.xlsx?file=` under `/runs/{id}/`.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/SummaryBar.tsx`, `src/components/RunWorkbench.tsx` (one prop), `src/components/MonthHeader.tsx` and `src/components/StatementPanels.tsx`. No new field and no new request. Render defensively: `statements` may be absent, empty, or carry entries without `file` or `writeback`.

## Why

The owner asked for exactly one button per output file on the month's Matching page. Today July's Matching page (`/runs/50622baec444`) has five download buttons for four files, in three places:

| Where today | Label | File |
|---|---|---|
| `MonthHeader`, next to "112 charges · Statement July2026.xlsx (...)" (`StatementSummary` > `DownloadStatement`) | Download | `statement-categorized.xlsx?file=July2026.xlsx` |
| `SummaryBar` action row, primary button | Download reconciliation (PDF) | `reconciliation-report.pdf` |
| `SummaryBar` "Downloads" row (`DownloadBtn`) | Report | `report.xlsx` |
| same row | Reconciled CSV | `reconciled.csv` |
| same row, when `writeback_available` | Statement | `statement-categorized.xlsx` (no `file`) |

The annotated statement workbook is offered twice, and the PDF sits apart from the other files. August (`/runs/074a7b8905d7`) shows the opposite gap: it has two statements (`August2026.xlsx` and a PDF statement), `writeback_available` is false, so the Downloads row has no Statement button and the workbook download is only inside the collapsed "2 statements ›" table in the header.

After this change the Downloads row is the only place on the Matching page that downloads anything, with one button per file.

## 1. The Downloads row holds every file (`SummaryBar.tsx`)

- Remove the primary "Download reconciliation (PDF)" button and its `pdfPending` state from the action row. The row keeps "Confirm all matched", "Commit learnings", the published-by line and "Publish" exactly as they are.
- Add a prop `statements?: unknown`. In `RunWorkbench.tsx`, pass `statements={data.statements}` to `<SummaryBar ... />`.
- `DownloadBtn` gets its own pending state: while the download runs it is `disabled` and shows `Loader2` (`mr-1.5 h-3 w-3 animate-spin`) in place of the `Download` icon. Errors still go to `toast.error`.
- After the "Downloads" label, render in this order:
  1. `label={t("sum.dl.pdf")}`, `path={`/runs/${runId}/reconciliation-report.pdf`}`, `fallback={`reconciliation-report-${runId}.pdf`}`
  2. `label={t("sum.dl.report")}`, `path={`/runs/${runId}/report.xlsx`}`, `fallback={`report-${runId}.xlsx`}`
  3. `label={t("sum.dl.reconciled")}`, `path={`/runs/${runId}/reconciled.csv`}`, `fallback={`reconciled-${runId}.csv`}`
  4. One button per statement workbook: take `safeStatements(statements)` (from `@/lib/api`) filtered to entries with `writeback === true` and a non-empty `file`, deduplicated by `file`. For each: `label={t("sum.dl.statementFile", { file: s.upload_name || s.file })}`, `path={`/runs/${runId}/statement-categorized.xlsx?file=${encodeURIComponent(s.file)}`}`, `fallback={s.file}`.
  5. Only when step 4 produced no button and `writebackAvailable` is true: today's single `t("sum.dl.statement")` button with the path without `file`.

## 2. The header stops offering downloads on the Matching page

- `StatementPanels.tsx`: `StatementSummary` and `StatementsPanel` take `showDownload?: boolean` (default `true`). `StatementSummary` passes it on to `StatementsPanel`.
  - In the one-line branch of `StatementSummary`, render `<DownloadStatement ... />` only when `showDownload` is true.
  - In the last column of `StatementsPanel`: when `showDownload` is true, render as today. When false, render nothing for a row with `writeback === true`, and keep the `stm.notExcel` note for the others.
- `MonthHeader.tsx`: `<StatementSummary runId={runId} statements={statements} showDownload={active !== "matching"} />`.

The Expenses page keeps its header download, because its own buttons ("Download report (PDF)", "Download CSV (data export)") are different files and it has no Downloads row.

## 3. Do not change

- The Expenses page: its header, "Download report (PDF)" (`expense-report.pdf`) and "Download CSV (data export)" (`expenses.csv`).
- The statement line's text, the "2 statements ›" toggle and the table's other columns and advisories.
- "Statement loaded: ..." under the page subtitle, the Publish dialog, the status line and every row.
- `sum.dl.statement` and `stm.download` stay in the dictionary (both are still used).

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `sum.dl.pdf` | Reconciliation (PDF) | Conciliação (PDF) |
| `sum.dl.report` (change) | Report (Excel) | Relatório (Excel) |
| `sum.dl.statementFile` | Statement {file} | Extrato {file} |

`sum.pdf` is no longer used; delete it from both languages. `sum.downloads` ("Downloads" / "Downloads") and `sum.dl.reconciled` ("Reconciled CSV" / "CSV conciliado") stay as they are.

## Checking it landed

Do not click any download: read the labels only.

1. July 2026 Matching (`/runs/50622baec444`): the header line reads "112 charges · Statement July2026.xlsx (Jun 30, 2026 – Jul 31, 2026)" with no button after it. The action row reads "Confirm all matched", "Commit learnings", "Publish", with no download. The Downloads row reads exactly "Reconciliation (PDF)", "Report (Excel)", "Reconciled CSV", "Statement July2026.xlsx": four buttons for four files, where there were five.
2. August 2026 Matching (`/runs/074a7b8905d7`): the Downloads row reads "Reconciliation (PDF)", "Report (Excel)", "Reconciled CSV", "Statement August2026.xlsx". Opening "2 statements ›" shows the table with no Download button; the PDF statement's row still says "not an Excel workbook".
3. July and August Expenses (`/expenses/50622baec444`, `/expenses/074a7b8905d7`): unchanged. July's header line still has its "Download" button; both pages still show "Download report (PDF)" and "Download CSV (data export)".
4. PT on July Matching: "Conciliação (PDF)", "Relatório (Excel)", "CSV conciliado", "Extrato July2026.xlsx".
5. Bundle: `sum.dl.pdf` and `sum.dl.statementFile` in `chunk-runs._runId`; `sum.pdf` absent from every chunk.
````
