# Lovable prompt: say when a receipt's card comes from the charge it is matched with (item 111)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend: `expenses[].card_source: "settled_charge"`
> on `GET /api/expense-batches/{id}` (item 111). Paste after that backend is deployed.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change in `src/components/ExpensesReviewGrid.tsx` (the card cell) and two new strings. No API type change: `card_source?: string` already exists on the expense row. Render defensively: a row without the new value renders exactly as today.

## Why

A receipt that prints no card number ("VISA", "Link", or nothing) asked Criss for a company and a person even when the matching page had already paired it with a bank charge, and that charge's card names both. The backend now gives such a receipt the card of the charge it is matched with, so its company and person fill in and it leaves the "No company or person" box. The row says `card_source: "settled_charge"`. Today the grid shows the card chip for it but no line saying where the card came from, and no way to change it, because `CardFixCell` renders its controls only for `none`, `override`, `learned` and `hint`.

## 1. The card cell (`CardFixCell`)

- When `row.card_source === "settled_charge"`, treat the row exactly like `hint`: render the small ghost button `Button size="sm" variant="ghost" className="mt-1 h-6 px-1.5 text-[11px] text-muted-foreground"` labelled `t("expx.cardFix.change")`, which reveals the same card `Select` (value `row.card?.key ?? ""`, the active cards from `getCards()`, saving `card_key` through the row's field saver). Picking a card there makes it `override`, as on every other row.
- After the `CardChip`, where the muted source line renders for `override` and `learned` (`text-[10px] text-muted-foreground`), also render it for `settled_charge` with `t("expx.cardFix.source.settled_charge")`.
- A row with `row.private === true` still shows no card control (the backend never gives a private row this source).
- `none`, `override`, `learned` and `hint` keep rendering exactly as today.

## 2. Do not change

`CardChip`, `CardEndingNote`, the entity Select, `EntitySourceLabel`, `PaidThroughCell`, the private-expense controls (the row already carries `can_mark_private: false`, so "Paid with a private card" stays hidden on it), the box tiles and their counts, the card-review strip.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.cardFix.source.settled_charge` | Card from the statement charge this receipt is matched with | Cartão da cobrança do extrato que corresponde a este recibo |
| `expx.cardFix.settledHint` | Change the card only if the match itself is right and the statement names the wrong card; otherwise reject the match on the matching page. | Troque o cartão só se a correspondência estiver certa e o extrato indicar o cartão errado; caso contrário, rejeite a correspondência na página de comparação. |

Render `expx.cardFix.settledHint` as the `title` of the "Change card" button on a `settled_charge` row only.

## Checking it landed

Re-read `GET /api/expense-batches/50622baec444` (July) and `.../074a7b8905d7` (August) first and note which rows carry `card_source: "settled_charge"` and the `summary.n_needs_company_or_person` count.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit): `settled_charge` and `expx.cardFix.source.settled_charge` in the expenses chunk, `expx.cardFix.settledHint` in `chunk-i18n`.
2. July Expenses (`/expenses/50622baec444`): a row the API marks `settled_charge` (for example `0029__2026-07-13__ZE__Aposto_Karlsruhe__ZE_7150901.jpg`, card 2838) shows its card chip, the line "Card from the statement charge this receipt is matched with", and "Change card". The "No company or person" tile shows the API's count.
3. Hover "Change card" on that row: the tooltip is the settledHint sentence. Click it, the card list opens; close with Escape and pick nothing (a pick is a write on Criss's month).
4. August Expenses (`/expenses/074a7b8905d7`): the Invoice-DZ9BH3VA-0036 row shows card 3645 with the same line.
5. PT: "Cartão da cobrança do extrato que corresponde a este recibo".
6. Network: no PUT, POST, PATCH or DELETE during the drive except `POST /api/login`.
````
