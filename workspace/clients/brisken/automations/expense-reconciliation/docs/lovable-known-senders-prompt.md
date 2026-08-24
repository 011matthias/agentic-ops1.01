# Lovable prompt: the people we recognise

Paste the block below into Lovable for the `brisken-expense-review` SPA
(production: `brisken-reconcile-dash.lovable.app`). It calls the existing
FastAPI backend at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT
add Supabase or any database.** Auth is the existing
`Authorization: Bearer <token>`.

Backend is already deployed. This adds ONE settings field. Nothing on the
inbound page changes shape, and the page works untouched if you skip it.

---

## Why this exists

Anyone may email receipts in; that stays. The narrower question the tool
could not answer is whether a submitter is one of Brisken's own people.

Dirk mails receipts from a private iCloud address as well as his work one.
Until now the backend refused to reply to any address outside
`@brisken.com`, on purpose: replying to strangers as Brisken is
backscatter. The side effect was that his private sends got no
confirmation and no bounce either, so a receipt that arrived and a receipt
that was lost looked exactly the same from his chair.

The fix is a short, operator-curated list of outside addresses that count
as ours.

## 0. First, delete the "Accepted senders" editor (it is dead)

The Settings > Email intake section still shows an **"Accepted senders --
Full addresses or @domain entries"** tag editor. That is the retired
`intake.senders` allowlist. Submission opened to any sender on 2026-08-23
and the backend now DROPS that key on save, so whatever an operator types
there is discarded without a word. It sits exactly where someone would go
to authorise a sender, so it produces a false result and reads as a broken
tool.

Delete the editor and stop sending a `senders` key in the settings PUT. The
field in section 1 replaces it with one that works.

While you are in that section, two help lines predate the month pool and are
now wrong. Receipts land in the month PRINTED on them, or wait for it; they
do not land in "the open month".

- The intake address line becomes, **EN**: "Receipts can be emailed to
  any-name@expenses.brisken.com, from any address. Use dirk@, criss@ or
  matthias@ to book the expense to that person." / **PT**: "Recibos podem ser
  enviados para qualquer-nome@expenses.brisken.com, de qualquer endereco. Use
  dirk@, criss@ ou matthias@ para atribuir a despesa a essa pessoa."
- The section's own description and the auto-confirmation help text must stop
  saying "the open month". **EN**: "People who can email receipts in. A
  receipt files under the month printed on it, and waits if that month does
  not exist yet." / **PT**: "Pessoas que podem enviar recibos por email. Um
  recibo entra no mes impresso nele e aguarda se esse mes ainda nao existe."

## 1. Settings: "People we recognise"

In the Settings screen's "Email intake" section, below the alias rows, add
a tag editor for outside addresses.

- Reads from `GET /api/settings` -> `intake.known_senders` (a list of
  strings; treat a missing key as an empty list).
- Writes with the existing settings PUT, as
  `{"intake": {"known_senders": [...]}}`.
- Send the whole list on every save; it replaces, it does not append.

Validation, so the operator sees the error before the API does:

- one plain address per tag, no display name and no angle brackets
- exactly one `@`, and a dot in the domain
- no commas, semicolons, spaces or line breaks inside a tag
- at most 25 addresses

The API refuses the same cases with a 400 and a message naming the field;
surface that message rather than a generic failure.

## 2. The help line under it

Say what listing an address actually does, because it does two things.

- **EN**: "Addresses here belong to people we know. They get the
  confirmation email when they send a receipt in, and a receipt they
  forward in the body of an email is read automatically instead of
  waiting for someone to open it. Everyone else can still email receipts;
  they just do not get a reply."
- **PT**: "Enderecos aqui pertencem a pessoas que conhecemos. Recebem o
  email de confirmacao ao enviar um recibo, e um recibo encaminhado no
  corpo do email e lido automaticamente em vez de esperar que alguem o
  abra. Os demais continuam podendo enviar recibos por email; apenas nao
  recebem resposta."

Suggest `dirk_.neumann@icloud.com` as placeholder text, since that is the
address the field was built for.

## 3. What changed on the inbound page (context, no work)

Body-only mail from a recognised sender no longer lands in
`held_body_only`. It renders itself on arrival and goes straight to
`ingested` or `pooled`, so the Held strip now holds only mail from
senders we do not recognise, plus mail that genuinely failed. Any help
text that tells the operator to click "Read email body" on every
forwarded receipt is out of date.

Addresses inside `@brisken.com` are recognised automatically and are not
listed in this field.

## Contract rules for this round

- `intake.known_senders` is a NEW settings key. Nothing existing changed
  type or meaning.
- **The `intake` object is stored exactly as you send it.** The merge is
  shallow at the top level, so `PUT {"intake": {"known_senders": [...]}}`
  replaces the whole intake block and drops the aliases, the caps and the
  alert recipients with it. Read the current `intake` from
  `GET /api/settings`, change the one key, and send the whole object back.
  This is true of every field in that section, not only the new one.
- Render defensively: a missing or non-list `known_senders` reads as an
  empty list, never an error.
