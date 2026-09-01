# Lovable prompt: Card strip, group by card number and separate tender words

**APPLIED. Verified 2026-09-01 in the published bundle (`brisken-reconcile-dash.lovable.app`): "Card ending" and "No card number on the receipt" are both present.**

Paste into `brisken-expense-review` (production
`brisken-reconcile-dash.lovable.app`). No backend change; this reshapes
how the existing `card_review.unresolved_hints[]` data is displayed and
submitted. Touches only `CardReviewStrip` in
`src/components/ExpensesReviewGrid.tsx` (line 2446) plus i18n
(`src/lib/i18n.tsx`, EN keys around 790-803 and the PT mirror around
1880-1893; every new string ships in BOTH).

## Why

Operator, 2026-08-28: "there should only be clearly defined cards listed
and not stuff like 'cartao de credito', we want the card number." On the
April month the strip showed 26 receipts across nine-plus rows: five of
those rows were the SAME card, 0340, under five spellings
(`***********0340`, `VISA - ******0340`, `****0340`, `*****0340`,
`CARTAO ***********0340`), and beside them tender phrases (`CARTAO TEF`,
`COMPRA CREDITO VISA`, `Cartao Credito 30 Dias`, `Cartao de Credito`)
were presented exactly like cards. The assign endpoint already accepts a
LIST of assignments, so one click can assign every spelling of a card at
once.

## 1. Partition the rows

Split `unresolved_hints` (type `CardReviewUnresolvedHint {hint, n_rows,
documents?, generic?}`, api.ts:1397-1402) into two sections. Precedence
matters:

- Section 2 FIRST: every hint with `generic === true`, regardless of
  digits. Header EN "No card number on the receipt" / PT "Sem número de
  cartão no recibo", with one shared note replacing the current per-row
  generic note (key `expx.cards.strip.generic`): EN "Assignments here
  apply to this month only; the tool will not remember them." /
  PT "A atribuição vale só para este mês; a ferramenta não vai
  memorizá-la."
- Section 1: of the REMAINING hints, those containing a run of 3 or more
  digits, grouped (next section). Header EN "Cards by number" /
  PT "Cartões por número".
- Everything else (non-generic, no 3+ digit run, e.g. `CARTAO TEF`
  today) keeps today's ungrouped single-row rendering, WITHOUT the
  this-month-only note: assigning such a hint with the learn switch on
  IS remembered as an exact alias, so the note would be false there.

## 2. Group section 1 by card number

- Grouping key: the LAST run of 3+ digits in the hint (regex
  `/(\d{3,})(?!.*\d)/`), reduced to its last 4 characters. The 3-digit
  floor matches the backend's own card-digit rules; it also stops "30"
  in `Cartao Credito 30 Dias` from becoming an invented "Card ending
  30".
- Grouped row: EN "Card ending {digits}" / PT "Cartão final {digits}",
  then "{n} receipts, {m} spellings" / PT "{n} recibos, {m} grafias"
  (n = sum of the members' `n_rows`, m = member count). Show the digits
  exactly as printed in the hints; keep a leading zero.
- A "Show spellings" / PT "Mostrar grafias" toggle expands the member
  list, each spelling with its own count, and a small per-spelling
  Assign action as an escape hatch for the rare case where one spelling
  belongs to a different card.
- ONE assign select and one Assign button per group. On assign, call the
  existing mutation (`assignBatchCards`, api.ts:1439-1444, POST
  `/api/expense-batches/{batchId}/cards`) with `assignments` = one
  `{hint, card}` entry PER MEMBER SPELLING, in a single request; the
  backend loops the list with no count cap. The "New card..." option
  (key `expx.cards.strip.newCard`) and the "Remember for future months"
  switch (key `expx.cards.strip.learn`; it is a Switch, not a checkbox)
  keep working exactly as today and apply to the whole group.

## 3. What to expect from today's data (so verification is honest)

With the currently deployed backend, only `Cartao de Credito` comes back
`generic: true`; `CARTAO TEF` and `COMPRA CREDITO VISA` are
non-generic and digit-less, and `Cartao Credito 30 Dias` prints only the
digits "30". So on the April batch this prompt yields: one grouped
"Card ending 0340" row (11 receipts, 5 spellings), `Cartao de Credito`
under "No card number on the receipt", and the other three phrases as
ungrouped single rows. A small backend vocabulary round (already logged)
will later move those three under the no-card-number section; nothing in
this prompt needs to change when it ships.

## 4. Defensive rendering

Per the api-contract rules: guard every mapped element
(`typeof h.hint === "string"`), tolerate absent `documents` and absent
`generic` (absent means false), and if the grouping produces nothing,
the strip must render exactly as it does today.

## Do not

- Do not change what a single assignment sends per hint; only batch
  them.
- Do not normalize digits beyond display grouping: no stripping leading
  zeros in what is shown, no invented card identities. The backend stays
  the authority on card resolution and learning.
- Do not remove or reorder the existing resolved footer
  (`expx.cards.strip.resolved`).
- Patch EN and PT in the same edit. No em-dashes in UI copy.

## Verify after publish

1. Open the April demo batch: the five 0340 spellings render as one
   "Card ending 0340" row counting 11 receipts, expandable to the five
   spellings.
2. `Cartao de Credito` sits under "No card number on the receipt" with
   the this-month-only note; `CARTAO TEF`, `COMPRA CREDITO VISA` and
   `Cartao Credito 30 Dias` remain ungrouped single rows (expected until
   the backend vocabulary round ships).
3. After the 0340 card exists in Settings, assign the group to it: all
   five spellings resolve in one click and the resolved footer updates.
4. Switch to PT and re-check all new strings.
