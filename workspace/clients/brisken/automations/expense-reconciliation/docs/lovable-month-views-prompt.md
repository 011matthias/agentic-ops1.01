# Lovable prompt: a month is two views, Expenses and Matching (item 79)

Backlog item 79 (owner direction 2026-09-16, verbatim): "A month's page needs
to be structured differently. A user needs overview and visibility of the
following: 1) the expenses that were created just with receipts; 2) (if a
statement has been attached) a separate overview of the transaction-expense
matching. The transactionless receipts, receiptless transactions,
needs-review, refund should all be ordered in their respective overview
pages." Plus the item 79 design constraint from note #46: every list shows
open items as the work, and decided items (confirmed, posted, settled outside,
copy set aside) move to a collapsed record with an undo.

SPA only. Every field named below ships on the live backend today (read off
July `50622baec444`, August `074a7b8905d7` and September `51a22ad72864` on
2026-09-16). No backend gate: paste any time. The optional top-level
`updated_at` the strip reads is being added by a separate backend PR; until it
deploys the strip falls back to `created_at`, exactly as the page does today.

Written against SPA main `c9f30bf8b5` (2026-09-16), with items 70 and 71
applied. Item 76 (clean rows confirm themselves) is being built in parallel
and owns the Status cell and per-row labelling of posted rows; this prompt
does not touch `RowView`, `RowStatusBadge` or the Status cell, so 76's prompt
lands on this shape without a conflict.

Reviewed adversarially before commit (three lenses against the SPA source, the
live payloads and the house rules; 46 confirmed findings folded in).

Paste everything between the two rules into the `brisken-expense-review`
Lovable project.

---

