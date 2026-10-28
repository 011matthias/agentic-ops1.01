# Lovable prompt: the main menu's tabs never scroll sideways, and "Paid by bank transfer" says what it does (items 244-245, notes #109-#110)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. One new text key (`expx.bills.moveToBill.tip`, EN + PT). Measured
> live on `/months`, 2026-09-29, read-only headless Chrome: in PT the header
> nav shows 724 of 905 px at 1600 and 2500 px wide, so "Comparar" and
> "Configurações" sit past the edge with the scrollbar hidden; in EN
> "Settings" does (688 of 727 px). At 1280 px PT loses "Configurações" and EN
> fits.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/DashboardHeader.tsx` (`MainMenuHeader`, the tab bar on `/months`), `src/components/ExpensesReviewGrid.tsx` (`MoveToBillControl`) and `src/lib/i18n.tsx` (one new key, EN and PT). No new field, no new request.

## Why

The owner left two notes on 2026-09-29:

- On `/months`, just under the right end of the header tabs: "make this a non scroll tab bar, because people without side scroll on their mouse cant scroll"
- On August 2026's Expenses page, on the "Paga por transferência bancária" button of a receipt with no card: "what happens to expenses when user clicks on this?"

Today the header tabs sit in the same 56 px row as the logo, the language switch, "Signed in as" and Log out, inside a `nav` with `overflow-x-auto` and a hidden scrollbar. In Portuguese at desktop width the row is 905 px of tabs in a 724 px box, so Compare and Settings are cut off and a mouse without a side wheel cannot reach them. The "Paid by bank transfer" button saves at once with no word on what it changes.

## 1. `MainMenuHeader`: the tabs get their own row and wrap instead of scrolling

In `src/components/DashboardHeader.tsx`, inside `MainMenuHeader`:

1. Remove the `<nav className="ml-1 hidden min-w-0 flex-1 items-center gap-0.5 overflow-x-auto md:flex [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">...</nav>` block from the logo's `div` (the one with `flex min-w-0 items-center gap-3`). The logo `Link` stays where it is.
2. Directly after the closing tag of the top row (`<div className="mx-auto grid h-14 max-w-7xl grid-cols-[minmax(0,1fr)_auto] ...">...</div>`) and still inside `<header>`, add the tabs as a second row:

```tsx
<nav className="mx-auto hidden max-w-7xl flex-wrap items-center gap-1 px-4 pb-2 sm:px-6 md:flex">
  {items.map((item) => {
    const Icon = item.icon;
    return (
      <Link
        key={item.to}
        to={item.to}
        title={item.label}
        aria-label={item.label}
        className={navLink}
        activeProps={navLinkActive}
        {...(item.exact ? { activeOptions: { exact: true } } : {})}
      >
        <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
          <Icon className="h-4 w-4 shrink-0" />
          <span className="hidden lg:inline">{item.label}</span>
        </span>
      </Link>
    );
  })}
</nav>
```

The `nav` has no `overflow-x-*` class and no scrollbar rule: when the tabs do not fit on one line they wrap onto a second line, never behind an edge. `title` and `aria-label` name each tab where only its icon shows (between 768 and 1023 px wide).

Everything else in the header stays: the top row keeps the logo, the tagline at 2xl, the EN/PT switch, "Signed in as", Log out and, below 768 px, the menu button that opens the side sheet with the same tabs. Every page other than `/months` keeps its single "Back to menu" bar.

## 2. `MoveToBillControl`: the button says what it does

In `src/components/ExpensesReviewGrid.tsx`, inside `MoveToBillControl`, wrap the existing "Paid by bank transfer" `Button` in a tooltip (`Tooltip`, `TooltipTrigger`, `TooltipContent` are already imported in this file):

```tsx
<Tooltip>
  <TooltipTrigger asChild>
    <Button ...unchanged...>
      ...unchanged...
    </Button>
  </TooltipTrigger>
  <TooltipContent className="max-w-xs text-xs">{t("expx.bills.moveToBill.tip")}</TooltipContent>
</Tooltip>
```

The button's props, its click (the same one PUT) and when it shows are unchanged. The "Looks like a bank-paid invoice" chip beside it keeps its own tooltip.

Add the key in `src/lib/i18n.tsx`, next to `expx.bills.moveToBill` in each language:

- EN: `"expx.bills.moveToBill.tip": "Moves this receipt to Bills: it leaves the card queue and the month's total and goes into the bills CSV, to book by hand in Zoho. Nothing is posted. If a statement charge is matched to it later, it comes back to the card queue by itself. \"Move to the card queue\" undoes it.",`
- PT: `"expx.bills.moveToBill.tip": "Move este recibo para Contas: ele sai da fila do cartão e do total do mês e vai para o CSV de contas, para lançar à mão no Zoho. Nada é lançado. Se uma cobrança de extrato for pareada com ele depois, ele volta sozinho para a fila do cartão. \"Mover para a fila do cartão\" desfaz.",`

## 3. Do not change

- The tab list, its order, its targets, and which tab reads as active.
- The side sheet menu below 768 px.
- What "Paid by bank transfer" sends, when it shows, the Bills section and its "Move to the card queue" button.

## Checking it landed

Read only: hover and resize, nothing is clicked that writes.

1. `/months` at 1600 px wide in PT: the header has two rows, the logo row and under it all eight tabs, "Execuções" through "Configurações", on one line with nothing cut off and no scrollbar. The same in EN, "Runs" through "Settings".
2. The same at 1280 px and at 2500 px: all eight tabs visible.
3. At about 900 px wide: the tabs show as icons; hover one and its name appears; none is cut off.
4. From 768 px up, drag the window narrower: the tabs wrap onto a further line rather than disappearing past the edge.
5. Below 768 px: the tab row is gone and the menu button opens the side sheet with the eight tabs, as today.
6. Open any month: the page shows only the "Back to menu" bar, as today.
7. August 2026 Expenses (`/expenses/074a7b8905d7`), the Perplexity AI USD 25.00 row: hover "Paid by bank transfer" / "Paga por transferência bancária" and the tooltip reads the sentence above in that language. Do not click it: that row is a card-paid subscription waiting for the 0340 statement.
````
