# Lovable prompt: the month says when it was last matched, and whether a match is still owed (item 129, notes #53 #54)

> **NOT APPLIED** (written 2026-09-18). Backend gate: `last_rematch` and
> `rematch_pending` on both month payloads ship with the item 129 PR; until
> that is deployed the fields are absent and the header renders exactly as
> today. Notes #53 and #54 (do dropped or mailed receipts get the full
> treatment?) are answered yes: every arrival on a month with a statement
> re-matches that month; this prompt makes the answer visible on the page.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Auth stays the existing `Authorization: Bearer <token>`. One change, in the shared month header. Render defensively: a missing field degrades to the header as it is today, never to an error or a raw key.

## What the backend now sends

Both month payloads, `GET /api/runs/{id}` and `GET /api/expense-batches/{id}`, carry two new top-level keys next to `updated_at`:

- `last_rematch`: the most recent re-match of this month, or `null` when the month has never been re-matched:
  `{ at: string (ISO), trigger: string, n_transactions: number, n_matched: number, n_review: number, n_unmatched_tx: number, n_receipts: number, n_unmatched_rec: number, event_id: string }`
- `rematch_pending`: `null` in steady state; an object when the month owes a re-match that has not committed yet (a receipt landed a moment ago, or an attempt failed):
  `{ since: string (ISO), changed_at: string (ISO), trigger: string, error?: string, failed_at?: string, attempts?: number }`

`trigger` is one of `statement`, `reread`, `receipts`, `cards`, `master_data`, `set_aside`, `trip`, `adjacent_receipts`, `expense_edit`, `resume`, `duplicates`, `month_move`. Treat any other value as unknown and print it as is.

## 1. `src/lib/api.ts`

On the batch type the `MonthHeader` query reads (and on the run view type, same fields): add

```ts
last_rematch?: {
  at: string; trigger: string;
  n_transactions?: number; n_matched?: number; n_review?: number; n_unmatched_tx?: number;
  n_receipts?: number; n_unmatched_rec?: number; event_id?: string;
} | null;
rematch_pending?: {
  since: string; changed_at?: string; trigger: string;
  error?: string; failed_at?: string; attempts?: number;
} | null;
```

## 2. `MonthHeader`: the meta line under the strip

The line that reads `{t("expx.review.lastUpdated")}: {fmtDate(updated_at ?? created_at, locale)}` today gains one more muted fragment after it, separated by ` · `, chosen in this order and rendered with the same `text-xs text-muted-foreground` styling:

1. `rematch_pending` is an object AND `rematch_pending.error` is a non-empty string:
   `t("mh.rematch.failed", { when: fmtDate(rematch_pending.failed_at ?? rematch_pending.since, locale), trigger: triggerLabel(rematch_pending.trigger) })`, with `title={rematch_pending.error}` on the span so the raw error is a hover, not body text.
2. `rematch_pending` is an object (no error):
   `t("mh.rematch.pending", { since: fmtDate(rematch_pending.since, locale), trigger: triggerLabel(rematch_pending.trigger) })`.
3. `last_rematch` is an object:
   `t("mh.rematch.last", { when: fmtDate(last_rematch.at, locale), trigger: triggerLabel(last_rematch.trigger), matched: last_rematch.n_matched ?? 0, total: last_rematch.n_transactions ?? 0, review: last_rematch.n_review ?? 0 })`.
4. Both `null` or absent: nothing (the header is byte-for-byte today's).

`triggerLabel(trigger)` returns `t("mh.rematch.trigger." + trigger)` when that key exists in the active language, else the raw `trigger` string. Put the helper next to the header; no new component.

The fragment renders on both tabs the header serves (Matching and Expenses), because the header is mounted once per month page. Do not add a second copy inside `RunWorkbench.tsx` or `ExpensesReviewGrid.tsx`.

While the batch query is loading, the fragment is absent (same rule as the strip's skeleton). When the query errored (the `/classic` case), the meta line is not rendered at all today; keep that.

## New strings

| Key | EN | PT-BR |
|---|---|---|
| `mh.rematch.last` | Last matched {when} ({trigger}): {matched} of {total} charges paired, {review} to review. | Última comparação {when} ({trigger}): {matched} de {total} cobranças pareadas, {review} para revisar. |
| `mh.rematch.pending` | A new match is queued since {since} ({trigger}); the counts below may still move. | Uma nova comparação está na fila desde {since} ({trigger}); os números abaixo ainda podem mudar. |
| `mh.rematch.failed` | Matching failed {when} ({trigger}). It runs again on the month's next change. | A comparação falhou {when} ({trigger}). Ela roda de novo na próxima alteração do mês. |
| `mh.rematch.trigger.statement` | statement added | extrato adicionado |
| `mh.rematch.trigger.reread` | statement re-read | extrato relido |
| `mh.rematch.trigger.receipts` | receipts arrived | recibos chegaram |
| `mh.rematch.trigger.cards` | card changed | cartão alterado |
| `mh.rematch.trigger.master_data` | settings changed | configurações alteradas |
| `mh.rematch.trigger.set_aside` | a page was set aside | uma página foi separada |
| `mh.rematch.trigger.trip` | trip changed | viagem alterada |
| `mh.rematch.trigger.adjacent_receipts` | receipts for a neighbouring month | recibos de um mês vizinho |
| `mh.rematch.trigger.expense_edit` | an expense was edited | uma despesa foi editada |
| `mh.rematch.trigger.resume` | resumed after a restart | retomada após reinício |
| `mh.rematch.trigger.duplicates` | duplicates decided | duplicatas decididas |
| `mh.rematch.trigger.month_move` | a receipt moved between months | um recibo mudou de mês |

## Do not change

`expx.review.lastUpdated` and its date; `StatementSummary`; the tabs and counts in the strip; `CardTabs`; the Receipts page's per-month `rcpt.rematch.*` lines (they stay the drop-time answer, this header is the month-time answer); anything on `/api/operator/state` (the header must not call it).

## Checking it landed

1. `GET /api/expense-batches/074a7b8905d7` (August) carries `last_rematch` with a `trigger` and an `at`; the August header, both tabs, reads "Last updated … · Last matched <date> (<trigger>): N of 111 charges paired, M to review." with N equal to the payload's `n_matched`.
2. PT-BR (`brisken.lang` = `pt-BR`): the same line reads "Última comparação …" with the trigger in Portuguese.
3. July (`50622baec444`): same line with July's own numbers; the two months never show the same `at`.
4. A month whose payload has `last_rematch: null` and `rematch_pending: null` shows only "Last updated: <date>", nothing after it.
5. The pending and failed variants cannot be forced on Criss's months; they are checked on the next real drop (drop a receipt into a month with a statement, open the month within a few seconds: "A new match is queued since …", then after the re-match commits the line flips to "Last matched …" with a fresh `at`).
6. No request other than the existing batch/run queries appears in the network log when the month opens.
````
