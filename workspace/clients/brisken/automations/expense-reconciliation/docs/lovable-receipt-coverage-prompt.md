# Lovable prompt - the Receipt column's third state (item 68)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

The Receipt column has two states today: a file was found, or it was not. That
is a question about the disk, and it gets answered before anyone knows whether
the file can be turned into a page. A password-protected PDF, a truncated
image, or a receipt whose picture lives inside an uploaded expense-report PDF
all show as "attached" on the grid and then do not appear in the month's
report at all; the caption page in the report says "this file could not be
rendered into the report", and nothing on the screen ever did. So the number
of expenses with usable proof could read higher than it was.

The backend now answers the second question separately.

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
verdict is known. It becomes known for a row the moment either report has been
built, and for a row with no file at all it is known immediately (`false`).
Replacing a receipt's file returns that row to absent.

`summary.n_receipts_in_report` is an integer and is **absent** whenever any
row is still undecided, so it is never a count that is quietly short.

`receipt_image_available` and `source_file` keep exactly their current meaning
and their current renderer: they answer "can the app show you this file", which
is still the right question for the preview button.

## 2. The render rule

Three states, in this order:

1. `receipt_in_report === false` -> **"No page in report"**, in the same
   warning tone the grid already uses for a row that needs attention. Keep
   the preview control if `receipt_image_available` is true: the file is
   still there to look at, it just did not make it into the document.
2. `receipt_image_available` is true -> "attached", exactly as today.
3. otherwise -> "none", exactly as today.

`receipt_in_report === true` adds nothing on screen: "attached" already says
it. Do not add a second badge for the normal case.

A row where the key is **absent** renders exactly as it does today. That is
the common state before a report has been built, and it must not read as a
problem.

## 3. The count

Under the receipt counts, when `summary.n_receipts_in_report` is present AND
lower than `summary.n_receipts`, show one line:

> {n_receipts_in_report} of {n_receipts} receipts have a page in the report

Equal numbers: show nothing. Absent: show nothing. This is a quiet line, not
a tile; it only earns space when the two numbers differ.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `grid.receipt.noPage` | No page in report | Sem pagina no relatorio |
| `grid.receipt.noPage.hint` | The file is here, but it could not be rendered into the report | O ficheiro esta aqui, mas nao pode ser incluido no relatorio |
| `grid.receipt.coverage` | {inReport} of {total} receipts have a page in the report | {inReport} de {total} recibos tem pagina no relatorio |

## 5. Do not change

`receipt_image_available`, `source_file`, the preview control, `n_receipts`,
and every other count keep their meaning. `receipt_in_report` is additive: a
month where nothing has been built yet carries the key nowhere, and the page
renders exactly as it does today.
