# Lovable prompt: the Matching page header reads at a glance (notes #99-#106)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. Every value used here is already in `/api/runs/{id}` (read live on
> September 2026, run `51a22ad72864`, 2026-09-27): `statements[]`,
> `card_sections[].statements` + `digits`, and `summary.cards_uncovered`,
> `unreconciled_by_ccy`, `booked_no_receipt_by_ccy`.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/RunWorkbench.tsx` (the Matching page header: the intro paragraph, `StatementLoadedLines`, `StatusLine`), `src/components/CardScope.tsx` (the "Showing card" block) and `src/lib/i18n.tsx` (new keys and one removed key, EN and PT). No new field and no new request.

## Why

The owner left eight notes on September 2026's Matching page (`/runs/51a22ad72864`), all on the header above the tiles. Verbatim:

- On "51 charges from the bank statement, matched against this month's receipts. Confirm or reject each suggested match.": "remove first 2 sentences here"
- On "Statement loaded: 20260904-statements-9693-.pdf, Aug 05, 2026 to Sep 04, 2026, 32 charges…": "this should be compressed to just display the cards 4 ending didgits for clarity", and "Change this to a dropdown button labelled "View all Statements loaded" or something like that"
- On "7 cards have no statement for this month: Apple Credit Card - 0113, Credit Card - 2838, …": "change this to a dropdown: something like "View cards with no statement for this month" or something like that"
- On "USD 7,496.60 still open": "format this so that it is more visible"
- On "USD 1,467.27 booked without a receipt (11 charges)": "format this so its more visible"
- On "Showing card 2838": "this should also be more evident"
- On "· No statement loaded for this card": "this should be more evident for user to see"

Today September's header is three statement lines with long file names, one run-on sentence listing seven card names, and two money figures in the same small grey text as everything around them. After this change: no intro paragraph, one "View all 3 statements loaded" dropdown, one "View cards with no statement for this month (7)" dropdown, the two money figures as bold chips, and the card being shown as a clear heading with an amber badge when its statement is missing.

## 1. The intro paragraph goes

In `RunWorkbench.tsx`, remove the `<p>` that renders `t("wb.subtitle.template", ...)` (the two sentences "{n} charges from the bank statement, matched against this month's receipts. Confirm or reject each suggested match."). Delete the key `wb.subtitle.template` from both the EN and the PT dictionary; nothing else uses it. The surrounding `<div className="max-w-2xl space-y-1">` now holds only `StatementLoadedLines`.

## 2. `StatementLoadedLines` becomes one dropdown, one line per card

Pass the month's card sections in: `<StatementLoadedLines statements={data.statements} hasStatement={data.has_statement} cardSections={cardSections} />` (`cardSections` is already computed higher up in the same component).

Inside:

- `rows.length === 0`: unchanged (nothing, or the `wb.statement.loadedOld` line).
- Otherwise render a `Popover` (`@/components/ui/popover`, the same primitive `ExpensesReviewGrid` uses) whose trigger is a small outline button: `<Button variant="outline" size="sm" className="h-7 gap-1 px-2 text-xs">` with the label `t(rows.length === 1 ? "wb.statement.view.one" : "wb.statement.view.many", { n: rows.length })` and a `ChevronDown` icon (`h-3.5 w-3.5`). Closed by default.
- `PopoverContent` (`align="start"`, `className="w-auto max-w-md space-y-1.5 p-3"`) lists one entry per statement, in the order they come.

Each entry names the card by its last four digits instead of the file name:

```ts
function statementCard(s: StatementUpload, sections: CardSection[]): string {
  const names = [s.file, s.upload_name].filter(Boolean);
  const sec = sections.find((c) =>
    (c.statements ?? []).some((f) => names.includes(f)),
  );
  const d = (sec?.digits ?? []).filter(Boolean);
  return d.length ? d[d.length - 1] : "";
}
```

(The same "last digits entry" rule as `cardChipText` in `src/lib/card-scope.ts`.) With a card:

- with a period: `t("wb.statement.cardLine", { card, from: formatDate(s.period_start), to: s.period_end ? formatDate(s.period_end) : "", n })`
- without a period: `t("wb.statement.cardLineNoPeriod", { card, n })`

When no section names the file (`card === ""`), fall back to exactly today's line (`wb.statement.loaded` / `wb.statement.loadedNoPeriod` with the file name), so a statement never goes nameless.

Each entry is a `<p className="text-xs">`; its `title` is `t("wb.statement.fileTip", { name, date })` so the file name and upload date stay one hover away. The existing "left out" sub-line (`leftOut`, from `month_filter`) stays under its own entry, unchanged, as `<p className="pl-3 text-xs text-muted-foreground">`.

September should read, inside the dropdown:

- Card 9693: Aug 05, 2026 to Sep 04, 2026, 32 charges
- Card 1176: Sep 01, 2026 to Sep 10, 2026, 4 charges
- Card 9693: Sep 04, 2026 to Sep 14, 2026, 15 charges

## 3. `StatusLine`: the uncovered cards become a dropdown

Replace the amber `<span>` that renders `wb.status.cardsUncovered` / `.one` with a `Popover`:

- Trigger: `<Button variant="outline" size="sm" className="h-8 gap-1 border-amber-500/40 bg-amber-500/10 px-3 text-sm text-amber-700 hover:bg-amber-500/15 dark:text-amber-300">` with `t(n === 1 ? "wb.status.cardsUncovered.view.one" : "wb.status.cardsUncovered.view", { n })` and a `ChevronDown` icon.
- Content (`align="start"`, `className="w-auto max-w-sm p-3"`): first the explanation that today only shows on hover, visible now: `<p className="mb-2 text-xs text-muted-foreground">{t("wb.status.cardsUncovered.tip")}</p>`; then `<ul className="space-y-0.5 text-sm">` with one `<li>` per entry of `summary.cards_uncovered`, the label as it comes.
- Shown only when `summary.n_cards_uncovered > 0`, as today. The keys `wb.status.cardsUncovered` and `wb.status.cardsUncovered.one` are no longer used on this page; leave them in the dictionaries.

## 4. `StatusLine`: the two money figures become chips

The row already has one chip, the status pill (`rounded-md border px-3 py-1.5 font-semibold`). Give the two money figures the same frame, with the amount as the loud part:

- **Still open**, one chip per entry of `ccyEntries`: `<span className="inline-flex items-baseline gap-1.5 rounded-md border border-border bg-muted/40 px-3 py-1.5">`, inside it `<span className="text-base font-semibold tabular-nums text-foreground">{ccy} {amt}</span>` then `<span className="text-sm text-muted-foreground">{t("wb.status.stillOpen.label")}</span>`.
- **Booked without a receipt**, one chip per currency as today and only when `summary.n_booked_no_receipt > 0`: `<span className="inline-flex items-baseline gap-1.5 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-1.5" title={t("wb.status.bookedNoReceipt.tip")}>`, inside it the amount `<span className="text-base font-semibold tabular-nums text-amber-800 dark:text-amber-200">{ccy} {amt}</span>` then `<span className="text-sm text-amber-700 dark:text-amber-300">{t("wb.status.bookedNoReceipt.label", { n: summary.n_booked_no_receipt })}</span>`.

The old keys `wb.status.stillOpen` and `wb.status.bookedNoReceipt` stay in the dictionaries (other pages may read them); this page uses the new `.label` keys. The "no receipt expected", "nothing to decide" and "next door" spans stay exactly as they are.

## 5. `CardScope`: the card being shown is a heading, a missing statement is a badge

This component is shared by the Matching and the Expenses page; the change applies to both, on purpose. It imports no icons today: add `import { AlertCircle, CreditCard } from "lucide-react";`.

- The first line becomes `<p className="flex flex-wrap items-center gap-x-2 gap-y-1">`. The "Showing card {card}" text (or "Showing receipts with no card") goes from `text-sm font-medium` to `<span className="inline-flex items-center gap-1.5 text-base font-semibold text-foreground">`, with a `CreditCard` icon (`h-4 w-4`, `aria-hidden`) before it when `scope !== ""`.
- Compute `const noStatement = !!selected && !(isSubcard(selected) && selected.statement_on_account) && selected.statement === "not_loaded";`. When true, render right after the heading, on the same line: `<span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300"><AlertCircle className="h-3.5 w-3.5" aria-hidden />{t("cardScope.statement.notLoaded")}</span>`. In the `if / else if` chain that builds `parts`, the `not_loaded` branch no longer pushes anything (the badge replaces the grey part), so the text is not shown twice.
- The "Show all cards" link follows, after a muted separator `<span className="text-muted-foreground">·</span>`, unchanged.
- The second line (`parts` and the "Add statement for this card" button) is unchanged, apart from no longer carrying "No statement loaded for this card". The `not_recorded` and `statement_on_account` texts stay grey parts as today; only a statement that is simply missing is flagged.
- The `empty` branch at the top of the component is unchanged.

