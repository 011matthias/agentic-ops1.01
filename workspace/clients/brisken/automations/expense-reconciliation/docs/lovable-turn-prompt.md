# Lovable prompt - a row says whose turn it is; booked rows never ask (item 76)

Paste this into the `brisken-expense-review` Lovable project. It calls the
existing FastAPI backend at `https://api.expenses.brisken.com` as a JSON API.
**Do NOT add Supabase or any database.** Auth stays the existing
`Authorization: Bearer <token>`.

## Background

Every charge row on the Matching view prints its status from `row.status`,
and that is `pending` on almost every row, so the page says "Awaiting
decision" and offers Reject / Confirm on a charge Criss has already booked
(a yellow row in her workbook) exactly as it does on a real open pairing. The
owner asked, on a booked AMAZON row: "why is it asking this if its been
matched with no uncertainties?" The backend now says whose move each row is,
and it confirms clean exact pairs itself (same amount, same day, one
candidate, category ready, vendor agreeing), recording that it did so.

## 1. The new fields (`GET /api/runs/{id}`)

On every `rows[]` element:

```json
{
  "turn": "decide",
  "decided_by": "tool",
  "decided_rule": "exact_vendor_75"
}
```

- `turn`, always present, one of:
  - `"decide"`: a pending pairing waiting on the reviewer. The ONLY value that
    offers Reject / Confirm.
  - `"confirmed"`: a confirmed pairing (by the tool or a person).
  - `"rejected"`: a rejected pairing.
  - `"posted"`: already booked in the workbook. Nothing to do.
  - `"none"`: no pairing to decide (no receipt, or a credit on the statement).
- `decided_by`: `"tool"` or `"reviewer"`, present only when `status` is not
  `"pending"`. Absent otherwise, never null.
- `decided_rule`: a string, present only when `decided_by` is `"tool"`.

`summary.n_self_confirmed` (integer): how many rows the tool confirmed itself.
`summary.n_undecided` keeps its meaning and equals the number of rows with
`turn === "decide"`.

## 2. The status badge (`RowStatusBadge`, called from the charge row in `RunWorkbench.tsx`)

Pass the row, not only the status: `<RowStatusBadge status={row.status}
turn={row.turn} decidedBy={row.decided_by} />`. When `turn` is a string, pick
the label from it:

| `turn` | Label key | Style (existing map) |
|---|---|---|
| `decide` | `row.status.pending` (unchanged text) | `pending` |
| `confirmed`, `decidedBy === "tool"` | `row.status.confirmedByTool` | `confirmed` |
| `confirmed`, otherwise | `row.status.confirmed` | `confirmed` |
| `rejected` | `row.status.rejected` | `rejected` |
| `posted` | `row.status.posted` | `already_posted` |
| `none` | `row.status.none` | `pending` |

Each label keeps its `.tip` tooltip the way the component does today. When
`turn` is absent or any other value, render exactly what renders today from
`status`.

## 3. The action cell (same row, the cell with Reject / Confirm match)

- Render the **Reject** and **Confirm match** buttons only when
  `row.turn === "decide"`. When `row.turn` is absent, keep today's rule.
- The reset (undo) button that shows when `row.status !== "pending"` stays
  exactly as it is, so a confirmed row, including one the tool confirmed,
  keeps its undo. That undo is how a reviewer takes back a self-confirmation;
  the tool never re-confirms a row a person reset.
- Leave every other control in that cell as it is: Attach receipt, Match by
  hand, Reopen on a rejected row.

## 4. Bulk actions (`bulkTargets` in `RunWorkbench.tsx`)

Where `bulkTargets` filters `shownOpen` on `r.status === "pending"`, filter on
`(r.turn ?? (r.status === "pending" ? "decide" : "")) === "decide"` instead,
for both `confirmable` and `rejectable`. A booked row and a row with no
pairing are never part of "Confirm N shown" / "Reject N shown".

## 5. The Matched card caption

When `summary.n_self_confirmed > 0`, add one muted line under the Matched
card's existing caption: `wb.selfConfirmed.count` with `{n}`. Nothing when it
is 0 or absent.

## 6. i18n keys (EN and PT in the same edit, `src/lib/i18n.tsx`)

| Key | EN | PT |
|---|---|---|
| `row.status.confirmedByTool` | Confirmed automatically | Confirmada automaticamente |
| `row.status.confirmedByTool.tip` | Same amount, same day, one receipt, and the vendor agrees, so the tool confirmed it. Use undo to take it back. | Mesmo valor, mesmo dia, um recibo e o fornecedor confere, por isso a ferramenta confirmou. Use desfazer para reverter. |
| `row.status.posted` | Already booked | Já lançada |
| `row.status.posted.tip` | This charge is marked yellow in your statement workbook, so it is already booked. Nothing to decide here. | Esta transação está marcada em amarelo na planilha do extrato, por isso já está lançada. Nada a decidir aqui. |
| `row.status.none` | Nothing to decide | Nada a decidir |
| `row.status.none.tip` | There is no receipt paired with this charge to confirm or reject. | Não há recibo associado a esta transação para confirmar ou rejeitar. |
| `wb.selfConfirmed.count` | {n} confirmed automatically | {n} confirmadas automaticamente |

## 7. Do not change

- `row.status`, `effective_bucket`, `section`, `review`, `candidates[]` and
  every count keep their meaning.
- The decision calls (`POST /api/runs/{id}/decisions`, `.../decisions/bulk`,
  `.../decisions/confirm-ready`, confirm all matched) are unchanged.
- The views, folds, filters and sort from the month-views change.
- `row.status.already_posted` stays; it is the reviewer's own already-posted
  verdict and the `posted` turn reuses its style only.

## 8. Render defensively

`turn` may be absent on an older payload: every rule above falls back to
today's behaviour. An unknown `turn` value renders today's badge and today's
buttons. Never print a raw key.

## 9. After publishing, check

Re-read `GET /api/runs/{id}` for July `50622baec444` and August
`074a7b8905d7` first; the self-confirmed rows appear only after each month's
next re-match.

1. Bundle (`uv run tools/lovable-bundle-audit.py`, controls must hit):
   `n_self_confirmed`, `row.status.confirmedByTool`, `row.status.posted`,
   `row.status.none`, `wb.selfConfirmed.count` (not `decided_by` or `turn`
   alone: the duplicates panel already reads a `decided_by`).
2. July, Matching, the posted fold of Charges without a receipt: every booked
   row reads "Already booked" with no Reject and no Confirm match. The booked
   AMAZON* Z11US7DF5 315.56 row reads "Confirmed" (a person confirmed it) and
   keeps its undo.
3. July, Credits on the statement: "Payment Thank You-Mobile" reads "Already
   booked", no Reject.
4. A row with `decided_by: "tool"` (after the next re-match) reads "Confirmed
   automatically" with its tooltip and an undo; the Matched card shows
   "{n} confirmed automatically" equal to `summary.n_self_confirmed`.
5. Rows with `turn: "decide"` still offer Reject / Confirm match, and their
   count equals `summary.n_undecided`.
6. PT: "Já lançada", "Nada a decidir", "Confirmada automaticamente".
7. Network: no POST other than `/api/login` during the drive.
