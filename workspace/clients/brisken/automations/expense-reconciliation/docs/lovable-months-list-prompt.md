# Lovable prompt 1 of 3: the Months list (the screen that is missing)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

**Paste this one FIRST.** It is prompt 1 of 3; the other two are
`lovable-known-senders-prompt.md` (Settings) and
`lovable-inbound-status-refusals-prompt.md` (Email intake page). They touch
different screens and do not depend on each other.

---

## What your app already has (measured on the published build, 2026-08-25)

Read this before changing anything. The app is further along than a
first-time reader would assume, and the point of this section is that you do
NOT rebuild any of it.

**Working and untouched by this prompt:**

- The batch page at `/expenses/{id}` is complete. It renders the expense
  grid, the stat row (EXPENSES / CATEGORIZED / NEEDS CATEGORY / READY /
  TOTALS / MISSING ENTITY / MISSING RECEIPT IMAGE), the card-review strip
  with "Assign to card...", the set-aside strip with "This is a receipt —
  restore", per-row entity and category editing, and the action row: Add
  receipts, Add expense, Save corrections to memory, Attach bank statement &
  reconcile, Download expense report (PDF), Download CSV (data export). Its
  overflow menu holds "Refresh master data".
- The statement workbench at `/runs/{id}` works, with Download
  reconciliation (PDF).
- The Email intake page at `/inbound` works, and its Month column already
  links to `/expenses/{id}`. That is currently the only way a human reaches
  a month.
- Settings, Memory, Compare and the double-click feedback widget all work.

**The gap.** `/months` renders the "New expense batch" upload form and
nothing else: 518 characters of body text, **zero tables, zero rows**, and no
batch label anywhere in the HTML. `/`, `/expenses` and `/expenses/new` render
the same page. That page DOES call `GET /api/expense-batches` and DOES get a
`200` with six batches. The response is fetched and discarded.

So there is no list. A reviewer who opens the app cannot get to last month's
receipts. Everything downstream works; only the way IN is missing.

## 1. Render the list

On `/months`, render the batches. Keep the create form exactly as it is,
above or below the list as you prefer; the form is not the problem.

`GET /api/expense-batches` returns:

```json
{ "batches": [
  { "batch_id": "ae61e122a505",
    "run_id": "ae61e122a505",
    "label": "April 2026",
    "created_at": "2026-08-22T12:07:03+00:00",
    "has_statement": false,
    "summary": { "n_expenses": 40, "n_receipts": 40, "n_categorized": 37,
                 "n_uncategorized": 3, "n_set_aside": 1, "n_parse_notes": 1,
                 "llm_cost_usd": "0.21506055", "upload_issues": [],
                 "mode": "expense_generation" } } ] }
```

One row per batch, newest `created_at` first:

| Column | Source | Notes |
| --- | --- | --- |
| Month | `label` | the link, see below |
| Receipts | `summary.n_expenses` | |
| Needs category | `summary.n_uncategorized` | muted at 0, amber above 0 |
| Set aside | `summary.n_set_aside` | omit the cell at 0 |
| Statement | `has_statement` | badge EN "Reconciled" / PT "Reconciliado" when true; nothing when false |
| Created | `created_at` | short date |

**Where a row links.** `has_statement: false` goes to
`/expenses/{batch_id}`. `has_statement: true` goes to `/runs/{run_id}` (the
batch has graduated to the workbench, and that one route serves both
payloads). Both ids are the same string, so a mistake here is not fatal, but
it lands the reviewer on the wrong screen.

A batch whose `summary.mode` is not `expense_generation` is not an expense
month. Leave it out rather than linking somewhere that will not render.

Empty list: show the create form alone with a quiet line, EN "No months
yet." / PT "Nenhum mes ainda." No empty table.

## 2. Rename, from the row

**There is no rename dialog anywhere in the app today** (the batch page has
no Rename control; its only overflow item is "Refresh master data"). Build
one here. If you later add rename elsewhere, reuse this dialog.

`POST /api/runs/{id}/rename` with `{"label": "July 2026"}`.

This is not cosmetic: the label decides which emailed receipts join the
month. Six real receipts are waiting right now for months that do not exist.

The response carries `month` (a `"YYYY-MM"` string, or `null` when the label
names no month). Non-null means mail waiting for that month is being added
right now on a background thread. Toast: EN "July 2026. Any waiting receipts
for this month are being added." / PT "Julho 2026. Recibos aguardando este
mes estao sendo adicionados." Then refresh the list, and the Email intake
page if it is open, a couple of seconds later.

Accepted month forms: "April 2026", "abril 2026", "2026 Apr", "2026-04". A
label carrying a full date names no month on purpose, which is why the
default label never claims mail.

## 3. Delete month, from the row

Specified long ago in `lovable-intake-quickwins-prompt.md` section 3 and
never built, because there was no list to put it on. It goes in a per-row
overflow menu, never a primary button.

`POST /api/runs/{id}/delete` with `{"confirm": "April 2026"}` (the exact
label, trimmed, case-sensitive; the batch id is also accepted).

- Dialog: EN "Type the month label to delete" / PT "Digite o nome do mes
  para excluir". Show the label as text the user must retype. Do NOT prefill
  the input and do NOT add a copy button; retyping IS the gate.
- Warn before the input: EN "Deletes the month, its expense rows and edits.
  Received emails are kept and go back to waiting for this month." / PT
  "Exclui o mes, suas despesas e edicoes. Os e-mails recebidos sao mantidos e
  voltam a aguardar este mes." And: EN "Learned memory is kept." / PT "A
  memoria aprendida e mantida."
- `400` (no phrase) and `409` (`confirm label mismatch`): keep the dialog
  open, show EN "Label does not match" / PT "O nome nao confere".
- `200` carries `{ "deleted": true, "pooled_back": 4, "inbound_marked": 0,
  "next_open_batch": "February 2026", "learned_memory": "kept" }`. Remove the
  row. When `pooled_back > 0`: EN "Month deleted. 4 emailed receipts are
  waiting again for this month; re-create it and they are added
  automatically." / PT twin. `inbound_marked` is a different, older number;
  never present the two as the same thing.

## 4. The month advisory on create

`POST /api/expense-batches` returns `month` (a `"YYYY-MM"` string or `null`)
and, when `month` is null, an `advisory` string.

`null` means the new batch's label names no month, so emailed receipts can
never join it. The default label is a full date, so this fires on every batch
created without an explicit label.

Show the returned `advisory` as an informational banner on the new batch,
with a Rename action opening the dialog from section 2. Do not block
anything; the batch is perfectly usable for uploaded receipts. The advisory
is only about mail.

**If a create-time advisory banner already appears in your app, leave it and
just wire its Rename action to the section 2 dialog.**

## 5. Do not

- Do not remove, move or restyle the create form.
- Do not touch the batch page, the workbench, the Email intake page or
  Settings. This prompt adds one screen.
- Do not compute totals or counts client-side; render `summary` as sent.
- Do not add a bulk delete.
- No em-dashes in UI copy.

## Verify after publish

`/months` lists six batches. Clicking "April 2026" opens the batch page that
already renders today. "January 2026" (which has a statement) opens the
workbench. The per-row overflow menu offers Delete month behind the
retyped-label gate, and Rename opens a dialog.
