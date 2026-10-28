# Lovable prompt: the Confirm button moves under the account picker (Dirk, 2026-10-07)

> **NOT PASTED.** SPA only, no backend gate, no new i18n keys. Dirk asked for
> the "Confirm {account}" button under the vendor name to replace the amber
> "Suggested" line under the Category / Account picker on the Expenses grid.
> Written against SPA `origin/main` `0ac4b07` (2026-10-07), where the button
> is `KeepCategoryButton` (rendered in the vendor cell) and the line is
> `SuggestionLine` (rendered under the account `Select`), both in
> `src/components/ExpensesReviewGrid.tsx`.

````markdown
Change in the Expenses review grid (`src/components/ExpensesReviewGrid.tsx`). UI only: no backend, API or Supabase changes, no new endpoints, no new translation strings. The backend at https://api.expenses.brisken.com stays as is.

**What Dirk asked for:** move the "Confirm {account}" button from under the vendor name into the Category / Account column, where it takes the place of the amber "Suggested" line under the account dropdown.

How it works today, for a row whose account is a model suggestion:
- Vendor cell: vendor name, the "From:" chip, the italic reason line ("The model suggested this account from the receipt's lines. Confirm it, or pick another, before it posts."), then `<KeepCategoryButton runId={runId} row={row} />`, which renders "Confirm IT: equipment, peripherals, phones, devices".
- Category cell: the account `Select` ("Pick an account"), then `{row.suggested_category ? <SuggestionLine s={row.suggested_category} /> : null}`, which renders the amber "Suggested" badge and the account name.

Change it to:
1. Remove `<KeepCategoryButton … />` from the vendor cell. The vendor name, the "From:" chip and the italic reason line stay exactly where they are.
2. In the category cell, render `<KeepCategoryButton runId={runId} row={row} />` directly under the account Select, where `SuggestionLine` renders now.
3. When the button shows its "Confirm {account}" variant (the row has a `suggested_category`, no posted category, and `row.category_confirmable === true`), do NOT render `SuggestionLine`. The button replaces it.
4. Keep `SuggestionLine` in these two cases so no information disappears:
   - the row has a `suggested_category` but no button is shown (`category_confirmable` is not true): show the Suggested line as today.
   - the button is the `Keep "{category}"` variant (a posted category exists) and the row also has a `suggested_category`: show the Keep button, then the Suggested line under it.
5. The `Keep "{category}"` variant moves with the button. It also renders under the dropdown now, never under the vendor name.

How the button looks in its new place:
- Full width of the category column, left-aligned text, the same outline style and small size it has now, with a small gap (about `mt-1`) under the Select.
- A long account name wraps onto a second line (`whitespace-normal h-auto py-1 text-left`) instead of being truncated, so the reviewer always sees the full account before confirming it. Also put the full account name in `title`.
- What the button does stays the same: the same `confirmExpenseCategory(runId, row.document_id)` mutation, the same `afterExpenseEdit` refresh, disabled while pending, the same error toast.

Done when:
- A row with a suggested account shows the vendor cell as name + chip + italic reason with no button, and the category cell as the "Pick an account" dropdown with the "Confirm IT: …" button directly under it and no amber "Suggested" line.
- Clicking the button confirms the account and refreshes the row exactly as it does today.
- A row with a posted category shows "Keep …" under the dropdown. A row with no suggestion and nothing to confirm looks unchanged.
- It works in dark mode and at narrow widths: the button wraps and does not make the column wider.
````

## Verify after publish

No new key to grep, so verify by structure on a replayed month payload
(writes aborted, never on Criss's live rows): in the published
ExpensesReviewGrid chunk the confirm button renders inside the category cell
after the account `Select`; on a suggested row the vendor cell holds no
button and the category cell shows "Confirm <account>" with no "Suggested"
badge beside it. Clicking it must fire `POST .../confirm-category` (aborted).