Paste into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API
at `api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth
stays the existing `Authorization: Bearer <token>`. No backend change: every
field named below already ships. Query keys stay `["expense-batch", id]` and
`["run", id]`; the batch id and the run id are the same id.

## Why

A month has two pages today, `/expenses/{id}` (Review expenses) and
`/runs/{id}` (the reconciliation workbench), and they are joined badly:

- The workbench has no standing link back to Review expenses. Its fixed links
  are "Menu" (to `/months`) and "Dashboard", which lands on the old upload
  form at `/`. The only link across is inside the card-attention banner ("Add
  a statement", "Refresh master data"), which renders only when a card needs
  attention (August today, not July). The Months list sends every statement
  month to the workbench, so reaching July's Review expenses page takes a
  detour through another month and the old `/expenses` list.
- `/runs/{id}` for a month with no statement (September, June, May, January)
  shows "This page didn't load". The backend answers that address with the
  EXPENSE payload, which has no `rows`, and `RunWorkbench.tsx` reads
  `data.rows.length` (the `FilterBar` `totalRows` prop) and
  `data.unmatched_receipts.length` without a guard.
- The four classes the owner names sit as stacked sections plus a side list
  on one page 12,000 to 15,000 px tall, under a sticky bar of thirteen tiles
  that pins 301 px of a 900 px screen.
- On July, 85 of 112 charges are already posted in Criss's workbook (yellow
  fill). They sit inside the sections looking exactly like open work, while
  the "Posted" bucket chip reads 0 and cannot be switched back on once off.
- Review expenses of a statement month still shows "Expenses are read-only"
  although every control there has worked since item 70.

After this prompt a month is ONE place with two views under one shared strip:
**Expenses** (every expense that came from a receipt) and **Matching** (the
statement's charges against those receipts, sorted into five cards, one open
at a time).

## 0. Hook order (read first; applies to every section)

`RunWorkbench` declares all of its hooks, then returns early for `isLoading`
(the skeleton) and for `error || !data`. Every hook this prompt adds to
`RunWorkbench` (`useNavigate`, the redirect `useEffect`, the per-view
open/decided `useMemo`s, any fold `useState`) goes WITH the existing hooks,
ABOVE `if (isLoading)`, so the same hooks run on every render. Any new
sub-component (`MonthHeader`, a fold) declares its hooks at its own top, above
any early return of its own. In `DuplicatesPanel`, declare any new `useState`
directly under `const t = useT()`, above `if (groups.length === 0) return
null`. A hook placed below an early return throws "Rendered more hooks than
during the previous render" on every load.

## 1. A shared month strip on both pages (new `src/components/MonthHeader.tsx`)

Mount `<MonthHeader>` on both `ExpensesReviewGrid` and `RunWorkbench`,
directly under `<DashboardHeader />`.

Props: `runId: string`, `active: "expenses" | "matching"`,
`onAddStatement?: () => void`, `refreshing?: boolean`,
`fallbackLabel?: string`.

Data: `useQuery({ queryKey: ["expense-batch", runId], queryFn: () =>
getExpenseBatch(runId), retry: 1 })`. Both pages already have this entry in
the cache (`CoverageAttention` reads it on the workbench), so this adds no
request.

Two parts:

**a) The strip, sticky** (`sticky top-14 z-10`, directly under the sticky
Menu bar; one compact row):

- A link "← Months" to `/months`.
- The month name: `trip.name` when `batch_type === "trip"` and `trip` is
  present, else `label`, else `fallbackLabel`, else `runId`.
- The tabs:
  - "Expenses · {summary.n_expenses}" linking to `/expenses/$batchId`.
  - When `batch_type === "trip"`: no second tab. A trip never takes a
    statement.
  - Else when `has_statement === true`: "Matching · {n} charges" linking to
    `/runs/$runId`, where `n` is the sum of `coverage[].n_transactions` (July
    112, August 111; equal to the run payload's `summary.n_transactions`).
    Never sum `statements[].n_rows`: that is what each uploaded file held, so a
    partial statement followed by the full cycle counts the overlap twice.
    Omit the count when `coverage` is not a non-empty array.
  - Else, when `onAddStatement` is given: a tab-styled button "Add a
    statement" that calls `onAddStatement()`. When it is not given, render
    nothing in that slot.
  - The active tab is the `active` prop. While the batch query is loading,
    render a skeleton for the name and both tab outlines; never block the page
    body on it.
- **When the batch query errors** (an older statement-first run opened from
  `/classic`, which is not an expense batch: the backend answers 400 "not an
  expense batch"): render "← Months", the name `fallbackLabel ?? runId`, and a
  single active "Matching" tab with no count. No Expenses tab, no Add a
  statement, and never an error message inside the strip.

**b) One meta line under the strip, NOT sticky**:
`{t("expx.review.lastUpdated")}: {fmtDate(updated_at ?? created_at, locale)}`
(the existing key and markup `ExpensesReviewGrid` uses today; only its mount
moves; `updated_at` is optional), then the existing `<StatementSummary
runId={runId} statements={statements} />` when `statements` is a non-empty
array, then, when `refreshing` is true, a small muted `· {t("wb.refreshing")}`.

Remove the page-level copies that the strip replaces:

- `ExpensesReviewGrid.tsx`, normal state only: the back link labelled
  `expx.landing.title` (to `/expenses`), the page `<h1>` and "Last updated"
  line, the "Open reconciliation" link (`months.locked.openWorkbench`), and the
  `<StatementSummary>` mount. The ERROR state (batch query failed) keeps its
  own back link unchanged. Keep the subtitle line `expx.review.subtitle`, the
  trip meta block and the action buttons.
- `RunWorkbench.tsx`: the back link `wb.backToDashboard` (to `/`) in the normal
  state (the not-found state's link goes to `/months` instead), the `<h1>`, the
  "Run {id}" line and the `<StatementSummary>` mount. Pass
  `refreshing={isFetching}` from the existing `["run", runId]` query (the
  removed "Run {id}" line was the only place that indicator showed), and pass
  `fallbackLabel` = today's title (`t("wb.title.cardRun", { card, date:
  formatDate(date) })` when `parseLabel(data.label)` yields both, else
  `data.label`; keep `parseLabel` and `wb.title.cardRun`). Keep the subtitle
  `wb.subtitle.template` and the "Add digital receipts (folder or zip)"
  trigger.

Route titles: `/runs/$runId` becomes "Matching · Brisken" (today's title
contains an em-dash); `/expenses/$batchId` becomes "Expenses · Brisken".

## 2. `/runs/{id}` for a month without a statement goes to Expenses

In `RunWorkbench`, the run payload shape is recognised by
`Array.isArray(data.rows)`. Redirect only on a FRESH read, because a reply
cached before a statement was attached is stale:

```ts
const navigate = useNavigate(); // import from @tanstack/react-router
useEffect(() => {
  if (isSuccess && isFetchedAfterMount && !isFetching && data && !Array.isArray(data.rows)) {
    navigate({ to: "/expenses/$batchId", params: { batchId: runId }, replace: true });
  }
}, [isSuccess, isFetchedAfterMount, isFetching, data, runId]);
```

(both hooks with the existing hooks, above `if (isLoading)`; section 0). After
the `error || !data` early return, add a plain `if (!Array.isArray(data.rows))
return <small loading placeholder/>` with no hook inside it. If that refetch
fails, the existing error state renders instead of a redirect.

Guard EVERY list read on this page so no render path can throw first:
`data.rows`, `data.unmatched_receipts`, `data.assignable_receipts`,
`data.unmatched_transactions`, `data.duplicate_groups`,
`data.duplicate_charges`, `data.duplicate_receipts`, `data.coverage`,
`data.statements`, inside hooks (`useMemo`, `optionCounts`, `grouped`) as well
as JSX. Use `Array.isArray(x) ? x : []`.

On `ExpensesReviewGrid`, pass `onAddStatement={() => setAttachOpen(true)}` to
`MonthHeader` when the month is not a trip. In `AttachStatementDialog`, when
the job reports `done`, call `queryClient.removeQueries({ queryKey: ["run",
runId] })` and `queryClient.invalidateQueries({ queryKey: ["expense-batch",
runId] })` BEFORE the existing `navigate({ to: "/runs/$runId" })`, so Matching
never opens on the stale expense-shaped cache.

## 3. Matching: five cards replace the bucket toggles and the tile bar

At the top of the Matching content, right under the meta line, render one row
of five cards, in this order. Each card is a button: label and the month's
whole count, plus a "{open} open" subline (rule in section 5). Exactly one
card is active; the active card decides which single table renders below.

| # | View key | EN label | Whole count |
|---|---|---|---|
| 1 | `receipts` | Receipts without a charge | `summary.n_unmatched_rec` |
| 2 | `unmatched` | Charges without a receipt | `summary.n_unmatched_tx` |
| 3 | `review` | Needs review | `summary.n_review` |
| 4 | `refund` | Credits on the statement | `summary.n_refunds` |
| 5 | `reconciled` | Matched | `summary.n_reconciled` |

Card 4 is named "Credits on the statement", never "Refund": the bucket holds
every credit line on the statement (both live rows are the card payment
"Payment Thank You-Mobile"), and the tool cannot yet tell a payment from a
refund. Do not add a client-side taxonomy.

**State.** Replace `buckets: RowBucket[]` in `Filters` with `view` (one of the
five keys, default `receipts`). In `loadFilters`, read `p.view` when it is one
of the five keys, else `receipts`; ignore any stored `buckets`. In the query
string, `view=` replaces `bucket=`; an unknown or missing value means
`receipts`, and an old `bucket=` parameter is ignored. Keep the per-month
storage key `brisken.workbench.filters.v2:{runId}` and replace-not-push URL
updates, as today. `view` is navigation, not a filter: both Clear filters
buttons (the FilterBar one and the empty-state one) reset to
`{ ...DEFAULT_FILTERS, view: filters.view }`, so clearing never changes the
active view.

Row membership for views 2 to 5 is `rows[].effective_bucket` (`unmatched`,
`review`, `refund`, `reconciled`). Never `rows[].section` for membership:
`section` is a display lane in which a posted row always reads `posted`. View
1 is `data.unmatched_receipts`.

Remove: the BUCKET toggle group in `FilterBar` (including the dead `posted`
entry and `wb.bucket.posted`), `BUCKET_ORDER` as a filter, and the stacked
`BUCKET_ORDER.map` sections.

**Status line** beside (or directly under) the cards:

- The readiness pill and the broken-month banner MOVE out of `SummaryBar.tsx`
  into this line: same logic (`ready_to_post`, `month_health.state`,
  `n_undecided` with the existing singular and plural keys), same i18n keys,
  same styling. After this change there is exactly one pill and at most one
  banner on the page.
- One "{amount} still open" per `unreconciled_by_ccy` pair, where `{amount}` is
  `${ccy} ${value}`: currency code first, one space, then the value string
  exactly as given (pre-formatted; never parse it), the order the card chips
  already use. Omit when the map is empty.
- "1 receipt from next door" / "{n} receipts from next door" only when
  `n_adjacent_borrowed > 0`.

**Retire the tile bar.** In `SummaryBar.tsx` remove the stat tiles (match rate,
reconciled, review, unmatched tx, unmatched receipts, undecided, unmapped
accounts, charges without a company, waiting on a pick, rejected pairings,
receipts from next door, settled outside, unreconciled), the readiness pill and
the broken-month banner. `SummaryBar` keeps its buttons (Download
reconciliation (PDF), Confirm all matched, Commit learnings, Publish) and its
Downloads row, and still computes `ready` and `brokenMonth` from `summary` for
those buttons' disabled states and titles, unchanged. Remove its
`onShowChargesNoEntity` prop with the tile. Make `SummaryBar` NOT sticky (drop
`sticky top-14 z-10`); only the Menu bar and the month strip stay pinned.
`match_rate` and `receipt_match_rate` are no longer shown on this page; they
stay on the payload.

**Captions inside a view**, one muted line above that view's table, each only
when the count is above zero (singular key when the count is 1):

- View 1: `summary.n_settled_outside` -> "{n} settled outside the card" (a
  button that opens the view's decided record).
- View 2: `summary.n_charges_receipt_taken` -> "{n} wait on a receipt another
  charge holds"; `summary.n_rejected_pairings` -> "{n} rejected pairings".
- View 5: `summary.n_unmapped_accounts` -> "{n} receipt lines without a
  category".

**Charges without a company.** `summary.n_charges_no_entity` keeps its line in
`CoverageAttention` and the "Charges without a company" chip in the FILTERS
row. The `onChargesNoEntity` callback `RunWorkbench` passes to
`CoverageAttention` no longer writes `buckets`: it sets `noEntity: true` and,
when the active view is `receipts`, switches `view` to the first of
`unmatched`, `review`, `reconciled`, `refund` that holds a row with
`legal_entity_id === ""` among its OPEN rows; if none has one open, the first
that holds one at all, with "Show decided rows" switched on so the rows are
visible. It never leaves the page on view 1.

## 4. One table per view

- **View 1** renders the existing UNMATCHED RECEIPTS table (columns, `View
  receipt`, the duplicate badge, `SettledByBadge`, `SettleOutsideControl`) as
  the view body. Its standalone section and heading below the charge tables go
  away.
- **Views 2 to 5** render the existing charge table (`RowView`,
  `CandidateRow`, every column and action) for that bucket only. The section
  heading is the card label and count.
- **The filter card** keeps search, STATUS, SORT, the card chips, COMPANY,
  SUGGESTED RECEIPT, the FILTERS chips and "{shown} of {total} charges" /
  Clear filters, all applied inside the active view; the per-option counts
  (`optionCounts`) count inside the active view. On view 1 show only the
  search box (applied to the receipt's vendor string) and the "Show decided
  rows" switch; hide every other control, since a receipt has no card key,
  status or candidates. The card chips keep today's rule for which chips exist
  (every card with month `n_transactions > 0`), so a card with no row in the
  active view shows its chip at 0.
- **The bulk bar** ("Confirm N shown" / "Reject N shown") renders on views 2
  to 5 only and targets the OPEN rows shown (section 5), never decided ones.
- **Empty inside a view.** When the view has at least one open row before the
  control-bar filters and none after them, show the existing "No charges match
  these filters" state with its Clear filters button (view 1: "No receipts
  match this search"). When the view has 0 open rows before any filter (July
  views 3 and 4), show one muted line "Nothing open here" in place of the
  table, with no Clear button, followed by the decided fold.
- **`HowThisWorks`** moves below the active table (dismiss behaviour and its
  storage key unchanged), so the first open row sits on the first screen.
- **`DuplicatesPanel`** stays at the bottom of the Matching view, below
  `HowThisWorks`, with one change in section 5.

## 5. Open work first, decided work in a collapsed record

Every view splits its rows into OPEN (rendered as the table) and DECIDED
(collapsed under one fold line with a count and "Show"; clicking shows them
below the open rows, same columns, visually muted; "Hide" collapses again).

| View | A row is decided when | Undo on the decided row |
|---|---|---|
| 1 | `duplicate?.is_extra === true` (a copy the tool set aside) | "Not a duplicate" for that group: `POST /api/runs/{id}/duplicates/resolve` `{group_id, action: "ignore"}` (the call the duplicates panel already makes) |
| 1, extra rows | a receipt settled outside the card (see the note under this table) | the existing `unsettleOutside(runId, document_id)` (DELETE) |
| 2 to 5 | `row.section === "posted"`, OR (`row.status` is `"confirmed"` or `"already_posted"` AND `row.effective_bucket === "reconciled"`) | for a confirmed or already-posted row: the reset `RowView` already shows in its Actions cell when `status !== "pending"` (no new control). For a workbook-posted row (`section === "posted"`, `status === "pending"`): none, and NO per-row chip (`RowView` stays unchanged; labelling posted rows one by one is item 76's) |

- A `rejected` row is NOT decided: it still has no receipt, so it stays open
  with its existing Reopen action.
- A `confirmed` row whose `effective_bucket` is not `reconciled` lost its
  receipt to a newer confirm or manual match. It holds no receipt, so it is
  OPEN, like a rejected row, and keeps its reset action.

**Settled-outside rows in view 1.** They are not in `unmatched_receipts`: read
them from the batch payload (`["expense-batch", runId]`), `expenses[]` with a
`settled_outside` object, and include one only when the run payload does not
place its `document_id` (it is not the `chosen_document_id` of a row whose
`effective_bucket` is `reconciled`, and not a candidate `document_id` with
`match_type` other than `"manual"` on a row whose `effective_bucket` is
`review`). These are `ExpenseRow` objects: their `vendor` is an object
`{display, raw, source}` (or a legacy string). Map each to the receipt row
shape before rendering: vendor = `vendorDisplay(e.vendor)` (from `@/lib/api`),
total, currency, date, `document_id`, `receipt_image_available`. Use that
string everywhere a vendor is used (cell, `ViewReceiptButton`, the view-1
search); never render `e.vendor` directly and never call `.toLowerCase()` on
it. These rows show the undo instead of `SettleOutsideControl`.

**Invalidations for settled outside on Matching.** The view-1 open list and
caption read the run query; the settled-outside record reads the batch query.
So on the Matching view, BOTH the settle action (the `onDone` passed to
`SettleOutsideControl`) and the new undo invalidate `["run", runId]` AND
`["expense-batch", runId]` on success. The settle keeps `applySummary` as
today; the undo applies `res.summary` to the run cache only when
`typeof res.summary?.n_transactions === "number"` (its reply is the batch
summary shape), otherwise it relies on the two invalidations.
`SettledOutsideCell` on the Expenses page stays as it is.

**Fold line text** (singular key when the count is 1): "{n} already posted in
your workbook" when every decided row in the view is workbook-posted; "{n}
copies set aside" when every decided row in view 1 is a copy; otherwise "{n}
decided".

**The switch.** "Show decided rows", persisted per month (same storage, flag
`decided` in `f=`), opens every fold at once. Off by default. It lives in the
existing `filters` state, so it adds no hook.

**Counts.** Each card keeps its whole count; the four charge cards add up to
the month (`n_reconciled + n_review + n_unmatched_tx + n_refunds` equals
`n_transactions`), and card 1 counts receipts outside that sum. A card shows
"{open} open" when `open < whole`. Card 1 is the exception: its settled-outside
rows are not in `n_unmatched_rec`, so it shows "{open} open" whenever its
decided record is not empty. `n_undecided` in the pill stays the backend's
number; do not recompute it.

**Duplicates panel.** A group is decided when its `resolution` is set, or when
it is a receipt group (`kind === "receipt"`) with `resolution` null, because
the tool already set its extra copy aside (the same rows view 1 folds). Only
charge groups with `resolution` null stay open. Open groups render as today.
Decided groups move under a collapsed "{n} decided · Show" line and keep both
of today's buttons, unchanged in label, style and handler: the button that does
NOT match the current resolution flips the ruling (Real duplicate / Not a
duplicate). The backend accepts only `"confirmed"` or `"ignore"` and cannot
clear a resolution, so do not add an "Undo" label and never send a null or
empty resolution. Do NOT filter or reorder the underlying arrays: the panel
pairs `duplicate_groups` with `duplicate_charges` / `duplicate_receipts` by
index within a kind, so partition only at render time.

## 6. Expenses view (`ExpensesReviewGrid.tsx`)

- Remove the "Reconciliation started" box (`months.locked.title` /
  `months.locked.body`). Editing works on statement months since item 70.
- The toolbar renders the same buttons on every company month, statement or
  not: Add receipts, Add expense, Save corrections to memory, Add a statement
  (not on a trip), Download report (PDF), Download CSV (data export), and the
  overflow menu. Remove the `hasStatement` branch that hid the first three
  (the backend accepts all three on a statement month and re-matches after
  them).
- On a month with `has_statement === true`, one line under the meta line,
  linking to `/runs/$runId`: `{t("expx.recon.prefix")}` followed by five
  segments joined with " · ", each picked by its count (`.one` when the count
  is 1, else `.many` with `{n}`): matched (`summary.n_reconciled`), need
  review (`summary.n_review`), charges without a receipt
  (`summary.n_unmatched_tx`), receipts without a charge
  (`summary.n_unmatched_rec`), credits (`summary.n_refunds`). Read it with
  `useQuery({ queryKey: ["run", runId], queryFn: () => getRun(runId), enabled:
  data?.has_statement === true })`. Render it ONLY when that reply has
  `Array.isArray(rows)` and a numeric `summary.n_transactions`; otherwise
  render nothing. This `n_review` (charges in review) is not the grid's own
  `summary.n_review` (receipts that need a look).
- Everything else stays: tiles, the collapsed card-review strip, set aside,
  parser notes, the duplicate-copies bar, the Needs a look / Assign a category
  / Ready groups, every cell and dialog.

## 7. Ride-along fixes on the same two pages

- **Raw key text in the Category / Account cell.** `SourceBadge` builds the
  label key `expx.review.badge.short.${source}` and the tooltip key
  `expx.review.badge.${source}` from `posting_category.source`, and sets its
  `learned` / `edited` / `needsReview` tones by exact equality. The source can
  be several sources joined with `"; "` (live: `"override; llm"`, `"override;
  registry"`, `"llm; review"`, `"override; review"`), and then literal keys
  print in the label and the tooltip and the tone falls back to grey. Split the
  source on `"; "` and look each part up: render the found short labels joined
  with " · " and the found tooltip texts joined with " · "; set `learned`,
  `edited` and `needsReview` when ANY part matches (needs-review still wins).
  An unknown part renders nothing, never a key; if no part is known, render no
  badge.
