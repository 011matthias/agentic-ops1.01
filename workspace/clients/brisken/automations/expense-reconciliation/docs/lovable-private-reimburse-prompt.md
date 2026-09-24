# Lovable prompt: a private expense asks who gets reimbursed (item 175), and the months list says what "From email" means (item 174)

> **NOT PASTED.** Backend for both is already live: item 175 needs no new
> field (`reimburse_to`, `reimburse_to_prefill` and `private` are all on the
> row today), and item 174 needs none either (`created_by` is already on the
> month). Item 176 shipped 2026-09-24 and is a precondition for section 1:
> before it, `POST .../private` refused a second `{private: true}` on a row
> that was already private.
>
> Written against the published bundle of 2026-09-24
> (`assets/chunk-expenses._batchId-7cO7KDYP.js`,
> `assets/chunk-months-D64oN5EB.js`), so the component behaviour described
> below is what the app does today, not what it is assumed to do.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. No new backend fields are needed: everything below already ships on the payload. Render defensively; a row or month missing a field renders exactly as today.

## Why

Two notes from the same week, both about a label saying something the data does not.

The operator, on a private expense (PT): *"No privado, deve haver quem deve reembolsar a despesa"* ("on a private one, there must be someone who has to reimburse the expense"). The card cell asks which company and which card paid. On a private expense the company did not pay, so neither question has an answer; the one that matters is who gets paid back.

The owner, on the months list: *"why does it say this even though there has been no statement sent for this month"*. September has no statement at all and the badge that reads "From email" is not about a statement; it is about how the month's receipts arrived. It reads as a statement claim because it sits in the same cell as the statement badge.

## 1. Let the reviewer correct who gets reimbursed, without undoing

Today the reimburse field is reachable exactly once, on the way in. The private dialog that holds it is rendered inside the card picker, and the card picker returns `null` as soon as `row.private` is true. So once a row is confirmed private the only way to change the name is to undo the private mark and set it again, which throws away the decision to change one word in it.

On a confirmed private row (`row.private === true`), the private badge currently renders as the badge `expx.private.badge` plus the undo button `expx.reimburse.undo`. Add a third control between them: a small ghost button labelled `expx.reimburse.edit` that opens the SAME private dialog the card picker opens, with the input pre-filled from `row.reimburse_to`, and saves with the same call the dialog already makes:

```
POST /api/runs/{runId}/expenses/{documentId}/private
{ "private": true, "reimburse_to": "<the new name>" }
```

The dialog needs one change to serve both entries: it pre-fills from `row.reimburse_to_prefill || row.person`, which is right on the way in and wrong on a correction. Pre-fill from `row.reimburse_to` first when the row is already private, then fall back to the existing pair. Keep the prefill help line (`expx.private.prefillHelp`) only when the value came from `reimburse_to_prefill`; on a correction it is describing the wrong thing.

To reach the dialog from the badge, lift it out of the card picker so both components can open it, or render a second copy next to the badge. Either is fine; do not duplicate the mutation.

## 2. Put the private option first on a row the tool already thinks is private

In the card select, the "Paid with a private card" option (`expx.privateCard.mark`) sits last, after a separator, below every company card. On a row where `row.suggested_private === true` the tool is itself saying no company card matches the payment method, so the answer it expects is the one it has buried.

When `row.suggested_private === true`, render that option FIRST, above the card list, with the separator below it instead of above. Leave the order exactly as it is on every other row: on a row with a real card the private option is the exception and belongs at the bottom.

## 3. Do not gate the new control on `can_mark_private`

As of 2026-09-24 `can_mark_private` is false on a row that IS private, which is the whole of item 176: the tool no longer offers to mark private something already marked private. Both controls in section 1 key on `row.private`, never on `can_mark_private`. The existing helper that reads `can_mark_private` (with its `row.card == null` fallback) stays exactly as it is and keeps gating the picker's private option on rows that are not yet private.

## 4. The months list: say what the badge is about

On the months list the origin badge renders `months.origin.intake` ("From email") when `month.created_by === "intake"` and `months.origin.drop` when it is `"drop"`. It is correct and it is about receipts, but it renders inside the same table cell as, and immediately before, the statement badge `months.state.matchedStatement`, so it reads as a claim about a statement.

Two changes:

* Re-word both to name receipts: see the strings table.
* Move the origin badge out of the statement cell. Put it under the month's name in the first column, in the same muted style it has now. The statement cell then holds statement state only.

Nothing about `created_by` changes, and a month whose `created_by` is absent still renders no badge.

## 5. The Paid Through cell prints the private label twice

This is the duplicate the operator saw, "Private (Dirk Neumann)Private (Dirk Neumann)", and it is in the Paid Through column, not in either private control. The cell renders the resolved value twice: once as a plain `<div class="px-1 text-sm text-foreground">` inside the cell's `flex flex-col gap-1` wrapper, and once as the `<span>` inside the account select's `role="combobox"` trigger. On an ordinary row those two carry different text, or the static line is absent; on a private row both resolve to `Private ({person})` and collide.

Measured on the live September month, 2026-09-24: of 80 rows on the page, exactly ONE has a repeated string in that cell, and it is the private one. So this is not a general Paid Through problem to redesign; it is one collision to remove.

Render one of the two, never both: when the static line's text equals the select trigger's current value, drop the static line. Do not special-case the word "Private", and do not remove the select, which is how the account gets changed on every other row.

## 6. Do not change

The undo button and what it posts. The private badge's own text. The refusal messages the backend returns. The card picker on any row that is not private. Every count, every other cell of the months list.

## New and changed strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.reimburse.edit` (new) | Change who is reimbursed | Alterar quem recebe o reembolso |
| `expx.private.editTitle` (new) | Who gets reimbursed | Quem recebe o reembolso |
| `months.origin.intake` (changed) | Receipts by email | Recibos por e-mail |
| `months.origin.drop` (changed) | Receipts uploaded | Recibos enviados |
````
