# Lovable prompt: the Matching page's header gets quieter and its open items louder (items 232-235, notes #99-#106)

> **NOT YET APPLIED.** SPA only, no backend change, no new field, no new
> request. Every value used here is already in `GET /api/runs/{id}` (read
> live on September 2026, 2026-09-27): `statements[]`, `coverage[]`
> (whose `statements` lists each upload's `file`, filled by the backend's
> own card attribution), `card_sections[]` and `summary`.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. Changes in `src/components/RunWorkbench.tsx` (the header of the month's Matching page, `StatementLoadedLines`, `StatusLine`), `src/components/CardScope.tsx` (the "Showing card" line, used on both the Matching and the Expenses page) and `src/lib/i18n.tsx` (new keys, EN and PT). No new field and no new request.

## Why

The owner left eight notes on September 2026's Matching page (`/runs/51a22ad72864`), all in the block above the tiles:

- On "51 charges from the bank statement, matched against this month's receipts. Confirm or reject each suggested match.": "remove first 2 sentences here"
- On "Statement loaded: 20260904-statements-9693-.pdf, Aug 05, 2026 to Sep 04, 2026, 32 charges…": "this should be compressed to just display the cards 4 ending didgits for clarity", and "Change this to a dropdown button labelled "View all Statements loaded" or something like that"
- On "Showing card 2838": "this should also be more evident"
- On "· No statement loaded for this card": "this should be more evident for user to see"
- On "7 cards have no statement for this month: Apple Credit Card - 0113, Credit Card - 2838, C…": "change this to a dropdown: something like "View cards with no statement for this month" or something like that"
- On "USD 7,496.60 still open": "format this so that it is more visible"
- On "USD 1,467.27 booked without a receipt (11 charges)": "format this so its more visible"

Today the top of the page is three grey lines of statement file names and a grey sentence, while the things that need a person (the card with no statement, the money still open) are the same small text as everything else. The new shape: the explanations and file lists fold away behind two buttons, and the open items become boxed, bold and amber.

## 1. Header: the two opening sentences go, the statements fold behind one button

**1a.** In the Matching page header (`<div className="max-w-2xl space-y-1">`), delete the `<p className="text-sm text-muted-foreground">` that renders `t("wb.subtitle.template", ...)`. Nothing replaces it.

**1b.** Pass the coverage to the statement list: `<StatementLoadedLines statements={data.statements} hasStatement={data.has_statement} coverage={asArray<CardCoverage>(data.coverage)} />` (`asArray` and `CardCoverage` are already imported in this file).

**1c.** Rewrite `StatementLoadedLines` so the statements sit behind one outline button that opens a popover. The case with no rows stays exactly as it is (nothing, or the plain "Statement loaded" line for old months). Each statement in the popover reads as the last four digits of the card it belongs to, then its period and its charge count; the file name moves into the line's tooltip. A statement's card comes from `coverage[]`: every coverage entry whose `statements` contains that upload's `file` names one of its cards (a file can hold several cards, then list every one). Only when no coverage entry names the file does the line fall back to the file name.

```tsx
function StatementLoadedLines({
  statements,
  hasStatement,
  coverage,
}: {
  statements?: unknown;
  hasStatement?: boolean;
  coverage: CardCoverage[];
}) {
  const t = useT();
  const locale = useLocale();
  const rows = safeStatements(statements);
  if (rows.length === 0) {
    if (!hasStatement) return null;
    return <p className="text-xs text-muted-foreground">{t("wb.statement.loadedOld")}</p>;
  }
  const cardDigits = (file: string) => {
    const out: string[] = [];
    for (const c of coverage) {
      if (!(c.statements ?? []).includes(file)) continue;
      for (const d of c.digits ?? []) if (d && !out.includes(d)) out.push(d);
    }
    return out.join(", ");
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
          <FileText className="h-3.5 w-3.5" aria-hidden />
          {t("wb.statement.viewAll", { n: rows.length })}
          <ChevronDown className="h-3.5 w-3.5" aria-hidden />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[min(34rem,calc(100vw-2rem))] space-y-2 p-3">
        {rows.map((s, i) => {
          const name = (s.upload_name || s.file || "").trim();
          const digits = cardDigits(s.file);
          const n = s.n_rows ?? 0;
          const date = s.uploaded_at ? formatDate(String(s.uploaded_at).slice(0, 10)) : "";
          const detail = [
            s.period_start
              ? t("cardScope.period", {
                  start: formatDate(s.period_start),
                  end: s.period_end ? formatDate(s.period_end) : "",
                })
              : "",
            n === 1 ? t("cardScope.charges.one") : t("cardScope.charges.many", { n }),
          ]
            .filter(Boolean)
            .join(" · ");
          const mf = readMonthFilter(s.month_filter);
          const leftOut =
            mf && mf.n_left_out > 0
              ? joinLead(
                  t("wb.statement.leftOut", { n: mf.n_left_out, total: mf.n_file_rows }),
                  monthFilterParts(mf, t, locale),
                )
              : "";
          return (
            <div
              key={`${s.file}-${i}`}
              title={date ? t("wb.statement.fileTip", { name, date }) : name}
            >
              <p className="text-sm">
                <span className="font-semibold tabular-nums">{digits || name}</span>
                {detail ? <span className="text-muted-foreground">{" · " + detail}</span> : null}
              </p>
              {leftOut ? <p className="pl-3 text-xs text-muted-foreground">{leftOut}</p> : null}
            </div>
          );
        })}
      </PopoverContent>
    </Popover>
  );
}
```

Imports, only if this file does not have them yet: `import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";`, and `FileText` and `ChevronDown` added to the existing `lucide-react` import.

## 2. `CardScope`: the card being shown, and a missing statement, stand out

In `src/components/CardScope.tsx`:

**2a.** Work out once whether the picked card has no statement: `const notLoaded = !!selected && !(isSubcard(selected) && selected.statement_on_account) && selected.statement === "not_loaded";`. In the `parts` list, the `else if (selected.statement === "not_loaded") push(t("cardScope.statement.notLoaded"));` branch goes: the sentence moves to 2b and is no longer in the grey line.

**2b.** Replace the first `<p className="text-sm">` (the "Showing card" line) with:

```tsx
<div className="flex flex-wrap items-center gap-2">
  <span className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1 text-base font-semibold text-primary">
    {scope === "" ? null : <CreditCard className="h-4 w-4" aria-hidden />}
    {scope === "" ? t("cardScope.showingNoCard") : t("cardScope.showing", { card: cardText })}
  </span>
  {notLoaded ? (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/50 bg-amber-500/10 px-2.5 py-1 text-sm font-medium text-amber-800 dark:text-amber-200">
      <AlertCircle className="h-4 w-4" aria-hidden />
      {t("cardScope.statement.notLoaded")}
    </span>
  ) : null}
  {notLoaded && showAdd ? (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-8 px-2.5 text-xs"
      onClick={() => onAddStatement?.(addKey)}
    >
      {t("cardScope.addStatement.forCard")}
    </Button>
  ) : null}
  <span className="text-sm">{showAll}</span>
</div>
```

**2c.** In the second line (the grey `parts` line), render its "Add this card's statement" / "Add another statement for this card" button only when `!notLoaded`, so the button never shows twice. Everything else in that line stays as it is.

`CreditCard` and `AlertCircle` come from `lucide-react`; add them to the file's imports. This component is also used on the Expenses page, so the same line changes there too: that is intended.

## 3. `StatusLine`: cards with no statement behind a button, the open amounts boxed and bold

In `StatusLine` in `RunWorkbench.tsx`:

**3a.** The `wb.status.cardsUncovered` span becomes an amber outline button that opens a popover with the list:

```tsx
{(summary.n_cards_uncovered ?? 0) > 0 ? (
  <Popover>
    <PopoverTrigger asChild>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 border-amber-500/50 text-amber-800 hover:bg-amber-500/10 dark:text-amber-200"
      >
        <AlertCircle className="h-3.5 w-3.5" aria-hidden />
        {summary.n_cards_uncovered === 1
          ? t("wb.status.cardsUncovered.view.one")
          : t("wb.status.cardsUncovered.view", { n: summary.n_cards_uncovered ?? 0 })}
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="start" className="w-[min(26rem,calc(100vw-2rem))] p-3">
      <p className="mb-2 text-xs text-muted-foreground">{t("wb.status.cardsUncovered.tip")}</p>
      <ul className="space-y-1 text-sm">
        {(Array.isArray(summary.cards_uncovered) ? summary.cards_uncovered : []).map((c) => (
          <li key={String(c)}>{String(c)}</li>
        ))}
      </ul>
    </PopoverContent>
  </Popover>
) : null}
```

**3b.** Each "still open" amount becomes a box with the amount in bold:

```tsx
{ccyEntries.map(([ccy, amt]) => (
  <span
    key={ccy}
    className="inline-flex items-baseline gap-1.5 rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-amber-800 dark:text-amber-200"
  >
    <span className="text-base font-semibold tabular-nums">{`${ccy} ${amt}`}</span>
    <span className="text-sm">{t("wb.status.stillOpen.rest")}</span>
  </span>
))}
```

**3c.** Each "booked without a receipt" amount gets the same box, keeping its `title` tooltip:

```tsx
<span
  key={`bnr-${ccy}`}
  title={t("wb.status.bookedNoReceipt.tip")}
  className="inline-flex items-baseline gap-1.5 rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-amber-800 dark:text-amber-200"
>
  <span className="text-base font-semibold tabular-nums">{`${ccy} ${amt}`}</span>
  <span className="text-sm">
    {t("wb.status.bookedNoReceipt.rest", { n: summary.n_booked_no_receipt ?? 0 })}
  </span>
</span>
```

The row's flex classes stay as they are (`flex flex-wrap items-center gap-x-4 gap-y-2 text-sm`).

## 4. `i18n.tsx`: new keys, both languages

| Key | EN | PT |
|---|---|---|
| `wb.statement.viewAll` | View all statements loaded ({n}) | Ver todos os extratos carregados ({n}) |
| `wb.statement.fileTip` | File {name}, added {date} | Arquivo {name}, adicionado em {date} |
| `wb.status.cardsUncovered.view` | View cards with no statement for this month ({n}) | Ver cartões sem extrato neste mês ({n}) |
| `wb.status.cardsUncovered.view.one` | View the card with no statement for this month | Ver o cartão sem extrato neste mês |
| `wb.status.stillOpen.rest` | still open | em aberto |
| `wb.status.bookedNoReceipt.rest` | booked without a receipt ({n} charges) | lançados sem recibo ({n} cobranças) |

Keep `wb.status.cardsUncovered.tip`, `wb.status.bookedNoReceipt.tip`, `wb.statement.loadedOld`, `wb.statement.leftOut*`, `cardScope.period`, `cardScope.charges.*` and `cardScope.statement.notLoaded` (all still used). `wb.subtitle.template`, `wb.statement.loaded`, `wb.statement.loadedNoPeriod`, `wb.status.stillOpen`, `wb.status.bookedNoReceipt`, `wb.status.cardsUncovered` and `wb.status.cardsUncovered.one`: search the project first, and remove a key only if nothing else uses it.

## 5. Do not change

- The status chip at the start of `StatusLine` (ready / not complete / broken month), the "no receipt expected" span, the "next-door month" span and the health box above them.
- The tiles grid, the card strip, `CoverageAttention`, the attach-statement dialog and everything below the status line.
- On `CardScope`: the grey figures line (charges, matched, still open, booked, receipts, own line) apart from the two changes in 2a and 2c; the empty-card box.
- How any number is computed. Opening a popover writes nothing.

## Checking it landed

Read only; opening a popover or picking a card tab writes nothing.

1. September 2026 Matching (`/runs/51a22ad72864`), no card picked: the sentence "51 charges from the bank statement, matched against this month's receipts. Confirm or reject each suggested match." is gone. In its place one outline button "View all statements loaded (3)". Open it: three lines, "9693 · Aug 05, 2026 to Sep 04, 2026 · 32 charges", "1176 · Sep 01, 2026 to Sep 10, 2026 · 4 charges", "9693 · Sep 04, 2026 to Sep 14, 2026 · 15 charges"; hovering the first shows "File 20260904-statements-9693-.pdf, added Sep 24, 2026". No file name is on the page until the button is opened.
2. Pick card 2838: "Showing card 2838" in a blue box with a card icon, then an amber box "No statement loaded for this card", then the "Add this card's statement" button right beside it, then "Show all cards". The grey line under it no longer says "No statement loaded for this card" and has no second Add button. Pick 9693: the blue box, no amber box, and the grey line as today (it still names 9693's two statement files; that line is not part of this change).
3. The status line: an amber outline button "View cards with no statement for this month (7)"; open it and it lists the seven cards under the sentence about them not being counted. "USD 7,496.60" is bold in an amber box followed by "still open", and "USD 1,467.27" is bold in an amber box followed by "booked without a receipt (11 charges)" (Criss's work moves every figure).
4. September 2026 Expenses (`/expenses/51a22ad72864`), card 2838 picked: the same blue box and amber box as step 2.
5. Switch to PT: "Ver todos os extratos carregados (3)", "Mostrando o cartão 2838", "Nenhum extrato carregado para este cartão", "Ver cartões sem extrato neste mês (7)", "USD 7,496.60 em aberto".
6. At phone width (about 400 px) the boxes wrap onto new lines and each popover stays inside the screen.
````
