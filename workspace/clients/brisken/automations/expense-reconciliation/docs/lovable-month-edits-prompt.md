# Lovable prompt - Changes in a month that did not stick (item 70)

Paste this into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Criss wrote on 2026-09-14 (July): "when I open the category and set the right
one, nothing happens... it stays uncategorized even after a refresh." Three
things caused it, and the backend fixed all three:

- A category set on a **needs review** row's candidate was saved but never
  shown, because the row had no confirmed receipt to read it from.
- On a month that has a bank statement, every edit on **Review expenses**
  (company, category, account, paid through, cost center, amount, date,
  vendor, add, delete, private) was refused. Both live months have a
  statement, so none of it could be set anywhere. The backend now takes those
  edits all month, and when an edit can change which receipt pairs with which
  charge it re-matches the month before it answers.
- **Reclassify** in the workbench changed only line 0 of a receipt (a 33-line
  Lidl receipt ended up with two categories) and kept the old account.

This prompt is the page half.

## 1. Review expenses: unlock the grid on statement months

File: `src/components/ExpensesReviewGrid.tsx`.

- Remove the lock on the grouped tables: the `<fieldset disabled={hasStatement}>`
  wrapper (and its `hasStatement && "opacity-90"` class) around the grouped
  tables. Every control in the grid stays enabled whether or not
  `has_statement` is true. Keep **View receipt** clickable, as it is now.
- Do not remove anything else that reads `hasStatement` (the statement banner
  and the attach / add-statement controls stay as they are).

## 2. Refresh both screens after every edit

The same receipt shows on Review expenses AND in the reconciliation
workbench, and an edit on a statement month can move a charge in the
workbench. After every SUCCESSFUL expense edit, invalidate BOTH queries:

```ts
queryClient.invalidateQueries({ queryKey: ["expense-batch", runId] });
queryClient.invalidateQueries({ queryKey: ["run", runId] });
```

Apply this to every mutation that calls one of these api functions:
`updateExpenseField`, `updateExpenseEntity`, `setExpensePrivate`,
`addExpense`, `deleteExpense` (today they invalidate only
`["expense-batch", runId]`; in `useFieldSaver`, the entity mutation, the
delete dialog, the add dialog and `PrivateExpenseCell`). `runId` and the
batch id are the same id.

## 3. Say so when the month could not be re-matched

The five expense-edit responses can now carry `rematch`, parallel and
**absent** when nothing re-matched (a month with no statement, or a field
that does not affect matching such as category, tax or cost center):

```json
{ "ok": true, "summary": { "...": "..." },
  "rematch": { "n_transactions": 111, "n_matched": 15, "n_review": 7,
               "n_unmatched_tx": 89, "n_refunds": 0 } }
```

When the re-match failed, the edit is still saved and `rematch` is
`{ "error": "RuntimeError: ..." }`. Add to `ExpenseMutationResponse` in
`src/lib/api.ts`:

```ts
rematch?: { error?: string; [key: string]: unknown };
```

In every mutation listed in §2, on success: if `res.rematch?.error` is a
non-empty string, show a warning toast `expx.review.toast.rematchFailed`
with `{error}` filled in. Otherwise behave exactly as today.

## 4. Workbench Reclassify: the whole receipt, and show the current value

File: `src/components/RunWorkbench.tsx`, `CandidateRow`, the Reclassify select
(`onValueChange={(v) => onCategory(0, v)}`).

- Send **no `line_index`**. The backend then applies the category to every
  line of that receipt. In `src/lib/api.ts` make `line_index` optional on
  `postCategory` (`line_index?: number`) and in `RunWorkbench` change the
  `category` mutation and `onCategory` so the Reclassify select sends only
  `{ document_id, category }`.
- Make the select show the current category as its `value`: the row's
  `posting_category.category` when this candidate is the one the row holds or
  would take (`candidate.is_chosen`, or the row carries
  `posting_category_proposed` and this is the first candidate), otherwise the
  candidate receipt's `receipt.line_items[0].category`. Leave it empty when
  neither exists. When `posting_category.category` holds several categories
  joined with `"; "`, show the placeholder instead of a value.
- Change the label copy `wb.candidate.reclassify` from "Reclassify line 0:" to
  "Reclassify:" (PT "Reclassificar:").
- After a successful reclassify, invalidate the run query (`["run", runId]`),
  which the existing `invalidate()` already does; keep that, and also
  invalidate `["expense-batch", runId]` so Review expenses shows the new
  category.

## 5. A proposed category on a needs-review row

`GET /api/runs/{id}` -> `rows[].posting_category_proposed`, parallel and
**absent** (never `false`) unless the row's `posting_category` came from the
candidate the Confirm button would take rather than from a confirmed receipt:

```json
"posting_category": { "category": "Software & Subscriptions",
                      "zoho_account": "", "source": "EDITED" },
"posting_category_proposed": true
```

Where the row renders `posting_category`, when `posting_category_proposed` is
`true`, render the category as usual and add a muted note under it:
`wb.category.proposedNote`. Nothing else about the row changes: it is still a
needs-review row, the Confirm button still decides, and no count moves.

## 6. i18n keys

| Key | EN | PT |
|---|---|---|
| `expx.review.toast.rematchFailed` | Saved; the month could not be re-matched yet: {error} | Salvo; o mês ainda não pôde ser reconciliado novamente: {error} |
| `wb.category.proposedNote` | applies when you confirm this match | vale quando você confirmar esta correspondência |
| `wb.candidate.reclassify` (changed) | Reclassify: | Reclassificar: |

## 7. Do not change

- The Confirm, Reject and Match buttons, `candidates[].is_chosen`, buckets,
  sections and every summary count keep their meaning.
- The expense grid's category / account selects keep sending the generic
  `PUT /api/runs/{id}/expenses/{doc}` with `field: "category"` or
  `field: "zoho_account"`, as today.
- A category change without an account now clears the account chosen for
  the old category on the backend. Do not send the old account back along
  with a new category.
- Auth, the API base URL and the query keys other than the two named above.