- **"1 receipts".** The expanded card-review strip prints
  `expx.cards.strip.rows` as "1 receipts". Use a singular key when `n === 1`.
- **Em-dashes in copy on these pages.** Replace in EN and PT:
  `expx.setaside.restore` ("This is a receipt, restore" / "Isto é um recibo,
  restaurar"), `expx.setaside.restored` ("Restored: now an expense" /
  "Restaurado: agora é uma despesa"), `expx.review.toast.committed` ("{n}
  corrections saved; they will auto-fill next month" / "{n} correções salvas;
  vão preencher automaticamente no próximo mês"), `fb.done` ("Thanks.
  Double-click anywhere to leave another." / "Obrigado. Dê um duplo-clique em
  qualquer lugar para deixar outra.").

## 8. i18n (EN and PT in the same edit, `src/lib/i18n.tsx`)

`t()` has no plural logic: pick `.one` at the call site when the count is 1.

| Key | EN | PT |
|---|---|---|
| `month.back` | ← Months | ← Meses |
| `month.tab.expenses` | Expenses | Despesas |
| `month.tab.matching` | Matching | Conciliação |
| `month.tab.charges` | {n} charges | {n} lançamentos |
| `month.tab.addStatement` | Add a statement | Adicionar extrato |
| `wb.view.receipts` | Receipts without a charge | Recibos sem lançamento |
| `wb.view.unmatched` | Charges without a receipt | Lançamentos sem recibo |
| `wb.view.review` | Needs review | Precisa revisão |
| `wb.view.refund` | Credits on the statement | Créditos no extrato |
| `wb.view.reconciled` | Matched | Conciliadas |
| `wb.view.open` | {n} open | {n} em aberto |
| `wb.view.noneOpen` | Nothing open here | Nada em aberto aqui |
| `wb.filter.emptyReceipts` | No receipts match this search | Nenhum recibo corresponde a esta busca |
| `wb.status.stillOpen` | {amount} still open | {amount} em aberto |
| `wb.status.nextDoor.one` | 1 receipt from next door | 1 recibo do mês vizinho |
| `wb.status.nextDoor.many` | {n} receipts from next door | {n} recibos do mês vizinho |
| `wb.caption.settledOutside.one` | 1 settled outside the card | 1 liquidado fora do cartão |
| `wb.caption.settledOutside.many` | {n} settled outside the card | {n} liquidados fora do cartão |
| `wb.caption.receiptTaken.one` | 1 waits on a receipt another charge holds | 1 aguarda um recibo que outro lançamento usa |
| `wb.caption.receiptTaken.many` | {n} wait on a receipt another charge holds | {n} aguardam um recibo que outro lançamento usa |
| `wb.caption.rejected.one` | 1 rejected pairing | 1 pareamento rejeitado |
| `wb.caption.rejected.many` | {n} rejected pairings | {n} pareamentos rejeitados |
| `wb.caption.unmapped.one` | 1 receipt line without a category | 1 linha de recibo sem categoria |
| `wb.caption.unmapped.many` | {n} receipt lines without a category | {n} linhas de recibo sem categoria |
| `wb.decided.fold.one` | 1 decided | 1 decidido |
| `wb.decided.fold.many` | {n} decided | {n} decididos |
| `wb.decided.foldPosted.one` | 1 already posted in your workbook | 1 já lançado na sua planilha |
| `wb.decided.foldPosted.many` | {n} already posted in your workbook | {n} já lançados na sua planilha |
| `wb.decided.foldCopies.one` | 1 copy set aside | 1 cópia separada |
| `wb.decided.foldCopies.many` | {n} copies set aside | {n} cópias separadas |
| `wb.decided.show` | Show | Mostrar |
| `wb.decided.hide` | Hide | Ocultar |
| `wb.decided.switch` | Show decided rows | Mostrar linhas decididas |
| `expx.recon.prefix` | Reconciliation: | Conciliação: |
| `expx.recon.matched.one` | 1 matched | 1 conciliada |
| `expx.recon.matched.many` | {n} matched | {n} conciliadas |
| `expx.recon.review.one` | 1 needs review | 1 precisa revisão |
| `expx.recon.review.many` | {n} need review | {n} precisam revisão |
| `expx.recon.unmatchedTx.one` | 1 charge without a receipt | 1 lançamento sem recibo |
| `expx.recon.unmatchedTx.many` | {n} charges without a receipt | {n} lançamentos sem recibo |
| `expx.recon.unmatchedRec.one` | 1 receipt without a charge | 1 recibo sem lançamento |
| `expx.recon.unmatchedRec.many` | {n} receipts without a charge | {n} recibos sem lançamento |
| `expx.recon.credits.one` | 1 credit | 1 crédito |
| `expx.recon.credits.many` | {n} credits | {n} créditos |
| `expx.cards.strip.rows.one` | 1 receipt | 1 recibo |

Reuse the existing `expx.review.lastUpdated` and `wb.refreshing`. No em-dashes
in any UI copy. "Zoho" appears in no new string.

## 9. Do not change

`RowView`, `RowStatusBadge` and the Status cell (item 76 owns them),
`CandidateRow`, `ManualMatchDialog`, `SuggestedReceiptCell`,
`PostingCategoryCell`, `SettleOutsideControl`, `CardChips`,
`CoverageAttention` (the component; only the callback `RunWorkbench` passes it
changes, section 3), `StatementSummary` itself, `DuplicatesPanel` behaviour
beyond the section 5 partition, the Downloads row and its buttons, every
mutation and every query invalidation except the ones sections 2 and 5 add
(the attach dialog's cache reset, the two settled-outside invalidations on
Matching), `MonthsHome` and its link rule (statement month to `/runs`, else
`/expenses`), `/`, `/expenses`, Settings, auth, the API base URL, the query
keys, every backend call. `CoveragePanel` and `StatementsPanel` stay in the
codebase.

## 10. Render defensively

Type-check every list element before rendering (`rows`, `unmatched_receipts`,
`statements`, `coverage`, `duplicate_groups`, `expenses`); an unexpected shape
degrades to plain text, never a blank page. Treat every summary count as
optional (`typeof n === "number"`): a missing count hides its card subline,
caption or segment rather than printing "undefined". Absent parallel fields
(`updated_at`, `settled_outside`, `duplicate`, `held_by`) mean "not set".

---

## Verify after publish

Re-read `GET /api/runs/{id}` and `GET /api/expense-batches/{id}` for the three
months minutes before driving and substitute the live numbers: counts move
with every re-match. Expected on the 2026-09-16 reads.

**Bundle** (`tools/lovable-bundle-audit.py`, every chunk crawled; the controls
`posting_category_proposed`, `wb.filter.card.empty`, `n_settled_outside`,
`period_suggestion`, `seen_undefined` must hit before any absence is believed):

- In the i18n chunk and in at least one non-i18n chunk: `month.tab.matching`,
  `month.tab.addStatement`. `MonthHeader` is imported by both month routes, so
  the build puts it in a SHARED chunk (today's pages share
  `chunk-ReceiptViewer-*`; the name can change), not in either route chunk.
  Absence from both route chunks is expected, not a failure.
- In the i18n chunk and `chunk-runs._runId-*`: `wb.view.receipts`,
  `wb.view.refund`, `wb.decided.switch`, `wb.decided.foldPosted.many`.
- In the i18n chunk and `chunk-expenses._batchId-*`: `expx.recon.credits.one`.
- Absent from `chunk-runs._runId-*`: `wb.backToDashboard`, `wb.bucket.posted`,
  `sum.matchRate`, `sum.unmatchedTx`, `sum.unmatchedRec`.
- Absent from `chunk-expenses._batchId-*`: `months.locked.body`,
  `months.locked.openWorkbench`. `expx.landing.title` goes from 2 hits to 1 in
  that chunk (the error-state back link stays) and survives in the `/expenses`
  list chunk.
- The entry bundle (`index-*.js`, where route titles live) no longer contains
  `Run review` followed by an em-dash.

**Browser drive**, 1440x900, named session, read-only (tabs, cards, folds,
switches, hovers; no Confirm, Reject, Settle, Resolve, Save or upload), EN then
PT:

1. `/runs/51a22ad72864` lands on `/expenses/51a22ad72864`, zero console errors.
   Same for June `a5f97a85b1d0`, May `86929f2a909a`, January `4ceaeb461386`.
2. September `/expenses/51a22ad72864`: strip "← Months · September 2026 ·
   Expenses · 35 · Add a statement" (the last opens the attach dialog; close it
   without uploading); no "Reconciliation started" box; toolbar with Add
   receipts, Add expense, Save corrections to memory; groups Needs a look 31,
   Assign a category 4; no literal `expx.review.badge.` text anywhere,
   including the tooltip on DB Fernverkehr AG 16.00 EUR (source `llm; review`:
   AI and review labels, amber).
