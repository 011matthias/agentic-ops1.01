# Lovable prompt: a date edit that moves the receipt says where it went (item 247)

> **NOT YET APPLIED.** Backend half ships with item 247: a `date` edit
> (`PUT /api/runs/{id}/expenses/{doc}`) or a typed-in expense
> (`POST /api/runs/{id}/expenses`) whose date names another calendar month
> moves the receipt there in the same request. Without this prompt the move
> still happens and the row leaves the month on the next refresh, but nothing
> says where it went and a month the move opened is missing from the months
> list until a reload.
>
> **Drive bundle-first.** Never type a date into a live month to test it: the
> edit moves a real receipt. Verify by the keys in the bundle, then by
> replaying a recorded `moved` reply through `route.fulfill`.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/ExpensesReviewGrid.tsx` (the `afterExpenseEdit` helper), `src/lib/api.ts` and `src/lib/i18n.tsx`. No new endpoint.

## Why

The owner: "the dates extracted from receipts are the foundation for how receipts get sent to months. So if the user changes the date, the month changes accordingly." The backend now does exactly that: when someone types a date (or clears a typed date, or adds an expense) and that date falls in another month, the receipt moves to that month in the same save. Today the row then silently disappears from the page.

## 1. `api.ts`

`ExpenseMutationResponse` (the reply of `updateExpenseField` and `addExpense`) gains three optional fields:

```ts
moved?: MoveExpenseMonthResponse;   // the existing type of the Move button's reply
move_held?: { held: "month_published"; month: string; label: string; batch_id: string };
move_error?: { error: string; code: string };
```

## 2. `afterExpenseEdit`

Both the field saver and the add dialog already call `afterExpenseEdit(queryClient, t, runId, res)`. Extend it, keeping everything it does today:

1. When `res.moved` is present:
   - also invalidate `["expense-batches"]` (the months list; the move may have opened a month) and `["expense-batch", res.moved.batch_id]`.
   - show the SAME toast the Move button shows today, built the same way: key `expx.review.monthMove.already` when `moved.already_in_batch`, else `expx.review.monthMove.opened` when `moved.created_batch`, else `expx.review.monthMove.done`; `{month}` = `moved.label`; with the same action button that navigates to `/expenses/$batchId` with `batchId = moved.batch_id`. Give `afterExpenseEdit` the router's `navigate` (an optional parameter, passed from the two callers) so the action can use it.
   - do not show the generic "updated" / "added" toast for that save; the move toast replaces it.
2. When `res.move_held` is present: `toast.info(t("expx.review.monthMove.held", { month: move_held.label }))`. The row stays and keeps its "Move to" offer.
3. When `res.move_error` is present: `toast.warning(t("expx.review.monthMove.failed", { error: move_error.error }))`. The date is saved; the row keeps its "Move to" offer.

## 3. The "Move to" offer

No change to the offer itself. Its comment in `api.ts` ("Present only when the reviewer typed a date belonging to another month") becomes: "Present when the row's date, typed or read from the receipt, lies outside this month's window."

## 4. Strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.review.monthMove.held` | {month} is published, so the receipt stays here for now | {month} está publicado, então o recibo fica aqui por enquanto |
| `expx.review.monthMove.failed` | Date saved, but the receipt could not be moved: {error} | Data salva, mas o recibo não pôde ser movido: {error} |
````
