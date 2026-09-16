# Lovable prompt - a broken month is never "ready to post" (item 57)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

On 2026-09-10 August 2026 was uploaded with every purchase printed negative.
The matcher saw 111 credits and no purchases, proposed nothing, and the
month reported "ready to post" with 0 of 111 matched and 31 receipts in the
pool. Nothing was undecided because nothing had been proposed.

The backend now judges this itself. Both payloads carry a new object, and
`summary.ready_to_post` is false whenever it says the month is broken:

`GET /api/runs/{id}` and `GET /api/expense-batches/{id}` ->
`summary.month_health`:

| Field | Type | Meaning |
|---|---|---|
| `checked` | boolean | false before a statement is loaded (then everything below is empty) |
| `state` | `"ok"` or `"broken"` | broken = the matcher proposed nothing while exact same-day same-amount pairs sit in the pool |
| `reason` | `"zero_match_with_exact_pairs"` or null | the one rule so far; render by code |
| `n_exact_pairs` | integer | how many receipts are the same amount within a day of a charge |
| `suspects` | string[] | which input is broken, in this order: `sign`, `currency`, `entity`, `card`, `unknown` |
| `detail` | string or null | one English sentence, the fallback when a code has no copy |

## 1. The "Ready to post?" bar

Today the bar reads `summary.ready_to_post` and, when false, shows the
undecided count. Keep that. Add one case: when `ready_to_post` is false AND
`summary.month_health.state === "broken"`, the bar renders as a red
blocked state instead of the undecided count:

- Title: `Not ready: this month cannot be matched`
- Body: the localized sentence for `reason`, then one bullet per entry in
  `suspects` (copy below), then the fix line.
- No Confirm-all / Post action is enabled while the state is broken.

Render `detail` verbatim when `reason` is a code this build does not know.

## 2. Copy

| Key | EN | PT |
|---|---|---|
| `wb.health.title` | Not ready: this month cannot be matched | Nao pronto: este mes nao pode ser conciliado |
| `wb.health.reason.zero_match_with_exact_pairs` | The tool matched nothing, yet {n} receipts in the pool are the same amount on the same day as a charge. Something in the inputs is broken. | A ferramenta nao conciliou nada, mas {n} recibos no conjunto tem o mesmo valor no mesmo dia de um lancamento. Algo nos dados de entrada esta errado. |
| `wb.health.suspect.sign` | The statement's sign: purchases arrived as credits. | O sinal do extrato: as compras chegaram como creditos. |
| `wb.health.suspect.currency` | The currency: same amounts in different currencies. | A moeda: mesmos valores em moedas diferentes. |
| `wb.health.suspect.entity` | The legal entity: receipts and charges name different companies. | A empresa: recibos e lancamentos apontam empresas diferentes. |
| `wb.health.suspect.card` | The card: receipts name a different card than the charge. | O cartao: os recibos apontam um cartao diferente do lancamento. |
| `wb.health.suspect.unknown` | Something the tool cannot name. Contact support. | Algo que a ferramenta nao consegue identificar. Fale com o suporte. |
| `wb.health.fix` | Fix the input, then have the statement re-read (an operator action) before posting anything. | Corrija a entrada e peca a releitura do extrato (acao do operador) antes de lancar qualquer coisa. |

`{n}` is `n_exact_pairs`.

## 3. The months list

No change to the list payload. Do not derive a badge from this field on
the list screen; the bar on the month page is the one surface.

## 4. Do not change

`n_undecided`, `n_unmapped_accounts` and the rest of the bar's inputs keep
their meaning. `ready_to_post` keeps its type; it is simply false in one
more situation, and this prompt is what says why.
