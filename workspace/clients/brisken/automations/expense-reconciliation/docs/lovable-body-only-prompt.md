# Lovable prompt — held mail actions: view body, render as PDF, dismiss

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`.

Context: mail that arrives with no usable attachment (an Uber forward, a
credit-reload notice) is held as `held_body_only` and until now had no
handling path. Three per-mail actions fix that on the Email-intake page.
This amends the earlier "never render the archive" rule: the body is now
viewable, but ONLY through the sanitized endpoint below — still never the
raw archive.

---

## 1. Row actions on held mail

Each row in `GET /api/inbound/log` has an `archive` id. Rows whose
`status` starts with `held_` get an actions menu with up to three items:

- **View body** (all held rows): `GET /api/inbound/{archive}/body` →
  `{ "from", "subject", "at", "status", "text" }`. Open a modal showing
  from/subject/date and `text` rendered as PLAIN TEXT (pre-wrap, never
  HTML). EN "Email body" / PT "Corpo do e-mail". Empty `text`: EN "No
  readable body" / PT "Sem corpo legível".
- **Add to month as PDF** (only when `status` is `held_body_only`, or the
  row has failed after a previous render — the backend decides; just show
  the action for `held_body_only`, `held_failed`, `held_no_valid_files`
  and let a 409 explain): `POST /api/inbound/{archive}/render-ingest`.
  This renders the body to a PDF and runs the normal pipeline (the same
  quarantine and reading every receipt gets). It takes a few seconds —
  disable the button and show a spinner while pending.
  - `200` `{ "status": "ingested", "batch_id", "documents": [...] }`:
    toast EN "Added to the open month" / PT "Adicionado ao mês aberto",
    refresh the log (the row now shows its month).
  - `200` with `"status": "held_failed"`: toast EN "Reading failed — you
    can retry" / PT "Falha na leitura — tente novamente".
  - `409` `{"error": ...}`: show the backend message (no open month, not
    a body-only mail, or already being rendered).
- **Dismiss** (all held rows): `POST /api/inbound/{archive}/dismiss`
  after a small confirm (EN "Dismiss this email? It stays archived but
  will no longer be listed as waiting." / PT "Dispensar este e-mail? Ele
  permanece arquivado, mas não ficará mais como pendente."). `200` →
  refresh; the held counter drops. `409` → show the backend message.

## 2. Two new statuses in the log

- `rendering`: a render is in flight. Show EN "Processing…" /
  PT "Processando…" with a spinner glyph; no actions on the row.
- `dismissed`: terminal. Muted row, EN "Dismissed" / PT "Dispensado";
  only "View body" stays available.

## 3. No other changes

Do not add a day-budget display, do not touch the expense grid: a
rendered mail's expense row appears there through the existing flow with
its "From:" submitted-by chip, source file `rendered-body.pdf`.
