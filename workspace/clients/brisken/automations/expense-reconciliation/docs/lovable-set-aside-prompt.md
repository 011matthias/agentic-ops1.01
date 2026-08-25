# Lovable prompt — set-aside strip on the expense batch grid

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`. Change only the expense-batch grid screen; leave everything
else (reconciliation workbench, publish flow, upload) untouched.

The backend for this is already deployed, so the API fields named below are
live now.

---

## The set-aside strip

When the tool decides an uploaded file is not a receipt (a bank-statement
page, an expense-report summary sheet), it sets the file aside instead of
creating an expense from it. Today that only shows up in the technical issues
list. Give it a visible home.

**Where the data comes from.** `GET /api/expense-batches/{id}` now returns:

- `set_aside`: an array of `{ file, display, reason, reason_label, restored,
  at }`. `display` is the reviewer-facing filename; `file` is the exact id to
  send back on restore; `reason` is a machine code (`statement` |
  `report_summary` | `other`); `restored` is true once the reviewer has
  restored that file.
- `summary.n_set_aside`: how many files are currently set aside (restored
  ones excluded).

**What to render.** On the expense-batch grid, when `set_aside` is non-empty,
show a strip between the summary header and the expenses table:

- Header: **EN** "Set aside (not counted as expenses)" / **PT** "Separados
  (não contam como despesas)", with the count from `summary.n_set_aside`.
- One row per entry: the `display` name, the reason worded from the `reason`
  code (see table below — do not show the raw code or the English
  `reason_label` to a PT user), and the restore button.
- A restored entry stays in the strip, struck through or muted, labelled
  **EN** "Restored — now an expense" / **PT** "Restaurado — agora é uma
  despesa", with no button.
- When `set_aside` is empty, render nothing at all (no empty-state box).

Reason wording, keyed on the `reason` code:

| code | EN | PT |
|---|---|---|
| `statement` | Looks like a bank or card statement page | Parece uma página de extrato do banco ou do cartão |
| `report_summary` | Looks like an expense-report summary page | Parece uma página de resumo de relatório de despesas |
| `other` | Does not look like an expense document | Não parece um documento de despesa |

**The restore button.** Label: **EN** "This is a receipt — restore" / **PT**
"Isto é um recibo — restaurar".

- On click: `POST /api/expense-batches/{id}/set-aside/restore` with JSON body
  `{ "file": entry.file }`.
- The success response carries `{ ok, file, n_expenses, n_set_aside, batch }`
  where `batch` is the full refreshed batch view — replace the screen's state
  with it directly, no second GET needed. The restored file appears as a
  normal expense row and its strip entry flips to restored.
- On error the response is `{ "error": "..." }` with status 400 — show the
  message as a toast and leave the strip unchanged.
- Disable the button while the request is in flight (the backend refuses a
  double restore, but the button should not invite one).

**Do not** add a confirm dialog (restore is reversible: the reviewer can
delete the expense row like any other), and do not build any client-side
logic about WHY a file was set aside — the backend decides everything; the
SPA only renders.
