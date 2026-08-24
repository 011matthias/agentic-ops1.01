# Lovable prompt: the Months list (the screen that is missing)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Backend is live and has always been. **Apply this before anything else.**

---

## The problem, measured on the published app

The "Months" nav item goes to `/months`. That route renders the "New expense
batch" upload form and nothing else: 518 characters of body text, **zero
tables, zero rows**, and no batch label anywhere in the HTML. `/`,
`/expenses` and `/expenses/new` all render the same thing.

The page DOES call `GET /api/expense-batches`. It answers `200` with six
batches (April 2026, January 2026, January, May 2026, and two others). The
response is fetched and then discarded.

So there is no way to open an existing month from the UI. The only paths that
work today are the `/expenses/{id}` links that happen to sit in the Email
intake page's Month column, or typing the URL by hand. A reviewer who opens
the app and wants last month's receipts cannot get to them.

Everything else on the batch page works: `/expenses/ae61e122a505` renders 40
expenses, the card-review strip, the set-aside strip and both download
buttons. It is only the way IN that is missing.

## 1. The list

On `/months` (and on `/` if that is the landing route), render the batches
above or beside the create form. Keep the create form; it is not the problem.

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
                 "llm_cost_usd": "0.21506055", "upload_issues": [] } } ] }
```

One row per batch, newest `created_at` first. Columns:

| Column | Source | Notes |
|---|---|---|
| Month | `label` | the link target, see below |
| Receipts | `summary.n_expenses` | |
| Needs category | `summary.n_uncategorized` | muted when 0, amber when > 0 |
| Set aside | `summary.n_set_aside` | omit the cell when 0 |
| Statement | `has_statement` | badge: EN "Reconciled" / PT "Reconciliado" when true, nothing when false |
| Created | `created_at` | short date |

**Where a row links.** `has_statement: false` goes to
`/expenses/{batch_id}`. `has_statement: true` goes to `/runs/{run_id}` (the
batch has graduated to the statement workbench, and that one route serves
both payloads). Getting this wrong is not fatal (both ids are the same
string) but the reviewer lands on the wrong screen.

A batch whose `summary.mode` is not `expense_generation` is not an expense
month; if any appear, leave them out rather than linking them somewhere that
will not render.

Empty list: show the create form alone with a quiet line, EN "No months yet."
/ PT "Nenhum mes ainda." Do not show an empty table.

## 2. Rename, from the row

`POST /api/runs/{id}/rename` with `{"label": "July 2026"}`.

This matters more than a cosmetic rename: the label is what decides which
emailed receipts join the month. The response carries `month` (a `"YYYY-MM"`
string, or `null` when the label names no month). When it comes back
non-null, mail waiting for that month is being added right now on a
background thread; show a toast, EN "July 2026. Any waiting receipts for this
month are being added." / PT "Julho 2026. Recibos aguardando este mes estao
sendo adicionados.", then refresh the list and the Email intake page a couple
of seconds later.

Accepted month forms: "April 2026", "abril 2026", "2026 Apr", "2026-04". A
label carrying a full date names no month on purpose, which is why the
default label never claims mail.

## 3. Delete month, from the row

This was specified in `lovable-intake-quickwins-prompt.md` section 3 and has
never had a screen to live on. Put it in a per-row overflow menu, never a
primary button.

`POST /api/runs/{id}/delete` with `{"confirm": "April 2026"}` (the exact
label, trimmed, case-sensitive; the batch id is also accepted).

- Confirm dialog: EN "Type the month label to delete" / PT "Digite o nome do
  mes para excluir". Display the label as text the user must retype. Do NOT
  prefill the input or add a copy button; retyping IS the gate.
- Warn before the input: EN "Deletes the month, its expense rows and edits.
  Received emails are kept and go back to waiting for this month." /
  PT "Exclui o mes, suas despesas e edicoes. Os e-mails recebidos sao
  mantidos e voltam a aguardar este mes." And: EN "Learned memory is kept." /
  PT "A memoria aprendida e mantida."
- `400` (no phrase) and `409` (`confirm label mismatch`): keep the dialog
  open, show the message, EN "Label does not match" / PT "O nome nao
  confere".
- `200` carries `{ "deleted": true, "pooled_back": 4, "inbound_marked": 0,
  "next_open_batch": "February 2026", "learned_memory": "kept" }`. Remove the
  row. When `pooled_back > 0`, say so: EN "Month deleted. 4 emailed receipts
  are waiting again for this month; re-create it and they are added
  automatically." / PT twin. `inbound_marked` is a different, older number;
  do not present the two as the same thing.

## 4. The month advisory on create

`POST /api/expense-batches` returns `month` (a `"YYYY-MM"` string or `null`)
and, when `month` is null, an `advisory` string.

`null` means the new batch's label names no month, so emailed receipts can
never join it. The default label is a full date, so this fires on every batch
created without an explicit label. Show the returned `advisory` as an
informational banner on the new batch with a **Rename** action opening the
dialog from section 2. Do not block anything; the batch is perfectly usable
for uploaded receipts. The advisory is only about mail.

## 5. Do not

- Do not remove or move the create form. It works.
- Do not compute totals or counts client-side; render `summary` as sent.
- Do not add a bulk delete.
- No em-dashes in UI copy.

## Verify after publish

`/months` lists six batches; clicking "April 2026" opens the batch page that
already renders today; "January 2026" (which has a statement) opens the
workbench; the overflow menu offers Delete month behind the retyped-label
gate.
