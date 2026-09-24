# Lovable prompt: filter the months list by card (item 187)

**NOT PASTED.** Owner, 2026-09-24, after the `/cards` page went live: the
months list itself should filter by card. Scope is exactly that and nothing
else ("but just that").

**No backend change.** `GET /api/cards/status` already carries everything
this needs: `cards[]` for the strip, and `cards[].months[]` keyed by
`run_id` for the per-month figures. It is the same call `/cards` makes.

````markdown
On the months list (`/months`), add a card filter. Nothing else on the page changes. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`. No new backend field is needed.

## Why

The `/cards` page answers "pick a card, which months is it on". The months list cannot be asked that at all: it is one chronological list of every month, and the only way to find a card in it is to open each month in turn.

## The data, which already exists

`GET /api/cards/status`, the same call `/cards` already makes; reuse the `["cards", "status"]` query so both pages share one cache entry.

- `cards[]` gives the strip: `key`, `label`, `digits`, `n_transactions`, `never_loaded`, `known`.
- `cards[].months[]` gives the per-month figures, keyed by `run_id`, which joins to the month rows the page already renders: `n_transactions`, `n_reconciled`, `n_review`, `n_unmatched_tx`, `statements`, `unreconciled_by_ccy`, `period_start`, `period_end`.

## 1. The strip

Put the same card strip component the `/cards` page uses directly above the months table. Same look, same "All" chip first, same `never_loaded` disclosure ("Show {n} cards with nothing loaded"), same "not in Settings" marker on a card with `known === false`.

"All" is selected on load, and with "All" selected the page is byte-for-byte what it is today.

## 2. Picking a card filters the rows

With a card selected, show only the months in that card's `months[]` array, in the order the page already sorts months. A card whose `months[]` is empty shows an empty table with one line: EN "No month has a charge or a statement on this card." / PT "Nenhum mês tem cobrança ou extrato neste cartão."

## 3. Picking a card also changes the figures, because otherwise they lie

This is not extra scope, it is the filter being correct. The month row's numbers (Receipts, Needs category, Set aside) are the WHOLE month's. Showing "50 receipts" on the August row while the strip says 1176 would state something untrue about that card, which is the same class of defect as the old "From email" badge.

So with a card selected, keep the **Month** and **Created** columns and replace the middle columns with that card's own figures, the same columns the `/cards` page table already uses:

| Month | Period | Charges | Matched | Needs review | No receipt | Statements | Still open | Created |
|---|---|---|---|---|---|---|---|---|

`Period` is the card's `period_start` to `period_end` in that month. `Still open` prints `unreconciled_by_ccy` as one line per currency, already formatted; print it, never re-format it. `Statements` lists the file names.

With "All" selected the original columns come back unchanged.

## 4. The row still opens the month

Clicking a row goes to `/expenses/{run_id}` exactly as it does today, whichever card is selected. The selection is a view of the months list, not a different destination.

## 5. Do not change

The month sort order. The statement badge and the receipts-origin badge. The "new month" control. Anything on `/cards`. Anything inside a month. No new nav entry, no new route: this is a control on the page that already exists.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `months.cardFilter.empty` (new) | No month has a charge or a statement on this card. | Nenhum mês tem cobrança ou extrato neste cartão. |
| `months.cardFilter.period` (new) | Period | Período |

Reuse the existing card-strip strings; do not duplicate them.

## How to check it worked

Live numbers, read 2026-09-24. Selecting **1176** leaves exactly one month row, August 2026, reading 3 charges, 0 matched, 0 needs review, 1 no receipt, `20260804-statements-1176-.pdf`, still open USD 36.00. Selecting **3876** leaves August and July. Selecting **0340** leaves July and April. Selecting **2838** leaves August, July and April. Each of 9693, 0113, 6013 and 8311 sits behind the disclosure and leaves the table empty with the line from section 2. "All" restores the full list of seven months with today's columns.
````
