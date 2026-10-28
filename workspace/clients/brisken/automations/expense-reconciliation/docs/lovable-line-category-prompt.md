# Lovable prompt: a category for each line that has none (note #64, item 136)

> **APPLIED 2026-09-17** (published 12:42 UTC, verified in `PROMPT-STATUS.md`). No backend change: `POST /api/runs/{id}/categories`
> with `line_index` already writes one line (probed 2026-09-17 on the current
> code: the pick clears `partial_uncategorized`). Note answered: #64 (Criss).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change in `src/components/ExpensesReviewGrid.tsx`. Render defensively: a row without `line_items` renders exactly as today.

## Why

Criss, on a receipt with two lines (Pressmaster FZCO 135.00: "Workspace / Team Member" 39.00 has a category, "CUSTOM" 96.00 has none): "I made the changes, refreshed, and it still asks for the category." The row's category dropdown shows the category of the line that has one, so picking that same value does nothing, and nothing on the row addresses a single line. The backend already takes a category for one line.

## 1. Pickers for the lines without a category

In the expense row's category cell, directly after the category `Select` (the one whose first item can be `CATEGORY_UNDO`) and before the `variance?.varies` chip:

- `const openLines = (row.line_items ?? []).filter((li) => !cleanText(li.category));`
- Render nothing when `(row.line_items?.length ?? 0) < 2` or `openLines.length === 0`. A one-line receipt keeps using the row dropdown.
- Otherwise render a block `mt-1 space-y-1 rounded border border-amber-500/30 bg-amber-500/5 p-1.5`:
  - a caption `text-[11px] font-medium text-amber-700 dark:text-amber-300`: `t(openLines.length === 1 ? "expx.lines.open.one" : "expx.lines.open.many", { n: openLines.length })`
  - one row per open line, `flex items-center gap-2 text-[11px]`: the line's `description` (`truncate max-w-[10rem]`, full text in `title`), its amount `fmtAmount(li.line_total, locale)` (`tabular-nums text-muted-foreground`), and a `Select` (`SelectTrigger className="h-6 w-40 text-[11px]"`, placeholder `t("expx.lines.pick")`, items = `options.category_options`).
- Picking a category calls the existing `postCategory(runId, { document_id: row.document_id, line_index: li.index, category: v })`, then `afterExpenseEdit(queryClient, t, runId)`. Disable that line's `Select` while its save is pending. On error, `toast.error(e.message)`.
- Use `li.index` from the payload, never the array position: the payload's `index` is the line's position on the receipt, and the filtered list skips lines.

When the last open line gets its category the block disappears on refetch, the row's reason line moves on (or the row is ready), and "Books as" loses its "(uncategorized - assign)" part. Nothing else has to change for that.

## 2. Do not change

The row's category dropdown and its Undo item (it still sets every line at once), `Keep "{category}"`, the "Books as" line, the variance chip, the account picker, every other cell.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `expx.lines.open.one` | 1 line on this receipt has no category | 1 linha deste recibo está sem categoria |
| `expx.lines.open.many` | {n} lines on this receipt have no category | {n} linhas deste recibo estão sem categoria |
| `expx.lines.pick` | Category for this line | Categoria desta linha |

## Checking it landed

1. August Expenses (`/expenses/074a7b8905d7`), Pressmaster FZCO 135.00: under its category dropdown, "1 line on this receipt has no category", then "CUSTOM Aug 23-Sep 23, 2026 · 96.00" with a "Category for this line" picker. Open the picker and close it with Escape; picking is Criss's.
2. PT: "1 linha deste recibo está sem categoria" and "Categoria desta linha".
3. A one-line receipt (OpenAI 80.04) shows no such block.
````
