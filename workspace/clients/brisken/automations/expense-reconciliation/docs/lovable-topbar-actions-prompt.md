# Lovable prompt: page buttons into the month's top bar, and the held-mail note (note #128, item 259)

> **PASTED and published 2026-10-29, verified live (see PROMPT-STATUS).** Follow-up to `lovable-chase-actions-prompt.md` section 4,
> which did not land: audited 2026-10-29 on October `/expenses/4ac14cb8b9e8`,
> the buttons still sit in the page body beside the "Review by exception" line
> (no `<header>`; the prompt said "page header row", and the page's real top
> bar is `MonthHeader`'s sticky nav). Also fixes a sentence the backend made
> false: item 259's "Retry held" now renders mail whose receipt is in the
> message text.
>
> No backend change. Both pieces are SPA only.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No new request.

## Why

The operator, on the October Expenses tab, anchored on "Review by exception. Ready rows can go out as is; the others need a look." and the buttons beside it: *"these buttons should be all the way in the top bar"*.

The "top bar" is the sticky bar `MonthHeader` renders: Back to menu, the month name, then the tabs (Expenses, Add a statement). Today the page-level buttons (Add receipts, Add expense, Save corrections to memory, Add a statement, Download report (PDF), Download CSV (data export), Send to Zoho, and the "..." menu) are a row in `ExpensesReviewGrid`'s `<main>`, level with the intro sentence, below that bar.

## Scope

`src/components/MonthHeader.tsx`, `src/components/ExpensesReviewGrid.tsx`, `src/lib/i18n.tsx`. Nothing else.

## 1. The buttons live in MonthHeader's bar

1. Give `MonthHeader` an optional prop `actions?: React.ReactNode`. Render it as the LAST child of the bar's inner `div.flex` row (the one holding the back button, the month name and the `<nav>`), wrapped in `<div className="ml-auto flex flex-wrap items-center justify-end gap-2">`. When `actions` is absent, the bar renders exactly as today (the Matching tab passes none).
2. In `ExpensesReviewGrid`, take the existing page-level button group out of `<main>` and pass the SAME elements to `<MonthHeader actions={...} />`. Keep every button, its label, its icon, its handler, its disabled state, its order and the "..." menu. Do not copy them: move them, so there is one set.
3. Leave the intro sentence "Review by exception. Ready rows can go out as is; the others need a look." where it is, in the body, now without the buttons beside it.
4. Row-level and section-level buttons (View, Compare copies, Retry held, Review, etc.) do not move.
5. At narrow widths the bar's row already wraps (`flex-wrap`); the actions block wraps under the tabs and stays right-aligned. Do not add a second bar.

## 2. The held-mail note says what Retry now does

`InboundHeldStrip` shows `inbound.held.bodyOnlyNote` under the held list when any held mail is body-only. The sentence is now false: the backend's Retry renders those mails (up to 25 per press) and reads them like any receipt. Change the string in both languages:

| key | EN | PT |
|---|---|---|
| `inbound.held.bodyOnlyNote` | Emails with the receipt in the message text are read too, up to 25 per press. Mail that is not an expense lands in "Set aside". | E-mails com o recibo no corpo da mensagem também são lidos, até 25 por clique. O que não for despesa vai para "Separados". |

Check the PT word for the set-aside section against the existing key for "Set aside (not counted as expenses)" and reuse that exact translation for `"Set aside"`/`"Separados"`.

Also: `replayHeldInbound`'s response now carries `rendered` (a number) next to `replayed`. In the existing success toast keep `inbound.held.retried` with `n = r.replayed` (it already includes rendered mail); do not add a second toast.

## Checks

1. On October Expenses, the buttons Add receipts, Add expense, Save corrections to memory, Add a statement, Download report (PDF), Download CSV (data export), Send to Zoho and the "..." menu are in the sticky top bar, right-aligned, and are gone from the body. The intro sentence is still in the body.
2. Each moved button still does what it did (open its dialog / download), and Add a statement still opens the attach dialog.
3. The Matching tab's top bar is unchanged.
4. On a window about 700px wide the bar wraps without horizontal scroll and without overlapping the tabs.
5. With a held body-only mail present the banner reads the new sentence in English and Portuguese, and no longer says "cannot be retried yet".
````
