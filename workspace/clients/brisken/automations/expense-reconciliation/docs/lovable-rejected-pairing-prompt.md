# Lovable prompt - a rejected receipt is still offered as an option (item 16)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

## Background

Rejecting a match sends the charge back to unmatched and frees its receipt,
and it stays reversible until the month is exported. But `candidates[]` keeps
every receipt the matcher paired with the charge, so the receipt the reviewer
just pushed away re-renders underneath the row exactly as it did before,
offered again as though it were still on the table. Nothing on the page says a
pairing was turned down, and nothing offers a way back, so the reviewer has no
answer to "what now" (noted 2026-07-27).

## 1. The new fields

`GET /api/runs/{id}` -> `rows[].candidates[].rejected`, parallel and **absent**
(not `false`) unless the reviewer's current verdict on that charge is
`rejected`:

```json
"rejected": true
```

It sits on every candidate of a rejected charge, because a reject means "none
of these": the backend ignores which document was named, and a bulk reject
names none.

`summary.n_rejected_pairings` (integer, run payload) is how many
charge-and-receipt pairings the reviewer has turned down. A rejected charge
that never had a candidate refused nothing and adds nothing to it.

## 2. The candidate

A candidate carrying `rejected` renders **muted** (the same treatment as a
`held_by` candidate: reduced opacity, no primary action), with the label
`wb.cand.rejected` and, beside it, an `undo` action labelled
`wb.cand.rejectedUndo`. Read as one line: `Rejected · undo`.

It is information plus a way back, not an option: the confirm / pick action on
that candidate is hidden while the flag is present.

## 3. The undo action

`POST /api/runs/{id}/decisions`

```json
{ "transaction_id": "<the row's transaction_id>",
  "status": "pending",
  "chosen_document_id": null }
```

No new endpoint; this is the same route the reject went through. The reply
carries the fresh `summary`, and re-fetching `GET /api/runs/{id}` shows the
charge back in its original bucket with the receipt returned to it and the
`rejected` flags gone. Treat a non-200 as a failed undo and leave the row as
it was.

## 4. i18n keys

| Key | EN | PT |
|---|---|---|
| `wb.cand.rejected` | Rejected | Rejeitado |
| `wb.cand.rejectedUndo` | undo | anular |
| `wb.tile.rejectedPairings` | Rejected pairings | Associacoes rejeitadas |

## 5. The tile

`summary.n_rejected_pairings` beside WAITING ON A PICK, labelled
`wb.tile.rejectedPairings`. Neutral at 0. It answers "what did I push away this
month, and is any of it waiting on me".

## 6. Do not change

`candidates[].is_chosen`, `held_by`, the bucket, the section and every other
count keep their meaning. `rejected` is additive: a month nobody rejected in
does not carry the key at all, and the page renders exactly as it does today.
A candidate can carry both `rejected` and `held_by`; render the muted state
once and show both reasons.