3. July `/runs/50622baec444`: strip "Expenses · 51 · Matching · 112 charges"
   with Matching active; no tile bar; exactly one pill, "Blocked · 3 rows to
   decide"; "USD 1,054.48 still open"; "1 receipt from next door". Cards:
   Receipts without a charge 14 (9 open), Charges without a receipt 73 (24
   open), Needs review 7 (0 open), Credits on the statement 1 (0 open), Matched
   31 (3 open). View 1 opens by default: 9 open rows, fold "5 copies set aside".
   View 2: 24 open rows, fold "49 already posted in your workbook", bulk bar
   counts only open rows; card chips `3876 · 31`, `2838 · 18`, `3645 · 24`,
   `0340 · 0`. View 3: "Nothing open here", fold "7 already posted in your
   workbook". View 4: "Nothing open here", fold "1 already posted in your
   workbook" (Payment Thank You-Mobile -9,664.81 USD). View 5: 3 open rows
   (WEB*NETWORKSOLUTIONS 7.98, ELEVENLABS.IO 5.00, ANTHROPIC 50.54), fold "28
   already posted in your workbook", caption "1 receipt line without a
   category". Clear filters on view 3 stays on view 3. "Show decided rows" on:
   every fold opens; reload keeps both the view and the switch. Duplicates
   panel: 2 open charge groups (COMPUTER 15.96 x4, POSTO SANTOS 9.80 x2) and
   "6 decided · Show". At scrollY 3000 only the Menu bar and the strip are
   pinned. The first open row of view 1 sits above 900 px.
