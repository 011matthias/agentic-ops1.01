# Lovable prompt - anyone can email in receipts

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Backend is live. Apply this only if the Settings screen actually shows an
"Accepted senders" / "Remetentes aceitos" field; if it was never built, there
is nothing to do here.

## Why

Receipts arrive from more places than Brisken mailboxes: a faculty member
mailing from a private address on the road, a hotel sending the invoice
directly, a supplier's billing robot. Those were all refused. The restriction
is gone as of 2026-08-23; the intake now takes mail from any sender.

## 1. Remove the "Accepted senders" editor

In the Settings screen's "Email intake" section, delete the senders tag
editor and stop putting a `senders` key in the `PUT /api/settings` body. The
backend ignores the key, so a stale editor would silently discard whatever
the operator types into it, which is worse than not having it.

Everything else in that section stays: the alias rows, and the read-only
line naming the intake address.

## 2. Say who may write in

Replace the read-only intake line with one that states the rule as it now is.

- **EN**: "Receipts can be emailed to any-name@expenses.brisken.com, from
  any address. Use dirk@, criss@ or matthias@ to book the expense to that
  person."
- **PT**: "Recibos podem ser enviados para
  qualquer-nome@expenses.brisken.com, de qualquer endereco. Use dirk@,
  criss@ ou matthias@ para atribuir a despesa a essa pessoa."

## 3. Do not change

No payload shapes changed. The intake log, the held-mail strip, the
submitted-by chip and the alias rows all behave exactly as before.
