# Lovable prompt - how much of the month is actually in the report (item 68)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

**Read `lovable-render-failed-prompt.md` (item 67) first.** That prompt builds
the per-row chip for a receipt that could not be rendered, and the tile that
counts them. This one is its positive companion and adds no second chip: it is
one line saying how much of the month the report actually carries.

## Background

The Receipt column has two states today: a file was found, or it was not. That
is a question about the disk, answered before anyone knows whether the file
can become a page. Item 67 gave a broken file its own chip. What is still
missing is the whole-month number a reviewer needs before sending the report
to an auditor: of this month's receipts, how many are actually in it.

Those are not the same number. A receipt whose picture lives inside an
uploaded expense-report PDF is previewable in the app and never carried into
the document, and it is not a "failed" file; it simply has no page.

## 1. The new fields

`GET /api/expense-batches/{id}`:

```json
"expenses": [
  { "document_id": "0043__Invoice-H0LHY2WQ-0029.pdf",
    "receipt_image_available": true,
    "source_file": "Invoice-H0LHY2WQ-0029.pdf",
    "receipt_in_report": false }
],
"summary": { "n_receipts": 51, "n_receipts_in_report": 50 }
```

`receipt_in_report` is a boolean and is **absent** (never null) until the
verdict is known. It becomes known for a row the moment the month's expense
report has been built, and for a row with no file at all it is known
immediately (`false`).

`summary.n_receipts_in_report` is an integer and is **absent** whenever any
row is still undecided, so it is never a count that is quietly short.

`receipt_image_available` and `source_file` keep exactly their current meaning
and their current renderer: they answer "can the app show you this file",
which is still the right question for the preview button.

## 2. The one line

Under the receipt counts, when `summary.n_receipts_in_report` is present AND
lower than `summary.n_receipts`, show one line:

> {n_receipts_in_report} of {n_receipts} receipts have a page in the report

Equal numbers: show nothing. Absent: show nothing. This is a quiet line, not
a tile; it only earns space when the two numbers differ.

## 3. The row field is for filtering, not for a second chip

Do **not** add a per-row badge for `receipt_in_report === false`. Item 67's
`expense.notInReport` chip already covers the case a reviewer can act on (a
file that broke). A row that is merely absent from the report without a broken
file needs no alarm on its own line.

Where it is useful: if the grid has a filter bar, add one option that keeps
rows with `receipt_in_report === false`, labelled `grid.filter.notInReport`.
Rows where the key is absent are not matched by that filter, because "we have
not established it" is not "it is missing".

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `grid.receipt.coverage` | {inReport} of {total} receipts have a page in the report | {inReport} de {total} recibos tem pagina no relatorio |
| `grid.filter.notInReport` | Not in the report | Fora do relatorio |

## 5. Do not change

`receipt_image_available`, `source_file`, the preview control, `n_receipts`,
item 67's chip and tile, and every other count keep their meaning.
`receipt_in_report` is additive: a month where no report has been built
carries the key nowhere, and the page renders exactly as it does today.
