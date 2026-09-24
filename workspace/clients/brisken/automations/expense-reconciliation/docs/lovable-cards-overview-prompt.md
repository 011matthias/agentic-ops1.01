# Lovable prompt: /cards becomes an overview, not a door into the months (item 192)

**NOT PASTED.** Owner, 2026-09-24, on the Cards page: *"this should just be an
overview and not another gate to inside the months. we can insert more
relevant data though."* Then: *"alright then do the backend work and hand me
the lovable prompt"*.

**Backend: shipped first (PR #1312, Fly `45d4c494`).** `GET /api/cards/status`
now counts receipts per card: how many found no charge, and which months hold
receipts on a card that has no statement there. Every value in the check table
was read off the deployed endpoint the same day.

````markdown
Turn the Cards page (`/cards`) into an overview: one table, every card, and what is still open on each. It stops being a way into the months; the months list's card filter (`/months?card=`) is that now. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## 1. Take out the door into the months

- Remove the card chip strip from `/cards`. Keep the `CardStrip` component exactly as it is: the months list (`/months`) uses it, including any `nestSubcards` behaviour it has.
- Remove the selected-card panel (the card's header line and its per-month table with month links) and the state that selects a card.
- Rows are no longer clickable: no `cursor-pointer`, no row `onClick`. Nothing on this page navigates into a month. The "not in your card list" badge keeps its link to Settings, Cards, because that edits the card.
- Subtitle, new text: "Every card across every month: what is still open on each."

## 2. The data

`GET /api/cards/status` (the `["cards", "status"]` query) has new fields:

- `cards[].n_receipts`: receipts on the card, all months.
- `cards[].n_receipts_without_charge`: of those, the ones no charge holds.
- `cards[].n_receipts_no_statement`: of those, the ones in months where the card has no statement (waiting for a statement, not unmatched).
- `cards[].receipt_months[]` entries add `n_without_charge` and `statement` (true when the card has a statement in that month).
- `no_card.n_without_charge`, beside the existing `no_card.n_expenses`.

Already there and used below: `n_refunds`, `n_statements`, `statements[].file`, `never_loaded`, `period_start`, `period_end`, `unreconciled_by_ccy`.

## 3. The table

One row per card, then one **No card** row last. Columns in this order:

| Column | Content |
|---|---|
| Card | As today: digits, the not-in-list badge, label · entity |
| Statements cover | `period_start` to `period_end` as today (this is the Period column renamed). Under it, in small muted text, "No statement for: {months}" listing the labels of the card's `receipt_months` with `statement` false, newest first. When the card has no statement at all (`n_statements` 0), the first line reads "No statement loaded" instead of dates |
| Charges | `n_transactions` |
| Matched | `n_reconciled` |
| Needs review | `n_review` |
| No receipt | `n_unmatched_tx`, amber when > 0 (as today) |
| Receipts | `n_receipts` |
| Without a charge | `n_receipts_without_charge`, amber when > 0. Tooltip: "Receipts on this card that no charge holds yet." plus, when `n_receipts_no_statement` > 0, " {n} of them are in months with no statement for this card." |
| Credits | `n_refunds` |
| Statements | `n_statements` as a number, the file names (`statements[].file`) as its tooltip; "-" when 0 |
| Still open | As today |

"Newest first" for the month labels: sort them the way the months list sorts months (`monthSortKey` in `MonthsHome.tsx`, which parses the label and falls back to `created_at`). Move that helper to a shared file and use it in both places; do not take the order from the array.

**The No card row:** "No card" (the existing `cardStrip.noCard` text, with its tooltip `cardStrip.noCard.tip`), Receipts = `no_card.n_expenses`, Without a charge = `no_card.n_without_charge`, every other cell "-".

**Sort:** cards with the most open work first, open work being `n_unmatched_tx + n_review + n_receipts_without_charge`, largest first; ties keep the order the API returns. The No card row stays last.

**The fold:** "Show {n} cards with nothing loaded" now holds only cards with `never_loaded` true AND `n_receipts` 0. A card with receipts and no statement (9693 today) is a normal row in the table, because receipts are waiting on it.

The footnote under the table stays the payload's `note`, rendered as today.

## 4. Strings (EN dictionary and the PT mirror in `src/lib/i18n.tsx`)

| Key | EN | PT-BR |
|---|---|---|
| `cardsPage.subtitle` (changed) | Every card across every month: what is still open on each. | Todos os cartões em todos os meses: o que ainda está em aberto em cada um. |
| `cardsPage.col.period` (changed) | Statements cover | Extratos cobrem |
| `cardsPage.col.receipts` (new) | Receipts | Recibos |
| `cardsPage.col.noCharge` (new) | Without a charge | Sem lançamento |
| `cardsPage.col.credits` (new) | Credits | Créditos |
| `cardsPage.noStatementFor` (new) | No statement for: {months} | Sem extrato para: {months} |
| `cardsPage.noStatementEver` (new) | No statement loaded | Nenhum extrato carregado |
| `cardsPage.noCharge.tip` (new) | Receipts on this card that no charge holds yet. | Recibos deste cartão que nenhum lançamento cobre ainda. |
| `cardsPage.noCharge.waiting` (new) | {n} of them are in months with no statement for this card. | {n} deles estão em meses sem extrato para este cartão. |

Drop `cardsPage.col.month`, `cardsPage.months`, `cardsPage.neverLoaded` and `cardsPage.trip` if nothing references them any more.

## 5. Do not change

`/months` and the `CardStrip` component (§1). The months inside (`/expenses/{id}`, `/runs/{id}`). Any backend call beyond reading the new fields. No new route, no new nav entry.

## 6. How to check it worked

Live numbers, read 2026-09-24 off the deployed endpoint.

| Drive | Expect |
|---|---|
| Open `/cards` | No chip strip, no card panel; clicking a row does nothing; subtitle "Every card across every month: what is still open on each." |
| Row order | 2838, 3645, 3876, 0340, 9693, 1176, 4700 ●, then No card |
| 2838 | Statements cover "Mar 31, 2026 – Aug 30, 2026" and "No statement for: September 2026, June 2026, May 2026"; Charges 111, Matched 25, Needs review 9, No receipt 75, Receipts 41, Without a charge 12, Credits 2, Statements 3, Still open USD 11,011.31 |
| 3645 | "No statement for: September 2026, June 2026"; Charges 85, No receipt 77, Receipts 14, Without a charge 6, Statements 3, Still open USD 4,811.16 |
| 3876 | "No statement for: September 2026, June 2026, May 2026, January 2026"; Charges 85, Matched 47, Needs review 12, No receipt 26, Receipts 95, Without a charge 39 with tooltip ending "32 of them are in months with no statement for this card.", Still open USD 365.27 |
| 9693 | In the table, not behind the fold: "No statement loaded", "No statement for: September 2026, August 2026"; Charges 0, Receipts 16, Without a charge 16, Statements "-" |
| 1176 | "No statement for: September 2026"; Receipts 8, Without a charge 8, Credits 2, Still open USD 36.00 |
| 4700 ● | Receipts 0, Without a charge 0, no "No statement for" line |
| No card row | Receipts 72, Without a charge 62, every other cell "-" |
| The fold | "Show 3 cards with nothing loaded"; opening it shows 0113, 6013, 8311 |
| Statements cell of 2838 | "3", tooltip listing August2026.xlsx, July2026.xlsx and the April CSV |
| Switch to PT | Column "Sem lançamento", "Sem extrato para: …" |
````
