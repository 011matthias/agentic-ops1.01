# Lovable prompt - a corrected date moves the receipt to its month (item 77)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend at
`brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A receipt is filed in the month its printed date names. When that date is
misread, the receipt lands in the wrong month: a Mercado Pago slip printing
`04/07/26` was read as a January date, so a "January 2026" month was created
for it. Criss corrected the date to July, and the receipt stayed in January,
because nothing moved it. The backend now offers the move on the row and
carries it out in one call.

## 1. The new fields

`GET /api/expense-batches/{id}` -> `expenses[].month_move`, parallel and
**absent** (never null) unless the row's date was typed by the reviewer and
belongs to another month:

```json
"month_move": {"month": "2026-07", "label": "July 2026", "batch_id": "50622baec444"}
```

`batch_id` is present when that month already exists and absent when the move
would create it. Build the month name from `month` with the page's locale
(`label` is English).

`summary.n_month_moves` (integer) counts the rows carrying an offer.

`expenses[].time` (`"23:56"`), `expenses[].invoice_number` and
`expenses[].receipt_number` (strings) are also new, each absent when the
receipt did not print it.

## 2. The move

`POST /api/runs/{batchId}/expenses/{documentId}/move` with an empty JSON body
(`{}`) moves the row to the month its offer names. The reply:

```json
{"ok": true, "document_id": "0051__receipt.pdf", "batch_id": "50622baec444",
 "label": "July 2026", "month": "2026-07", "created_batch": false,
 "already_in_batch": false, "source": {"batch_id": "4ceaeb461386", "n_expenses": 0},
 "summary": {"n_expenses": 0}}
```

On success: invalidate this month's batch query and the months list, then show
a toast with a link to the target month (`/expenses/$batchId` with the reply's
`batch_id`). When `created_batch` is true, say the month was opened. When
`already_in_batch` is true, say the receipt was already there. On a 4xx, show
the reply's `error` string in the toast.

## 3. The render

In `ExpensesReviewGrid.tsx`, `ExpenseRowView`, directly under the date cell's
`EditableText`, when `row.month_move` is present render one line:

- text `expx.review.monthMove.body` with `{month}` = the localized month name
  from `row.month_move.month`;
- a small outline button `expx.review.monthMove.action`, same `{month}`, that
  calls the move and shows a spinner while pending (disable it meanwhile).

Amber text, the same weight as the existing review reason. Nothing else on the
row changes: the date stays editable, and editing the date back into this
month makes the offer disappear on the next load.

When `summary.n_month_moves > 0`, add one line above the grid:
`expx.review.monthMove.banner` with `{n}`. No button there; the rows carry
the action.

If `row.time` is present, render it after the date in muted small text. The
two numbers need no render in this round.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `expx.review.monthMove.body` | This date belongs in {month} | Esta data pertence a {month} |
| `expx.review.monthMove.action` | Move to {month} | Mover para {month} |
| `expx.review.monthMove.banner` | {n} receipts are dated in another month | {n} recibos têm data de outro mês |
| `expx.review.monthMove.done` | Moved to {month} | Movido para {month} |
| `expx.review.monthMove.opened` | Moved to {month}, which was opened for it | Movido para {month}, que foi aberto para ele |
| `expx.review.monthMove.already` | {month} already had this receipt; removed here | {month} já tinha este recibo; removido daqui |

## 5. Do not change

The date cell, `review`, `edited_fields`, every existing count and the month
header keep their meaning. `month_move` is additive: a month with no
misfiled receipt does not carry the key, and the page renders exactly as it
does today. The move never deletes the source month, even when it leaves it
empty.
