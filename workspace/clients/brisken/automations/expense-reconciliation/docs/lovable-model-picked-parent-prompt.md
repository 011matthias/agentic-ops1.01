# Lovable prompt: the refusal sentence for a summary account the model named (item 216 Build 2 step 1)

> **NOT PASTED.** SPA half of backlog item 216 Build 2 step 1 (PR #1447, Fly
> `2820e33c`). The backend is live and needs no SPA change to be correct: the
> app already falls back to the English `reason` for a refusal code it does not
> map, so without this prompt the row reads in English even in Portuguese. No
> live row carries the code yet; the first ones appear at a month's next
> re-match (receiptless charges) or on a newly categorized receipt.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`.

## Why

The tool no longer lets its automatic reading book an expense to a summary account that has more specific accounts under it (for example `E500010 IT: Computer and Internet Expenses`, which has Cloud Subscriptions, Hardware and other accounts under it). When the reading names one anyway, the row is refused with a new refusal code on the existing `review` object: `reason_code: "category_refused"`, `refusal: "model_picked_parent"`. The app already shows refusal sentences from `gl.refusal.<code>` and falls back to the backend's English `reason`, so today this row reads in English in both languages. Criss can still pick a summary account herself; the account picker is unchanged.

## Scope

`src/lib/i18n.tsx` only. Add one key to BOTH the English and the Portuguese dictionaries, next to the existing `gl.refusal.account_unresolved` entries. Change no component: `ExpensesReviewGrid.tsx` and `refusalText` in `GlAccountPicker.tsx` already look the key up.

| Key | EN | PT |
|---|---|---|
| `gl.refusal.model_picked_parent` | The tool's reading named a summary account with more specific accounts under it, so it was not used. Pick one by hand. | A leitura da ferramenta indicou uma conta sintética, que tem contas mais específicas abaixo dela, então ela não foi usada. Escolha uma manualmente. |

## Checks

1. `src/lib/i18n.tsx` carries `gl.refusal.model_picked_parent` in both dictionaries, and the English sentence is word for word the one above (it matches the backend's `reason`).
2. No other file changed.
````
