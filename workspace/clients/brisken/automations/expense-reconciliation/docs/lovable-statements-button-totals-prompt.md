# Lovable prompt: the statements toggle becomes a real button, the Totals amounts grow (items 241-242, notes #107-#108)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request, no new text key. Read live on August 2026, 2026-09-28 (GET only):
> 4 statements, one of them carrying an advisory; totals BRL 1,853.98,
> EUR 851.07, USD 1,574.95.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/StatementPanels.tsx` (`StatementSummary`, the statements toggle in the grey line under the month's tabs) and `src/components/ExpensesReviewGrid.tsx` (the currency amounts inside the Totals tile). No new field, no new request, no new text key.

## Why

The owner left two notes on August 2026's Expenses page (`/expenses/074a7b8905d7`):

- On the "4 statements ˅" toggle under the month's tabs: "make this an actual button"
- On the Totals tile: "need the actual number "tabs" to be larger"

Today the toggle is a `<button>` styled as dotted-underlined grey text, so it reads as part of a sentence rather than as a control. The Totals tile shows each currency as a small 12 px pill while the Expenses count beside it is 24 px, so the money reads smaller than the count.

## 1. `StatementSummary`: an outline button

In `src/components/StatementPanels.tsx`, inside `StatementSummary`, replace the toggle (the `<button type="button" onClick={() => setOpen(!open)} ...>` that renders `{t("stm.many", { k: rows.length })} {open ? "˅" : "›"}`) with:

```tsx
<Button
  type="button"
  variant="outline"
  size="sm"
  aria-expanded={open}
  onClick={() => setOpen(!open)}
  className={cn(
    "h-8 gap-1.5 text-xs",
    anyAdvisory && "border-amber-500/60 text-amber-700 dark:text-amber-300",
  )}
>
  <FileText className="h-3.5 w-3.5" aria-hidden />
  {t("stm.many", { k: rows.length })}
  <ChevronDown
    className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
    aria-hidden
  />
</Button>
```

Add `FileText` and `ChevronDown` to the file's existing `lucide-react` import; `Button` and `cn` are already imported. The "˅" and "›" characters go.

Everything else in `StatementSummary` stays: the toggle still starts open when a statement carries an advisory, it still opens the same `StatementsPanel` table below it, and a month with a single clean statement still shows its one plain line with no button.

This is the same look as the "View all statements loaded" button on the Matching page (outline, small, document icon, chevron).

## 2. Totals: the amounts at the size of the numbers beside them

In `src/components/ExpensesReviewGrid.tsx`, in the summary tiles block, the `Tile` labelled `t("expx.review.tile.totals")` renders one pill per currency from `totalsByCcy`. Change only those pills:

- the wrapper `div` around them: `flex flex-wrap items-center gap-1.5 pt-1` becomes `flex flex-wrap items-center gap-2 pt-1`
- each pill `span`: `inline-flex items-center rounded border bg-muted/40 px-1.5 py-0.5 text-xs tabular-nums` becomes `inline-flex items-baseline gap-1.5 rounded-md border bg-muted/40 px-2.5 py-1 text-xl font-semibold tabular-nums`
- the currency code `span` inside each pill: `mr-1 text-muted-foreground` becomes `text-xs font-medium text-muted-foreground`

The amount text is unchanged (the string from `totals_by_ccy`). The lines under the pills (amounts unreadable, copies set aside, bills) keep their small grey text.

## 3. Do not change

- What the statements toggle opens (`StatementsPanel`), its Download buttons, and when it starts open.
- The Matching page's own "View all statements loaded" button.
- How `totalsByCcy` is computed (it follows the card tab) and the amount strings.
- The Expenses tile, the "Needs a look" tiles and the done chips.

## Checking it landed

Read only: the toggle opens and closes a table, nothing is written.

1. August 2026 Expenses (`/expenses/074a7b8905d7`): under the tabs, the grey line shows an outline button with a document icon, "4 statements" and a chevron. It is amber-edged and starts open (chevron pointing up) because one of August's statements carries an advisory. Click it: the table closes and the chevron points down. Click again: it opens.
2. September 2026 Expenses (`/expenses/51a22ad72864`): the same button in grey, "3 statements", closed on load.
3. August's Totals tile: three pills "BRL 1,853.98", "EUR 851.07", "USD 1,574.95" (figures move with Criss's work), each amount in large bold digits close to the size of the Expenses count on its left, the currency code small and grey in front of it.
4. July 2026 Expenses (`/expenses/50622baec444`), the widest amounts ("USD 31,882.49"): the three pills fit on one line at desktop width; at phone width (about 400 px) they wrap onto a second line.
5. Pick a card tab: the pills show that card's totals, as they do today.
6. Switch to PT: the button reads "4 extratos"; the amounts are unchanged.
````
