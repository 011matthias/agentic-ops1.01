# Lovable prompt: the model's account is a labelled suggestion (item 216 Build 2 step 4)

> **NOT PASTED.** SPA half of item 216 Build 2 step 2 (owner ruling
> 2026-09-25, backend PR #1451, Fly `e3f0eb1f`). The backend is live and
> correct on its own: the model's account no longer reaches `expenses.csv` or
> any file as an account. Until this is pasted, the published grid shows those
> rows with an empty category and hides their Confirm button (it reads
> `posting_category.category`, which is now empty on them): Criss can still
> pick an account by hand, but the one-click Confirm is unreachable. The
> `model_picked_parent` refusal sentence is a separate prompt,
> `docs/lovable-model-picked-parent-prompt.md` (#1449).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`.

## Why

On a month categorized in Zoho accounts, the owner ruled that the model only suggests an account; a rule or a person decides it. The backend now keeps the model's answer out of `posting_category` and sends it in a new parallel field, `suggested_category`. Such a row reads `review.reason_code: "model_suggestion"` (or `vendor_guess`) and `category_confirmable: true`, and one click on the existing Confirm (`POST /api/runs/{runId}/expenses/{documentId}/confirm-category`) makes it a posting. The screen must show the suggestion, clearly labelled as one, with its Confirm button.

## Scope

`src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx`, `src/components/RunWorkbench.tsx`, `src/lib/i18n.tsx`. No other file. Do not compute anything the backend does not send: never derive "suggestion" from `source`, read the fields.

## 1. Types (`src/lib/api.ts`)

- A shared type `SuggestedCategory = { category: string; zoho_account: string; source: string; origin?: "suggestion" }`.
- `ExpenseRow` gains `suggested_category?: SuggestedCategory` (ABSENT when there is none). `ExpensePostingCategory` gains `origin?: "person" | "rule" | "suggestion" | null`. `posting_category` can now be `null` on a row that has a `suggested_category`.
- The run row type (the one with `posting_category?: {category, zoho_account, source} | null`) gains `suggested_category?: SuggestedCategory` and the same optional `origin` on `posting_category`.
- `ExpenseBooksAsPart` gains `suggested?: boolean` (ABSENT unless true). When true, its `account` starts with the literal `suggested: `.

## 2. Expenses grid, category cell (`ExpensesReviewGrid.tsx`)

- Keep the account picker exactly as it is. When `row.posting_category` is null and `row.suggested_category` is present, render under the picker one line: a small amber outline badge reading `t("expx.suggestion.label")`, then the account name `suggested_category.zoho_account` (fall back to `suggested_category.category` when the name is empty), with the code `suggested_category.category` in the `title` tooltip. The same line style the variance chip uses; no new colours.
- When a row has BOTH (some lines decided, some suggested), the picker shows `posting_category` as today and the suggestion line shows under it.
- `KeepCategoryButton`: take the category from `row.posting_category?.category`, else `row.suggested_category?.category`, and the shown name from the matching `zoho_account` (else the category). Keep the condition `row.category_confirmable === true` and a non-empty name. When the name came from `suggested_category`, the label is `t("expx.suggestion.confirm", { account })`; otherwise the existing `expx.category.keep` label. Same mutation, same toasts.
- `books_as` (rendered on split rows): for a part with `suggested === true`, strip the leading `suggested: ` from `account` and render the badge `t("expx.suggestion.label")` before it.
- The review line: `reviewReason` must return `t("expx.review.reason.model_suggestion")` for `reason_code: "model_suggestion"`, falling back to `review.reason` if the key is missing, exactly like the other codes.

## 3. Matching tab (`RunWorkbench.tsx`)

- `PostingCategoryCell`: pass `row.suggested_category ?? null` as a new optional prop `suggested`. When `pc` is null and `suggested` is present, render the same amber badge `t("expx.suggestion.label")` followed by the account name (code in the tooltip), instead of the empty state. When both are present, show `pc` as today and the suggestion line under it. `proposed` keeps its current meaning for both.
- `ChargeCategoryCell` (receiptless rows): when `row.charge_category?.origin === "suggestion"`, put the same badge before the category it already shows. Nothing else changes there.
- The "uncategorized" filter: a row with a `suggested_category` is not uncategorized. Change `if (f.uncategorized && row.posting_category) return false;` to `if (f.uncategorized && (row.posting_category || row.suggested_category)) return false;`.

## 4. Strings (`src/lib/i18n.tsx`, both languages)

| Key | English | Portuguese |
|---|---|---|
| `expx.suggestion.label` | Suggested | Sugerida |
| `expx.suggestion.confirm` | Confirm {account} | Confirmar {account} |
| `expx.review.reason.model_suggestion` | The model suggested this account from the receipt's lines. Confirm it, or pick another, before it posts. | O modelo sugeriu esta conta a partir dos itens do recibo. Confirme-a ou escolha outra antes do lançamento. |

## 5. Check before you finish

On September 2026 (Expenses tab), a row whose review line reads the new sentence shows the amber "Suggested" badge with an account name under an empty picker, and a "Confirm <account>" button. Clicking it re-fetches the month: the picker now holds that account, the badge and the button are gone. A row a person already picked shows no badge. The Matching tab renders every row; the "uncategorized" filter no longer lists rows that carry a suggestion. No console errors, EN and PT both render the new strings.
````
