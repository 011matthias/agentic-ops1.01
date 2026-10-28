# Lovable prompt: the Cards overview nests a card's subcards under it (item 194)

**NOT PASTED.** Owner, 2026-09-24, on the published `/cards` overview (item
192): apply the same subcard logic as the months strip (item 191), adapted to
the overview's table.

**No backend change.** `GET /api/cards/status` has carried `cards[].parent` and
`cards[].subcards` since item 191 (PR #1310), and the three parents are live
(3645, 3876, card-0340 under card-2838). The table reads the same query.

**The adaptation.** A strip has tabs, so the months strip hides a subcard's tab
until its account is clicked. A table has rows, so the overview collapses a
subcard's ROW under its account's row: collapsed on load, opened by clicking the
account row. Every row keeps its own figures, as the strip keeps its own counts.

````markdown
On the Cards overview (`/cards`) only, the table nests a card's subcards under the card they belong to: their rows leave the main list and appear directly under their account's row once the viewer clicks that row. Every figure stays what it is. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`. No backend change is needed.

## Why

Card 2838 is an account with three cards under it (3645, 3876, 0340). The months strip already hides those three until 2838 is clicked. The overview still lists all four as unrelated rows. The owner wants the same logic here, adapted to a table.

## The data

The fields the months strip already reads, on every `cards[]` entry of `GET /api/cards/status` (the `["cards", "status"]` query this page already makes):

- `parent`: the `key` of the account this card sits under, or `""` when it stands alone.
- `subcards`: on an account, the `key`s of the cards under it; `[]` otherwise.

Reuse the `parentOf` / subcards helpers `CardStrip` already has in `src/components/CardsStatusScreen.tsx` (move them to module level if they are inside the component, so both use one definition). Treat a `parent` that names no card in `cards` as `""`.

## 1. Which rows are listed

In `CardsStatusScreen`, a card with a non-empty `parent` is left out of the main list: out of `shown` AND out of `empty` (the "Show {n} cards with nothing loaded" fold), so the fold's count counts only cards that stand alone or are accounts. Everything else about the main list is unchanged: the same `openWork` sort, the fold, the No card row last.

## 2. The account row

An account (a card with a non-empty `subcards`) is listed in its normal sorted place, by its OWN `openWork`, with its OWN figures. Its Card cell gains:

- a chevron button before the digits: lucide `ChevronRight` while collapsed, `ChevronDown` while expanded, `h-4 w-4`, muted; `aria-expanded` set; `aria-label` = the existing `cardStrip.subcards.aria` string with `{card}` = the account's digits,
- one more line under the label, muted and `text-xs`: `cardsPage.subcards.count` with `{n}` = the number of subcards ("3 cards on this account").

Clicking anywhere on the account row, or the chevron, toggles it. Give the account row `cursor-pointer` and a hover background. Rows that are not accounts stay exactly as they are now: not clickable, no hover change.

Every account starts collapsed each time the page loads. Keep the open accounts in component state (a `Set` of keys); nothing is saved.

## 3. The subcard rows

While an account is expanded, its subcards' rows render directly under it, before the next row of the main list:

- in the table's own order (`openWork`, largest first), the same way `shown` is sorted,
- rendered by the same `row()` with every column exactly as today: figures, amber highlights, tooltips, "No statement for:" line, "not in your card list" badge,
- marked as a level below: a light background (`bg-muted/30`) on the row, and the Card cell indented (`pl-8`) with a thin left rule (`border-l-2 border-muted` on its inner block),
- a subcard with nothing loaded is included here too; the fold never hides it.

The account row's figures are NOT a sum of its subcards and do not change when it expands.

## 4. Do not change

The months list (`/months`) and `CardStrip`. The columns, their order, their labels and the footnote. The No card row. Anything inside a month. Settings.

## 5. When nothing is nested

When no card has a `parent`, the table is exactly what it is now, row for row, with no chevron and no extra line anywhere.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `cardsPage.subcards.count` (new) | {n} cards on this account | {n} cartões nesta conta |

Reuse `cardStrip.subcards.aria` for the chevron's label; add nothing else.

## How to check it worked

Live numbers, read 2026-09-24.

| Drive | Expect |
|---|---|
| Load `/cards` | rows in this order: 2838, 9693, 1176, 4700, No card; 2838 shows a right-pointing chevron and "3 cards on this account"; no 3645, 3876 or 0340 row; "Show 3 cards with nothing loaded" under the table |
| The 2838 row's figures | exactly as before: Charges 111, Matched 25, Needs review 9, No receipt 75, Receipts 41, Without a charge 12, Credits 2, Statements 3, Still open USD 11,011.31 |
| Click the **2838** row | chevron points down; directly under it, indented on a light background: 3645, 3876, 0340 in that order; then 9693 |
| The three subcard rows | 3645: Charges 85, Receipts 14, Without a charge 6, Still open USD 4,811.16. 3876: Charges 85, Receipts 95, Without a charge 39, Still open USD 365.27. 0340: Charges 34, Receipts 19, Without a charge 1, Still open USD 1,299.83 |
| Hover the 3876 "Without a charge" figure | the same tooltip as before |
| Click the **9693** row | nothing happens |
| Click **2838** again | the three rows collapse |
| **Show 3 cards with nothing loaded** | 0113, 6013, 8311 appear; none of them is a subcard |
| Reload | 2838 collapsed again |
| Open `/months` | the strip unchanged by this prompt |
````
