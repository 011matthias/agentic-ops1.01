# Lovable prompt: the private-card list (item 208), a personal card confirmed private once

> **APPLIED 2026-09-25, with Follow-up 1; Follow-up 2 (the strip pre-fill)
> NOT pasted.** Backend shipped 2026-09-25 (item 208): `settings.private_cards`,
> `expenses[].private_source`, and `private_to` on the unknown-card strip's
> assignments. First live entry the same day: 3281 -> Dirk Neumann, a
> placeholder the owner set through the Settings tab.
>
> Written against the published bundle of 2026-09-25 (43 files, transitive
> crawl; `assets/chunk-expenses._batchId-C1cysI_S.js`,
> `assets/chunk-settings-Bs6HU6LV.js`): the private badge already carries
> `expx.private.badge`, `expx.reimburse.edit` and `expx.reimburse.undo` (item
> 175 is applied), the strip carries `expx.cards.strip.assign`,
> `.learn`, `.newCard` and `.sec.numbered`, and none of `private_source`,
> `private_cards`, `private_to` appears in any chunk. `API_BASE` is
> `https://api.expenses.brisken.com`. Case 6 (item 203) shipped no prompt,
> so there is no paste order to respect.

Paste into Lovable:

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Render defensively: a row or a settings payload missing a new field renders exactly as today.

## Why

A personal card that shows up every month (the DB Fernverkehr receipts print "DEBIT-MASTERCARD ***** ***** ***** 3281") had to be confirmed as a private expense by hand, month after month, because nothing recorded whose card 3281 is. The backend now keeps a private-card list: the last four digits of a card that is NOT the company's, and the person to reimburse. A receipt printing a listed number is a private expense in every month at once, with no per-row confirmation. This prompt adds the three places where that list is seen and written: a Settings panel, an option on the unknown-card strip, and a word on the private badge.

## 1. Settings: a "Private cards" tab

Add a tab right after Cards, label `set.tabs.privateCards`. Same mechanics as the other tabs (mounted, its own unsaved-changes state, its own Save button). It edits `settings.private_cards`, which `GET /api/settings` now returns:

```json
"private_cards": {
  "3281": {"person": "Dirk Neumann", "note": "personal DKB card", "active": true}
}
```

Render one row per key: **Last 4 digits** (the key, shown as printed, a leading zero kept), **Reimburse to** (`person`, required), **Note** (`note`), **Active** (`active`, a Switch; an inactive entry stays listed but decides nothing). Add row, remove row, edit in place. Empty state `set.privateCards.empty`.

Save with `PUT /api/settings {"private_cards": {...}}`: the WHOLE map, every row, the same whole-key replace the Cards editor does. Never send `private_cards` from any other tab's save, and never send `cards` from this one. The reply carries `applied: ["private_cards"]` and the stored map; re-seed the editor from it. A key may be typed with a mask or more digits ("***3281", "0501-1462-9129"): the backend keeps the last four, so show what comes back.

A 400 comes with a `code`; show these in plain words (EN / PT below), the rest verbatim as this page already does:

