# Lovable prompt: say what a statement upload left out of the month (backlog item 215)

**NOT APPLIED.** Paste into `brisken-expense-review`. The backend half is
live (see `docs/api-contract.md`, "A statement attach keeps only the month's
own charges").

## Why

Criss uploads her lifetime card sheets from SharePoint into a month (the 9693
sheet holds 724 rows since 2024). The app now keeps only that month's charges
and records how many it left out, but the page never says so: the attach
dialog closes on success, and the loaded-statement line counts only the kept
rows. She should see, on the line for that file, that 700 rows were left out
because they belong to other months, and how many were already in a
neighbouring month.

Every change below goes into BOTH dictionaries in `src/lib/i18n.tsx` (EN and
the pt-BR mirror further down). The PT strings are final copy; use them
verbatim.

## 1. The field

Each entry of a month's `statements[]` may now carry:

```ts
month_filter?: {
  month: string;            // "2026-04", the month the file was added to
  n_file_rows: number;      // rows the file printed
  n_kept: number;           // rows the month kept (equals the entry's n_rows)
  n_left_out: number;
  outside_month: Record<string, number>;  // "YYYY-MM" -> rows that belong to that month
  already_held: Record<string, number>;   // "YYYY-MM" -> rows that month already holds
};
```

Add it to the `StatementUpload` type in `src/lib/api.ts` as optional. It is
ABSENT on every entry uploaded before 2026-09-25, on a file that prints no
post date (a Chase cycle PDF), and on months whose name is not a month;
render nothing then. Treat a missing or malformed map as `{}`.

## 2. The loaded-statement line (`StatementLoadedLines`, `RunWorkbench.tsx`)

Under a file's existing "Statement loaded: ..." line, when
`month_filter.n_left_out > 0`, add ONE more quiet line in the same style
(`text-xs text-muted-foreground`, indented slightly under its file). Build it
from parts; show only the parts that are non-zero:

- lead: `wb.statement.leftOut` EN "Left out {n} of the file's {total} rows:" /
  PT "Ficaram de fora {n} das {total} linhas do arquivo:"
  (`n` = `n_left_out`, `total` = `n_file_rows`)
- other months, when `outside_month` has keys:
  `wb.statement.leftOut.otherMonths` EN "{n} belong to other months ({from} to {to})" /
  PT "{n} são de outros meses ({from} a {to})"
  where `n` is the sum of the map's values and `from` / `to` are the first
  and last keys (sorted) as "Month YYYY" in the page language. With a single
  month use `wb.statement.leftOut.otherMonth` EN "{n} belong to {month}" /
  PT "{n} são de {month}". Ignore a key `"undated"` for the span.
- already held, one part per key of `already_held`:
  `wb.statement.leftOut.alreadyIn` EN "{n} are already in {month}" /
  PT "{n} já estão em {month}"

Join the parts with "; " and end with ".". Example, EN:
"Left out 721 of the file's 724 rows: 700 belong to other months (February
2024 to August 2026); 21 are already in May 2026."

## 3. The attach dialog (`AttachStatementDialog.tsx`)

On `done`, when `s.result?.month_filter?.n_left_out > 0`, show a success
toast before navigating, built with the same keys as section 2 but led by
`months.attach.kept` EN "Kept {kept} of {total} charges for {month}." /
PT "Mantidas {kept} de {total} cobranças para {month}." followed by the
parts. The toast must survive the navigation (the app's `sonner` toaster sits
above the router).

On `error`, when `s.result?.code === "statement_outside_month"`, show
`months.attach.outsideMonth` EN "None of the {total} charges in this file
belong to {month}." / PT "Nenhuma das {total} cobranças deste arquivo é de
{month}." followed by the section-2 parts (other months; already in), in
place of the raw English `s.error`. Any other error keeps today's text.

## 4. Do not

- Do not change the "{n} charges" count on the loaded line: `n_rows` is
  already the kept count.
- Do not show anything for an entry without `month_filter` or with
  `n_left_out` 0.
- No new request: everything is on the payload the page already loads and on
  the job poll it already makes.

## 5. Checks after publishing

| Where | Expect |
|---|---|
| A month whose statements carry no `month_filter` (every live month today) | No new line anywhere; the loaded lines read exactly as before |
| A `TEST -` month given a multi-month file | Under that file's line: "Left out N of the file's M rows: ..." with the months and counts from its `month_filter` |
| The attach of that file | Toast "Kept K of M charges for {month}. ..." after the dialog closes |
| A file with no row in the month | The dialog's error reads the translated "None of the ... belong to {month}." line |
| PT | The same three, in the PT strings above, month names in Portuguese |
