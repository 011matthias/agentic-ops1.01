# Lovable prompt: Month suggestion banner

**APPLIED. Verified 2026-09-01 in the published bundle (`brisken-reconcile-dash.lovable.app`): the bundle reads `period_suggestion`; the owner pasted this one on 2026-09-01, after PR #657 deployed the field.**

The gate is spent: `period_suggestion` deployed with PR #657 and this
prompt was pasted on 2026-09-01. Kept as the record of what the banner
was asked to do.

Paste into `brisken-expense-review`. Touches the month (expense batch)
page plus i18n (EN and PT; the PT strings below are final accented
copy).

## Why

Operator, 2026-08-28: "why does the tool not automatically recognize
what month the receipts inserted are from?" Emailed receipts already
file by their printed month; manually uploaded ones follow the month
label the operator typed, because scanned dates are the least reliable
field and a silent misfile is worse than a question. The missing piece
is the suggestion: the backend derives "which month do these receipts
collectively read as" and will expose it on
GET /api/expense-batches/{batchId} as `period_suggestion`:
`{ month: "YYYY-MM", label_month: "YYYY-MM" | null, n_dates: number,
n_in_month: number }`.

## 1. The banner

On the month page, when `batch.period_suggestion` exists AND
(`period_suggestion.label_month == null` OR it differs from
`period_suggestion.month`): render a dismissible banner above the grid.
Reuse the exact style of the existing `MonthAdvisory` callout
(`ExpensesReviewGrid.tsx:190-276`, the sky-blue
`rounded-md border border-sky-500/30 bg-sky-500/5 p-4 text-sm` box):

EN "These receipts read as {Month Year}. Rename the month to match?"
with buttons "Rename" and "Not now".
PT "Estes recibos parecem ser de {Month Year}. Renomear o mês?"
with "Renomear" and "Agora não".

- "Rename" calls the existing `renameRun` (src/lib/api.ts:587, POST
  /api/runs/{id}/rename, body `{label}`) with a label of the form
  "{Month Year}" in the current UI language (the backend parses EN and
  PT month names, including "abril de 2026"), then refreshes the batch.
- "Not now" hides the banner for this batch for the session (local
  state only).
- Use `== null` (loose) for the label_month check so an omitted key
  behaves like null.

## 2. No double banner

The existing `MonthAdvisory` (shown after creating a batch whose label
names no month) covers the same situation. When the `period_suggestion`
banner renders, suppress `MonthAdvisory`; the suggestion banner is
strictly more useful because it knows WHICH month to propose. A batch
must never show two stacked rename banners.

## 3. Defensive rendering

Only render when `period_suggestion` is an object with a string `month`
matching /^\d{4}-\d{2}$/. Absent or malformed: render nothing. Never
block the grid.

## Verify after publish (once the backend field is live)

1. Create a month whose label names no month and upload at least 4
   receipts dated in the same month (the backend needs 4 or more dated
   expenses with a clear majority before it suggests anything): the
   banner appears with that month, exactly one banner shows, Rename
   applies it and the banner disappears.
2. A month whose label already matches shows no banner.
