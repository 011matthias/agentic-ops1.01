# Lovable prompt: a duplicate click uses the month its reply carries (owner 2026-10-07)

> **NOT YET APPLIED.** Owner, 2026-10-07: "removing duplicates takes way too
> long to load". The backend half (PR #1583, Fly v281) made the re-match a
> duplicate click waits for about twice as fast. This is the second half:
> after the reply, the page refetched `GET /api/expense-batches/{id}` and
> `GET /api/runs/{id}`, so the deleted row stayed on screen until both came
> back and the server built the month twice more. The backend now answers
> `DELETE /api/runs/{id}/expenses/{doc}?views=1` and
> `POST /api/runs/{id}/duplicates/resolve?views=1` with `views.batch` /
> `views.run`, equal to what those two GETs serve at that moment
> (`tests/test_duplicate_click_reply_views.py`).
>
> **Measured (local, September, server time from the click until the grid
> holds the new month, two rounds):** Delete this copy 3.96 / 4.41 s today vs
> 3.83 / 3.71 s with `views`; Not a copy 3.68 / 4.48 s vs 3.13 / 3.70 s. The
> reply takes longer (it builds the month), the refetch disappears, and the
> grid changes in one step instead of showing the old row until the refetch
> lands. Not a copy also starts refreshing the reconciliation line, which it
> left stale before.
>
> **Proven on a scratch clone** of SPA `735c7f9` + this prompt (`tsc` clean,
> node-server build) against a local API over the 2026-10-07 08:19 UTC backup:
> one "Not a copy" on September sent one `POST .../duplicates/resolve?views=1`;
> no `GET /api/expense-batches/{id}` or `GET /api/runs/{id}` followed (the same
> drive saw two of those during page load, so it can see them); the group's
> control left the grid (20 -> 19).
>
> **Safe in either order.** An older backend ignores the unknown `views`
> parameter and replies as before; the SPA then falls back to the refetch it
> does today.
>
> **Drive bundle-first.** Verify on a local build with the API route-guarded
> (`route.fulfill` replays, every non-GET aborted or answered from a recorded
> reply). Never click Delete or Not a copy on a live month to test it.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/lib/api.ts` and `src/components/ExpensesReviewGrid.tsx` only. No new endpoint, no new text, no layout change.

## Why

"Delete this copy" and "Not a copy" make the server re-check the whole month, and the button's spinner waits for that. When the reply arrives, the page throws away its copy of the month and downloads it again twice (`GET /api/expense-batches/{id}` for the grid, `GET /api/runs/{id}` for the reconciliation line), so the deleted row stays on screen for another one to several seconds and the server builds the month two more times. The backend can now put the updated month inside the reply. Use it, so the grid shows the result the moment the dialog closes.

## 1. `src/lib/api.ts`

1. `deleteExpense(runId, documentId)` calls `` `/api/runs/${runId}/expenses/${documentId}?views=1` `` (method `DELETE`, as today).
2. `resolveDuplicateGroup(runId, body)` calls `` `/api/runs/${runId}/duplicates/resolve?views=1` `` (method `POST`, same body as today).
   Only these two calls. Do not add `?views=1` to `resolveDuplicate` or to any other request.
3. Add this type:
   ```ts
   /** The month as the two page GETs would serve it right after the write. */
   export interface MonthViews {
     /** Exactly what getExpenseBatch(runId) returns. */
     batch?: ExpenseBatchDetail;
     /** Exactly what getRun(runId) returns. */
     run?: RunDetail;
   }
   ```
4. `ExpenseMutationResponse` gains `views?: MonthViews;`. The reply type of `resolveDuplicateGroup` becomes `{ ok: boolean; summary?: ExpenseBatchSummary; views?: MonthViews }`.

## 2. `src/components/ExpensesReviewGrid.tsx`

1. Import `MonthViews` from `@/lib/api`. Add this helper right above `afterExpenseEdit`:
   ```ts
   /** A duplicate click's reply carries the month it just re-matched
    *  (`views`). Put it straight into the cache; refetch only what the
    *  reply did not carry. */
   function applyMonthViews(
     queryClient: ReturnType<typeof useQueryClient>,
     runId: string,
     views?: MonthViews | null,
   ) {
     if (views?.batch) queryClient.setQueryData(["expense-batch", runId], views.batch);
     else queryClient.invalidateQueries({ queryKey: ["expense-batch", runId] });
     if (views?.run) queryClient.setQueryData(["run", runId], views.run);
     else queryClient.invalidateQueries({ queryKey: ["run", runId] });
     // Other months can lend this one receipts: mark them stale, refetch nothing now.
     queryClient.invalidateQueries({
       predicate: (q) => q.queryKey[0] === "expense-batch" && q.queryKey[1] !== runId,
       refetchType: "none",
     });
   }
   ```
2. `afterExpenseEdit`: replace its two `queryClient.invalidateQueries(...)` lines with `applyMonthViews(queryClient, runId, res?.views);` and add `views?: MonthViews` to the `{ rematch?: ... }` member of its `res` parameter type. Keep the "re-match failed" warning toast exactly as it is. Every other edit that calls `afterExpenseEdit` gets no `views` in its reply and so keeps refetching, exactly as today.
3. `DeleteExpenseDialog` needs no change: it already calls `afterExpenseEdit(queryClient, t, runId, res)`.
4. The two "Not a copy" mutations, the `ignore` mutation in `BoundGroupHeader` and the one in `DuplicateCell`, change their `onSuccess` from
   ```ts
   onSuccess: () => {
     toast.success(t("expx.dup.toast.ignored"));
     queryClient.invalidateQueries({ queryKey: ["expense-batch"] });
   },
   ```
   to
   ```ts
   onSuccess: (res) => {
     toast.success(t("expx.dup.toast.ignored"));
     applyMonthViews(queryClient, runId, res?.views);
   },
   ```

## What must not change

- The dialogs, buttons, spinners, toasts and every text stay as they are. The Delete dialog still waits for the reply before it closes.
- No optimistic removal: the grid only changes when the server's reply arrives.
- Every other mutation and query is untouched.

## Check

Open a month with a duplicate and click "Not a copy". In the browser's network panel there is ONE `POST .../duplicates/resolve?views=1` and NO `GET /api/expense-batches/{id}` and NO `GET /api/runs/{id}` after it, and the row's duplicate badge is gone as soon as the success toast shows. The same for "Delete this copy": one `DELETE ...?views=1`, no refetch, and the row is gone when the dialog closes.
````
