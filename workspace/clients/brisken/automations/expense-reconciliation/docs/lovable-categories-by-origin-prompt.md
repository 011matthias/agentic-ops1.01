# Lovable prompt: who answered the month's categories (item 216 Build 2 step 3)

> **NOT PASTED.** SPA half of item 216 Build 2 step 3 (backend: the PR that
> adds `summary.categories_by_origin`). Additive: until it is pasted the SPA
> shows exactly what it shows today. Independent of
> `docs/lovable-model-suggests-prompt.md` (the "Suggested" badge and its
> Confirm), which should be pasted first; both can go in one publish.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`.

## Why

Both month payloads now say who answered the categories: `summary.categories_by_origin = { person, rule, suggestion, none }`, four integers, always all present. On the Expenses tab they sum to `summary.n_expenses`; on the Matching tab they sum to the number of rows. The month's readiness pill does NOT change: `n_charges_category_guessed` keeps its meaning (the guesses that still block the month), so leave `monthBlockers` exactly as it is.

## Scope

`src/lib/api.ts`, `src/components/ExpensesReviewGrid.tsx`, `src/components/RunWorkbench.tsx`, `src/lib/i18n.tsx`. No other file. Show the numbers the backend sends; never count rows yourself.

## 1. Types (`src/lib/api.ts`)

- `export type CategoriesByOrigin = { person: number; rule: number; suggestion: number; none: number };`
- `RunSummary` and `ExpenseBatchSummary` each gain `categories_by_origin?: CategoriesByOrigin` (absent on an older backend).

## 2. One line on each tab

Add a small component `CategoriesByOriginLine({ split })` (put it in `RunWorkbench.tsx` and export it). It renders one muted text line (`text-sm text-muted-foreground`): the label `t("sum.byOrigin.label")`, a colon, then the non-zero parts joined with ` · `, in this order: `t("sum.byOrigin.person", { n })`, `t("sum.byOrigin.rule", { n })`, `t("sum.byOrigin.suggestion", { n })`, `t("sum.byOrigin.none", { n })`. A part whose count is 0 is left out. Render nothing when `split` is undefined or all four are 0.

- Matching tab (`RunWorkbench.tsx`): directly under `<StatusLine summary={summary} />`, render `<CategoriesByOriginLine split={summary.categories_by_origin} />`.
- Expenses tab (`ExpensesReviewGrid.tsx`): directly under the row of box tiles (the one holding the categorized / needs-category tiles), render `<CategoriesByOriginLine split={data.summary.categories_by_origin} />`, but ONLY when no card tab is selected (`cardTab === null`). The split counts the whole month, and inside a card tab the tiles count that card only, so the two would disagree.

## 3. Strings (`src/lib/i18n.tsx`, both languages)

| Key | English | Portuguese |
|---|---|---|
| `sum.byOrigin.label` | Who answered the categories | Quem respondeu as categorias |
| `sum.byOrigin.person` | {n} by a person | {n} por uma pessoa |
| `sum.byOrigin.rule` | {n} by a rule | {n} por uma regra |
| `sum.byOrigin.suggestion` | {n} suggested by the model | {n} sugeridas pelo modelo |
| `sum.byOrigin.none` | {n} without a category | {n} sem categoria |

## 4. Check before you finish

Open September 2026. On the Matching tab, under the readiness pill, one line reads "Who answered the categories: …", and its numbers equal `summary.categories_by_origin` in the `GET /api/runs/{id}` response. On the Expenses tab with no card selected, the same kind of line sits under the box tiles and matches `GET /api/expense-batches/{id}`; selecting a card tab hides it. The readiness pill's text is unchanged. EN and PT both render, no console errors.
````
