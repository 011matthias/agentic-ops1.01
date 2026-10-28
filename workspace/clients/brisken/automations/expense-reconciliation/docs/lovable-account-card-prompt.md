# Lovable prompt: say when a receipt's card comes from its billing account (item 204 step 4)

> **NOT APPLIED** (see PROMPT-STATUS.md). Backend: `expenses[].card_source: "account"`
> on `GET /api/expense-batches/{id}` (item 204 step 4, owner decision D4). Paste after
> that backend is deployed.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change in `src/components/ExpensesReviewGrid.tsx` (the card cell) and two new strings. No API type change: `card_source?: string` already exists on the expense row. Render defensively: a row without the new value renders exactly as today.

## Why

Subscription invoices (Anthropic, Fireflies, Wispr, Vercel...) print an invoice number like `WWT1PNYP-0016`. The first eight characters are the billing account: one login, paid with one card at a time. Many of these invoices print no card at all, so they asked Criss for a company and a person every month. The backend now looks at the account's other invoices: when at least two of them were paid with one card (the card printed on the invoice, the statement charge, or Criss's own pick) and none with any other card, the card-less invoice takes that card, and its company and person fill in. The row says `card_source: "account"`. Today the grid shows the card chip for it but no line saying where the card came from.

## 1. The card cell (`CardFixCell`)

- When `row.card_source === "account"`, treat the row exactly like `learned`: the card chip, the small ghost "Change card" button (`t("expx.cardFix.change")`) that reveals the same card `Select` and saves `card_key` through the row's field saver (a pick makes the row `override`, as everywhere else), and the private-card option, which the backend keeps open on this row (`can_mark_private: true`; read the flag, do not re-derive it).
- After the `CardChip`, where the muted source line renders for `override`, `learned` and `settled_charge` (`text-[10px] text-muted-foreground`), also render it for `account` with `t("expx.cardFix.source.account")`, and give that line the `title` `t("expx.cardFix.accountHint")`.
- `none`, `override`, `learned`, `hint`, `settled_charge` and `merchant` keep rendering exactly as today.

## 2. Do not change

`CardChip`, `CardEndingNote`, the entity Select, `EntitySourceLabel`, `PaidThroughCell`, the private-expense controls and their rules, the box tiles and their counts, the card-review strip, the card tabs (the backend already files the row under its card in `expenses[].card_section`).

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.cardFix.source.account` | Card this billing account has always been paid with | Cartão com que esta conta de cobrança sempre foi paga |
| `expx.cardFix.accountHint` | At least two other invoices of this billing account were paid with this card, and none with another. Change the card if this one was paid differently. | Pelo menos duas outras faturas desta conta de cobrança foram pagas com este cartão, e nenhuma com outro. Troque o cartão se esta foi paga de outra forma. |

## Checking it landed

Re-read `GET /api/expense-batches/86929f2a909a` (May 2026) first and note which rows carry `card_source: "account"`.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit): `expx.cardFix.source.account` in the expenses chunk, `expx.cardFix.accountHint` in `chunk-i18n`.
2. May Expenses (`/expenses/86929f2a909a`): the Anthropic invoice `WWT1PNYP0014` (99.95 EUR) shows card 3876, Corporate Services, Nicolas Neumann, the line "Card this billing account has always been paid with", and "Change card". Hovering the line shows the accountHint sentence.
3. Same page: the two Fireflies invoices and the Wispr invoice show the same line; the Lovable invoice `HMVWDWIL0023` does NOT (that account is paid with three different cards, so it stays blank).
4. Click "Change card" on one of them: the card list opens; close with Escape and pick nothing (a pick is a write on Criss's month).
5. PT: "Cartão com que esta conta de cobrança sempre foi paga".
6. Network: no PUT, POST, PATCH or DELETE during the drive except `POST /api/login`.
````
