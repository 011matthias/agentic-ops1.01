# Lovable prompt: every page fits the screen, nothing is cut off (backlog item 247, owner 2026-10-07)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request, no new text key. Owner, 2026-10-07: "i need all pages to
> successfully adapt to users screen size and maintain 100% visability of all
> the content." Builds on the owner's own Lovable pass the same morning
> (`aef936db` "Made months pages responsive", `0ac4b07a` "Set full-width page
> layout"), and undoes one part of it: the `overflow-x-clip` it put on the two
> month screens hides content instead of fitting it.
>
> **Measured before (SPA `0ac4b07`, local build, local API over the
> 2026-10-06 20:40 UTC backup, 21 routes x EN/PT x 7 widths 360-1920):**
> 1,379 page views (21 routes x EN/PT x 7 widths, each in its default
> state, every filter tile / tab one at a time, everything expanded, and
> the receipt + compare-copies dialogs open). Findings (capped at 40 per kind
> per view, so lower bounds): 7,664 cut off by a clipping box, 1,053 past the
> screen edge, 1,705 shortened with an ellipsis or clip, 445 behind a
> sideways scroll, the whole page wider than the screen in 102 views. The
> worst: August's Expenses grid is cut off at every width below 1920. The
> published SPA already carries the `overflow-x-clip` (live bundle read
> 2026-10-07: 5 hits in the ExpensesReviewGrid chunk), so this is what Criss
> sees today.
>
> **Proven on a scratch clone** (`0ac4b07` + this prompt's code, `vite build`
> + `tsc` green, node-server preset, same data, every non-GET aborted):
> the same 1,379 views read **zero** in every kind. Tables fit as tables
> where whole words fit (August's grid from 1280 px) and become labelled
> cards where they do not (1024 px and below). Driven at 390 px: a category
> dropdown inside a card opens with its 68 options, the receipt viewer opens
> inside the screen, no page error, no write attempted.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. This is a layout-only change: no new field, no new request, no new text key, and every button, select and link keeps its click handler, props and wording.

## Why

Every page must fit the screen it is opened on, from a 360 px phone to a 1920 px monitor, with 100% of its content visible: nothing cut off at an edge, nothing hidden behind a sideways scroll, no text shortened with "…". Measured today across all pages at 7 widths:

- On a month's Expenses page the review grid is about 1,700 px wide. It sits in a `<fieldset>`, and a fieldset never gets narrower than its content, so the grid pushes past the page. The `overflow-x-clip` added to `<main>` this morning then cuts it off with no way to reach it: at 1280 px the Legal entity, Paid through, Receipt and Actions columns are simply not there. Same at every width below 1920.
- On phones the Matching page, the Statements panel and Memory run off the right edge of the page.
- About 30 places shorten text with `truncate` (file names, line items, account names, subjects, "Signed in as"), and dropdowns clip their selected value ("Chase Visa | 9693 | Cloud Expenses").
- Buttons never wrap their label, so a long one ("Confirm CorpServ | Travel Expense | Transportation") pokes out of its cell.
- The Settings tabs and the Email intake table need a sideways scroll, and the scrollbar of the Settings tabs is hidden.

## 1. New file `src/lib/fit-tables.ts`: tables become cards when their columns do not fit

Create this file exactly:

```ts
/**
 * Every <table> in the app shows as a normal table while its columns fit the
 * space it has, and switches to stacked cards (one card per row, each value
 * under its column name) as soon as they do not. Nothing scrolls sideways and
 * nothing is cut off, at any screen width.
 *
 * Installed once from the root component. It finds tables as they appear,
 * re-checks one when its container resizes or its content changes, and works
 * the same for the shadcn <Table> and for plain <table> markup.
 *
 * The check always measures the table in its normal layout (the stacked flag
 * is lifted, measured, and restored inside one frame, before anything paints),
 * so a table goes back to columns the moment the screen is wide enough again.
 */

const STACKED = "data-stacked";

function columnLabels(table: HTMLTableElement): string[] {
  const head = table.tHead;
  const row = head && head.rows.length ? head.rows[head.rows.length - 1] : null;
  const labels: string[] = [];
  if (!row) return labels;
  for (const cell of Array.from(row.cells)) {
    const text =
      (cell.textContent || "").replace(/\s+/g, " ").trim() ||
      cell.getAttribute("aria-label") ||
      cell.getAttribute("title") ||
      "";
    labels.push(text);
    for (let i = 1; i < (cell.colSpan || 1); i++) labels.push("");
  }
  return labels;
}

function labelCells(table: HTMLTableElement) {
  const labels = columnLabels(table);
  const n = labels.length;
  const rows: HTMLTableRowElement[] = [];
  for (const body of Array.from(table.tBodies)) rows.push(...Array.from(body.rows));
  if (table.tFoot) rows.push(...Array.from(table.tFoot.rows));
  for (const row of rows) {
    let col = 0;
    for (const cell of Array.from(row.cells)) {
      const span = cell.colSpan || 1;
      const fullRow = n > 0 && span >= n;
      const label = fullRow ? "" : labels[col] || "";
      if (cell.getAttribute("data-label") !== label) cell.setAttribute("data-label", label);
      if (fullRow) {
        if (!cell.hasAttribute("data-full")) cell.setAttribute("data-full", "");
      } else if (cell.hasAttribute("data-full")) {
        cell.removeAttribute("data-full");
      }
      col += span;
    }
  }
}

function tooWide(table: HTMLTableElement): boolean {
  const r = table.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return false; // not shown right now
  const parent = table.parentElement;
  if (!parent) return false;
  const ps = getComputedStyle(parent);
  const inner =
    parent.clientWidth - (parseFloat(ps.paddingLeft) || 0) - (parseFloat(ps.paddingRight) || 0);
  // Wider than the box it sits in.
  if (table.offsetWidth > inner + 1) return true;
  // The box grew to hold it and now runs past the screen or a clipping box.
  const vw = document.documentElement.clientWidth;
  if (r.right > vw + 1) return true;
  for (let p: HTMLElement | null = parent; p && p !== document.body; p = p.parentElement) {
    if (getComputedStyle(p).overflowX !== "visible") {
      if (r.right > p.getBoundingClientRect().right + 1) return true;
      break;
    }
  }
  return false;
}

function fit(table: HTMLTableElement) {
  if (!table.isConnected) return;
  if (table.hasAttribute(STACKED)) table.removeAttribute(STACKED);
  if (tooWide(table)) {
    labelCells(table);
    table.setAttribute(STACKED, "");
  }
}

export function installTableFit(): () => void {
  if (typeof window === "undefined" || typeof ResizeObserver === "undefined") return () => {};
  const tables = new Set<HTMLTableElement>();
  const byContainer = new Map<Element, Set<HTMLTableElement>>();
  const pending = new Set<HTMLTableElement>();
  let frame = 0;

  const flush = () => {
    frame = 0;
    const list = Array.from(pending);
    pending.clear();
    for (const t of list) {
      if (!t.isConnected) {
        tables.delete(t);
        for (const [c, set] of byContainer) {
          if (set.delete(t) && set.size === 0) {
            ro.unobserve(c);
            byContainer.delete(c);
          }
        }
        continue;
      }
      fit(t);
    }
  };
  const schedule = (t: HTMLTableElement) => {
    pending.add(t);
    if (!frame) frame = requestAnimationFrame(flush);
  };
  const ro = new ResizeObserver((entries) => {
    for (const e of entries) byContainer.get(e.target)?.forEach(schedule);
  });
  const watch = (t: HTMLTableElement) => {
    if (!tables.has(t)) {
      tables.add(t);
      const c = t.parentElement;
      if (c) {
        const set = byContainer.get(c);
        if (set) set.add(t);
        else {
          byContainer.set(c, new Set([t]));
          ro.observe(c);
        }
      }
    }
    schedule(t);
  };
  const mo = new MutationObserver((records) => {
    for (const rec of records) {
      const target =
        rec.target instanceof Element ? rec.target : (rec.target as Node).parentElement;
      const inTable = target?.closest("table");
      if (inTable) watch(inTable as HTMLTableElement);
      for (const node of Array.from(rec.addedNodes)) {
        if (!(node instanceof Element)) continue;
        if (node.tagName === "TABLE") watch(node as HTMLTableElement);
        node.querySelectorAll("table").forEach((t) => watch(t as HTMLTableElement));
      }
    }
  });
  document.querySelectorAll("table").forEach((t) => watch(t as HTMLTableElement));
  mo.observe(document.body, { childList: true, subtree: true, characterData: true });
  const onResize = () => tables.forEach(schedule);
  window.addEventListener("resize", onResize);

  return () => {
    mo.disconnect();
    ro.disconnect();
    window.removeEventListener("resize", onResize);
    if (frame) cancelAnimationFrame(frame);
  };
}
```

## 2. `src/routes/__root.tsx`: install it once

Add the import next to the other `@/lib` imports:

```tsx
import { installTableFit } from "@/lib/fit-tables";
```

and make `RootComponent` start it:

```tsx
function RootComponent() {
  useEffect(() => installTableFit(), []);
  return (
    <RootProviders>
      <Outlet />
    </RootProviders>
  );
}
```

(`useEffect` is already imported in this file.)

## 3. `src/styles.css`: the stacked-card look

Append this block at the very END of `src/styles.css`, OUTSIDE any `@layer` (it must stay unlayered so it wins over the cells' width, alignment and nowrap utilities while a table is stacked):

```css
/*
 * Stacked tables. src/lib/fit-tables.ts sets data-stacked on any table whose
 * columns do not fit the space it has; each row then shows as a card and each
 * value under its column name (data-label). Unlayered on purpose, so it wins
 * over the width/alignment/nowrap utilities the cells carry in table layout.
 */
table[data-stacked],
table[data-stacked] > tbody,
table[data-stacked] > tfoot {
  display: block;
  width: 100%;
}
table[data-stacked] > colgroup {
  display: none;
}
/* The header row hides, except a header cell that holds a control (a
   select-all box, an info tip): those stay as a strip above the cards. */
table[data-stacked] > thead {
  display: block;
}
table[data-stacked] > thead > tr {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  border: 0;
}
table[data-stacked] > thead > tr > th {
  display: none;
}
table[data-stacked] > thead > tr > th:has(button, input, [role="checkbox"], [data-state]) {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: auto;
  height: auto;
  padding: 0 0 0.5rem;
}
table[data-stacked] > tbody > tr,
table[data-stacked] > tfoot > tr {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 13rem), 1fr));
  gap: 0.25rem 1rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}
table[data-stacked] > tbody > tr > :is(td, th),
table[data-stacked] > tfoot > tr > :is(td, th) {
  display: block;
  width: auto;
  min-width: 0;
  max-width: none;
  height: auto;
  padding: 0.25rem 0;
  text-align: left;
  white-space: normal;
  overflow-wrap: anywhere;
}
table[data-stacked] > tbody > tr > :is(td, th):empty {
  display: none;
}
/* Inside a card nothing runs past its cell: a fixed-width control (`w-56`
   picker) shrinks to the cell, and a row of chips or controls wraps. */
table[data-stacked] > tbody > tr > :is(td, th) * {
  max-width: 100%;
}
table[data-stacked] > tbody > tr > :is(td, th) .flex {
  flex-wrap: wrap;
}
table[data-stacked] :is(td, th)[data-full] {
  grid-column: 1 / -1;
}
table[data-stacked] :is(td, th)[data-label]:not([data-label=""])::before {
  content: attr(data-label);
  display: block;
  margin-bottom: 0.125rem;
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1rem;
  color: var(--muted-foreground);
}
```

## 4. `src/lib/utils.ts`: one helper

Add this function below `cn`:

```ts
/** A control whose text may wrap onto a second line keeps the height a caller
 *  asks for (`h-7`) as a minimum (`min-h-7`), so it looks the same on one line
 *  and grows instead of spilling when its text wraps. */
export function heightAsMinimum(className: string | undefined): string | undefined {
  if (!className) return className;
  return className.replace(/(^|\s)h-(\[[^\]]+\]|[\d.]+)(?=\s|$)/g, "$1h-auto min-h-$2");
}
```

## 5. `src/components/ui/button.tsx`: a label wraps instead of running out of the button

1. Import the helper: `import { cn, heightAsMinimum } from "@/lib/utils";`
2. In the base classes of `buttonVariants`, replace `whitespace-nowrap` with `whitespace-normal text-center`.
3. Replace the three text sizes (keep `icon` exactly as it is):
   - `default: "h-9 px-4 py-2"` -> `default: "min-h-9 px-4 py-2"`
   - `sm: "h-8 rounded-md px-3 text-xs"` -> `sm: "min-h-8 rounded-md px-3 py-1 text-xs"`
   - `lg: "h-10 rounded-md px-8"` -> `lg: "min-h-10 rounded-md px-8 py-2"`
4. In the `Button` component, pass the caller's classes through the helper, except for icon buttons:

```tsx
    return (
      <Comp
        className={cn(
          buttonVariants({
            variant,
            size,
            // Labels wrap instead of running past the button; icon buttons keep their square.
            className: size === "icon" ? className : heightAsMinimum(className),
          }),
        )}
        ref={ref}
        {...props}
      />
    );
```

On one line every button looks exactly as before; only a label that does not fit now takes a second line.

## 6. `src/components/ui/select.tsx`: the chosen value wraps instead of being clipped

1. Import the helper: `import { cn, heightAsMinimum } from "@/lib/utils";`
2. In `SelectTrigger`, replace the base class string with:

```
"flex min-h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-transparent px-3 py-1.5 text-left text-sm shadow-sm ring-offset-background cursor-pointer data-[placeholder]:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:min-w-0 [&>span]:break-words"
```

and pass the caller's classes as `heightAsMinimum(className)` instead of `className` in the same `cn(...)` call.

## 7. Nothing is cut off on purpose any more

1. Remove `overflow-x-clip` from every `<main>` that has it (one in `ExpensesReviewGrid.tsx`, four in `RunWorkbench.tsx`). Keep every other class on those lines.
2. `ExpensesReviewGrid.tsx`: the review grid's `<fieldset className="space-y-6 border-0 p-0">` becomes `<fieldset className="min-w-0 space-y-6 border-0 p-0">`.
3. In every file under `src/components/` EXCEPT `src/components/ui/`, replace the Tailwind class `truncate` with `break-words` wherever it appears in a `className` (or inside `cn(...)`). Leave the `truncate()` JavaScript function in `FeedbackWidget.tsx` alone; it is not a class. Today that is: `DashboardHeader.tsx` (3), `ExpensesReviewGrid.tsx` (6), `GlAccountPicker.tsx` (3), `InboundLogScreen.tsx` (3), `OperatorDashboard.tsx` (1), `ReceiptViewer.tsx` (1, the `DialogTitle`), `RunWorkbench.tsx` (10), `SettingsScreen.tsx` (2), `SettledByBadge.tsx` (1). Keep any `max-w-[...]` next to it: the text now wraps inside that width instead of being shortened.
   **Exception, file names only** (one long word with no spaces, so `break-words` cannot break it early enough): use `wrap-anywhere` instead of `break-words` at these places, and nowhere else:
   - `ExpensesReviewGrid.tsx`: the receipt file-name button `max-w-[18rem] truncate underline ...`, the source-file line `mt-0.5 max-w-[12rem] truncate text-[10px] ...`, and the file link `max-w-[14rem] truncate text-xs text-primary underline ...`
   - `InboundLogScreen.tsx`: the file-name button `block max-w-full truncate text-left text-sm text-primary ...`
   - `ReceiptViewer.tsx`: the `DialogTitle` (`truncate pr-6 text-sm`)
   Do NOT use `wrap-anywhere` on ordinary text: it lets a table squeeze a column to one letter wide ("CO GS - Oth er…"); `break-words` keeps whole words together, and when a table cannot fit whole words, `fit-tables.ts` turns it into cards instead.
4. `RunWorkbench.tsx`, the outline `Button` whose className is `"h-7 px-2 text-xs font-mono max-w-[16rem] truncate"`: make it `"h-auto min-h-7 max-w-[16rem] whitespace-normal px-2 py-1 text-left font-mono text-xs wrap-anywhere"`.
5. `ExpensesReviewGrid.tsx`, the restored-file name in the list of re-ingested files: `className={cn("font-medium", e.restored && "text-muted-foreground line-through")}` becomes `className={cn("min-w-0 font-medium wrap-anywhere", e.restored && "text-muted-foreground line-through")}`.
6. `InboundLogScreen.tsx`: remove `whitespace-nowrap` from the five `KIND_CLASS` badge tones (`resting`, `held`, `working`, `done`, `unknown`), from the `mt-1 whitespace-nowrap text-[11px] ...` line under a status, and from the outline `Badge` with `whitespace-nowrap font-medium text-muted-foreground`. The date cells keep theirs.

## 8. Rows of buttons and tabs wrap instead of running off the side

1. Every `<div className="ml-auto flex items-center gap-2">` becomes `<div className="ml-auto flex flex-wrap items-center gap-2">`: `ExpensesReviewGrid.tsx` (1), `ReceiptsDropScreen.tsx` (1), `ReceiptsFolderUploader.tsx` (1), `RunWorkbench.tsx` (2), `SummaryBar.tsx` (1).
2. `SettingsScreen.tsx`, the tab bar: `<div className="hidden overflow-x-auto sm:block [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">` becomes `<div className="hidden sm:block">`, and its `<TabsList className="h-auto w-max">` becomes `<TabsList className="h-auto w-full flex-wrap justify-start">`. The phone view below `sm` stays as it is.
3. `MemoryScreen.tsx`, the page header: `<div className="flex items-end justify-between gap-4">` gets `flex-wrap`, the `<div className="flex items-center gap-3">` holding the facts count and the search box gets `flex-wrap`, the search `Input`'s `h-9 w-56` becomes `h-9 w-full sm:w-56`, and the section toolbar `<div className="flex items-center gap-2">` gets `flex-wrap`.
4. `ExpensesReviewGrid.tsx`, `OpenLinePickers`: each open line's row `<div key={li.index} className="flex items-center gap-2 text-[11px]">` becomes `<div key={li.index} className="flex flex-wrap items-center gap-2 text-[11px]">`, so the per-line account picker drops under the description instead of past the edge.
5. `RunWorkbench.tsx`, the right end of the Matching filter bar (the "Showing N of M rows" text and "Clear all"): `<div className="ml-auto flex items-center gap-3">` becomes `<div className="ml-auto flex flex-wrap items-center gap-3">`.

## 8b. `CompareCopies.tsx`: the copies sit side by side at every width

Today the compare grid is `10rem` of field names plus `18rem` per copy inside an `overflow-x-auto` box, so below about 800 px the second copy is behind a sideways scroll.

1. Add `type CSSProperties` to the existing `react` import: `import { useState, type CSSProperties, type ReactNode } from "react";`
2. Replace the wrapper and the grid opening:

```tsx
      <div className="min-w-0">
        <div
          className="grid grid-cols-[repeat(var(--copies),minmax(0,1fr))] gap-x-3 gap-y-2 break-words text-sm sm:grid-cols-[minmax(6rem,10rem)_repeat(var(--copies),minmax(0,1fr))]"
          style={{ "--copies": n } as CSSProperties}
        >
          <div className="hidden sm:block" />
```

   (the empty top-left `<div />` becomes `<div className="hidden sm:block" />`; everything inside the grid stays).
3. In `FieldLine`, the field-name cell `<div className="pt-1 text-xs text-muted-foreground">` becomes `<div className="col-span-full pt-1 text-xs text-muted-foreground sm:col-span-1">`.

From 640 px up nothing changes visually (names on the left, one column per copy, now sharing the width instead of forcing 18rem each). Below 640 px each field name sits on its own line above the copies' values, which stay side by side.

## 9. `DashboardHeader.tsx` (`MainMenuHeader` on `/months`): everything in the header shows at every width

1. `LanguageToggle`: `className="hidden overflow-hidden rounded-md border sm:inline-flex"` becomes `className="inline-flex shrink-0 overflow-hidden rounded-md border"`, so EN/PT can be switched on a phone too.
2. The logo `Link`: drop `shrink-0` (`"flex min-w-0 items-center gap-3"`).
3. The tagline span: `"hidden truncate text-xs uppercase tracking-wider text-muted-foreground 2xl:inline"` becomes `"min-w-0 break-words text-xs uppercase tracking-wider text-muted-foreground"`.
4. "Signed in as": `"hidden max-w-[16ch] truncate text-xs text-muted-foreground lg:inline"` becomes `"hidden break-words text-xs text-muted-foreground md:inline"` (below 768 px it stays in the menu sheet, where it already shows).
5. The top row `mx-auto grid h-14 max-w-7xl ...` becomes `mx-auto grid min-h-14 max-w-7xl ...` (same look, grows if a long name wraps).
6. The tab labels in the second-row `nav`: `<span className="hidden lg:inline">{item.label}</span>` becomes `<span>{item.label}</span>`. The row already wraps, so between 768 and 1023 px the tabs show their names instead of icons only.

## 10. Do not change

- No other component, route, request, field, text key or click handler.
- Do not add `overflow-x-auto`, `overflow-hidden`, `overflow-x-clip` or a hidden scrollbar anywhere to make something "fit". If something still does not fit, it should wrap or stack, never hide.
- The shadcn `Table` wrapper keeps its current classes; `fit-tables.ts` handles every table, shadcn or plain `<table>`.
````

## How to verify after publish

1. Bundle (`.scratch/live_bundle_grep.py`-style crawl, controls first): the
   published chunks carry the strings `data-stacked`, `data-full`,
   `data-label` and `h-auto min-h-` (function names are minified, so do not
   grep for `installTableFit` / `heightAsMinimum`), the CSS asset carries
   `table[data-stacked]`, and `overflow-x-clip` is gone from every chunk.
2. Structure, read-only, against the live API with each month's payload read
   once and replayed (`feedback_recon_drive_replay_payloads`): open August's
   Expenses page at 390 px and 1280 px; at 390 px every grid row is a card
   (`table[data-stacked]`, `td[data-label]`), at 1920 px it is a plain table;
   `document.documentElement.scrollWidth <= innerWidth` at every width.
3. Re-run `.scratch` audit's measure over the published build: offscreen,
   clipped, sidescroll and truncated all zero.
