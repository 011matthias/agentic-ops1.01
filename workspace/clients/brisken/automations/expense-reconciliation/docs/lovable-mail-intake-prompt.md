# Lovable prompt — mail intake: submitted-by column + inbound mail strip

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>` from
`POST /api/login`.

Context: the tool now has its own mailbox. Receipts mailed to
`...@expenses.brisken.com` land in the open month batch automatically, with
WHO submitted them attached. Three small UI pieces make that visible.

---

## 1. "Submitted by" on expense rows

Each expense row in `GET /api/expense-batches/{id}` may now carry:

```json
"submitted_by": { "person": "Dirk Neumann", "source": "alias",
                  "address": "dirk.neumann@brisken.com",
                  "received_at": "2026-08-20T09:15:02+00:00" }
```

- `null` for receipts uploaded in the app (most rows today) — render nothing.
- When present, show a small muted chip on the row: the `person` value, with
  a tooltip showing "Emailed by {address} on {received_at date}". EN prefix
  "From:" / PT "De:".
- `source` is `alias` (mailed to a personal intake address) or `sender`
  (attributed from the sending mailbox). No visual difference needed; keep
  both in the tooltip ("via personal address" / "via sender").
- Do not make it editable in this round.

## 2. Inbound mail strip on the batch page

`GET /api/inbound/log?limit=50` returns:

```json
{ "entries": [ { "at": "...", "from": "...", "person": "...", "subject": "...",
                 "n_files": 2, "status": "ingested", "batch_id": "..." } ],
  "n_held": 1 }
```

Statuses: `ingested` (receipts landed), `replayed` (landed on a later
drain), `received` (still processing), and the held family
(`held_no_batch`, `held_failed`, `held_body_only`, `held_no_valid_files`).

- On the expense-batch page, when `n_held > 0`, show a compact amber strip
  (same visual family as the set-aside strip): **EN** "N emails are waiting"
  / **PT** "N e-mails aguardando", with an expandable list showing from,
  subject, and a short reason per held status:
  - `held_no_batch`: "arrived before this month was opened" / PT "chegou
    antes do mês ser aberto"
  - `held_failed`: "processing failed, can be retried" / PT "o processamento
    falhou, pode tentar de novo"
  - `held_body_only`: "the receipt is in the email text, not attached" / PT
    "o recibo está no corpo do e-mail, não anexado"
  - `held_no_valid_files`: "no readable receipt file" / PT "nenhum arquivo
    de recibo legível"
- One button on the strip: **EN** "Retry held emails" / **PT** "Reprocessar
  e-mails" → `POST /api/inbound/replay-held` (no body). Response
  `{replayed, still_held, failed}`; show a toast "N emails added" and
  refresh the batch. Note in the UI that body-only emails cannot be retried
  yet.
- When `n_held == 0`, render nothing (no empty strip).

## 3. Intake addresses in the Merchants/Settings area

`GET/PUT /api/settings` now accepts an `intake` key:

```json
"intake": {
  "aliases": { "dirk": "Dirk Neumann", "criss": "Cristiane Cavalcanti" }
}
```

- In Settings, add a small "Email intake" section listing the aliases as
  rows (address shown fully: `dirk@expenses.brisken.com` → "Dirk Neumann")
  with add/remove. Saving PUTs the whole `intake` object back.
- SUPERSEDED 2026-08-23: this prompt originally specified an "Accepted
  senders" tag editor. The sender allowlist no longer exists (anyone may
  submit); the backend ignores a `senders` key. Do not build that editor.
  If it was already built, remove it per
  `docs/lovable-open-intake-prompt.md`.
- Show the intake domain read-only: "Receipts can be emailed to
  any-name@expenses.brisken.com" / PT "Recibos podem ser enviados para
  qualquer-nome@expenses.brisken.com".

## Out of scope

- No mail composing, no reply UI — the tool only receives.
- Do not render the raw `/data/inbound` archive anywhere.