4. July `/expenses/50622baec444`: strip with Expenses active; line
   "Reconciliation: 31 matched · 7 need review · 73 charges without a receipt
   · 14 receipts without a charge · 1 credit"; no read-only box; groups 36 / 1
   / 14; hovering the category badge on Lovable Labs Incorporated 200.00 USD
   (source `override; llm`) shows "Edited by you · Categorized by AI" with no
   raw key; the tab "Matching · 112 charges" opens `/runs/50622baec444`.
5. August `/runs/074a7b8905d7`: cards 21 (10 open) / 100 (no subline, no fold)
   / 2 / 1 (0 open) / 8; pill "Blocked · 10 rows to decide"; "USD 10,950.12
   still open"; the attention banner for cards 1176 and 9693 still there;
   duplicates panel 1 open charge group (OPENAI 86.06 x2) and "11 decided".
   August `/expenses/074a7b8905d7`: line "Reconciliation: 8 matched · 2 need
   review · 100 charges without a receipt · 21 receipts without a charge · 1
   credit".
6. A legacy statement run `/runs/f639bef7813a` (listed on `/classic`): the
   strip shows the run's title with a single Matching tab and no Expenses tab,
   the charge table renders, and the only console noise is the expected 400 on
   `/api/expense-batches/f639bef7813a`.
7. PT pass on July: "Despesas · 51", "Conciliação · 112 lançamentos", cards
   "Recibos sem lançamento", "Lançamentos sem recibo", "Precisa revisão",
   "Créditos no extrato", "Conciliadas"; view 4 fold "1 já lançado na sua
   planilha"; "Mostrar linhas decididas"; "Última atualização" in the meta line.
8. Network during the drive: the only non-GET is `POST /api/login` (nothing at
   all if an existing token is reused).

Bundle signatures (decisive, for `tools/lovable-bundle-audit.py`):
`month.tab.matching` (shared chunk), `wb.decided.switch`,
`expx.recon.credits.one`.
