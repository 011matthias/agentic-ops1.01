# Lovable prompt: paid with a private card (reimbursement), only where no company card paid

> **NOT YET APPLIED.** Needs the 2026-09-17 private-card backend deploy
> (`expenses[].can_mark_private`). Builds on the applied
> `lovable-feedback-0917-prompt.md` section 4.

The app calls the FastAPI backend at `https://api.expenses.brisken.com`.
**Do NOT add Supabase or any database.** Auth is the existing
`Authorization: Bearer <token>`. Every new string ships in EN and PT in
`src/lib/i18n.tsx`.

## Why

An expense is paid either by a company card (a card defined in Settings >
Cards) or by someone's own card. Only the second is owed a reimbursement.
Today the Expenses grid offers "Mark as reimbursement" on every row, company
card rows included, so a company card charge can be booked as money owed to
a person. The backend now says per row whether the private-card option
applies, and refuses it where a company card paid.

## 1. The new field

`GET /api/expense-batches/{id}`, on each `expenses[]` row:

- `can_mark_private` (boolean). True when no defined company card paid the
  row, and always true on a row already marked private (so it can be
  undone). False means a company card paid: nothing to reimburse.

Add `can_mark_private?: boolean` to the `ExpenseRow` type in `src/lib/api.ts`.
Read it defensively: when it is absent (older backend), use
`row.card == null || row.private === true`.

## 2. Move the control into the card column and gate it

In `src/components/ExpensesReviewGrid.tsx`:

- Remove `<PrivateExpenseCell runId={runId} row={row} />` from the vendor
  cell.
- Render it in the entity/card cell, directly after `<CardFixCell ... />`.
- Inside `PrivateExpenseCell`: when the row is not private and
  `can_mark_private` is false, render nothing.

## 3. Name it as a private card

Inside `PrivateExpenseCell`:

- The trigger button reads `expx.privateCard.mark` on every eligible row,
  suggested or not. Keep the `expx.private.chip` chip on rows with
  `suggested_private: true`.
- Dialog title: `expx.privateCard.mark`. Dialog body: `expx.private.body` when
  `suggested_private` is true, else `expx.privateCard.body`. The "Reimburse"
  field, its prefill (`reimburse_to_prefill`, else `person`) and the request
  (`POST /api/runs/{id}/expenses/{doc}/private` with
  `{"private": true, "reimburse_to": "<name>"}`) stay exactly as they are.
- Save button: `expx.privateCard.save`.
- On a private row the badge keeps `expx.private.badge` and the undo button
  keeps sending `{"private": false}`; only the copy changes (below).
- Show the backend error message verbatim in the dialog, as today. It now
  also answers 400 with `"code": "company_card"` when a company card paid.

| Key | EN | PT |
|---|---|---|
| `expx.privateCard.mark` | Paid with a private card | Pago com cartão particular |
| `expx.privateCard.body` | No company card paid this expense. Name the person who paid with their own card; they are owed a reimbursement. | Nenhum cartão da empresa pagou esta despesa. Indique quem pagou com o próprio cartão; essa pessoa tem direito a reembolso. |
| `expx.privateCard.save` | Save as private card | Salvar como cartão particular |
| `expx.private.badge` (change) | Private card: reimburse {name} | Cartão particular: reembolsar {name} |
| `expx.reimburse.undo` (change) | Undo private card | Desfazer cartão particular |

`expx.reimburse.mark` is no longer used; delete it from both languages.

## 4. No company-card pick on a private row

In `CardFixCell`: when `row.private` is true, render nothing. The backend
refuses a card pick on a private row (400, `"code": "private_card"`); the way
to put a company card on it is Undo private card first, then pick the card.

## 5. Nothing else changes

Tiles, boxes, the card strip, the suggested-private filter and the reports
stay as they are.

## Verify after publish

- Bundle: `can_mark_private` and `expx.privateCard.mark` in the expenses
  chunk; `expx.privateCard.body` in i18n; `expx.reimburse.mark` absent.
- August 2026 month, row "Moghul Mahal Indisches Restaurant" (paid with
  "EC-Karte"): the card column shows the "Suggested private expense" chip and
  "Paid with a private card". The vendor cell shows no private control.
- Same month, any row on "Credit Card Chase Visa - 3645" or "Credit Card -
  2838": no private control anywhere on the row.
