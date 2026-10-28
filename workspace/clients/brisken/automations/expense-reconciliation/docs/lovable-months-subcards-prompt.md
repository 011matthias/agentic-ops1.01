# Lovable prompt: the months strip nests a card's subcards under it (item 191)

**APPLIED** (published 2026-09-24, check table driven cold; evidence in
`PROMPT-STATUS.md` → Applied). Owner, 2026-09-24: *"adjust the subcards' tabs in the filter
in months menu to not be next to the 2838 tab but rather only appear once
viewer clicks on 2838. maintain their filter function"*.

**Backend: ships first (item 191 PR).** `GET /api/cards/status` now carries
`cards[].parent` and `cards[].subcards`, read from the LIVE card registry, so
the strip can nest without hard-coding which card is the account. Parallel
fields only: every figure stays the card's own.

**Live data gate: cleared 2026-09-24.** The three parents are entered (owner
yes), so the live payload nests 3645, 3876 and 0340 under 2838 and the §
"How to check" table applies from the moment this is published. Its "BEFORE
the parents are set" line is history now; skip it.

````markdown
On the months list (`/months`) only, the card strip nests a card's subcards under the card they belong to: they leave the top row and appear in a second row once the viewer clicks their account. Filtering does not change. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`.

## Why

Card 2838 is an account with three cards under it (3645, 3876, 0340). Today all four sit side by side on the strip as if they were unrelated cards. The owner wants the three subcards out of the top row, shown only when 2838 is clicked, each still filtering exactly as it does now.

## The data

`GET /api/cards/status` (the `["cards", "status"]` query the page already makes) now carries two more fields on every `cards[]` entry:

- `parent`: the `key` of the account this card sits under, or `""` when it stands alone.
- `subcards`: on an account, the `key`s of the cards under it, in the order to show them; `[]` on every other card.

Add both to the `CardStatus` interface in `src/lib/api.ts` as optional (`parent?: string; subcards?: string[]`) and treat a missing field as `""` / `[]`. The backend only links two cards when both are in `cards[]`, so a subcard's `parent` always names a card you have.

## 1. The top row

In `CardStrip` (`src/components/CardsStatusScreen.tsx`), add an optional prop `nestSubcards?: boolean`, default `false`. Only `MonthsHome` passes it: `<CardStrip cards={cards} active={cardKey} onChange={setCardKey} showNoCard nestSubcards />`. The `/cards` page does not pass it and stays exactly as it is (if `/cards` no longer shows a strip at all, there is nothing there to change; keep `CardStrip` exported for `/months` either way).

With `nestSubcards` on, a card with a non-empty `parent` is left out of the top row: out of the loaded chips AND out of the never-loaded disclosure, and the "Show {n} cards with nothing loaded" count counts only top-row cards. Everything else on the top row is unchanged: "All" first, the loaded cards in payload order, "No card", the disclosure.

An account (a card with a non-empty `subcards`) carries a small chevron after its count badge: lucide `ChevronDown` while its second row is showing, `ChevronRight` while it is not, `h-3.5 w-3.5`, muted colour.

## 2. Clicking the account opens its second row

The account chip does exactly what it does today: `onChange(account.key)`, so the months list shows the account's own months.

While the active key is the account OR any of its subcards, render a second row directly under the strip:

- its own `role="tablist"`, `aria-label` = `cardStrip.subcards.aria` with `{card}` = the account's chip text (its last digits),
- indented (`ml-4`), with the subcard chips in `subcards` order,
- each chip rendered the same way as a top-row chip (digits, count badge, the amber "not in Settings" dot when `known === false`) but one size smaller (`h-9`, `text-sm`), so it reads as a level below,
- subcards with `never_loaded` included here too; the disclosure does not hide them.

Clicking a subcard calls `onChange(sub.key)`: the same filter that card's chip applies today. While a subcard is active, the account chip on the top row keeps its selected look (it is the open tab) and the subcard is the selected chip in the second row.

Clicking the account chip while one of its subcards is active goes back to the account's own months (`onChange(account.key)`); the second row stays open. Clicking "All", "No card" or any other top-row card closes the second row.

Derive "open" purely from the active key; hold no extra state. That is what makes a deep link work: `/months?card=3645` (for instance, coming back from a month with the browser's back button) opens 2838's second row with 3645 selected.

## 3. Filtering does not change

Do NOT touch the filter logic in `MonthsHome`. `selectedCard` is looked up over the whole `cards` array, so a subcard picked from the second row filters the months, shows the caption and carries `?card=` into the month exactly as it does today. The numbers on every chip stay each card's own; the account's badge is NOT a sum of its subcards.

## 4. Do not change

The `/cards` page (its strip stays flat). Anything inside a month (the scope line, `CardScope`). The months table's columns, the captions, the empty line, the row click. Settings.

## 5. When nothing is nested

When no card has a `parent` (the live registry today, until the parents are set in Settings, Cards), the strip is exactly what it is now, chip for chip, and no chevron shows anywhere.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `cardStrip.subcards.aria` (new) | Cards on account {card} | Cartões da conta {card} |

Reuse every other card-strip string; do not duplicate them.

## How to check it worked

Live numbers, read 2026-09-24. First, BEFORE the parents are set, `/months` is unchanged: `All · 2838 111 · 3645 85 · 3876 85 · 0340 34 · 1176 3 · 4700 2 · No card`, "Show 4 cards with nothing loaded", no chevron.

Then in Settings, Cards, set "Account" = "Credit Card - 2838" on 3645, 3876 and 0340, save, and reload `/months`:

| Drive | Expect |
|---|---|
| Load `/months` | top row `All · 2838 111 › · 1176 3 · 4700 2 · No card`, "Show 4 cards with nothing loaded"; no second row |
| Click **2838** | URL `/months?card=card-2838`; chevron turns down; second row `3645 85 · 3876 85 · 0340 34`; months September, August, July, June, May, April; the caption shown |
| Click **3645** in the second row | URL `/months?card=3645`; 2838 still looks selected, 3645 selected below; months September, August, July, June, April |
| Click **3876** | months September, August, July, June, May, January |
| Click **0340** | months July, April |
| Open **July** from the 0340 list, then browser **back** | back on `/months?card=card-0340` with the second row open and 0340 selected |
| Click **2838** again | second row stays; months back to 2838's own six |
| Click **1176** | second row gone; September and August |
| Click **All** | full seven months; no second row |
| Open `/cards` | nothing on it changed by this prompt: no second row, no chevron |
````
