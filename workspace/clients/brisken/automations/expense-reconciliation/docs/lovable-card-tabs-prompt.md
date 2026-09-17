# Lovable prompt: the month page split by card (item 138)

> **NOT YET APPLIED.** Backend first: `card_sections[]` and `card_section` on
> `GET /api/runs/{id}` and `GET /api/expense-batches/{id}` (item 138, the
> months-page half; contract in `docs/api-contract.md`). Until that deploy the
> fields are absent and both pages render exactly as today.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One new component `src/components/CardTabs.tsx`, types in `src/lib/api.ts`, and mounts in `src/components/RunWorkbench.tsx` (Matching) and `src/components/ExpensesReviewGrid.tsx` (Expenses). Render defensively: a payload without `card_sections`, or with an empty list, renders both pages exactly as today.

## Why

The bookkeeper reconciles a month card by card: one bank statement per card, and the receipts paid on that card. Both month pages show every card mixed together, so she cannot take one card's statement and check it against its receipts. The owner decided: a tab per card, showing whether its statement is loaded, how many charges matched and what is still open, plus "All" and "No card". The PDFs are already organized this way, and the backend now sends the same grouping to both pages.

## 1. Types (`src/lib/api.ts`)

```ts
export interface CardSection {
  key: string;                 // "" is the No card tab
  label: string;
  digits?: string[];
  statement?: "loaded" | "not_recorded" | "not_loaded" | null;
  statements?: string[];
  period_start?: string | null;
  period_end?: string | null;
  n_charges?: number;
  n_matched?: number;
  unreconciled_by_ccy?: Record<string, string>;
  n_booked_without_receipt?: number;
  booked_without_receipt_by_ccy?: Record<string, string>;
  n_receipts?: number;
  n_receipts_without_charge?: number;
  n_expenses?: number;          // Expenses payload only
  totals_by_ccy?: Record<string, string>; // Expenses payload only
}

export function safeCardSections(v: unknown): CardSection[] {
  if (!Array.isArray(v)) return [];
  return v.filter(
    (s): s is CardSection =>
      !!s && typeof s === "object" && typeof (s as CardSection).key === "string",
  );
}
```

Add `card_sections?: CardSection[]` to `RunDetail` and `ExpenseBatchDetail`, and `card_section?: string` to `RunRow`, `UnmatchedReceipt` and `ExpenseRow`.

`key` is `""` for No card. Always compare keys with `===`, never by truthiness: `""` is a real tab.

## 2. `src/components/CardTabs.tsx`

Export three things.

**`inCardTab(active: string | null, key: unknown): boolean`**: `active === null || (typeof key === "string" ? key : "") === active`. `null` is the All tab.

**`useCardTab(runId: string, sections: CardSection[]): [string | null, (key: string | null) => void]`**: the selected tab, `null` (All) by default. Remember it per month in `localStorage` under `brisken.month.cardTab.v1:${runId}` as JSON `{"key": <string or null>}`; both pages use the same key, so the choice carries between Matching and Expenses of one month. Read it in a `useEffect` that re-runs when `runId` or the joined section keys change (never during render: the app renders on the server too, and the sections arrive after the first render), wrap every `localStorage` call in `try/catch`, and fall back to `null` when nothing is stored, when the stored value is not a string or `null`, or when the stored key is not among `sections[].key` (a card that left the month). When `sections` is empty the hook returns `null`.

**`CardTabs({ runId, sections, coverage, active, onPick, page })`**, with `page: "matching" | "expenses"` and `coverage: CardCoverage[]`. Return `null` when `sections.length === 0`.

Otherwise render a `div` with `role="tablist"` and `aria-label={t("cardTabs.aria")}`, a flex row with `gap-1 border-b`, and one `button` per tab with `role="tab"` and `aria-selected`. Style each like the month tabs in `MonthHeader`: `inline-flex h-8 items-center gap-1.5 rounded-t-md px-3 text-sm`, selected `border-b-2 border-primary font-medium text-primary`, others `text-muted-foreground hover:text-foreground`.

