# Lovable prompt - a private expense is not told to set a company (item 220 step 7)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

A private expense (paid on someone's own card, reimbursed to a person) needs
no company: the to-do boxes already stop asking for one. On the months opened
on the Zoho accounts the category engine still refused such a row with "This
expense has no company yet, so no account was picked. Set the company, then
pick the account.", right beside the Private badge. The backend now names that
case with its own refusal code. Live: July's Brauhaus Kühler Krug and
September's DB Fernverkehr AG.

## 1. The field

`GET /api/expense-batches/{id}` -> `expenses[].review.refusal` gains one value,
`private_no_company`, on a row where `private` is true and `legal_entity_id`
is empty. Everything else on the row is unchanged: `review.state` stays
`"pick"`, `review.reason_code` stays `"category_refused"`, the boxes do not
move. `review.reason` carries the English sentence.

`reviewReason()` in `ExpensesReviewGrid.tsx` already renders
`gl.refusal.<refusal>` and falls back to `review.reason` when the key is
missing, so the row shows the English sentence today. The two keys below give
it its Portuguese.

## 2. i18n keys

| Key | EN | PT |
|---|---|---|
| `gl.refusal.private_no_company` | A private expense needs no company, so no account was picked. If a company should book it, set the company, then pick the account. | Uma despesa privada não precisa de empresa, então nenhuma conta foi escolhida. Se uma empresa deve lançá-la, defina a empresa e depois escolha a conta. |

## 3. Do not change

- `reviewReason()` itself, the `category_refused` branch, or any other
  `gl.refusal.*` key.
- The account picker (`gl.picker.noCompany` stays "Set the company first":
  it is the picker's own state, and a company set on a private row does get
  an account list).
- The Private badge, the reimbursement controls, the boxes.

## 4. Check after publishing

Open July 2026 (`/expenses/50622baec444`), row Brauhaus Kühler Krug, in PT:
the review line reads "Uma despesa privada não precisa de empresa ...", and
"Defina a empresa e depois escolha a conta" no longer opens the sentence.