## 6. i18n (EN and PT)

Remove `wb.subtitle.template` from both dictionaries. Add:

| Key | EN | PT |
|---|---|---|
| `wb.statement.view.one` | View the statement loaded | Ver o extrato carregado |
| `wb.statement.view.many` | View all {n} statements loaded | Ver os {n} extratos carregados |
| `wb.statement.cardLine` | Card {card}: {from} to {to}, {n} charges | Cartão {card}: de {from} a {to}, {n} cobranças |
| `wb.statement.cardLineNoPeriod` | Card {card}: {n} charges | Cartão {card}: {n} cobranças |
| `wb.statement.fileTip` | {name}, added {date} | {name}, adicionado em {date} |
| `wb.status.cardsUncovered.view` | View cards with no statement for this month ({n}) | Ver cartões sem extrato neste mês ({n}) |
| `wb.status.cardsUncovered.view.one` | View the card with no statement for this month | Ver o cartão sem extrato neste mês |
| `wb.status.stillOpen.label` | still open | em aberto |
| `wb.status.bookedNoReceipt.label` | booked without a receipt ({n} charges) | lançados sem recibo ({n} cobranças) |

## Check it on September 2026 (`/runs/51a22ad72864`)

1. No "51 charges from the bank statement…" sentence above the header.
2. One button "View all 3 statements loaded"; opening it shows three lines starting "Card 9693", "Card 1176", "Card 9693", no file names; hovering one shows its file name and upload date.
3. One amber button "View cards with no statement for this month (7)"; opening it shows the explanation sentence and seven card names, one per line.
4. "USD 7,496.60" bold in a grey chip with "still open", "USD 1,467.27" bold in an amber chip with "booked without a receipt (11 charges)" (amounts move with Criss's work).
5. Pick card 2838: "Showing card 2838" is a bold heading with a card icon and an amber "No statement loaded for this card" badge beside it; the grey line below no longer repeats it. Pick card 9693: heading, no badge.
6. Switch to PT and repeat 2 to 5.
````
