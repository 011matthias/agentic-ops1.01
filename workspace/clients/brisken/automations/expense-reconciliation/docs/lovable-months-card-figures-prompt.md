# Lovable prompt: the months list shows the picked card's own figures (item 231)

**NOT PASTED.** Owner, 2026-09-27, on `/months` with 2838 picked: *"remove that
number"* (the one beside each card chip, item 193's needs-category count) and
*"the 'Receipts', 'Needs Category', 'Set Aside' rows in the Months' rows needs
to adjust automatically to only display the number of the Receipts, Expenses
that need category, and expenses set aside under the card chosen in filter by
user in that month."* Asked whether an account includes its subcards: no,
**2838 counts only its own**, each subcard its own.

**Backend:** ships in the same PR. `n_set_aside` is new on
`GET /api/cards/status` (`cards[].receipt_months[]`, `no_card.months[]`);
`n_expenses` and `n_needs_category` were already on those entries.

````markdown
Two changes on the months list (`/months`, `MonthsHome`). Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## 1. The card strip loses its numbers

In `CardStrip` (`src/components/CardsStatusScreen.tsx`), remove the count badge from every chip: the top-row cards, the subcard row, the cards behind "Show {n} cards with nothing loaded", and the No card chip. That means removing `countBadge`, both places it is rendered, and the `noCardCount` prop; `MonthsHome` stops passing `noCardCount`. Remove the i18n keys `cardStrip.count.one` and `cardStrip.count.many` from the EN dictionary and the PT mirror in `src/lib/i18n.tsx`. Nothing else on the strip changes: the chip text, the amber "not in Settings" dot, the chevrons, the nesting, the disclosure, the order.

## 2. The table shows the picked card's figures

`GET /api/cards/status` (the `["cards", "status"]` query `MonthsHome` already runs) carries, per card and per month, the three figures the table shows:

- `cards[].receipt_months[]` entries: `run_id`, `n_expenses`, `n_needs_category`, `n_set_aside`
- `no_card.months[]` entries: the same fields

Add `n_needs_category?: number;` and `n_set_aside?: number;` to `CardReceiptMonth` in `src/lib/api.ts`, and `n_set_aside?: number;` to `CardsStatusResponse.no_card`.

In `BatchRow`, the three cells read:

| Filter | Receipts | Needs category | Set aside |
|---|---|---|---|
| All (nothing picked) | `summary.n_expenses` (as today) | `summary.n_uncategorized` (as today) | `summary.n_set_aside` (as today) |
| A card | that card's `receipt_months[]` entry whose `run_id` equals the row's `batch_id`: `n_expenses` | its `n_needs_category` | its `n_set_aside` |
| No card | the `no_card.months[]` entry for the row's `batch_id`: `n_expenses` | its `n_needs_category` | its `n_set_aside` |

- A card's figures are its OWN. Picking 2838 shows 2838's receipts only, not those of its subcards 3876, 3645 and 0340; picking a subcard shows that subcard's. Never add a subcard's entry to its account's.
- A month listed for a card with no `receipt_months[]` entry for it (the card has charges or a statement there but no receipts) shows 0, 0 and an empty Set aside cell.
- Missing numbers read as 0. Keep today's styling: Needs category amber when above 0, muted at 0; Set aside empty at 0.
- Pass the picked card's month entry (or the No card one) from `MonthsHome` into `BatchRow`; do not fetch anything new.
- Which months are listed does not change, nor their order, the Statement and Created columns, the row menu, or where a row opens (`/expenses/{id}` with the card still carried in `?card=`).

## 3. Captions (EN dictionary and the PT mirror in `src/lib/i18n.tsx`)

The two captions under the strip said the figures were each month's totals, which is no longer true. New values, same keys (`{cards}` stays the link to `/cards`):

| Key | EN | PT-BR |
|---|---|---|
| `months.cardFilter.caption` | Receipts, Needs category and Set aside count only this card's own, per month. Open a month to see its rows, or {cards} for this card across all months. | Recibos, Sem categoria e Separados contam só os deste cartão, por mês. Abra um mês para ver as linhas, ou {cards} para este cartão em todos os meses. |
| `months.cardFilter.captionNoCard` | Receipts, Needs category and Set aside count only receipts with no card, per month. Open a month to see them. | Recibos, Sem categoria e Separados contam só os recibos sem cartão, por mês. Abra um mês para vê-los. |

## 4. Do not change

The All view of the table, the months themselves, the Cards page (`/cards`), the card tabs inside a month, and any backend call beyond reading the fields above.

## 5. How to check it worked

- `/months`: no chip in the strip carries a number, No card included; "All" as before.
- Pick 3876 (a subcard): each month's Needs category equals the NEEDS CATEGORY box on that month's page opened with 3876 picked.
- Pick 2838: its figures leave out 3876's, 3645's and 0340's receipts.
- For any one month, the figures under each top-level card, each subcard and No card add up to that month's row under All, column by column.
- Switch to PT: the caption reads "Recibos, Sem categoria e Separados contam só os deste cartão, por mês. …".
````
