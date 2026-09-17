# Lovable prompt - fix the card on one expense (item 87)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

A receipt that prints no card number ("VISA", "Cash", or nothing at all)
cannot be matched to a company card, so it sits in "No company or person" and
the card-review strip cannot help: the strip assigns by the printed words, so
it moves every "VISA" receipt in the month at once and never sees a receipt
that prints nothing. On July that is 24 of the 33 rows in that box. The backend
now takes a card for ONE expense, and remembers it for that vendor when the
month is published.

## 1. The API

- `PUT /api/runs/{batchId}/expenses/{documentId}` with
  `{"field": "card_key", "value": "<card key>"}` sets the card for that one
  expense; `"value": ""` clears it. It answers like every other field edit
  (use `updateExpenseField` and `afterExpenseEdit`, exactly as the other
  header fields do). A 400 carries `error` (unknown or inactive card): show it
  as the toast the field saver already shows.
- The card list is the existing `getCards()` (query key `["cards"]`); offer
  only cards with `active !== false`, labelled `label` (fallback `key`).
- Every `expenses[]` row gains `card_source` (string): `hint` (the receipt's
  printed payment method named the card), `override` (fixed by hand this
  month), `learned` (remembered from an earlier month's fix), or `none` (no
  card; `card` is null). Add `card_source?: string` to the expense row type and
  `"card_key"` to `ExpenseField` in `src/lib/api.ts`.

## 2. The control (`ExpensesReviewGrid.tsx`)

In the entity cell, directly under the existing `<CardChip ... />`:

- When `row.card_source === "none"` or `"override"` or `"learned"`, render a
  small `Select` (`SelectTrigger className="mt-1 h-7 w-48 text-xs"`), value
  `row.card?.key ?? ""`, placeholder `t("expx.cardFix.pick")`, items = the
  active cards, plus, when `row.card_source === "override"`, a first item
  `t("expx.cardFix.clear")` that saves `""`. Choosing a card saves
  `card_key` through the row's field saver.
- When `row.card_source === "hint"`, render nothing new: the printed card
  decided it, and the card-review strip remains the place to change that.
- After the `CardChip`, when `row.card_source` is `override` or `learned`,
  one muted line (`text-[10px] text-muted-foreground`):
  `t("expx.cardFix.source.override")` or `t("expx.cardFix.source.learned")`.
- Disable the Select while the save is pending.

## 3. The box's fix line

In the "No company or person" box banner, replace `t("expx.box.fixCard")` +
its Settings link with `t("expx.cardFix.boxHint")` followed by the same
`<Link to="/settings">` reading `t("expx.box.fixCard.link")`. Keep
`expx.box.fixCard` in the dictionary, unused.

## 4. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `expx.cardFix.pick` | Pick the card that paid | Escolher o cartão que pagou |
| `expx.cardFix.clear` | Remove the card picked by hand | Remover o cartão escolhido à mão |
| `expx.cardFix.source.override` | Card picked by hand; publishing the month remembers it for this vendor | Cartão escolhido à mão; publicar o mês guarda-o para este fornecedor |
| `expx.cardFix.source.learned` | Card remembered from an earlier month for this vendor | Cartão lembrado de um mês anterior para este fornecedor |
| `expx.cardFix.boxHint` | Pick the card on each row, or mark the receipt private. A card missing from the list is added once in | Escolha o cartão em cada linha ou marque o recibo como particular. Um cartão que falta na lista é cadastrado uma vez em |

## 5. Do not change

- The card-review strip, its assign dialog and its "Remember for future
  months" switch.
- The entity Select, `EntitySourceLabel`, `PaidThroughCell`, the private
  expense controls and every other cell.
- The box tiles and their counts.

## 6. Render defensively

`card_source` may be absent on an older payload: render no Select and no
source line. An unknown `card_source` renders nothing. Never print a raw key.

## 7. After publishing, check

Re-read `GET /api/expense-batches/{id}` for July `50622baec444` first.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `card_source`, `expx.cardFix.pick`, `expx.cardFix.source.learned`,
   `expx.cardFix.boxHint`.
2. July, Expenses, "No company or person": each of the 33 rows shows the
   "Pick the card that paid" select; rows whose card came from the receipt
   (for example the 3876 and 3645 rows) show none.
3. The banner reads "Pick the card on each row, or mark the receipt private.
   A card missing from the list is added once in Settings, Cards".
4. Open one select and close it with Escape; do not pick a card on Criss's
   month. Network: no PUT during the drive.
5. PT: "Escolher o cartão que pagou".
