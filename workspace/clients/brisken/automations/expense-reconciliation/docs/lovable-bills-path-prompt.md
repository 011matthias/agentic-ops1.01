# Lovable prompt: a Bills section for invoices paid by bank transfer (item 218)

> **NOT PASTED.** SPA half of backlog item 218 (Build 4, owner decisions
> 2026-09-25). The backend half ships first and needs no SPA change to be
> correct: bill rows already leave the card counts, the totals and
> `expenses.csv`. Without this prompt the page still lists a bill row among
> the card rows and offers no way to move a row between the two paths.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`.

## Why

Some invoices are not paid by a company card: a supplier bill paid by bank transfer (wire, SEPA, boleto, PIX). The backend now marks each expense row with the path it was paid through, `payment_path: "card" | "bill"`. A bill row never gets a card statement, so it must not sit among the card rows waiting for one. The owner decided: bills stay visible inside their month, in their own section, out of the card counts and the month's total, and downloadable as their own list for Criss to book by hand in Zoho.

## Scope

`src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx`, `src/lib/i18n.tsx`. Do NOT change the Matching tab (`RunWorkbench.tsx`): bill receipts already leave its unmatched list on the backend.

## 1. Types (`src/lib/api.ts`)

- `ExpenseRow` gains `payment_path?: "card" | "bill"`, `payment_path_source?: "person" | "settled_outside" | "stated" | "statement" | ""` and `bill_suggestion?: { evidence: string }`. Treat a missing `payment_path` as `"card"`.
- The Expenses summary gains `n_bills?: number` and `bills_by_ccy?: Record<string, string>` (same shape as `copies_set_aside_by_ccy`).
- `ExpenseField` gains `"payment_path"`. The move is the existing `updateExpenseField(runId, documentId, "payment_path", "bill" | "card")`.
- A bill row carries `counts_in_total: false` and `review: { state: "none", reason_code: "bill", reason: "..." }`. Render nothing for that review line in the card list (the row is not there) and do not treat `counts_in_total: false` on a bill row as a duplicate copy.
- Two new refusal codes on that PUT, for `errorText`: `bill_held_by_charge` and `invalid_payment_path` (strings in §5).
- A download helper for `GET /runs/{runId}/bills.csv`, saved as `bills-{runId}.csv`, shaped like the existing expenses.csv download.

## 2. The card list shows card rows only

Wherever the grid builds its row list (`tabRows` and the list rendered under the boxes), leave out rows with `payment_path === "bill"`. The boxes and the total already exclude them on the backend; do not recount them.

Under the month total, when `summary.n_bills > 0` and no card tab is selected, add one muted line in the style of the copies line: `expx.bills.totalsLine.one` / `.many` with `{amounts}` from `bills_by_ccy` (for example "1 bill paid by bank transfer, not in this total: BRL 27,203.34").

## 3. A "Bills (paid by bank transfer)" section

Below the card rows, only when at least one row has `payment_path === "bill"` and no card tab is selected: a section headed `expx.bills.title` with the count, a one-line explanation `expx.bills.hint`, and a **Download bills (CSV)** button (`expx.bills.download`) using the helper from §1.

Each bill row is one compact line: date, supplier (`vendor.display`), amount and currency, company (`legal_entity_id`, or `expx.bills.noCompany` in amber when empty), the file-name link that opens the existing receipt preview, and a small muted "why" chip from `payment_path_source`:

- `stated` -> `expx.bills.source.stated` ("The invoice says it was paid by bank transfer")
- `settled_outside` -> `expx.bills.source.settled` ("Marked as paid by bank transfer")
- `person` -> `expx.bills.source.person` ("Moved here by hand")

and one outline button **Move to the card queue** (`expx.bills.moveToCard`): `updateExpenseField(runId, row.document_id, "payment_path", "card")`, then the grid's existing after-edit invalidation and a toast `expx.bills.toast.movedToCard`. Keep the existing company control on the row (the entity picker) so Criss can set the company of a bill without leaving the section; no category, card or private controls on bill rows.

## 4. Moving a card row to Bills

On a card row with no card (`row.card == null`), not private (`!row.private`), that counts in the total (`row.counts_in_total !== false`) and has no `transaction_id`, offer a small outline button **Paid by bank transfer** (`expx.bills.moveToBill`) next to the existing settled-outside / private controls: `updateExpenseField(runId, row.document_id, "payment_path", "bill")`, invalidate, toast `expx.bills.toast.movedToBill`. On a 400 show `errorText(e, t)` as for every other edit.

When the row carries `bill_suggestion`, show an amber chip **Looks like a bank-paid invoice** (`expx.bills.suggest.chip`) beside that button; its tooltip reads `expx.bills.suggest.tip` followed by the evidence line in quotes. The chip never moves the row by itself.

## 5. Strings (EN, then PT)

| Key | EN | PT |
|---|---|---|
| `expx.bills.title` | Bills (paid by bank transfer) | Contas (pagas por transferência bancária) |
| `expx.bills.hint` | These were not paid by a company card, so no statement will cover them. They are not in the card counts or the month's total. Book them in Zoho by hand. | Estas não foram pagas com cartão da empresa, então nenhum extrato vai cobri-las. Não entram nas contagens de cartão nem no total do mês. Lance-as no Zoho manualmente. |
| `expx.bills.download` | Download bills (CSV) | Baixar contas (CSV) |
| `expx.bills.noCompany` | No company yet | Sem empresa ainda |
| `expx.bills.source.stated` | The invoice says it was paid by bank transfer | A fatura diz que foi paga por transferência bancária |
| `expx.bills.source.settled` | Marked as paid by bank transfer | Marcada como paga por transferência bancária |
| `expx.bills.source.person` | Moved here by hand | Movida para cá manualmente |
| `expx.bills.moveToCard` | Move to the card queue | Mover para a fila do cartão |
| `expx.bills.moveToBill` | Paid by bank transfer | Paga por transferência bancária |
| `expx.bills.suggest.chip` | Looks like a bank-paid invoice | Parece uma fatura paga por banco |
| `expx.bills.suggest.tip` | The document prints the supplier's bank details: | O documento traz os dados bancários do fornecedor: |
| `expx.bills.toast.movedToBill` | Moved to Bills | Movida para Contas |
| `expx.bills.toast.movedToCard` | Moved to the card queue | Movida para a fila do cartão |
| `expx.bills.totalsLine.one` | 1 bill paid by bank transfer, not in this total: {amounts} | 1 conta paga por transferência, fora deste total: {amounts} |
| `expx.bills.totalsLine.many` | {count} bills paid by bank transfer, not in this total: {amounts} | {count} contas pagas por transferência, fora deste total: {amounts} |
| `err.bill_held_by_charge` | A card charge on the statement already holds this receipt, so a card paid it. Reject that match first. | Uma cobrança do cartão no extrato já está com este recibo, então um cartão pagou. Rejeite esse pareamento primeiro. |
| `err.invalid_payment_path` | Choose card or bill. | Escolha cartão ou conta. |

## 6. Checks

1. July (`/expenses/50622baec444`): the Bills section lists the Rodrigo Tanure Tricarico invoice (BRL 27,203.34, chip "Marked as paid by bank transfer"); it is not among the card rows; the totals line reads "1 bill paid by bank transfer, not in this total: BRL 27,203.34".
2. July: the Redis invoice `0004` and the 360Crossmedia invoice `0008` show the amber "Looks like a bank-paid invoice" chip beside "Paid by bank transfer"; the Konsultancy Finance row `0003` shows the button and no chip.
3. August and September: no Bills section, no totals line, no chip.
4. "Download bills (CSV)" on July saves `bills-50622baec444.csv`.
5. PT: the section title reads "Contas (pagas por transferência bancária)".
````
