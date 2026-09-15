# Lovable prompt: the card list leaves the top of the month

Backlog item 71 (owner, 2026-09-15: "the card list at the top of a month's
page makes everything harder to overview; come up with something better").
SPA only: every field below already ships and was read off the live payloads
of July (`50622baec444`) and August (`074a7b8905d7`) on 2026-09-15.

Paste everything between the two rules into the `brisken-expense-review`
Lovable project.

---

Paste into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`. No backend change: every field named below
already ships.

## Why

On a month's page, the "Coverage by card" table (9 rows, 5 or 6 of them
"nothing loaded yet") and the Statements box fill the whole first screen under
the sticky summary bar; on the live July month the first charge row starts 1.7
screen heights down. On Review expenses the card-review strip adds another
673 to 941px before the first expense. The bookkeeper decides almost nothing
from these blocks on a normal month, so they move out of the way and speak up
only when something needs her.

## 1. Fix the filter option counts first (RunWorkbench.tsx, `optionCounts`)

Every Card, Bucket and suggested-receipt option currently shows the total row
count (live July: "112" on all nine cards, including cards with 0 charges),
because `countWith(patch, skip)` applies the option and then skips that same
dimension inside `rowMatches`. Count with the option applied and no skip:
`rows.filter((r) => rowMatches(r, { ...filters, ...patch })).length`.
Expected on July with no other filter: 3876 = 48, card-2838 = 36, 3645 = 27,
card-0340 = 1, the other five = 0. Buckets: Needs review 12, Unmatched 73,
Reconciled 26, Refund 1.

## 2. Workbench: take the Coverage and Statements panels off the top

In `RunWorkbench.tsx` remove the `<StatementPanels>` mount under the title.
In its place render one muted line under the subtitle, built from
`statements[]`:

"{n} charges · Statement {upload_name} ({period_start} to {period_end}) · Download"

- When there is exactly one entry and its `advisory` is null: that line, with
  the existing per-file download link.
- When there are two or more entries, or any `advisory` is set: keep today's
  `StatementsPanel` table, collapsed behind "{k} statements ›", opened by
  default only when an advisory is set.

## 3. Card chips replace the Card select in the filter bar

Replace the CARD `Select` in `FilterBar` with a chip row, same chip style as
the FILTERS toggles:

- "All {n}" first, then one chip per `coverage[]` entry with
  `n_transactions > 0`, in API order. Chip text: the last value of
  `coverage[].digits` when present, else `coverage[].label`, then " · " and
  the section 1 count. Tooltip: the full `label`. Clicking sets
  `filters.card` to `coverage[].key` (same URL param `card=` as today);
  clicking the active chip clears it.
- Entries with `n_transactions === 0` collapse behind one link
  "+ {n} cards with nothing this month ›", which expands to muted,
  non-clickable chips. Do not drop them: they answer "which cards have no
  statement".
- When a card chip is active, one line under the chip row:
  "{label} · {person} · {entity} · {n_reconciled} matched ·
  {n_review} need a look · {n_unmatched_tx} no receipt · {unreconciled}".
  `person` comes from `GET /api/cards` (`cards[].key === coverage[].key`);
  omit it when there is no match. `unreconciled_by_ccy` values are
  pre-formatted strings: render "USD 1,054.48" as given, never parse them.
  Omit the unreconciled part when the map is empty.

## 4. One attention banner, only when something needs action

Above the filter bar, render an amber banner (the existing warning style)
ONLY when at least one of these holds; otherwise render nothing at all:

a) **A card on the statement the month did not know.** `coverage[]` entries
   with `known === false`. Before saying "not in your card list", check
   `GET /api/cards`: if a `cards[].key === coverage.key`, or any
   `cards[].digits` value is in `coverage.digits`, the card was defined after
   this month was loaded. Then say "defined after this month was loaded;
   refresh master data" and link to `/expenses/{id}` (where Refresh master
   data lives). Otherwise say "not in your card list" and link to Settings.
   `coverage[].known` describes the month's upload-time copy of the card
   list, never the live one.
b) **Cards with receipts but no charges.** `card_review.resolved[]` entries
   whose `card.key` matches a `coverage[]` entry with `n_transactions === 0`.
   List "{card.label} ({card.entity}): {n_rows} receipts" with a link
   "Add a statement" to `/expenses/{id}`. On the workbench `card_review` is
   not on the run payload: read it with `getExpenseBatch(runId)` under the
   grid's own query key (`["expense-batch", runId]`), so both pages share the
   cache. Live August shows two: card-1176 (Consulting) 2 receipts and
   card-9693 (Cloud Services) 2 receipts. Live July shows none.
c) **`summary.n_charges_no_entity > 0`**: "{n} charges without a company";
   clicking applies the existing "Charges without a company" filter.

Keep the existing `setup_advisories` and `statement_advisory` blocks as they
are.

## 5. Review expenses (ExpensesReviewGrid.tsx)

- Replace the `<StatementPanels>` mount with the same one-line statement
  summary from section 2 and the section 4 banner (a and b; `card_review` is
  already on this payload, and `card_review.resolved[].card.person` is there
  too).
- `CardReviewStrip`: collapsed by default to one amber line:
  "{n_unresolved_rows} receipts not matched to a company card ·
  {a} need a card · {b} look private · Review ›"
  where a = the sum of `n_rows` over `unresolved_hints` with
  `suggested_private !== true`, and b = the rest. Omit a part that is 0.
  Open by default when a > 0. The expanded content is today's strip,
  unchanged, except:
  - the private note under a unit that HAS `digits` uses the new key
    `expx.cards.strip.suggestedPrivate.numbered`; keep the current key for
    units without digits (today "no card number readable" appears under
    numbered units like 2544 and 9129, which contradicts itself).
  - write "Card ending {digits}" only when `digits.length === 4`; otherwise
    show the first spelling verbatim. Live August prints the hint
    "42463153XXXXXX38": 42463153 is the START of that card number, not its
    ending.
  Live expectation: July "25 receipts ... · 1 need a card · 24 look private",
  opened; August "8 receipts ... · 8 look private", collapsed.

## 6. i18n (EN and PT in the same edit)

| Key | EN | PT |
|---|---|---|
| `stm.oneLine` | {n} charges · Statement {file} ({period}) | {n} lançamentos · Extrato {file} ({period}) |
| `stm.many` | {k} statements | {k} extratos |
| `wb.filter.card.empty` | + {n} cards with nothing this month | + {n} cartões sem lançamentos neste mês |
| `wb.filter.card.breakdown` | {matched} matched · {review} need a look · {noReceipt} no receipt | {matched} conciliados · {review} precisam de revisão · {noReceipt} sem recibo |
| `cov.attn.notInList` | {n} cards on the statement are not in your card list | {n} cartões do extrato não estão na sua lista de cartões |
| `cov.attn.definedSince` | defined after this month was loaded; refresh master data | cadastrado depois que este mês foi carregado; atualize os dados mestres |
| `cov.attn.receiptsNoCharges` | {n} cards have receipts but no charges on a statement | {n} cartões têm recibos, mas nenhum lançamento em extrato |
| `cov.attn.receiptsNoCharges.item` | {card} ({entity}): {n} receipts | {card} ({entity}): {n} recibos |
| `cov.attn.addStatement` | Add a statement | Adicionar extrato |
| `expx.cards.strip.summary` | {n} receipts not matched to a company card | {n} recibos sem cartão da empresa identificado |
| `expx.cards.strip.summary.choose` | {n} need a card | {n} precisam de um cartão |
| `expx.cards.strip.summary.private` | {n} look private | {n} parecem particulares |
| `expx.cards.strip.review` | Review | Revisar |
| `expx.cards.strip.suggestedPrivate.numbered` | This card number is not a company card; suggested as a private expense. | Este número de cartão não é de um cartão da empresa; sugerido como despesa particular. |

No em-dashes in any UI copy.

## 7. Do not change

The row tables, bucket sections, "Confirm N shown" / "Reject N shown", the
summary bar, the Downloads row, the strip's assign / new-card / learn
behavior, Settings, and every backend call. `CoveragePanel` and
`StatementsPanel` stay in the codebase (section 2 reuses the Statements
table).

## 8. Render defensively

Type-check every `coverage[]`, `statements[]` and `card_review` element
before rendering; an unexpected shape degrades to plain text, never a blank
page. A month with an empty `coverage[]` shows no chip row and no banner, and
that is correct.

---

## Verify after publish (browser drive, PT, never bundle grep alone)

1. July `/runs/50622baec444`: no coverage table at the top; chips read
   3876 · 48, 2838 · 36, 3645 · 27, 0340 · 1 and "+ 5 cartões sem
   lançamentos"; no banner; clicking 3645 leaves 27 rows and the line reads
   "... 24 sem recibo · USD 1,054.48".
2. August `/runs/074a7b8905d7`: the banner lists 1176 (2 recibos) and 9693
   (2 recibos); the bucket toggles read Revisão 3, Sem recibo 96,
   Conciliados 11, Reembolso 1.
3. August `/expenses/074a7b8905d7`: the strip is collapsed to
   "8 recibos ... · 8 parecem particulares"; expanded, the 2544 unit carries
   the numbered private note and the 42463153 unit shows the verbatim
   spelling.
4. At 1440x900, with "How this works" dismissed, the first charge row is
   visible without scrolling on July's workbench.

Bundle signatures (decisive, for `tools/lovable-bundle-audit.py`):
`wb.filter.card.empty`, `cov.attn.receiptsNoCharges`,
`expx.cards.strip.summary.choose`.

Still open after this prompt, backend: the canonical last-4 grouping of
card hints (backlog item 35's second half), so a masked number like
`42463153XXXXXX38` resolves to its real ending instead of only being shown
verbatim.
