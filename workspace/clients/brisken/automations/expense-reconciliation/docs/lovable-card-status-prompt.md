# Lovable prompt: the per-card filter, outside the months (item 185)

**NOT PASTED.** Paste into the `brisken-expense-review` Lovable project
(production `brisken-reconcile-dash.lovable.app`). The backend half shipped
2026-09-24: `GET /api/cards/status` exists and needs no change. New strings
ship in BOTH the EN dictionary and the PT mirror in `src/lib/i18n.tsx`.

## Why

Owner, 2026-09-24, on feedback note #86 left on `/months`: *"the same per
card filter system inside the months should be outside of the months..."*

The note says what it is for: *"I'm looking for a feature where I'm able to
sort and find a status for a single card... which cards are missing / which
receipts are missing or don't have a corresponding statement / which
statements don't have a corresponding receipt. I don't know which month it
is on."*

Everything the tool shows is filed by month. Open August and the card strip
tells you what is open on each card in August. There is no way to ask the
question the other way round, and the practical cost is real: four defined
cards (9693, 0113, 6013, 8311) have never carried a charge or a statement in
any month, and finding that out today means opening every month in turn.

## The data

`GET /api/cards/status`, no parameters. Same auth as every other call.

```jsonc
{
  "cards": [                       // busiest first, empty cards last
    {
      "key": "card-1176",          // stable id, use as the React key
      "card_key": "card-1176",     // "" when the registry does not know it
      "label": "Credit Card Chase Visa - 1176",
      "digits": ["1176"],
      "entity": "Consulting",      // "" when unknown
      "known": true,               // false = a card seen on a statement, undefined
      "never_loaded": false,       // no charge and no statement in ANY month
      "n_months": 1,               // months this card is actually ON
      "n_transactions": 3,
      "n_reconciled": 0,
      "n_review": 0,
      "n_unmatched_tx": 1,         // charges with no receipt
      "n_refunds": 2,
      "n_statements": 1,
      "statements": [{"file": "20260804-statements-1176-.pdf",
                      "run_id": "074a7b8905d7", "month": "August 2026"}],
      "period_start": "2026-07-06",
      "period_end": "2026-08-04",
      "unreconciled_by_ccy": {"USD": "36.00"},   // formatted strings
      "months": [                  // newest first; only months it is ON
        {"run_id": "074a7b8905d7", "label": "August 2026",
         "batch_type": "expense_month", "n_transactions": 3,
         "n_reconciled": 0, "n_review": 0, "n_unmatched_tx": 1,
         "n_refunds": 2, "statements": ["20260804-statements-1176-.pdf"],
         "period_start": "2026-07-06", "period_end": "2026-08-04",
         "unreconciled_by_ccy": {"USD": "36.00"}}
      ]
    }
  ],
  "months": [{"run_id": "...", "label": "August 2026",
              "batch_type": "expense_month", "created_at": "...",
              "n_transactions": 114, "n_cards": 5,
              "period_start": "...", "period_end": "..."}],
  "unreadable": [],                // run ids whose snapshot could not be read
  "note": "..."                    // the stated limit, render it as a footnote
}
```

Money values are already formatted (`"1,234.56"`). Print them, never parse
and re-format them.

## 1. A new top-level page at `/cards`

Add "Cards" to the main nav, after "Months" and before "Trips". EN "Cards",
PT "Cartões". Fetch with a `["cards", "status"]` query alongside the existing
`["cards"]` one; they are different endpoints and both are needed here (this
one has the counts, the other has the registry fields).

## 2. The card strip, with the counts it already has

Reuse the month page's card strip component. Same look, same behaviour, one
difference: the counts are the estate's, not a month's.

- One chip per card: the digits (or `label` when there are none) over
  `n_transactions`, exactly as the month strip renders it.
- An "All" chip first.
- Cards with `never_loaded === true` are hidden behind the same disclosure
  the month page uses: EN "Show {n} cards with nothing loaded" / PT
  "Mostrar {n} cartões sem nada carregado". Note the wording differs from the
  month page's "nothing this month" on purpose: here it means nothing
  anywhere, which is a much stronger statement.
- A card with `known === false` carries the same "not in Settings" marker the
  month page already uses, and its label is what the statement printed.

## 3. Selecting a card shows its months

This is the half that does not exist today. Under the strip, for the selected
card:

- A header line: the label, the entity when there is one, the span
  `period_start` to `period_end`, and `n_months` months.
- A table, one row per entry in `months`, newest first:

  | Month | Period | Charges | Matched | Needs review | No receipt | Statements | Still open |
  |---|---|---|---|---|---|---|---|

  `Still open` prints `unreconciled_by_ccy` as one line per currency.
  `Statements` lists the file names. The whole row links to
  `/expenses/{run_id}`, which is where the work actually happens.
- A trip month is marked with the same badge the trips list uses
  (`batch_type !== "expense_month"`), so a card's spend on a trip is
  visible as a trip rather than silently mixed into a month.

With "All" selected, show one row per card instead: the same columns, summed,
each row selecting that card.

## 4. A card with nothing, said plainly

When `never_loaded === true`, do not render an empty table. Render one line:

- EN: "No charge and no statement in any month. Either this card is dormant,
  or its statement has never been loaded."
- PT: "Nenhuma cobrança e nenhum extrato em nenhum mês. Ou este cartão está
  inativo, ou o extrato dele nunca foi carregado."

That sentence is the answer to "which cards are missing", and it is the one
thing no month page can say.

## 5. Two small things

- `unreadable` is normally empty. When it is not, show a quiet line naming
  how many months could not be read, so the figures are never silently short.
- Render `note` as a footnote under the table.

## How to check it worked

On production data, `/cards` should show 9 chips plus `digits:4700`. Card
1176 selects to one month (August 2026), 3 charges, 1 with no receipt, one
statement `20260804-statements-1176-.pdf`, still open USD 36.00. Cards 9693,
0113, 6013 and 8311 sit behind the "nothing loaded" disclosure and each show
the single line from section 4.