| code | meaning |
|---|---|
| `private_card_digits_short` | `set.privateCards.err.digitsShort` |
| `private_card_person_required` | `set.privateCards.err.personRequired` |
| `private_card_duplicate` | `set.privateCards.err.duplicate` |
| `private_card_is_company_card` | `set.privateCards.err.companyCard`, with `card` (the company card's key) interpolated |

The Cards tab can now get the same `private_card_is_company_card` on ITS save (a company card may not carry a number the private list holds). Show it verbatim there; do not add a special case.

Help line under the table, `set.privateCards.help`.

## 2. The unknown-card strip: "Private card of..."

In the "Cards by number" section (`expx.cards.strip.sec.numbered`), on every group whose `ambiguous` is not true, the Assign select gains one more option at the end, after "New card...": `expx.cards.strip.privateOf`. Choosing it shows a text input beside the select, label `expx.cards.strip.privateOf.person`, pre-filled from the first non-empty `reimburse_to_prefill` among the group's rows (`documents[]` are the row ids; the field is on `expenses[]`). The Assign button then sends the existing mutation (`POST /api/expense-batches/{batchId}/cards`) with one entry PER MEMBER SPELLING, exactly as a card assignment does, but with `private_to` instead of `card`:

```json
{
  "assignments": [
    {"hint": "DEBIT-MASTERCARD ***** ***** ***** 3281", "private_to": "Dirk Neumann"}
  ],
  "learn": true
}
```

An entry names `card` OR `private_to`, never both. The "Remember for future months" switch (`expx.cards.strip.learn`) keeps its meaning: off, the group's rows are private this month only; on, the number is ALSO written to the private-card list and every other month reads it at once. The reply's `results[]` gains entries of the shape `{hint, private_to, n_rows, learned, digits}` beside the card ones; `learned: true` with `digits` means the list now holds that number. The reply's `batch` is the refreshed view; render it as today.

Do not offer the option in the "No card number on the receipt" section: a word names no card to list, and the per-row "Paid with a private card" already covers those rows.

400 codes to show in plain words: `private_card_is_company_card` (`expx.cards.strip.err.companyCard`, with `card`), `private_card_needs_digits` (`expx.cards.strip.err.needsDigits`). Anything else verbatim.

## 3. The row: say where the private mark came from

`expenses[].private_source` is new: `"row"` (the reviewer confirmed this row), `"month"` (assigned on the strip for this month), `"private_card_list"` (a listed number), `""` (not private). When it is `"private_card_list"`, the private badge (`expx.private.badge`) adds the suffix `expx.private.fromList`; when it is `"month"`, the suffix `expx.private.fromMonth`. No suffix otherwise. A missing field means no suffix.

The two controls beside the badge keep working, and their meaning on a list-derived row is:

- **Undo** (`expx.reimburse.undo`) calls the same route as today, `POST /api/runs/{batchId}/expenses/{documentId}/private {"private": false}`. On a list-derived row the backend stores an opt-out for that row, so the list stops applying to it; the list itself is untouched.
- **Change who is reimbursed** (`expx.reimburse.edit`) opens the same dialog and saves with the same call as today (`{"private": true, "reimburse_to": "..."}`). That edits THIS ROW: it becomes the reviewer's own private mark (`private_source` flips to `"row"`), and the list entry keeps its person. To change the person for every month, edit the list in Settings.

A per-row card pick on a list-derived row is allowed by the backend (the pick wins); nothing to change in the picker.

## 4. Do not change

- The private dialog, `expx.privateCard.mark`, `expx.private.editTitle`, `expx.reimburse.undo`, `expx.reimburse.edit`, and what they send.
- The card picker, `__private_card__`, and `can_mark_private` gating.
- The Cards editor's save payload (every card, every field, whole map), except that it may now receive `private_card_is_company_card`.
- The strip's card assignments and the New card flow.
- Any month, row or settings write other than the ones named above.

## New strings (EN / PT-BR, every key in both)

| key | EN | PT-BR |
|---|---|---|
| `set.tabs.privateCards` | Private cards | Cartões particulares |
| `set.privateCards.title` | Private cards | Cartões particulares |
| `set.privateCards.desc` | Cards that are not the company's. A receipt paid with one of these is a private expense, reimbursed to the person listed, in every month. | Cartões que não são da empresa. Um recibo pago com um deles é uma despesa particular, reembolsada à pessoa indicada, em todos os meses. |
| `set.privateCards.col.digits` | Last 4 digits | Últimos 4 dígitos |
| `set.privateCards.col.person` | Reimburse to | Reembolsar a |
| `set.privateCards.col.note` | Note | Observação |
| `set.privateCards.col.active` | Active | Ativo |
| `set.privateCards.add` | Add private card | Adicionar cartão particular |
| `set.privateCards.remove` | Remove | Remover |
| `set.privateCards.save` | Save private cards | Salvar cartões particulares |
| `set.privateCards.empty` | No private cards listed yet. | Nenhum cartão particular cadastrado ainda. |
| `set.privateCards.help` | Type the full last four digits. A number that belongs to a company card is refused: a card is the company's or private, never both. To stop using an entry without deleting it, switch it off. | Digite os quatro últimos dígitos completos. Um número que pertence a um cartão da empresa é recusado: um cartão é da empresa ou particular, nunca os dois. Para parar de usar um cadastro sem excluí-lo, desative-o. |
| `set.privateCards.err.digitsShort` | Enter the full last four digits of the card. | Informe os quatro últimos dígitos completos do cartão. |
| `set.privateCards.err.personRequired` | Name the person to reimburse. | Indique a pessoa a reembolsar. |
| `set.privateCards.err.duplicate` | This number is listed twice. | Este número está cadastrado duas vezes. |
| `set.privateCards.err.companyCard` | This number belongs to the company card {card}. A card is the company's or private, never both. | Este número pertence ao cartão da empresa {card}. Um cartão é da empresa ou particular, nunca os dois. |
| `expx.cards.strip.privateOf` | Private card of... | Cartão particular de... |
| `expx.cards.strip.privateOf.person` | Reimburse to | Reembolsar a |
| `expx.cards.strip.err.companyCard` | This number belongs to the company card {card}, so it cannot be a private card. | Este número pertence ao cartão da empresa {card}, então não pode ser um cartão particular. |
| `expx.cards.strip.err.needsDigits` | Only a card number can be remembered as a private card. Turn off "Remember for future months" to apply it to this month only. | Só um número de cartão pode ser memorizado como cartão particular. Desligue "Lembrar para os próximos meses" para aplicar só a este mês. |
| `expx.private.fromList` | (from the private card list) | (da lista de cartões particulares) |
| `expx.private.fromMonth` | (assigned for this month) | (atribuído para este mês) |

No em-dashes anywhere, in either language.

## Checks

1. Settings shows a "Private cards" tab after Cards, empty state at first. Add "3281", "Dirk Neumann", note "personal card", Active on; Save sends `PUT /api/settings` with `{"private_cards": {"3281": {"person": "Dirk Neumann", "note": "personal card", "active": true}}}` and nothing else, and the reply's `applied` is `["private_cards"]`. Reload: the row is still there.
2. Type "xx78" as the digits and Save: the digits-short message shows, nothing saved. Type the last four of a company card (Settings, Cards): the company-card message names that card.
3. Open September 2026 Expenses after check 1: the DB Fernverkehr 3281 row shows the private badge with "(from the private card list)", `Private (Dirk Neumann)` in Paid Through, and no "Suggested private expense" chip. Undo on it clears the badge for that row only; the Settings list still holds 3281.
4. On a month with a numbered group whose digits are not a company card, the group's Assign select ends with "Private card of...". Choosing it shows the Reimburse-to input, pre-filled when the rows carry a sender person. With Remember off, Assign sends `{"hint": ..., "private_to": ...}` per spelling and `"learn": false`; the group's rows come back private with "(assigned for this month)" and Settings is unchanged. With Remember on, the reply's result carries `learned: true` and `digits`, and the Private cards tab lists the number.
5. The "No card number on the receipt" section has no "Private card of..." option.
6. PT-BR: every string above in Portuguese, including the badge suffix and the two error messages.
7. No request other than the ones named above is sent by these screens; the Cards tab's save payload is unchanged.
````

## Follow-up 1 (2026-09-25, after the first publish): the strip option never renders

Audit of the published bundle (`chunk-expenses._batchId-BsXUzwCy.js`): the
group renderer computes `o = !!t.allowPrivate && !e.ambiguous` and shows
"Private card of..." only when `o` is true, but every section calls it as
`O(e, {})`, so the option renders on no group. The Settings tab and the badge
are live and were driven; the strings, the person input and the `private_to`
mutation are in the bundle. One wiring line is missing.

Paste into Lovable:

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com`. No backend change; one wiring fix in the unknown-card strip on the expenses page.

## What is wrong

The strip's group renderer takes an options object and shows the "Private card of..." select option only when `allowPrivate` is true (`o = !!t.allowPrivate && !e.ambiguous`). Every section calls it with an empty object (`ie.map(e => O(e, {}))` for "Cards by number", and the same for the other two), so the option never renders anywhere. On the published build the "Card ending 3281" group's Assign select on September 2026 lists the nine cards and "New card..." and nothing else, while the strings and the `private_to` mutation are already in the bundle.

## The fix

Pass `{ allowPrivate: true }` from the "Cards by number" section only. The other two sections keep `{}`. Change nothing else: the "Reimburse to" input, its pre-fill from `reimburse_to_prefill`, the `private_to` payload and the "Remember for future months" switch are already wired.

## Checks

1. September 2026, open the strip (Review), the "Card ending 3281" group: the Assign select ends with "Private card of..." after "New card...". Choosing it shows the "Reimburse to" input. Do not press Assign.
2. The groups under "No card number on the receipt" still have no such option.
3. PT: "Cartão particular de..." in the same place.
````

## Follow-up 2 (2026-09-25, after Follow-up 1 was published): the "Reimburse to" input never pre-fills

Follow-up 1 is live and driven: the "Card ending 3281" group's Assign select
ended with "Private card of..." and choosing it showed the input. The input
was EMPTY although the API gives that group `documents: ["0024__..."]` and
row `0024__` `reimburse_to_prefill: "Dirk Neumann"`. Cause, in the SPA source
(`src/components/ExpensesReviewGrid.tsx`, commit `1c18504`): the page renders
`<CardReviewStrip batchId={batchId} review={data.card_review} />` without
`expenses`, so `prefillFor` searches the prop's default `[]`.

Paste into Lovable:

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com`. No backend change; one prop is missing on the expenses page.

## What is wrong

`CardReviewStrip` pre-fills the "Reimburse to" input (shown when "Private card of..." is chosen) from `expenses[].reimburse_to_prefill`, looking up each row of the group by `document_id`. The page renders it as `<CardReviewStrip batchId={batchId} review={data.card_review} />`, without `expenses`, so the lookup runs over the default empty list and the input is always blank, even where the backend sent a name.

## The fix

Pass the batch's rows: `<CardReviewStrip batchId={batchId} review={data.card_review} expenses={data.expenses ?? []} />`. Change nothing else.

## Checks

1. On a month whose strip has a numbered group with a sender, choose "Private card of..." on that group: the "Reimburse to" input shows the sender's name (`reimburse_to_prefill`), and it can still be edited. Do not press Assign.
2. A group whose rows carry no sender still shows an empty input.
````
