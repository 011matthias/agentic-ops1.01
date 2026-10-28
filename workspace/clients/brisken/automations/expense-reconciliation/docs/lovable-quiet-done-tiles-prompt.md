# Lovable prompt: a month's done counts go small, the attention tiles stay big (item 231, note #97)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. Every count used here is already in `summary` (read live on
> September 2026, 2026-09-27).

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/ExpensesReviewGrid.tsx` (the summary tiles of the month's Expenses page and the `Tile` helper) and `src/lib/i18n.tsx` (new keys, EN and PT). No new field and no new request.

## Why

The owner left a note on September 2026's Expenses page (`/expenses/51a22ad72864`), just under "Review by exception. Ready rows can go out as is; the others need a look.":

"These filters inside months need to show the positive things ("categorized", "ready") small, and formatted with the obvious intent of enabling distinguishment from the stuff that needs user's attention"

Today the summary area is two grids of identical big tiles. September reads: Expenses 69 · Categorized 32 (green) · Needs category 37 (amber) · Ready 28 · Totals, then No company or person 18 (amber) · Private 2 · Missing receipt image 0. "Categorized 32" and "Ready 28" have the same size and weight as "Needs category 37", so the eye cannot tell at a glance what is done and what is waiting. A zero "Missing receipt image" is a big neutral 0.

The new shape, top to bottom:

1. **Context row**, neutral: the Expenses tile and the Totals tile, exactly as they are now.
2. **"Needs a look"**: a small amber label, then the attention tiles, full size, amber, only those with a count above zero.
3. **Done line**: one row of small chips with a check mark: "32 categorized", "28 ready", "Every receipt has its image", plus a plain neutral chip "2 private".

Every tile and chip keeps its filter behaviour: clicking it toggles `boxFilter` for its box, the active one is marked, and the Expenses tile still clears the filter.

## 1. `Tile`: one optional `attention` flag

Add an optional prop `attention?: boolean` to `Tile`. When true, the tile's frame gets an amber tint on top of its existing classes: `border-amber-500/40 bg-amber-500/5` (both the `<button>` and the `<div>` variant). The active state (`border-primary ring-1 ring-primary`) still wins when the tile is the active filter. Nothing else in `Tile` changes, and every existing caller that does not pass `attention` renders exactly as today.

## 2. A new `DoneChip` helper in the same file

Add a small component next to `Tile`:

```tsx
function DoneChip({
  children,
  tone = "done",
  help,
  onClick,
  active,
}: {
  children: React.ReactNode;
  tone?: "done" | "neutral";
  help?: string;
  onClick?: () => void;
  active?: boolean;
}) {
  const cls = cn(
    "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs tabular-nums",
    tone === "done"
      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300"
      : "border-border bg-muted/40 text-muted-foreground",
    onClick && "transition-colors hover:border-primary/60",
    active && "border-primary ring-1 ring-primary",
  );
  const inner = (
    <>
      {tone === "done" ? <Check className="h-3 w-3" aria-hidden /> : null}
      {children}
    </>
  );
  return onClick ? (
    <button type="button" className={cls} title={help} aria-pressed={!!active} onClick={onClick}>
      {inner}
    </button>
  ) : (
    <span className={cls} title={help}>
      {inner}
    </span>
  );
}
```

`Check` is already imported from `lucide-react` in this file.

## 3. The summary area, rebuilt from the same counts

Inside the `{/* Summary tiles */}` block, keep every count variable as it is (`nCategorized`, `nUncategorized`, `nReady`, `nCompanyOrPerson`, `nCostCenter`, `nPrivate`, `nMissingImage`, `nUnrenderable`, `boxTile`, `totalsByCcy`). They already follow the card tab. Only the markup moves.

**3a. Context row.** The first grid keeps only the Expenses tile and the Totals tile, both with their current props and content unchanged (the copies sub-line, the currency pills, the unreadable / copies / bills lines). Use `grid grid-cols-1 gap-3 sm:grid-cols-[minmax(10rem,1fr)_3fr]` so Totals takes the remaining width. The Categorized, Needs category and Ready tiles leave this grid.

**3b. "Needs a look".** Build the list of attention tiles from these, in this order, each rendered only when its count is above zero:

- Needs category: `nUncategorized`, `boxTile("uncategorized", nUncategorized)`, its current `sub` (the suggested-private count on older payloads) unchanged.
- No company or person: `nCompanyOrPerson`, with its current help and its clickable suggested-private `sub` unchanged. On an older payload where `n_needs_company_or_person` is not a number, the Missing entity and Needs person tiles take its place, exactly as today.
- Needs a cost center: `nCostCenter`.
- Missing receipt image: `nMissingImage`, only when `data.summary.has_image_info` is true.
- Receipts not in report: `nUnrenderable`, with its current help.

Every one of them passes `tone="warning"` and `attention`. If at least one renders, show above them a label `t("expx.review.attention.title")` in `text-[11px] font-medium uppercase tracking-wider text-amber-700 dark:text-amber-300`, then the tiles in `grid grid-cols-2 gap-3 sm:grid-cols-4`. If none renders, show instead one line `t("expx.review.attention.none")` in `text-xs text-emerald-700 dark:text-emerald-300` with a `CheckCircle2` icon (`h-3.5 w-3.5`) before it, and no empty grid.

**3c. Done line.** One `div` with `flex flex-wrap items-center gap-1.5` and `aria-label={t("expx.review.done.label")}`, holding, in this order:

- `<DoneChip tone={nCategorized > 0 ? "done" : "neutral"} {...boxTile("categorized", nCategorized)}>{t("expx.review.done.categorized", { n: nCategorized })}</DoneChip>`
- `<DoneChip tone={nReady > 0 ? "done" : "neutral"} help={t("expx.review.tile.readyHelp")} {...boxTile("ready", nReady)}>{t("expx.review.done.ready", { n: nReady })}</DoneChip>`
- only when `data.summary.has_image_info` is true and `nMissingImage === 0`: `<DoneChip>{t("expx.review.done.imagesComplete")}</DoneChip>` (not clickable; there is nothing to filter).
- only when `nPrivate > 0`: `<DoneChip tone="neutral" {...boxTile("private", nPrivate)}>{t("expx.review.done.private", { n: nPrivate })}</DoneChip>`. Private rows are decided, not waiting, so this chip is neutral grey without a check mark.

`boxTile(...)` returns `{ onClick, active }` only when rows carry `boxes` and the count is above zero, so a zero chip is a plain span: that is intended.

**3d. Order.** Context row, then "Needs a look" (or the "Nothing needs a look." line), then the done line, then `CategoriesByOriginLine` (when `cardTab === null`), then everything that follows today (the receipt coverage line, the filter strips, the grid) unchanged. The old second grid (`sm:grid-cols-4` with the Private and Missing receipt image tiles) is gone; its tiles now live in 3b and 3c.

## 4. `i18n.tsx`: new keys, both languages

| Key | EN | PT |
|---|---|---|
| `expx.review.attention.title` | Needs a look | Precisam do seu olhar |
| `expx.review.attention.none` | Nothing needs a look. | Nada precisa do seu olhar. |
| `expx.review.done.label` | Already in order | Já em ordem |
| `expx.review.done.categorized` | {n} categorized | {n} categorizadas |
| `expx.review.done.ready` | {n} ready | {n} prontas |
| `expx.review.done.private` | {n} private | {n} particulares |
| `expx.review.done.imagesComplete` | Every receipt has its image | Todos os recibos têm imagem |

Keep `expx.review.tile.categorized`, `expx.review.tile.ready`, `expx.review.tile.private` and `expx.review.tile.readyHelp`: search the project first, and if nothing else uses one of the first three, it may go; `readyHelp` stays (the Ready chip uses it).

## 5. Do not change

- How any count is computed, including the per-card-tab counts in `boxCount`.
- The strip that appears when a box filter is active (`expx.box.active` with its "Clear filter" button), the duplicates filter, the "not in report" filter and the vendor filter.
- The grid below: its Check / Pick / Ready groups, their headings and colours.
- The subtitle line and the reconciliation line above the tiles.

## Checking it landed

Read only; clicking a chip or tile only filters the grid, it writes nothing.

1. September 2026 Expenses (`/expenses/51a22ad72864`): the first row shows only Expenses and Totals. Below it an amber "NEEDS A LOOK" label and the big amber tiles Needs category and No company or person (37 and 18 when this was written; Criss's work moves them). Below that one small line: "✓ 32 categorized", "✓ 28 ready", "✓ Every receipt has its image", "2 private" (grey, no check). There is no big Categorized, Ready, Private or Missing receipt image tile.
2. Click "28 ready": the grid narrows to the ready rows, the chip shows the active ring and the strip above the grid names the filter with a "Clear filter" button. Click it again: the filter clears. Click "Needs category": the grid narrows to the uncategorized rows. Click the Expenses tile: the filter clears.
3. Pick a card tab on the same month: the tiles and chips show that card's counts, as they do today.
4. Switch to PT: "PRECISAM DO SEU OLHAR", "Sem categoria", "32 categorizadas", "28 prontas", "Todos os recibos têm imagem", "2 particulares".
5. At phone width (about 400 px) the chips wrap onto a second line and the attention tiles sit two per row.
````
