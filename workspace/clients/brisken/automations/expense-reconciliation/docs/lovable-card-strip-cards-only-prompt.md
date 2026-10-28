# Lovable prompt: the card strip's dropdown lists cards only (item 214, owner ruling 2026-09-25)

> **NOT YET APPLIED.** Needs the item 214 backend live first
> (`card_review.private_cards`, `unresolved_hints[].private_card_options`,
> the strip route's `private_card`). Replaces the "New card..." and "Private
> card of..." options that Follow-up 1 of item 208 published; the backend
> keeps accepting `private_to`, so the published screen works until this lands.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes are in `src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx` (the `CardReviewStrip` component only) and `src/lib/i18n.tsx`. Render defensively: a payload without the new fields must render exactly as today, minus the two removed options.

## Why

The owner ruled how the "Assign to card..." dropdown on the Expenses page's card strip works: "dropdown should only consist of cards"; "expenses that are suggested a private have only private cards in drop down unless user clicks that its not private"; and "New card..." goes. New cards are created in Settings (Cards, Private cards), never from this strip. The backend now sends the private cards and which of them fit each receipt, and it already removes from the strip every receipt whose card is known.

## 1. Types in `src/lib/api.ts`

- `CardReviewUnresolvedHint`: add `private_card_options?: string[];` (the four digits of each listed private card this group may be assigned to).
- `CardReview`: add `private_cards?: { digits: string; person: string; label: string }[];` and `n_private_rows?: number;`.
- `AssignCardsBody.assignments`: add a third shape `{ hint: string; private_card: string }` beside `{ hint, card }` and `{ hint, private_to }`.

## 2. The dropdown in `CardReviewStrip`

- Remove the `NEW_CARD` option ("New card...") and the whole inline new-card form it opens (label, digits, entity, person inputs), plus the `drafts` state and the `newCard` branch of `doAssign`. Remove the `PRIVATE_OF` option ("Private card of...") with its "Reimburse to" input, the `privatePersons` state, `prefillFor`, and the `privateTo` branch. Remove `opts.allowPrivate` from `renderUnit` and its call sites.
- Add `const PRIVATE_PICK = "__pc__:";`. For each unit keep the source hint entry's `private_card_options` (filter to strings) on the `Unit` as `privateOptions: string[]`, and read `const privateCards = Array.isArray(review?.private_cards) ? review.private_cards.filter((p) => p && typeof p.digits === "string" && p.digits) : [];` once. A unit's private items are the `privateCards` whose `digits` is in `unit.privateOptions`, in the backend's order.
- `SelectContent` lists, in this order: the company cards exactly as today (`cards` from `getCards`); then, when the unit has private items, `<SelectSeparator />` (import it from `@/components/ui/select`) and one `<SelectItem value={PRIVATE_PICK + p.digits}>{cleanText(p.label) || p.digits}</SelectItem>` per private item. Nothing else: no "New card...", no "Private card of...".
- `doAssign`: when `pick.startsWith(PRIVATE_PICK)`, call `assign.mutate({ hints, privateCard: pick.slice(PRIVATE_PICK.length) })`; otherwise `assign.mutate({ hints, card: pick })` as today. In the mutation, an entry with `privateCard` is sent as `{ hint, private_card: v.privateCard }`. `canSave` is `!!pick`.
- The "Remember for future months" switch stays. A private-card pick ignores it on the backend (the card is on the list already), so do not change it.

## 3. Suggested private: only private cards until "Not private"

- Add `const [notPrivate, setNotPrivate] = useState<Record<string, boolean>>({});`.
- For a unit with `suggestedPrivate` true and `!notPrivate[unit.id]`: the dropdown shows ONLY that unit's private items (no company cards, no separator). Beside the select render a small `variant="link"` button `t("expx.cards.strip.notPrivate")` that sets `notPrivate[unit.id] = true` and clears `picks[unit.id]`. After that the unit's dropdown shows the company cards only, and a link button `t("expx.cards.strip.showPrivate")` sets it back to false (and clears the pick). The toggle is screen state only; nothing is sent until Assign.
- A suggested unit with NO private items (a receipt that prints a card number the private list does not hold, or an empty list): hide the select and the Assign button until "Not private" is clicked, and show under the unit's line, in `text-xs text-muted-foreground`: `t("expx.cards.strip.listInSettings", { d: unit.digits ?? "" })` when `unit.digits` is set, else `t("expx.cards.strip.noPrivateCards")`, followed by a link "Settings > Private cards" (`t("expx.cards.strip.openPrivateCards")`) that navigates to `/settings` with `search: { tab: "private-cards" }`. The "Not private" button stays visible.
- Units that are not suggested private show company cards plus their private items (section above); a numbered unit normally has no private items, which is correct.
- Keep today's amber line under a suggested unit (`expx.cards.strip.suggestedPrivate` / `.numbered`).

## 4. Errors

In `assign`'s `onError`, before the generic branch:
- `e.code === "private_card_not_listed"` -> `toast.error(t("expx.cards.strip.err.notListed"))` and `queryClient.invalidateQueries({ queryKey: ["expense-batch", batchId] })`.
- `e.code === "private_card_number_mismatch"` -> `toast.error(t("expx.cards.strip.err.numberMismatch"))`.
Keep the existing `private_card_is_company_card` and `private_card_needs_digits` branches (the published `private_to` path can still raise them).

## 5. i18n (`src/lib/i18n.tsx`), English and Portuguese

| Key | English | Portuguese |
|---|---|---|
| `expx.cards.strip.notPrivate` | Not private | Não é particular |
| `expx.cards.strip.showPrivate` | Private cards | Cartões particulares |
| `expx.cards.strip.listInSettings` | Card ending {d} is not on the private card list. Add it there if it is a personal card. | O cartão final {d} não está na lista de cartões particulares. Adicione-o lá se for um cartão pessoal. |
| `expx.cards.strip.noPrivateCards` | No private card is listed yet. | Nenhum cartão particular cadastrado ainda. |
| `expx.cards.strip.openPrivateCards` | Settings > Private cards | Configurações > Cartões particulares |
| `expx.cards.strip.err.notListed` | That card is no longer on the private card list. The page has been refreshed. | Esse cartão não está mais na lista de cartões particulares. A página foi atualizada. |
| `expx.cards.strip.err.numberMismatch` | The receipt prints a different card number. Add that number under Settings > Private cards. | O recibo mostra outro número de cartão. Adicione esse número em Configurações > Cartões particulares. |

Delete the now-unused keys `expx.cards.strip.newCard`, `expx.cards.strip.privateOf` and `expx.cards.strip.privateOf.person` in both languages, and any `expx.cards.new.*` key no other component still uses (search first).

## Check

On September's Expenses page (open the strip with "Review"): the DB Fernverkehr receipt (card 3281, already on the private list) is no longer on the strip. The "credit card" and "saved payment method" groups (no card number, not suggested private) show the company cards, a separator, and "3281 · Dirk Neumann (private)". A suggested-private receipt such as "girocard" shows only "3281 · Dirk Neumann (private)" and a "Not private" link; clicking it swaps the list to the company cards. No dropdown anywhere shows "New card..." or "Private card of...".
````

## Backend it relies on (live after the item 214 deploy)

`docs/api-contract.md`, section "The strip asks only without payment info;
its dropdown holds cards (item 214, 2026-09-25)". Every field is parallel
and additive; `private_to` stays accepted.
