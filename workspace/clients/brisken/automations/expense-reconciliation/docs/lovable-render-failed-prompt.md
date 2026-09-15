# Lovable prompt - "not in report" on an expense whose receipt would not open (item 67)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A stored receipt can be perfectly present and still produce no page in the
month report: a password-protected PDF, or one whose page tree is damaged. The
report used to die on the first such file, so the whole month produced nothing
at all. It now renders everything else and prints a caption naming the file and
the reason. That caption is inside a PDF, which is the last place a reviewer
looks, so the grid has to say it too: the fix is to re-upload or unlock that
one file, and nobody can act on what only the document knows.

## 1. The new fields

`GET /api/expense-batches/{id}` (and `GET /api/runs/{id}` for a batch with no
statement attached):

`expenses[].receipt_render`, parallel and **absent** until a report has been
built for this month:

```json
"receipt_render": "failed"
```

Two values. `"ok"` = the receipt's pages are in the report. `"failed"` = the
file could not be turned into pages; the report has a caption naming it and
nothing behind it. An expense with no receipt document carries no key.

`summary.n_receipts_unrenderable` (integer) is how many of the month's
receipts produced no page. It follows the same rule: **absent** until a report
was built, present (possibly 0) afterwards.

Absence is a real state here, not a zero. Nothing knows whether a file opens
until a report is assembled, so `undefined` means "not established yet" and
must never render as "fine".

## 2. The row chip

On the expense row, beside the Receipt cell:

- `receipt_render === "failed"`: a warning chip `expense.notInReport`, with
  `expense.notInReport.help` as its tooltip or hover text. Use the same
  warning treatment the grid already uses for a row needing attention; do not
  invent a new colour.
- `receipt_render === "ok"`: nothing. No chip, no tick. The absence of the
  warning is the signal, and a green tick on every row is noise.
- key absent: nothing.

The chip does not replace or change the Receipt cell's existing content. A
failed row still has its file, still opens in the app, and still counts as
having a receipt.

## 3. The count

`summary.n_receipts_unrenderable`, when present AND greater than 0, renders as
a warning tile or banner labelled `expense.tile.notInReport`, in the same strip
as the other month counts. At 0, render it neutral or hide it; when the key is
absent, hide it. Clicking it filters the grid to the failed rows if the grid
already supports count-to-filter; if not, leave it as a number.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `expense.notInReport` | Not in report | Fora do relatorio |
| `expense.notInReport.help` | This receipt could not be opened, so the report has a caption for it instead of its pages. Unlock the file or upload it again, then download the report. | Nao foi possivel abrir este recibo, por isso o relatorio tem uma legenda em vez das paginas. Desbloqueie o ficheiro ou carregue-o novamente e transfira o relatorio. |
| `expense.tile.notInReport` | Receipts not in report | Recibos fora do relatorio |

## 5. Do not change

`has_receipt_image`, the Receipt cell, the review state, `n_receipts`,
`n_ready` and every other count keep their meaning. `receipt_render` is
additive: a month where every receipt opens renders exactly as it does today,
and a month nobody has built a report for carries neither field.
