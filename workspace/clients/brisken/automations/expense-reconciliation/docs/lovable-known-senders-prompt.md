# Lovable prompt 2 of 3: Settings, the Email intake section

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Prompt 2 of 3. It touches ONE section of the Settings screen and nothing
else. Independent of the other two; order does not matter.

---

## What that section looks like right now (measured 2026-08-25)

This is the exact live inventory. Everything in it stays unless this prompt
says otherwise.

```
Email intake
  "People who can email receipts straight into the open month."     <- reword
  "Receipts can be emailed to any-name@expenses.brisken.com"        <- reword
  Aliases
    "Mail sent to this-name@expenses.brisken.com is attributed to
     this person."
    3 rows: Address | @expenses.brisken.com | Person | Remove        <- KEEP
  Accepted senders                                                  <- DELETE
    "Full addresses or @domain entries."                            <- DELETE
  Send automatic confirmation emails  (toggle)                      <- KEEP
    "The sender gets a short reply when their receipts land in
     the open month."                                               <- reword
  Alert recipients                                                  <- KEEP
    "These people get an email when an incoming mail is held."      <- KEEP
  "Mail archives are kept 10 years"                                 <- KEEP
  Add address | Save email intake                                   <- KEEP
```

Two things are wrong with it, and one thing is missing.

## 1. Delete the "Accepted senders" editor (it is dead)

"Accepted senders / Full addresses or @domain entries" is the retired
`intake.senders` allowlist. Submission opened to any sender on 2026-08-23 and
the backend now DROPS that key on save, so **whatever an operator types there
is discarded without a word.** It sits exactly where someone would go to
authorise a sender, so it produces a false result and reads as a broken tool.

Delete the control and stop sending a `senders` key in the settings PUT.
Section 3 replaces it with a field that works.

## 2. Three help lines that predate the month pool

Emailed receipts no longer land in "the open month". They file under the
month PRINTED on the receipt, and wait in a pool if that month has no batch
yet. Three lines still describe the old behaviour:

- Section description. **EN**: "People who can email receipts in. A receipt
  files under the month printed on it, and waits if that month does not exist
  yet." / **PT**: "Pessoas que podem enviar recibos por email. Um recibo entra
  no mes impresso nele e aguarda se esse mes ainda nao existe."
- Intake address line. **EN**: "Receipts can be emailed to
  any-name@expenses.brisken.com, from any address. Use dirk@, criss@ or
  matthias@ to book the expense to that person." / **PT**: "Recibos podem ser
  enviados para qualquer-nome@expenses.brisken.com, de qualquer endereco. Use
  dirk@, criss@ ou matthias@ para atribuir a despesa a essa pessoa."
- Under the confirmation toggle. **EN**: "The sender gets a short reply
  naming the month their receipt joined, or the month it is waiting for." /
  **PT**: "O remetente recebe uma resposta curta informando em que mes o
  recibo entrou, ou qual mes esta aguardando."

## 3. New field: "People we recognise"

Add a tag editor for outside addresses, below the Aliases rows and where the
"Accepted senders" editor used to be.

- Reads `GET /api/settings` -> `intake.known_senders` (a list of strings;
  a missing key means an empty list).
- Writes through the existing settings PUT as
  `{"intake": {"known_senders": [...]}}`.
- Send the whole list on every save; it replaces, it does not append.

Validation, so the operator sees the error before the API does:

- one plain address per tag, no display name, no angle brackets
- exactly one `@`, and a dot in the domain
- no commas, semicolons, spaces or line breaks inside a tag
- at most 25 addresses

The API refuses the same cases with a `400` naming the field; surface that
message rather than a generic failure.

Placeholder text: `dirk_.neumann@icloud.com`. That is the address the field
was built for.

### The help line under it

Say what listing an address does, because it does two things.

- **EN**: "Addresses here belong to people we know. They get the
  confirmation email when they send a receipt in, and a receipt they forward
  in the body of an email is read automatically instead of waiting for
  someone to open it. Everyone else can still email receipts; they just do
  not get a reply."
- **PT**: "Enderecos aqui pertencem a pessoas que conhecemos. Recebem o email
  de confirmacao ao enviar um recibo, e um recibo encaminhado no corpo do
  email e lido automaticamente em vez de esperar que alguem o abra. Os demais
  continuam podendo enviar recibos por email; apenas nao recebem resposta."

Addresses inside `@brisken.com` are recognised automatically and are never
listed here.

## 4. The one thing that will break this if you get it wrong

**The `intake` object is stored EXACTLY as you send it.** The backend merges
shallowly at the top level, so
`PUT {"intake": {"known_senders": [...]}}` replaces the whole intake block
and silently drops the aliases, the caps, the auto-ack toggle and the alert
recipients with it.

Read the current `intake` from `GET /api/settings`, change the one key, send
the whole object back. This is already true of every field in that section,
so if the existing save does a partial PUT it has the same bug today and this
is the moment to fix it.

## 5. Do not

- Do not touch any other Settings section: Export approved rows, FX reference
  rates, Cards, Merchants, Legal entities and Clear memory all work and are
  out of scope.
- Do not remove the Aliases rows, the confirmation toggle, the Alert
  recipients field, or the retention line.
- Do not add a sender allowlist back in any form. Submission is open by
  design; this field is about who we RECOGNISE, not who may write in.
- No em-dashes in UI copy.

## Verify after publish

The Settings screen shows no "Accepted senders" control; "People we
recognise" accepts `dirk_.neumann@icloud.com` and rejects `not-an-address`
with the API's message; saving it and reloading keeps the three alias rows
and the alert recipient intact.
