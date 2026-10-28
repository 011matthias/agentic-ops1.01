# Lovable prompt: "Paid with a private card" becomes the last option of the card picker (item 139, notes #65 + #66)

> **NOT YET APPLIED.** SPA only, no backend change. Builds on the applied
> `lovable-private-card-prompt.md` (`expenses[].can_mark_private`, the dialog
> and `POST /api/runs/{id}/expenses/{doc}/private`).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. All changes are in `src/components/ExpensesReviewGrid.tsx`; no new field and no new request. Render defensively: a row without `can_mark_private` keeps today's fallback rule.

## Why

On the Expenses page each row's card column stacks three controls: the entity picker ("Leave blank (resolve from card)"), the card picker ("Pick the card that paid") and, below them, a separate "Paid with a private card" button. The owner looked for the private option inside the card picker, did not find it, and asked for it to be one of the picker's options, to save space. Paying with a private card is an answer to "which card paid", so it belongs in that list.

## 1. Split the dialog out of `PrivateExpenseCell`

Create `PrivateCardDialog({ runId, row, open, onOpenChange }: { runId: string; row: ExpenseRow; open: boolean; onOpenChange: (o: boolean) => void })` from the dialog that `PrivateExpenseCell` renders today, with no `DialogTrigger`:

- Same title `expx.privateCard.mark`, same description (`expx.private.body` when `row.suggested_private` is true, else `expx.privateCard.body`), same "Reimburse" field (`expx.private.field`), same prefill help line, same save button `expx.privateCard.save` with its spinner.
- Same mutation: `setExpensePrivate(runId, row.document_id, { private: true, reimburse_to: name.trim() })`, same `afterExpenseEdit(queryClient, t, runId, res)` on success, and the backend error message shown verbatim under the field, as today. A 400 with `"code": "company_card"` shows its message there like any other error.
- The prefill that runs today in `onOpenChange` runs when `open` turns true: name = `cleanText(row.reimburse_to_prefill)`, else `cleanText(row.person)`, else empty; error cleared.

## 2. The option in `CardFixCell`

- Add `runId: string` to its props and pass `runId={runId}` where the row renders `<CardFixCell ... />`.
- Compute `eligible` with today's rule from `PrivateExpenseCell`: `typeof row.can_mark_private === "boolean" ? row.can_mark_private : row.card == null`.
- Add `const PRIVATE_CARD = "__private_card__";` next to `CARD_FIX_CLEAR`, and `const [privateOpen, setPrivateOpen] = useState(false);`.
- In `SelectContent`, after the cards map, when `eligible`: `<SelectSeparator />` (import it from `@/components/ui/select`), then `<SelectItem value={PRIVATE_CARD}>{t("expx.privateCard.mark")}</SelectItem>`. It is always the last option.
- In `onValueChange`: when `v === PRIVATE_CARD`, call `setTimeout(() => setPrivateOpen(true), 0)` and return without calling `onSave` (the timeout lets the select close before the dialog takes focus). Every other value keeps today's handling.
- The select's `value` stays `row.card?.key ?? ""`: choosing the private option never becomes the shown value, so after Cancel the picker still reads "Pick the card that paid".
- Render `<PrivateCardDialog runId={runId} row={row} open={privateOpen} onOpenChange={setPrivateOpen} />` inside the div `CardFixCell` returns.

Rows that can be marked private have `card_source` `none` or `learned`, where the picker shows straight away. A `hint` row always has a card, so it is never eligible and its "Change card" button needs nothing new.

## 3. `PrivateExpenseCell` keeps the badge and the chip only

- A row with `row.private` true renders exactly as today: the badge `expx.private.badge` and the "Undo private card" button (`expx.reimburse.undo`, sends `{"private": false}`).
- A row that is not private: remove the "Paid with a private card" button and its dialog. When `eligible` and `row.suggested_private` are both true, keep rendering the `expx.private.chip` badge in the same place; otherwise render nothing.

## 4. Do not change

- `CardFixCell` still renders nothing on a private row; the way back to a company card is "Undo private card", then pick the card. If the backend refuses a card pick with 400 `"code": "private_card"`, that error shows the way it does today.
- The entity picker, the "Remove the card picked by hand" option, the card list and its order, `CardChip`, `CardEndingNote`, the card-review strip, the tiles and every count.
- The request body and the route of both private calls.

## New strings

None. The option and the dialog reuse existing keys; they must read exactly as below.

| Key | EN | PT-BR |
|---|---|---|
| `expx.privateCard.mark` (option label and dialog title) | Paid with a private card | Pago com cartão particular |
| `expx.cardFix.pick` (placeholder, unchanged) | Pick the card that paid | Escolher o cartão que pagou |
| `expx.privateCard.save` (unchanged) | Save as private card | Salvar como cartão particular |
| `expx.private.field` (unchanged) | Reimburse | Reembolsar |

## Checking it landed

Open the picker and the dialog, then press Escape or close the dialog every time: these are Criss's live months, and choosing a card or saving writes.

1. July 2026 Expenses (`/expenses/50622baec444`), row Hostinger, 2026-07-03, 172.61 USD (`0000__rendered-body.pdf`): the card column shows "Leave blank (resolve from card)" and "Pick the card that paid", and no separate "Paid with a private card" button. Opening the picker lists the nine cards from "Credit Card Chase Visa - 3645" to "Credit Card - 2838", a divider, then "Paid with a private card". Choosing it opens the dialog titled "Paid with a private card" with the "Reimburse" field empty; closing it leaves the picker reading "Pick the card that paid".
2. Same month, row Hostinger, 2026-07-28, 172.61 USD (`0002__rendered-body.pdf`, `can_mark_private: false`): the picker lists the nine cards and nothing after them.
3. Same month, row CREDIT AGRICOLE NORMANDIE SEINE, 6.60 EUR: the "Suggested private expense" chip still shows under the picker, with no button beside it.
4. August 2026 Expenses (`/expenses/074a7b8905d7`): Perplexity, 2026-08-20, 25.00 USD offers the option; OpenAI, 2026-08-21, 80.12 USD (card Credit Card Chase Visa - 9693, resolved from its payment method) shows "Change card", and its picker has no private option.
5. Anywhere on both months, the text "Paid with a private card" appears only inside an open picker or dialog.
6. PT on July, the Hostinger 2026-07-03 row: the last option reads "Pago com cartão particular" under "Escolher o cartão que pagou".
7. Bundle: `__private_card__` in `chunk-expenses._batchId`; `expx.privateCard.mark` still present.
````
