# Lovable prompt: the card filter leaves the month, the selection carries in (item 190)

**PASTED, NOT PUBLISHED** (Lovable repo `c27c7fd`, 2026-09-24 13:14Z; the
live bundle still serves the old build). Owner, 2026-09-24: *"i think the logical next step is removing
the card filter from inside the months since its outside now."* and *"when
using this filter, and a month is clicked on by user he should then only see
data from the card that he selected in the filter. that is part of extracting
the filter from inside the month because we need to maintain the
functionality, but layer it differently"*.

**Backend: shipped first (PR #1293).** `GET /api/cards/status` now carries
`cards[].receipt_months[]` and `no_card`, so the filter on `/months` can offer
a month that holds only receipts on a card (September, May and June have no
statement yet) and the months that hold receipts with no card. Every value in
the check table was read live: the in-month strings off a cold Chrome drive of
August, the month lists off the deployed endpoint (Fly, commit `93c69551`).

````markdown
Take the card filter out of the month and let the one on the months list carry into it. Nothing the in-month card strip does today is lost: the card now comes from outside. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## Why

The months list (`/months`) has a card filter now, and every month still has its own card strip on both of its pages: Expenses (`/expenses/{id}`: `All · 3645 5 · 3876 30 · 2838 10 · 1176 1 · 9693 2 · No card 2`) and Matching (`/runs/{id}`: `All · 3645 40 · 3876 37 · 2838 34 · 1176 3 · 9693 0 · No card`). Two filters for one question. The one outside wins, and a month opened from it shows only that card.

## 1. The data

`GET /api/cards/status` (the `["cards", "status"]` query `/months` and `/cards` already share) has two new fields:

- `cards[].receipt_months[]`: the months holding receipts on that card, each `{run_id, label, batch_type, n_expenses}`. This is separate from `cards[].months[]`, which stays the months with a charge or a statement.
- `no_card`: `{months: [{run_id, label, batch_type, n_expenses}], n_expenses}`, the months holding receipts that are on no card.

Inside a month nothing new is needed. The card keys are one space across the app: `cards[].key` from `/api/cards/status` is the same string as the month's `card_sections[].key` and as the `card_section` every row already carries (`expenses[].card_section` on `GET /api/expense-batches/{id}`; `rows[]`, `unmatched_receipts[]`, `copies_set_aside[]`, `assignable_receipts[]` `.card_section` on `GET /api/runs/{id}`). `""` is no card. Example keys: `card-1176`, `3876`, `card-2838`, `digits:4700`.

## 2. The selection lives in the URL

`?card=<key>` on `/months`, `/expenses/{id}` and `/runs/{id}`. No card is `?card=none`. All is no parameter. Build and read it with `URLSearchParams`, so a key like `digits:4700` is encoded (`digits%3A4700`).

- Picking a chip on `/months` sets the parameter with a history **replace**, so chip clicks do not pile up behind the back button.
- Opening a month from the filtered list goes to `/expenses/{run_id}?card=<key>`.
- The month's two tab links (`Expenses …` and `Matching …`) keep the parameter, so the scope follows between the tabs as it does today.
- A refresh, the back button and a pasted link all keep the scope.

The month no longer keeps its own selection. Stop reading and writing the localStorage key `brisken.month.cardTab.v1:{run_id}`, and delete that month's entry when the month loads.

## 3. The months list

**The strip.** Unchanged, plus one chip: **No card**, after the last card chip and before the "Show {n} cards with nothing loaded" disclosure. No count on it (the strip's counts are charges, and receipts on no card have none). Its tooltip is the existing "Receipts the tool could not place on a card".

**Which months a pick lists.** A month is listed when its `run_id` is in the card's `months[]` OR its `receipt_months[]`. For No card, the months in `no_card.months[]`. Keep the order the page already sorts months in; do not take the order from those arrays (they sort by charge dates, so months with no statement come last there). A card with nothing anywhere keeps the existing empty line, reworded (see strings).

The cards behind "Show {n} cards with nothing loaded" stay there: that disclosure is about statements, and 9693 still has none. Picking 9693 now lists the months holding its receipts.

**The caption** under the strip changes, because what it describes changed. With a card picked: "Figures are each month's totals. Open a month to see only this card's rows, or Cards for this card's own numbers." ("Cards" stays the link to `/cards`.) With No card picked: "Figures are each month's totals. Open a month to see only its receipts with no card." Absent under All, as today.

The columns do not change. They stay the whole month's numbers.

## 4. Inside a month

**Remove the card strip from both tabs:** the chip row, its "Show {n} cards with nothing this month" control and its "+ {n} cards with nothing this month" text. If the Matching page still renders the OLDER card chip row in any state (label "Card", an "All cards" chip, one chip per card with a breakdown line), remove that too and drop the `card` field from `brisken.workbench.filters.v2:{run_id}`; the URL scope replaces both.

**With no `?card=`** the month is exactly what it is today, minus the strip.

**With `?card=<key>`**, one scope line sits where the strip was, on both tabs:

- a card: "Showing card {card} · Show all cards", where {card} is the text the `/months` chip shows for that key (its digits, plus the same not-in-Settings marker `●` when the card is not in Settings). Take it from the `["cards", "status"]` query by key.
- No card: "Showing receipts with no card · Show all cards".

"Show all cards" drops the parameter and stays on the same tab.

Directly under the scope line: the card's statement line and "Add another statement for this card", **moved as they are** from under the strip, fed by the month's `card_sections[]` entry for the key, exactly as the strip feeds them today. On Expenses the line opens with the expense count and totals; on Matching it does not. "Add another statement for this card" opens the same Attach bank statement dialog with the card preselected, as it does now; it has no other route in the app, so it must survive. The account lines ("This account and its cards", "on this card alone: …", "Statement on {account}") move with it unchanged; no card in Settings has a parent today, so they have no live case.

**What scopes to the card** (keep every rule the strip uses today, only the source of the key changes):

- the rows: the Expenses grid, and on Matching the charge rows, receipts without a charge, copies set aside and the receipts offered for a hand match, all by `card_section`;
- the boxes on Expenses (EXPENSES, CATEGORIZED, NEEDS CATEGORY, READY, TOTALS, NO COMPANY OR PERSON), which already scope today;
- the two tab badges: `Expenses {card_sections[key].n_expenses}` and `Matching {card_sections[key].n_charges} charges`;
- the Reconciliation line on Expenses: the same five counts it shows now, taken over the selected card's rows only. They are the numbers the Matching tab's section headings already show for that card (Matched, Needs review, Charges without a receipt, Receipts without a charge, Credits on the statement);
- the "{n} cards have receipts but no charges on a statement" notice: show only the selected card's line, and hide the notice when the selected card is not in it.

**What stays the whole month's:** Last updated / Last matched; the header actions (Add receipts, Add expense, Save corrections to memory, Add a statement, Download report (PDF), Download CSV); the statements list; the readiness line on Matching ("Not complete · …"), because it gates the month's sign-off; the "Review … receipts matched to … cards" panel.

**Nothing on the card in this month.** A pasted link can scope a month where the key has no `card_sections[]` entry and no row. Show one line instead of the page body: "Nothing on card {card} in {month label} · Show all cards" (No card: "No receipts without a card in {month label} · Show all cards"). A key that has a section but no expense rows (4700 in April has 2 charges and 0 receipts) keeps today's "No expenses on this card this month." on the Expenses tab.

A month with fewer than two cards returns `card_sections: []`. Filter its rows by `card_section` all the same and show the scope line without the statement line.

## 5. Strings (EN dictionary and the PT mirror in `src/lib/i18n.tsx`)

**Renamed, text unchanged** (the chips `/months` and `/cards` share): `cardTabs.all` → `cardStrip.all`, `cardTabs.aria` → `cardStrip.aria`, `cardTabs.noCard` → `cardStrip.noCard`, `cardTabs.noCard.tip` → `cardStrip.noCard.tip`.

**Renamed, text unchanged** (the statement line, now under the scope line): every other `cardTabs.*` key except the two dropped below becomes `cardScope.*` with the same suffix: `group`, `expenses.one`, `expenses.many`, `statementOnAccount`, `statement.loaded`, `statement.notRecorded`, `statement.notRecorded.tip` (now the tooltip on "Statement not recorded" in the line), `statement.notLoaded`, `period`, `charges.one`, `charges.many`, `matched`, `open`, `openNothing`, `booked`, `receipts.one`, `receipts.many`, `receiptsNoCharge`, `ownLine`, `addStatement.forCard`, `addStatement.another`, `emptyExpenses`.

**Dropped** (chip-only, the chips are gone): `cardTabs.under`, `cardTabs.subcards`, `wb.filter.card.empty`. Then drop any other `wb.filter.card*` key that nothing references any more. When done, no `cardTabs.` key remains anywhere.

**New and changed:**

| Key | EN | PT-BR |
|---|---|---|
| `cardScope.showing` (new) | Showing card {card} | Mostrando o cartão {card} |
| `cardScope.showingNoCard` (new) | Showing receipts with no card | Mostrando recibos sem cartão |
| `cardScope.showAll` (new) | Show all cards | Mostrar todos os cartões |
| `cardScope.nothing` (new) | Nothing on card {card} in {month} | Nada no cartão {card} em {month} |
| `cardScope.nothingNoCard` (new) | No receipts without a card in {month} | Nenhum recibo sem cartão em {month} |
| `months.cardFilter.caption` (changed) | Figures are each month's totals. Open a month to see only this card's rows, or {cards} for this card's own numbers. | Os números são totais de cada mês. Abra um mês para ver só as linhas deste cartão, ou {cards} para os números deste cartão. |
| `months.cardFilter.captionNoCard` (new) | Figures are each month's totals. Open a month to see only its receipts with no card. | Os números são totais de cada mês. Abra um mês para ver só os recibos sem cartão. |
| `months.cardFilter.empty` (changed) | No month has a charge, a statement or a receipt on this card. | Nenhum mês tem cobrança, extrato ou recibo neste cartão. |

## 6. Do not change

`/cards` (its strip only picks up the renamed keys). The months list's columns, sort order and badges. The Attach bank statement dialog. Any backend call beyond reading the two new fields. No new route and no new nav entry.

## 7. How to check it worked

Live numbers, read 2026-09-24. August is `/expenses/074a7b8905d7`, July `/expenses/50622baec444`, April `/expenses/0603bb0e6f38`.

| Drive | Expect |
|---|---|
| `/months`, pick **1176** | September and August listed; caption shown; URL `/months?card=card-1176` |
| Open **August** from that list | URL `/expenses/074a7b8905d7?card=card-1176`; no chip row; "Showing card 1176 · Show all cards"; "1 expense · USD 100.00 · Statement 20260804-statements-1176-.pdf · Jul 06, 2026 to Aug 04, 2026 · 3 charges · 0 matched · still open USD 36.00 · 2 receipts · 1 without a charge"; "Add another statement for this card"; tabs "Expenses 1" and "Matching 3 charges"; "Reconciliation: 0 matched · 0 need review · 1 charges without a receipt · 1 receipts without a charge · 2 credits"; boxes EXPENSES 1, CATEGORIZED 1, NEEDS CATEGORY 0, READY 1, TOTALS USD 100.00; no 9693 notice |
| Click **Matching** | URL `/runs/074a7b8905d7?card=card-1176`; the same line without "1 expense · USD 100.00 ·"; Receipts without a charge 1, Charges without a receipt 1, Needs review 0, Credits on the statement 2, Matched 0 |
| **Refresh**, then browser **back** twice | the scope survives the refresh; back lands on `/months?card=card-1176` with 1176 picked |
| **Show all cards** on August | no parameter, no scope line; "Expenses 50", "Matching 114 charges", "Reconciliation: 35 matched · 3 need review · 73 charges without a receipt · 12 receipts without a charge · 3 credits"; EXPENSES 50, CATEGORIZED 45, NEEDS CATEGORY 5, READY 29; the 9693 notice shown |
| `/months`, pick **4700 ●** | April only; open it: "Showing card 4700 ●", Expenses shows "No expenses on this card this month.", Matching shows its 2 charges |
| `/months`, pick **No card** | September, August, July, June, May, April; the No card caption; open August: "Showing receipts with no card · Show all cards", "2 expenses · EUR 241.80 · USD 25.00 · 2 receipts · 2 without a charge", boxes EXPENSES 2, CATEGORIZED 2, NO COMPANY OR PERSON 2; on Matching "2 receipts · 2 without a charge" |
| Paste `/expenses/50622baec444?card=card-1176` | "Nothing on card 1176 in July 2026 · Show all cards" |
| `/months`, pick **9693** (behind the disclosure) | September and August |
| `/months`, pick **3876** | September, August, July, June, May, January; open January: "Showing card 3876 · Show all cards", no statement line (January has one card), its 1 expense |
| `/months`, pick **0113** | the empty line "No month has a charge, a statement or a receipt on this card." |
````
