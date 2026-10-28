# Lovable prompt: Paid Through stops asking for the card a second time (item 189)

> **NOT PASTED.** SPA only. Handed to the owner in conversation 2026-09-24;
> saved here so the status row has a file to point at. Written against the
> published bundle of 2026-09-24 (`assets/chunk-expenses._batchId-BZt6ewgZ.js`,
> the Paid Through cell component).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No backend change: every field below is already on the row. One component changes: the Paid Through cell on the Expenses page (the cell that renders `posting_paid_through`, its source badge, and the account select whose first option is `expx.review.paid.useAuto`).

## Why

Reviewers think they have to enter the card twice. A row with no card shows "Pick the card that paid" in the company column, and next to it the Paid Through cell shows an amber `(paid-through - assign)`, a "needs a card" badge, and its own account dropdown. The card pick already fills Paid Through by itself: choosing the card sets the row's company, person and Paid Through account in one step. The Paid Through dropdown is only a manual override. It changes the posting account alone, not the company, and it outranks the card from then on. A reviewer who fills it in instead of picking the card gets a row that looks done but is not.

## The change: the override appears only when there is something to override

The cell has three states. Decide which one applies from `row.posting_paid_through.source`, `row.paid_through` (the reviewer's override, empty when none) and `row.card`:

1. **No card yet** (`source === "unassigned"` AND `row.card` is null AND `row.paid_through` is empty):
   - Do NOT render the account select.
   - Do NOT render the amber static line that prints `(paid-through - assign)`.
   - Render only the badge, in its existing amber style, with the new text `expx.review.paid.pickCardFirst`.
   - The cell stays exactly this until a card is picked, and then it moves to state 2 on the normal refetch.

2. **Resolved, no override** (any other source, including `card`, `default` and `private`, AND `row.paid_through` is empty):
   - Keep the static account line and the source badge exactly as today.
   - Replace the always-visible select with a small ghost text button labelled `expx.review.paid.overridePlaceholder` ("Override account"). Clicking it reveals the same select as today, opened, with the same options and the same save call. Closing it without a choice hides it again.
   - Keep the existing tooltip (`expx.review.paid.tooltip`) on that button.

3. **Override set** (`row.paid_through` is non-empty, whatever the source):
   - Render the cell exactly as today, select visible, so the override can be changed or reset with "Use auto-resolved". This covers rows where someone already typed an account, including rows with no card.

Guard: a row with `source === "unassigned"` but a non-null `row.card` (the card is known but has no account behind it) goes to state 2, not state 1. Hiding the select there would leave the reviewer with no way to set the account.

## Do not change

The select's options, its `__auto__` sentinel, the save call and what it sends. The "you set this", "from card ···{last4}", "entity default" badges and their colours. The duplicate-label rule already in the cell (the static line is dropped when it equals the override). The company column, the card picker, the private controls, and every other cell.

## New string

| Key | EN | PT-BR |
|---|---|---|
| `expx.review.paid.pickCardFirst` (new) | Pick the card that paid first | Escolha primeiro o cartão que pagou |

`expx.review.paid.unassigned` ("needs a card") stays in the dictionary; other surfaces may read it.

## Checking it landed

Do not save anything: open rows and read them only.

1. On a month with a row that has no card and no override: its Paid Through cell shows only the "Pick the card that paid first" badge. No dropdown, no `(paid-through - assign)` line.
2. On a row whose card resolved: the account line and "from card ···NNNN" badge show, plus an "Override account" text button. Clicking it opens the account list with "Use auto-resolved" first. Press Escape and it hides again.
3. On a row with an override set: the dropdown is visible as before and reads the override.
4. Portuguese: the no-card badge reads "Escolha primeiro o cartão que pagou".
5. Bundle: `expx.review.paid.pickCardFirst` is present in the i18n chunk; `expx.review.paid.useAuto` and `expx.review.paid.overridePlaceholder` are still present.
````
