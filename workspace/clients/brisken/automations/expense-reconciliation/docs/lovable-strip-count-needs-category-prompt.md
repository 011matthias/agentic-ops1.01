# Lovable prompt: the number beside each card means "needs category" (item 193)

**NOT PASTED.** Owner, 2026-09-24, on the `/months` card strip: *"these numbers
next to the card ending numbers have to be consistent in their meaning, for
1176 it supposedly depicts how many expenses were set aside and in the other
cards(and subcards) there is no clearly identifiable meaning or representation
behind it."* The number was `n_transactions` (statement lines, credits
included, no label). Asked, the owner chose **all "needs category" items**, and
**2838 counts only itself**.

**Backend:** ships in the same PR (`n_needs_category` on `GET /api/cards/status`).
The check values below were read 2026-09-24 off the live Expenses pages with the
same definition; in every month the per-card counts plus No card equal the
months list's Needs category column (30 in total).

````markdown
The number beside each card on the card strip changes meaning. Today it is the card's charge count; from now on it is the number of expenses on that card that need a category, across all months. One meaning on every chip. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## 1. The data

`GET /api/cards/status` (the `["cards", "status"]` query) has a new field on each card, `cards[].n_needs_category`, and on `no_card`, `no_card.n_needs_category`. It counts the expenses in the NEEDS CATEGORY box, each card its own: an account (2838) does not include its subcards.

## 2. The strip (`CardStrip`)

- Every card chip, in the top row, in the nested subcard row and behind "Show {n} cards with nothing loaded", shows `n_needs_category` where it shows `n_transactions` today. Same badge, same place. Show the number also when it is 0.
- The **No card** chip gets the same badge, with `no_card.n_needs_category`.
- The **All** chip stays without a number.
- Each number carries a tooltip (`title`) and an `aria-label`: "{n} expenses need a category, across all months" ("1 expense needs a category, across all months" for 1).
- Nothing else changes: which months a pick lists, the order of the chips, the nesting, the disclosure and which cards sit behind it, the caption.

## 3. Strings (EN dictionary and the PT mirror in `src/lib/i18n.tsx`)

| Key | EN | PT-BR |
|---|---|---|
| `cardStrip.count.one` (new) | 1 expense needs a category, across all months | 1 despesa precisa de categoria, em todos os meses |
| `cardStrip.count.many` (new) | {n} expenses need a category, across all months | {n} despesas precisam de categoria, em todos os meses |

## 4. Do not change

The months list's table and its Needs category column, the months themselves, and any backend call beyond reading the new field.

## 5. How to check it worked

Live numbers, read 2026-09-24.

| Drive | Expect |
|---|---|
| `/months` strip | 2838 **3**, 1176 **2**, 4700 ● **0**, No card **8**; All with no number |
| Open 2838's subcards | 3645 **1**, 3876 **10**, 0340 **3** |
| "Show 4 cards with nothing loaded" | 9693 **3**; 0113, 6013, 8311 **0** |
| Hover 3876's number | "10 expenses need a category, across all months" |
| Hover 3645's number | "1 expense needs a category, across all months" |
| Switch to PT, hover 3876 | "10 despesas precisam de categoria, em todos os meses" |
| Pick 3876 and open its months | their NEEDS CATEGORY boxes add up to 10 |
````
