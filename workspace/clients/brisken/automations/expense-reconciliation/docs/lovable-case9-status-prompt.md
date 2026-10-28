# Lovable prompt - a receipt that names no card: what it waits for, which card it suggests, apply to this vendor, and which month a statement belongs to (backlog item 204, case 9, build 5)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend at
`brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

Most receipts that print no card are not waiting for a person. They are
waiting for a statement: September has no statement yet for most cards, so
no charge exists to pair the receipt with. Today every such row says "No
legal entity yet. Assign this expense's paying card...", which asks Criss to
do by hand what the next statement will do on its own. The backend now says
which statements the row is waiting for, suggests a card when a recurring
charge points to exactly one, lets a card picked on one row be applied to the
same vendor's other card-less rows with one explicit click, and tells the
statement upload when a file's charges belong to a different month. Nothing
is ever assigned without a click.

## 1. The waiting status (Expenses page, each row)

`GET /api/expense-batches/{id}` -> `expenses[]`:

- `review.reason_code: "waits_for_statement"` is a new review code, with
  `review.waits_for_statements: ["BCS Chase Visa - 9693", ...]` beside it.
- `waits_for_statements` (same list) also rides on the row itself whenever
  the row has no card and its date is not covered, even when the headline
  review is something else. Absent, never `[]` or null, otherwise.

Render the review line with the list joined by ", ":

| Key | EN | PT |
|---|---|---|
| `expx.review.reason.waits_for_statement` | Waiting for the statement of {cards}. The paying card shows once it is loaded; pick it now if you already know it. | Aguardando o extrato de {cards}. O cartão aparece quando o extrato for carregado; escolha agora se já souber. |

Styling: neutral (muted / info), not the amber of a problem, because the row
needs nothing from anyone yet. It stays in the "needs a look" count exactly
as `needs_entity` did; do not change any count or box.

`needs_entity` keeps its current copy and still appears when every card's
statement covers the date.

## 2. The suggested card (Expenses page, card cell)

`expenses[].card_suggestion`, absent unless one card is suggested:

```json
"card_suggestion": {
  "card_key": "3645",
  "label": "Credit Card Chase Visa - 3645",
  "evidence": [
    {"month": "2026-07", "date": "2026-07-05", "amount": "2.76",
     "currency": "USD", "description": "NETWORK SOLUTIONS"}
  ]
}
```

On a row whose `card` is null and that carries `card_suggestion`, show a
chip in the card cell: `cardSuggest.chip` with the label. Clicking the chip
opens a small popover listing each evidence entry as
`{description} · {amount} {currency} · {date}` under the heading
`cardSuggest.evidence`, and one button `cardSuggest.use`. The button sends the
existing per-row card pick, unchanged:

`PUT /api/runs/{run_id}/expenses/{document_id}` with
`{"field": "card_key", "value": card_suggestion.card_key}`

then reloads the batch as a pick does today. Never apply the suggestion
without that click, never pre-select it in the card picker, and never show
the chip on a row that has a card.

| Key | EN | PT |
|---|---|---|
| `cardSuggest.chip` | Suggested: {label} | Sugerido: {label} |
| `cardSuggest.evidence` | The same charge on this card | A mesma cobrança neste cartão |
| `cardSuggest.use` | Use this card | Usar este cartão |

## 3. Apply to this vendor's other rows (after a pick)

New route: `POST /api/expense-batches/{run_id}/cards/by-vendor`, body
`{"vendor": "<the row's vendor.display>", "card_key": "<the picked key>"}`.
It writes the same card pick to every row of that vendor in this month that
has no card, is not private or suggested private, printed no card number,
was not settled outside and is not a copy. Reply:
`{ok, vendor, card_key, documents: [document_id, ...], n_changed, summary}`.

With `"dry_run": true` in the body it writes nothing and replies the rows it
WOULD change in `documents` (`n_changed: 0`, `dry_run: true`).

After a successful card pick on a row (the PUT above, from the picker or from
the suggestion chip):

1. Call the route with `dry_run: true`, the row's `vendor.display` and the
   picked `card_key`.
2. If `documents` holds any row other than the one just picked, show an
   inline prompt under that row: `cardVendor.offer` with N = that count, and
   two buttons, `cardVendor.apply` and `cardVendor.dismiss`.
3. `cardVendor.apply` calls the route without `dry_run`, then reloads the
   batch and shows `cardVendor.done` with `n_changed`. `cardVendor.dismiss`
   hides the prompt; nothing is written.

Never call the route without the click in step 3.

| Key | EN | PT |
|---|---|---|
| `cardVendor.offer` | Apply {card} to the {n} other rows of {vendor} with no card? | Aplicar {card} às outras {n} linhas de {vendor} sem cartão? |
| `cardVendor.apply` | Apply to {n} rows | Aplicar a {n} linhas |
| `cardVendor.dismiss` | Only this row | Só esta linha |
| `cardVendor.done` | {n} rows now use {card}. | {n} linhas agora usam {card}. |

Refusals come back as today's `{error, code}`: `card_not_defined`,
`card_inactive`, `vendor_and_card_required`; show them the way the row PUT's
refusals are shown.

## 4. A statement says which month it belongs to (statement upload, statements list)

`GET /api/runs/{id}` -> `statements[]` entries now carry:

```json
"month_suggestion": {"month": "2026-07", "label_month": "2026-08",
                     "n_dates": 18, "n_in_month": 14}
```

absent when the file dated nothing or two months tie. When `month` differs
from `label_month`, the entry's `advisory_detail.code` is
`statement_month_differs` with fields `month`, `label_month`, `n_in_month`,
`n_dates` (the entry's English `advisory` sentence says the same).

Where the statement upload result and the statements list show an advisory
today, render this code with its own copy (months formatted as "July 2026"
in EN, "julho de 2026" in PT):

| Key | EN | PT |
|---|---|---|
| `adv.statement_month_differs` | {n_in_month} of this file's {n_dates} charges are dated {month}, but it was added to {label_month}. If it belongs to {month}, add it to that month instead. | {n_in_month} das {n_dates} cobranças deste arquivo são de {month}, mas ele foi adicionado a {label_month}. Se pertence a {month}, adicione-o a esse mês. |

Advisory only: the file stays attached, nothing is moved.

## 5. Do not change

Every count, box, tile and filter keeps its meaning. The card picker, the
row PUT, the private flow and the month pages are unchanged apart from the
additions above. `unmatched_receipts[].reason_code` gains no new value (a
no-card receipt waiting for a statement now reads the existing
`card_statement_not_loaded`), so the Matching page needs nothing.

## 6. Checks after publishing

1. September's Expenses page: a row with no card reads the waiting line
   naming the cards, in EN and PT, muted, and the "needs a look" count is
   unchanged from before the publish.
2. A row carrying `card_suggestion` shows the chip; the popover lists the
   evidence; nothing is picked until "Use this card" is clicked.
3. The by-vendor prompt appears only after a pick and only when the dry run
   names another row; "Only this row" writes nothing (0 non-GET requests
   after the pick's PUT and the dry run's POST).
4. A statement entry with `statement_month_differs` shows the localized
   sentence.
