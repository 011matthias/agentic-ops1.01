# Lovable prompt — intake files + month column + delete month

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`.

Context: three quick wins from the 2026-08-21 feedback walk. The Email-intake
page gains a Files column and an honest Month column, and the Months page
gains a guarded "Delete month" action. All backend fields are live.

---

## 1. Email intake: Files column

`GET /api/inbound/log` rows (plain mode, no `detail` needed) now carry:

```json
"files": ["uber trip.jpg", "hotel invoice.pdf"]
```

- Render the delivered filenames in a "Files" column (EN "Files" / PT
  "Arquivos"), comma-joined, truncated with a tooltip for long lists.
- The names are what the sender attached, in original spelling. Older mail
  may show sanitized spellings (underscores for special characters); that is
  expected, render as-is.
- `files` absent or `[]` with `n_files: 0`: render a muted dash (body-only
  mail delivered no files).
- Keep the existing `skipped` rendering (rejected attachments) as it is;
  `files` and `skipped` are different lists.

## 2. Email intake: Month column tells the truth

Every log row that routed to a month now carries `batch_label` in PLAIN
mode too (it was detail-only and often missing). Two new signals:

- `batch_label` present: render it as the Month cell (this replaces
  whatever produced "no date").
- `batch_deleted: true`: the month this mail landed in was deleted later.
  Render EN "Month deleted" / PT "Mês excluído" as a muted badge in the
  Month cell. In the `?detail=1` expansion these rows now return
  `"expenses": []` — do NOT interpret that as "operator removed each
  expense"; branch on `batch_deleted` first and show the badge instead of
  the expense list.
- Neither field, status starts with `held_`: render EN "Held" / PT "Retido"
  in the Month cell (the mail never reached a month). Never render "no
  date".

## 3. Months page: Delete month (guarded)

New action on each month row on the Months page: a "Delete month" item
(overflow menu, not a primary button).

The endpoint is `POST /api/runs/{id}/delete` and it now REQUIRES a confirm
phrase:

```json
{ "confirm": "January 2026" }
```

- Open a confirm dialog: EN "Type the month label to delete" / PT "Digite o
  nome do mês para excluir". Display the label as text the user must
  retype; do NOT prefill the input or add a copy button (retyping IS the
  gate). Comparison is exact after trimming (case matters). The batch id is
  also accepted as the phrase.
- Warn in the dialog body, before the input (EN / PT):
  - "Deletes the month, its expense rows and edits. Received emails are
    kept for custody and will show 'Month deleted'." / "Exclui o mês, suas
    despesas e edições. E-mails recebidos são preservados e mostrarão 'Mês
    excluído'."
  - "Learned memory is kept." / "A memória aprendida é mantida."
- Responses:
  - `400` `{"error": ...}`: no phrase sent — keep the dialog open, show the
    message.
  - `409` `{"error": "confirm label mismatch"}`: wrong phrase — keep the
    dialog open, EN "Label does not match" / PT "O nome não confere".
  - `200`:
    ```json
    { "ok": true, "deleted": true, "inbound_marked": 2,
      "next_open_batch": "February 2026", "learned_memory": "kept" }
    ```
    Close the dialog, remove the row, and show ONE toast:
    - `next_open_batch` non-null: EN "Month deleted. Incoming email now
      goes to {label}." / PT "Mês excluído. Novos e-mails vão para
      {label}."
    - `next_open_batch` null: EN "Month deleted. Incoming email will be
      held until a month is open." / PT "Mês excluído. Novos e-mails
      ficarão retidos até um mês estar aberto."

## 4. Job polling edge (no visual change)

After a month is deleted, `GET /jobs/{id}` for jobs of that month answers
`404`. Treat a 404 on a job poll as terminal (stop polling, refresh the
months list); do not retry it in a loop.

---

Out of scope for this round (do not build): body-only mail actions
(view/render/dismiss — next round), memory editing, receipt-column changes.
