# Lovable prompt: the journal CSV leaves the app (item 23 round 4, consumer half)

Backlog item 23, round 4. The Zoho-shaped journal export is being deleted: the
owner ruled on 2026-09-15 to "rename or delete whatever is necessary to make the
app better", and the journal emits 3 of July's 31 reconciled charges (the other
28 are already posted) with every account line a placeholder. A DELETE goes consumer first: the SPA stops calling
`/runs/{id}/zoho.csv`, the owner publishes, the bundle audit finds the route
string in zero chunks, and only then does the backend PR delete the route.

Three callers, read on SPA main `c9f30bf8b5` (2026-09-16) and in the published
bundle crawled the same day:

- `src/components/SummaryBar.tsx`, the Downloads row: `label={t("sum.dl.zoho")}`,
  `path={\`/runs/${runId}/zoho.csv\`}` (the "Journal CSV (data export)" button on
  every month's workbench). Bundle: `chunk-runs._runId-*`.
- `src/components/OperatorDashboard.tsx`, the Published runs table on `/classic`:
  a per-row button `t("dash.pub.download")` that downloads
  `/runs/${run.run_id}/zoho.csv` as `zoho-journal-{id}.csv`. Bundle:
  `chunk-classic-*`.
- `src/components/SettingsScreen.tsx`, the first card: the switch
  `export_approved_only` with `set.export.label` / `set.export.help`, whose help
  text names "the Zoho journal". The setting has no other consumer, so after the
  route dies it becomes a control that changes nothing.

Independent of `lovable-month-views-prompt.md` (item 79): paste in either order.
If both are pasted together, this one's `SummaryBar` edit is a single button and
does not touch the tile removal or the stickiness change there.

Paste everything between the two rules into the `brisken-expense-review`
Lovable project.

---

Paste into the `brisken-expense-review` Lovable project (production:
`expenses.brisken.com`). It calls the existing FastAPI backend as a JSON API at
`api.expenses.brisken.com`. **Do NOT add Supabase or any database.** Auth stays
the existing `Authorization: Bearer <token>`. No backend change in this prompt;
the backend route is deleted AFTER this is published.

## Why

The journal CSV (`/runs/{id}/zoho.csv`) is retired. Nothing imports it any more,
and the month's deliverables are the reconciliation PDF, the report workbook,
the reconciled CSV and the annotated statement. The app must stop offering the
file, and stop offering the one setting that only affected it, before the
backend removes the route.

## 1. Workbench Downloads row (`src/components/SummaryBar.tsx`)

Remove the download button whose label is `t("sum.dl.zoho")` and whose path is
`/runs/${runId}/zoho.csv`. Keep the other three exactly as they are: Report
(`sum.dl.report`, `report.xlsx`), Reconciled CSV (`sum.dl.reconciled`,
`reconciled.csv`) and Statement (`sum.dl.statement`,
`statement-categorized.xlsx`, only when `writeback_available`).

Remove the i18n key `sum.dl.zoho` in EN and PT.

## 2. Classic dashboard (`src/components/OperatorDashboard.tsx`)

In the "Published runs" table:

- Remove the Export column: the header cell `t("dash.pub.col.export")` and the
  per-row cell holding the `downloadFile(\`/runs/${run.run_id}/zoho.csv\`, ...)`
  button.
- Make each row's label a link to `/runs/$runId` (the month's Matching view), so
  the table still leads somewhere.
- Set every `colSpan={3}` in that table to `colSpan={2}`.
- Replace the empty-state body `dash.pub.empty.body` and the page subtitle
  `dash.subtitle`, which both promise a journal:

| Key | EN | PT |
|---|---|---|
| `dash.subtitle` | Run reconciliations and review published months. | Execute conciliações e revise os meses publicados. |
| `dash.pub.empty.body` | Open a run, resolve every row, then hit Publish. It will show up here. | Abra uma execução, resolva cada linha e clique em Publicar. Ela aparecerá aqui. |

Remove the keys `dash.pub.col.export` and `dash.pub.download` in EN and PT.

## 3. Settings (`src/components/SettingsScreen.tsx`)

In the first `<section>` card, remove the `Label` for `export_approved_only`,
its help paragraph and the `Switch` whose `onCheckedChange` saves
`{ export_approved_only: v }`. Keep the page's loading state: where that section
was, render `{isLoading ? (<section className="rounded-lg border bg-card
p-6"><Skeleton className="h-12 w-full" /></section>) : null}`, because it is the
only loading indicator on `/settings` (every other card is hidden until the
data arrives). Nothing else in Settings changes, and no other save payload may
start sending or dropping `export_approved_only`.

Remove the i18n keys `set.export.label` and `set.export.help` in EN and PT.
Leave `export_approved_only` on the `Settings` type in `src/lib/api.ts` as an
optional field (`export_approved_only?: boolean`) so an older payload still
type-checks; nothing reads it.

## 4. Guide copy

`guide.finish.p2` lists "the journal (.csv)" among the downloads. Replace it:

| Key | EN | PT |
|---|---|---|
| `guide.finish.p2` | Then download: the reconciliation (PDF), Reconciled data (.csv), Report (.xlsx), and, for an Excel statement, your sheet with a posting-account column. | Depois baixe: a conciliação (PDF), os dados conciliados (.csv), o relatório (.xlsx) e, para um extrato em Excel, a sua planilha com a coluna de conta contábil. |

## 5. Do not change

Every other download, the reconciliation PDF button, Confirm all matched,
Commit learnings, Publish / Unpublish, the Months list, both month pages beyond
section 1, every other Settings card and its save payload, auth, the API base
URL, the query keys, every other backend call. No em-dashes in any UI copy.

---

## Verify after publish

**Bundle** (`tools/lovable-bundle-audit.py`, every chunk crawled; controls
`posting_category_proposed`, `n_settled_outside`, `period_suggestion`,
`seen_undefined` must hit first):

- `zoho.csv`: 0 hits in EVERY chunk. On 2026-09-16 it is in exactly two,
  `chunk-classic-*` and `chunk-runs._runId-*`. This is the gate for the backend
  PR.
- `export_approved_only`: 0 hits in the settings chunk (1 on 2026-09-16).
- `sum.dl.zoho`, `dash.pub.download`, `set.export.help`: 0 hits in the i18n
  chunk.

**Browser drive**, read-only:

1. July `/runs/50622baec444`: the Downloads row shows Report, Reconciled CSV,
   Statement and no journal button.
2. `/classic`: no Export column; the Published runs table renders (it is empty
   today: `published_runs` is `[]` on `/api/operator/state`).
3. `/settings`: no "Export approved rows only" card, a skeleton while loading,
   and the remaining cards load. Do NOT click any Save or toggle anything on
   this page: every Save is a `PUT /api/settings` that replaces a whole stored
   map in Brisken's live settings. That no save payload carries
   `export_approved_only` is proven by the bundle check above (0 hits in the
   settings chunk), not in the browser.
4. Network during the drive: no request to any `/runs/*/zoho.csv`, and the only
   non-GET is `POST /api/login` (nothing at all if an existing token is
   reused).

Then, and only then: the round-4 backend PR (delete the route at
`app.py` `@app.get("/runs/{run_id}/zoho.csv")`, the journal module, and
`export_approved_only` with its store default), per backlog item 23.

Bundle signatures (decisive, absence): `zoho.csv`, `export_approved_only`.
