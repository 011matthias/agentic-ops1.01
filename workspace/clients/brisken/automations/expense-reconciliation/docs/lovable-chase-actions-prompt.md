# Lovable prompt: act on a charge from the "to chase" list (items 258 and 260)

> **NOT PASTED.** Answers the operator's notes #132, #133, #134 and #135
> (2026-10-29, August and September, "Charges with no receipt, to chase").
>
> **Backend half is in the same PR and needs no SPA change to stay safe:**
> `assignable_receipts[]` now carries `date` and `reference` (the hand-match
> picker printed "-" for every date), and the run `summary` carries
> `n_charges_open_no_receipt_due`. Both are parallel fields.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No new request: every call below already exists in `src/lib/api.ts`.

## Why

The operator, on the "Charges with no receipt, to chase" panel of the month workbench:

- *"there should be an option for user to match charge with the corresponding expense that has potentially not been matched by system yet"* (on GITHUB INC.)
- *"button to justify whether there exists a receipt"* (on a Credit Card - 2838 row)
- *"criss wants a line item specific match receipt button here that works"* (September, Credit Card Chase Visa - 3876)
- *"Charges without receipt... 47 open... what does this 'Open' mean specifically"*

The panel lists every charge with no receipt, but its rows have no actions. The three things a person does with such a charge (match a receipt the tool left alone, say none exists, say the holder was asked) exist only on the table row further down the page, where the operator is not looking.

## Scope

Only `src/components/ReceiptChasePanel.tsx`, `src/components/RunWorkbench.tsx` and `src/lib/i18n.tsx`. No change to how groups are built or sorted.

## 1. Each charge row in the chase panel gets its three actions

In the per-charge table of `ReceiptChasePanel`, replace the last (status) cell with a right-aligned cell holding, in this order:

1. The existing "asked on ..." / "asked N days ago" text, unchanged.
2. **Match a receipt** (`chase.row.match`): opens the existing `ManualMatchDialog` for this charge. Export `ManualMatchDialog` from `RunWorkbench.tsx` (or move it to its own file) and reuse it unchanged. Feed it `data.assignable_receipts` (pass the array down to the panel as a new prop `receipts`), the charge's `vendor`, `amount`, `currency`, and on pick call the existing `manualMatch(runId, { transaction_id, document_id })`, then invalidate `["run", runId]` and `["operator-state"]` exactly as the row actions do. A 409 or 400 shows the existing `errorText(e, t)` toast; do not retry.
3. **Asked / Clear asked** (`row.markRequested` / `row.clearRequested`, existing keys): the existing `markReceiptRequested` call.
4. **No receipt exists** (`row.noReceiptExpected`, existing key): the existing reason dialog and `markNoReceiptExpected` call.

Refactor `ReceiptChaseRowActions` so it takes `{ transactionId, asked, noReceipt, busy }` instead of a whole `RunRow`; the table row at `RunWorkbench.tsx` keeps working by passing `row.transaction_id`, `!!row.receipt_requested_at`, `!!row.no_receipt_expected`. The panel's rows pass `c.transaction_id`, `!!c.receipt_requested_at`, `false`. One component, two callers; do not copy the mutations.

### Ranking inside the picker

`ManualMatchDialog` today lists receipts alphabetically. For the chase panel, sort the `receipts` it is handed before passing them in:

1. Same currency as the charge first.
2. Then smaller absolute difference between `receipt.total` and the charge amount.
3. Then smaller day distance between `receipt.date` and the charge date (a receipt without a date sorts last).
4. Receipts with `held_by` set (another charge already holds them) last; they stay selectable, since picking one steals it.

Do not filter anything out. Keep the search box.

Show `receipt.reference` under the vendor in small muted text when it is not empty (it is new in the payload; older payloads simply lack it, so guard for `undefined`).

## 2. Say what "open" means

The "Charges without a receipt" view tile shows a count and a line "{n} open". The chase panel's title shows a different count. Cause, measured on live August: a gray-filled fee line (ANNUAL MEMBERSHIP FEE) is closed on the backend, but its `reason_code` is `not_a_purchase`, and `isRowDecided` in `RunWorkbench.tsx` only treats the codes `closed_recurring` and `no_receipt_expected` as closed, so the tile counts it as open.

- In `isRowDecided`, add one line before the final return: `if (row.closed_without_receipt === true) return true;`. The backend sets this flag on every unmatched row that the gray fill or a "no receipt exists" mark closed, whatever its `reason_code` says. Guard for `undefined` (older payloads).
- Give the tile's "{n} open" line a tooltip (`wb.view.open.tip`): "Open = still needs a person. Charges booked already, closed by a recurring booking, or marked 'no receipt exists' are not open."
- In the chase panel subtitle (`chase.subtitle`), when `summary.n_charges_open_no_receipt_due` is greater than 0 append a second sentence (`chase.subtitle.fees`): "{n} more open charge(s) here are fees or interest: they need a decision, not a receipt." Render nothing extra at 0. Read the count from the run `summary`; guard for `undefined` (older payloads).

## 3. Strings (English and Portuguese, both languages in `i18n.tsx`)

| key | EN | PT |
|---|---|---|
| `chase.row.match` | Match a receipt | Associar um recibo |
| `wb.view.open.tip` | Open = still needs a person. Charges already booked, closed by a recurring booking, or marked "no receipt exists" are not open. | Aberto = ainda precisa de uma pessoa. Lançamentos já registrados, fechados por um lançamento recorrente ou marcados como "não existe recibo" não estão abertos. |
| `chase.subtitle.fees` | {n} more open charges here are fees or interest: they need a decision, not a receipt. | Mais {n} lançamentos abertos aqui são tarifas ou juros: precisam de uma decisão, não de um recibo. |

## 4. The page's action buttons go in the top bar

Operator note #128, on the October Expenses tab: *"these buttons should be all the way in the top bar"*, anchored on the line "Review by exception. Ready rows can go out as is; the others need a look." followed by "Add receipts", "Add ..." and the other page-level buttons. Move that button group out of the body and into the page header row (the same bar that holds the month title and the language switch), right-aligned, wrapping under the title on narrow widths. Keep every button, its label, its handler and its order. Do not move row-level buttons.

## Checks

1. A charge in the chase panel shows Match a receipt, Asked and No receipt exists. Pressing Match a receipt on a charge opens the picker with the best same-currency, same-amount receipt first.
2. Picking a receipt removes the charge from the panel without a page reload, and the panel title count drops by one.
3. Marking "No receipt exists" with a reason removes the charge from the panel too.
4. The table row further down still shows its two marks and still works.
5. With `n_charges_open_no_receipt_due` = 1 the panel subtitle gains the fees sentence; at 0 it reads as before.
````
