# Lovable prompt - shorter review lines on the Expenses page (backlog item 213, owner note #87)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). Copy changes only: no new request, no new field, no
count or box changes. **Do NOT add Supabase or any database.**

## Background

The "waiting for a statement" line names every card whose statement is
missing for the row's date. On September that is seven to nine company cards
on each of 13 rows, 284 to 346 characters each, and it fills the page. The
backend's own sentence now names the cards only when one or two are waiting;
the page should do the same.

## 1. The waiting line (Expenses page, each row)

`review.reason_code: "waits_for_statement"` with
`review.waits_for_statements: [card label]`, unchanged.

- One or two labels: render `expx.review.reason.waits_for_statement` with
  `{cards}` = the labels joined by ", ".
- Three or more: render the new key `expx.review.reason.waits_for_statement_many`
  (no card names).

Keep the current neutral styling and every count as it is.

| Key | EN | PT |
|---|---|---|
| `expx.review.reason.waits_for_statement` (replace) | No card on this receipt; waiting for the statement of {cards}. | Sem cartão neste recibo; aguardando o extrato de {cards}. |
| `expx.review.reason.waits_for_statement_many` (new) | No card on this receipt, and no statement is loaded for its date yet. | Sem cartão neste recibo, e ainda não há extrato carregado para esta data. |

## 2. Settled outside the card system (Expenses page, each row)

| Key | EN | PT |
|---|---|---|
| `expx.review.reason.needs_entity_settled_outside` (replace) | This was settled outside the card system, so no card names the company. Set the legal entity on the row. | Esta despesa foi paga fora do sistema de cartões, então nenhum cartão indica a empresa. Defina a entidade legal na linha. |

## 3. Checks after publishing

| Where | Expect |
|---|---|
| September Expenses, the 13 rows waiting for a statement | Each reads "No card on this receipt, and no statement is loaded for its date yet." / PT "Sem cartão neste recibo, e ainda não há extrato carregado para esta data." No card label in the line |
| July Expenses, the one row settled outside the card system | The shorter `needs_entity_settled_outside` line, EN and PT |
| Any row whose `review.waits_for_statements` has one or two labels | The line names those labels |
| Every other review line | Unchanged |
