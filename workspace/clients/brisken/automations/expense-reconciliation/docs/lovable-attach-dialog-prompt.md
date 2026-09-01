# Lovable prompt: Attach statement dialog, pick the card instead of typing it

**APPLIED. Verified 2026-09-01 in the published bundle (`brisken-reconcile-dash.lovable.app`): `months.attach.cardOther` = "Other account..." and `months.attach.cardFilled` are both in the i18n dictionary.**

Paste into the `brisken-expense-review` Lovable project (production
`brisken-reconcile-dash.lovable.app`). No backend change is needed; every
field this prompt uses already exists in the API. This touches the Attach
bank statement dialog (`AttachStatementDialog` in
`src/components/ExpensesReviewGrid.tsx`, line 2053; its submit() builds
the FormData at lines 2124-2132) plus i18n strings in `src/lib/i18n.tsx`
(EN dictionary and the PT mirror; every new string ships in BOTH).

## Why

Operator, 2026-08-28, testing the April month: the dialog asked for a
"Card account id" with no guidance, and it was filled with "Brisken" and
currency "BRL". The account id is a free-text label the tool cannot
validate, and a wrong card currency silently ruins the month: the matcher
treats every statement amount as that currency, so a BRL entry against a
USD card reconciles near zero. The dialog's own help text says "choose
the account" but there is nothing to choose from, even though the app
already knows the cards (GET /api/cards).

## 1. Replace the free-text "Card account id" with a card picker

- Fetch the known cards with the same query the card strip already uses
  (queryKey `["cards"]`, `getCards` in `src/lib/api.ts:689`). The
  response is `{cards[], entity_options[], seen_undefined[]}`; card
  objects carry `key`, `label`, `label_pt`, `digits`, `entity`,
  `currency`, `active`, `source`.
- Render a Select labeled EN "Card" / PT "Cartão". Option text: `label`
  (backend guarantees it is non-empty), preferring `label_pt` when the
  UI language is PT, with the digits appended when present, e.g.
  "Corporate card · 2838". Hide cards with `active === false`. Last
  option: EN "Other account…" / PT "Outra conta…".
- On submit with a known card selected, in `submit()`
  (ExpensesReviewGrid.tsx:2124-2132): send `account_id` = the card's
  `key`, and `account_card_currency` = the card's `currency` when it has
  one (otherwise send nothing; the server defaults to USD). When and
  only when the card's `source === "preset"`, ALSO append
  `card_key` = the card's `key`. Do not send anything else new. The
  backend resolves the entity from the live card registry by matching
  the digits in the account id, which is the path that already works.
- Adjust the guard at ExpensesReviewGrid.tsx:2123 (currently
  `if (!statement || !accountId.trim()) return;`) so that in known-card
  mode it validates the picker selection instead of the free-text value.
- Muted helper while a known card is chosen: EN "Account id and currency
  are filled from this card." / PT "O id da conta e a moeda são
  preenchidos a partir deste cartão."

## 2. The "Other account…" mode

- Shows the existing free-text input and the currency input, as today.
- Prefill the currency input VALUE with "USD" (today it is empty with a
  "USD" placeholder; empty already falls back to USD server-side, but
  showing the real default removes the guesswork). Keep the
  uppercase-on-input behavior.
- Currency helper line: EN "The currency the card settles in. This is
  not the receipts' currency: receipts in other currencies are converted
  with the FX reference rates in Settings." / PT "A moeda em que o
  cartão é cobrado. Não é a moeda dos recibos: recibos em outras moedas
  são convertidos pelas taxas de câmbio em Configurações."
- Disable submit until the free-text name is non-empty, so the backend's
  silent fallback name "card" is never used by accident.

## 3. Fix the dialog help text

`months.attach.help` (EN i18n.tsx:1074, PT mirror :2160) currently says
"Upload the card statement, choose the account, and start
reconciliation. Expenses become read-only after this." The second
sentence is no longer true; the month stays open and re-matches itself
when receipts arrive later. Replace with:

EN "Upload the card statement, pick the card, and start reconciliation.
Receipts can still be added afterwards; the month re-matches itself."
PT "Envie o extrato do cartão, escolha o cartão e inicie a conciliação.
Recibos ainda podem ser adicionados depois; o mês se concilia sozinho."

(PT uses "conciliação", matching the dictionary's existing vocabulary;
do not introduce "reconciliação".)

## 4. Fix the dead column-mapping retry (real bug, same dialog)

When the first attach returns a 400 with the file's headers, the dialog
lets the operator pick which column is which and retries. Today that
retry appends FormData keys `map_date`, `map_description`, `map_amount`,
`map_currency` (ExpensesReviewGrid.tsx:2128-2132), but the backend
accepts `map_transaction_date`, `map_vendor`, `map_amount`,
`map_transaction_currency`; only `map_amount` matches, so the operator's
date, description, and currency picks are silently dropped. Rename the
appended keys: `map_date` becomes `map_transaction_date`,
`map_description` becomes `map_vendor`, `map_currency` becomes
`map_transaction_currency`; `map_amount` stays. UI labels do not change.

## Do not

- Do not touch the classic New-reconciliation screen.
- Do not change `attachStatement` in api.ts (it just POSTs the form the
  dialog builds); all changes live in the dialog's submit().
- Do not hardcode any card list; it must come from the cards query.
- No em-dashes in any UI copy.
- Patch the EN and PT dictionaries in the same edit.

## Verify after publish

1. Open a month, click Attach bank statement: the Card select lists the
   active cards from Settings plus "Other account…".
2. Pick a known card and attach a statement: the job runs, and the run
   header shows the card's key as its account id with the card's
   currency.
3. Pick Other account: free text plus currency prefilled "USD"; submit
   stays disabled while the name is empty.
4. Attach a CSV with unusual headers, pick the columns on the retry
   panel: dates and vendors now come through (before this fix they were
   silently dropped).
5. Switch the UI to PT and re-check every new string.
