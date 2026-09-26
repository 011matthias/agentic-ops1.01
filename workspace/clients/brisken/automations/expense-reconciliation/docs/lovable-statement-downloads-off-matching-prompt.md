# Lovable prompt: the Matching page stops offering statement downloads (item 226, note #92)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. The statement workbook stays downloadable from the Expenses page's
> Statements panel, which this prompt does not touch.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/SummaryBar.tsx`, `src/components/RunWorkbench.tsx` (two props) and `src/lib/i18n.tsx` (two keys removed). No new field and no new request.

## Why

The owner left a note on April 2026's Matching page (`/runs/0603bb0e6f38`), pointing at the Downloads row: "remove these statement download buttons". Today that row reads:

Downloads · Reconciliation (PDF) · Report (Excel) · Reconciled CSV · Statement Chase1176_2026-04_posted_0403-0413_from-SharePoint.xlsx · Statement Chase9693_2026-04_posted_0401-0430_from-SharePoint.xlsx

The two "Statement …" buttons are the ones to remove. They download the month's own statement workbooks with the tool's account column added (`/runs/{id}/statement-categorized.xlsx?file=…`). The same workbooks stay downloadable from the Expenses page (`/expenses/{id}`): its header's "N statements ›" table has a Download button on every workbook row, and a one-statement month shows a Download button beside the statement line. That is the one place left to get them.

## 1. `SummaryBar.tsx`: the Downloads row keeps three buttons

- Delete the `statementFiles` block (the `useMemo`-style IIFE that reads `safeStatements(statements)`).
- In the Downloads row, delete the `statementFiles.map(...)` buttons and the `statementFiles.length === 0 && writebackAvailable` fallback button. The row keeps, in this order and unchanged: "Reconciliation (PDF)", "Report (Excel)", "Reconciled CSV".
- Remove the `statements?: unknown` and `writebackAvailable: boolean` props from `Props` and from the destructuring. Remove the `safeStatements` import if nothing else in the file uses it.

## 2. `RunWorkbench.tsx`: stop passing the two props

In the `<SummaryBar ... />` call, delete `statements={data.statements}` and `writebackAvailable={data.writeback_available}`. Leave every other prop as it is. The later `statements={data.statements}` passed to `StatementLoadedLines` stays.

## 3. `i18n.tsx`: drop the two keys nothing uses any more

Delete `sum.dl.statement` and `sum.dl.statementFile` from both languages (EN "Statement" / "Statement {file}", PT-BR "Extrato" / "Extrato {file}"). Before deleting, search the project for both keys; if anything besides `SummaryBar.tsx` still uses one, keep that key.

## 4. Do not change

- `StatementPanels.tsx` and `MonthHeader.tsx`: the Expenses page's statement line, its "N statements ›" table and their Download buttons stay exactly as they are (`showDownload={active !== "matching"}` already keeps them off the Matching page).
- The three remaining download buttons, their pending spinner and their error toast.
- The action row ("Confirm all matched", "Commit learnings", the published line, "Publish") and everything below the Downloads row.

## Checking it landed

Read labels only; do not click any download.

1. April 2026 Matching (`/runs/0603bb0e6f38`): the Downloads row reads exactly "Reconciliation (PDF)", "Report (Excel)", "Reconciled CSV". No button on the page contains "Statement Chase".
2. July 2026 Matching (`/runs/50622baec444`): the same three buttons; "Statement July2026.xlsx" is gone.
3. April 2026 Expenses (`/expenses/0603bb0e6f38`): open "3 statements ›"; the two Chase workbook rows still show a Download button and the CSV row still says "not an Excel workbook".
4. PT on April Matching: "Conciliação (PDF)", "Relatório (Excel)", "CSV conciliado", and no "Extrato …" button.
````
