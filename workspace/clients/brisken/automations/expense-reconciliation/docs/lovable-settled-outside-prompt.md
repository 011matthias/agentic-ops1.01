# Lovable prompt - receipts settled outside the card (item 62)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

Some receipts never post to a card. July 2026 holds a Redis invoice for
13,200.00 USD, a Konsultancy Finance one for 15,972.00 EUR and a 360Crossmedia
one for 900.00 EUR, all paid by bank transfer, and the Lovable invoices print
"Pay with a bank transfer". No statement line will ever settle them, so they
sit in the unmatched pool and in the counts forever with nothing the reviewer
can do about it. The backend now has a disposition that retires such a receipt
from the reconciliation side while it stays an expense of the month: it still
shows in the grid and still prints in the month report, captioned with how it
was settled.

## 1. The new fields

`GET /api/runs/{id}` (workbench):

- `summary.n_settled_outside` (integer) - how many receipts the reviewer
  settled outside the card.
- A settled receipt is GONE from `unmatched_receipts` and from
  `n_unmatched_rec`. Nothing else about the month changes; `n_receipts` still
  counts it, because it is still in the month.
- `unmatched_receipts[].suggested_settled_outside`, parallel and **absent**
  (not null) unless the scan read a tender no card carries:

```json
"suggested_settled_outside": {
  "how": "bank_transfer",
  "evidence": "Pay $15.00 with a bank transfer"
}
```

`GET /api/expense-batches/{id}` (grid):

- `summary.n_settled_outside` (integer), same name, same question.
- `expenses[].settled_outside`, parallel and **absent** unless set:

```json
"settled_outside": {
  "how": "bank_transfer",
  "note": "wire sent 2026-08-11",
  "at": "2026-09-15T09:12:44"
}
```

`how` is one of `bank_transfer`, `cash`, `paypal`, `other`.

## 2. The control, on an unmatched receipt

On each row of the unmatched-receipts list, add an action
**"Settled outside the card"** opening a small dialog:

- a required choice of `how` (the four values above), and
- an optional free-text `note` (500 characters).

When the row carries `suggested_settled_outside`, show a chip on the row
reading `wb.settledOutside.suggested` with the tender named, and PRE-SELECT
that `how` in the dialog. The chip is a suggestion only; never apply it on its
own, never auto-open the dialog. Render `evidence` as muted secondary text
under the chip so the reviewer can see what the receipt actually said.

Confirm posts:

```
POST /api/runs/{run_id}/receipts/{document_id}/settled-outside
{"how": "bank_transfer", "note": ""}
```

`document_id` goes in the path and can contain `/`; encode it with
`encodeURIComponent`. The reply carries `summary` - use it to refresh the
counts without a full refetch, exactly as the duplicates resolve call does.

Errors come back `400 {"error": "..."}`; show the message as-is. The one the
reviewer will actually hit reads "That receipt is settled against a charge on
the statement. Reject that match first, then mark it settled outside the card."

## 3. The undo

On a grid row that carries `settled_outside`, show a badge reading
`expx.settledOutside.badge.{how}` with the note as a tooltip when present, and
a menu action **"Put back in the pool"**:

```
DELETE /api/runs/{run_id}/receipts/{document_id}/settled-outside
```

It is idempotent (`removed: false` when it was already gone), so a double
click is not an error. This is the same undo shape as the duplicates `ignore`
resolution: nothing about the receipt was ever changed, so releasing it
restores the pool and the counts exactly.

## 4. The tile

`summary.n_settled_outside` beside the existing tiles, labelled
`wb.tile.settledOutside`. Neutral at 0. It answers "how many receipts on this
month will never appear on a card statement", which is the question that made
the pool look permanently unfinished.

## 5. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.settledOutside.action` | Settled outside the card | Liquidado fora do cartao |
| `wb.settledOutside.suggested` | Looks paid outside the card | Parece pago fora do cartao |
| `wb.settledOutside.how` | How was it settled? | Como foi liquidado? |
| `wb.settledOutside.how.bank_transfer` | Bank transfer | Transferencia bancaria |
| `wb.settledOutside.how.cash` | Cash | Dinheiro |
| `wb.settledOutside.how.paypal` | PayPal | PayPal |
| `wb.settledOutside.how.other` | Something else | Outro meio |
| `wb.settledOutside.note` | Note (optional) | Nota (opcional) |
| `wb.tile.settledOutside` | Settled outside the card | Liquidado fora do cartao |
| `expx.settledOutside.badge.bank_transfer` | Paid by bank transfer | Pago por transferencia bancaria |
| `expx.settledOutside.badge.cash` | Paid in cash | Pago em dinheiro |
| `expx.settledOutside.badge.paypal` | Paid by PayPal | Pago por PayPal |
| `expx.settledOutside.badge.other` | Settled outside the card | Liquidado fora do cartao |
| `expx.settledOutside.undo` | Put back in the pool | Devolver a lista |

## 6. Do not change

The expense grid removes NOTHING: a settled-outside receipt is still a row,
still categorizable, still exported, and still prints in the month report. Only
the workbench's unmatched pool and its counts let it go. `n_receipts`,
`n_expenses` and every other count keep their meaning, and a month with no
dispositions carries neither new key at all, so the page renders exactly as it
does today.