- First tab: `t("cardTabs.all")`, selected when `active === null`, `onPick(null)`.
- Then one tab per section, in array order (the backend's order, No card last):
  - Text: for a card, the last value of `digits` when present, else `label`; for `key === ""`, `t("cardTabs.noCard")`. `title` is `label` for a card and `t("cardTabs.noCard.tip")` for No card.
  - Count, `tabular-nums text-xs text-muted-foreground`: on `page === "matching"` the card's `n_charges` (none on the No card tab); on `page === "expenses"` the tab's `n_expenses`.
  - For a card whose `statement` is `"not_recorded"` or `"not_loaded"`: a `span` dot `h-1.5 w-1.5 rounded-full bg-amber-500` after the text, `title={t("cardTabs.statement.notRecorded.tip")}` or `title={t("cardTabs.statement.notLoaded")}`.
  - `onPick(section.key)`.
- After the tabs, when some `coverage[]` entry has a non-empty `key` that is not any `sections[].key`: a muted, non-clickable `span` `t("wb.filter.card.empty", { n })` with that count. These are the cards with nothing this month.

Under the tab row, only when `active !== null`, one line `text-xs text-muted-foreground` built from the selected section, parts joined with ` · `, a part left out when it has nothing to say:

1. `page === "expenses"` only: `t("cardTabs.expenses.one")` when `n_expenses === 1`, else `t("cardTabs.expenses.many", { n })`; then the section's `totals_by_ccy` as `"EUR 426.20 · USD 1,473.73"` when not empty.
2. The statement: `"loaded"` gives `t("cardTabs.statement.loaded", { files: statements.join(", ") })`; `"not_recorded"` gives `t("cardTabs.statement.notRecorded")`; `"not_loaded"` gives `t("cardTabs.statement.notLoaded")`; `null` (No card) gives nothing.
3. When `period_start` or `period_end` is set: `t("cardTabs.period", { start, end })`, each date through the file's existing `formatDate`.
4. When `n_charges > 0`: `t("cardTabs.charges.one")` or `t("cardTabs.charges.many", { n })`; `t("cardTabs.matched", { n: n_matched })`; then `t("cardTabs.open", { amounts })` when `unreconciled_by_ccy` is not empty, else `t("cardTabs.openNothing")`.
5. When `n_booked_without_receipt > 0`: `t("cardTabs.booked", { n, amounts })` from `booked_without_receipt_by_ccy`.
6. `t("cardTabs.receipts.one")` or `t("cardTabs.receipts.many", { n: n_receipts })`, and when `n_receipts_without_charge > 0`, `t("cardTabs.receiptsNoCharge", { n })`.

Every money value in these maps is a pre-formatted string: render `${ccy} ${value}` as given, sorted by currency, never parse it. Guard every numeric field with `typeof === "number"` and treat anything else as 0.

## 3. Matching page (`RunWorkbench.tsx`)

- `const cardSections = safeCardSections(data?.card_sections);` and `const [cardTab, setCardTab] = useCardTab(runId, cardSections);` next to the other hooks, before the early returns. `const inTab = (k: unknown) => inCardTab(cardTab, k);`
- Render `<CardTabs runId={runId} sections={cardSections} coverage={asArray<CardCoverage>(data.coverage)} active={cardTab} onPick={setCardTab} page="matching" />` between the subtitle block (`wb.subtitle.template` and the folder trigger) and the grid of five view buttons.
- Filter by the tab everywhere the page reads charges or receipts:
  - `viewRows`: add `inTab(r.card_section)` (add `cardTab` to its dependencies);
  - `receiptsAll`: `asArray<UnmatchedReceipt>(data?.unmatched_receipts).filter((r) => inTab(r.card_section))`;
  - `receiptCopiesAll`: filter `copies_set_aside` the same way;
  - `settledOutsideReceipts`: carry `card_section: e.card_section` from the batch `expenses[]` and filter with `inTab`;
  - `allRows` (the per-view open counts): `asArray<RunRow>(data.rows).filter((r) => inTab(r.card_section))`.
- The five view buttons: when `cardTab !== null`, `wholeCount` counts the tab, not the summary: `receipts` is `receiptsAll.length`, and each charge view is the number of tab rows whose `effective_bucket` is that view. When `cardTab === null` keep the summary numbers exactly as today.
- Captions: when `cardTab !== null`, leave out the captions read from `summary` (`wb.caption.settledOutside.*`, `wb.caption.receiptTaken.*`, `wb.caption.rejected.*`, `wb.caption.unmapped.*`, `wb.selfConfirmed.count`); they count the whole month. The two reason breakdown lines stay (they already read the filtered lists).
- The Card chips in `FilterBar` duplicate the tabs: when `cardSections.length > 0` pass `cards={[]}` to `FilterBar`, and clear a stored card filter once with `useEffect(() => { if (cardSections.length > 0 && filters.card) setFilters((f) => ({ ...f, card: "" })); }, [cardSections.length, filters.card]);`. On a month without tabs the chips stay exactly as they are.
- The bulk "Confirm N shown" / "Reject N shown" act on the rows shown, so in a tab they act on that tab's rows only. No change needed.

## 4. Expenses page (`ExpensesReviewGrid.tsx`)

- `const cardSections = safeCardSections(data?.card_sections);` and `const [cardTab, setCardTab] = useCardTab(batchId, cardSections);` next to the other hooks, before the early returns.
- Render `<CardTabs runId={batchId} sections={cardSections} coverage={data.coverage ?? []} active={cardTab} onPick={setCardTab} page="expenses" />` directly above the summary tiles (after the `CoverageAttention` block).
- `grouped`: add `.filter((r) => inCardTab(cardTab, r.card_section))` to `source` (add `cardTab` to the dependencies).
- Tiles, only when `cardTab !== null`, from the selected section and the tab's rows:
  - Expenses tile: `value={section.n_expenses}`; no copies `sub`.
  - Totals tile: the section's `totals_by_ccy` in place of `summary.totals_by_ccy`; leave out the "amounts unreadable" and "copies set aside" lines under it (they count the whole month).
  - Every box tile (Categorized, Uncategorized, Ready, and the second row): its number is the count of the tab's rows whose `boxes` contains that box, used for the value, for the `> 0` checks that show a tile and for `boxTile`. Write it as one helper `boxCount(box, summaryValue)` that returns `summaryValue` when `cardTab === null` or `!boxesKnown`.
- When a tab is selected and it has no rows (live August: card 3876 has 37 charges and no receipt), show `t("cardTabs.emptyExpenses")` in the existing dashed empty box instead of the grouped tables.
- Everything else on the page stays month-wide: the card review strip, the held inbound strip, set-aside, upload and parse issues, the duplicates banner, the month-move banner, the report coverage line.

## 5. Do not change

- The All tab: with `cardTab === null` both pages render exactly as today, same numbers, same sections.
- `MonthHeader`, `SummaryBar` (its counts, "Ready to post" and Publish read the whole month), `StatusLine`, `CoverageAttention`, `DuplicatesPanel`, `HowThisWorks`, the manual-match picker (it keeps every card's receipts), every download, every backend call.
- `coverage` and `ready_to_post` keep their current readers.
- No new request: both fields ride the GETs the pages already make.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `cardTabs.aria` | Cards | Cartões |
| `cardTabs.all` | All | Todos |
| `cardTabs.noCard` | No card | Sem cartão |
| `cardTabs.noCard.tip` | Receipts the tool could not place on a card | Recibos que a ferramenta não conseguiu associar a um cartão |
| `cardTabs.statement.loaded` | Statement {files} | Extrato {files} |
| `cardTabs.statement.notRecorded` | Statement not recorded | Extrato não registrado |
| `cardTabs.statement.notRecorded.tip` | This card has charges this month, but no statement upload was recorded for it: its charges came in another card's statement. | Este cartão tem lançamentos neste mês, mas nenhum extrato foi registrado para ele: os lançamentos vieram no extrato de outro cartão. |
| `cardTabs.statement.notLoaded` | No statement loaded for this card | Nenhum extrato carregado para este cartão |
| `cardTabs.period` | {start} to {end} | {start} a {end} |
| `cardTabs.charges.one` | 1 charge | 1 lançamento |
| `cardTabs.charges.many` | {n} charges | {n} lançamentos |
| `cardTabs.matched` | {n} matched | {n} conciliados |
| `cardTabs.open` | still open {amounts} | em aberto {amounts} |
| `cardTabs.openNothing` | nothing open | nada em aberto |
| `cardTabs.booked` | booked without a receipt: {n} ({amounts}) | lançados sem recibo: {n} ({amounts}) |
| `cardTabs.receipts.one` | 1 receipt | 1 recibo |
| `cardTabs.receipts.many` | {n} receipts | {n} recibos |
| `cardTabs.receiptsNoCharge` | {n} without a charge | {n} sem lançamento |
| `cardTabs.expenses.one` | 1 expense | 1 despesa |
| `cardTabs.expenses.many` | {n} expenses | {n} despesas |
| `cardTabs.emptyExpenses` | No expenses on this card this month. | Nenhuma despesa neste cartão neste mês. |

Add every key to both dictionaries in the same edit. No em-dashes in any UI copy.

## Checking it landed

Numbers are August 2026 as of 2026-09-17; they move as the month is worked. What must hold is the shape, and that the tabs' counts add up to the All numbers.

1. Bundle: `card_sections`, `card_section`, `cardTabs.noCard` and `cardTabs.statement.notRecorded` appear in the `/assets/*.js` chunks (crawl the lazy route chunks, not only the six assets `index.html` names). Controls still present: `ready_to_post` and `coverage`.
2. Cold, from the login gate, August Matching (`/runs/074a7b8905d7`): the tab row reads All, 3645 (40), 3876 (37), 2838 (34), 1176 (3), 9693, No card, then "+ 4 cards with nothing this month". 1176 and 9693 carry the amber dot. All is selected and the page matches today's (Receipts without a charge 10, Charges without a receipt 101).
3. Click 2838: the line reads "Statement August2026.xlsx · Aug 01, 2026 to Aug 30, 2026 · 34 charges · 4 matched · still open USD 7,438.36 · 11 receipts · 5 without a charge"; the view buttons read Receipts without a charge 5, Charges without a receipt 28, Matched 4. Click 1176: "Statement not recorded · ... · 3 charges · 0 matched · still open USD 36.00 · 2 receipts · 1 without a charge". Click No card: "2 receipts · 2 without a charge" and no charges.
4. Reload the page: 2838 (or the last tab picked) is still selected. Open Expenses of the same month (`/expenses/074a7b8905d7`): the same tab is selected.
5. August Expenses, tab 2838: "10 expenses · EUR 426.20 · USD 1,473.73 · Statement August2026.xlsx · ..."; the Expenses tile reads 10. Tab 3876: "No expenses on this card this month." All: the Expenses tile reads 20 and the totals EUR 668.00 · USD 2,033.86, as today.
6. PT: the tabs read Todos ... Sem cartão; the 1176 line starts "Extrato não registrado".
7. A month with one card or none shows no tab row on either page.
````
