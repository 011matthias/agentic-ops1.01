# Lovable prompt: receipts that wait for a statement (backlog item 220)

Paste everything below the line into Lovable. Written for the Lovable agent.

---

## Background

On the month workbench, an unmatched receipt dated after the last loaded
charge used to read "Dated at the edge of this statement; the charge is
likely in the previous or next month." In September 2026 that was 40 of 51
unmatched receipts, while the Expenses tab said "waiting for the statement"
for the same rows. The backend now reads the receipt's card first and adds
one new reason code for this case, names the cards each such receipt waits
on, and counts those receipts apart in the month summary. This prompt
renders the new code, the card list and the new count. Nothing else changes.

## The new fields (all come from `GET /api/runs/{id}`)

1. `unmatched_receipts[].reason_code` has ONE new value:
   `"statement_not_loaded_for_date"`. The existing five values are unchanged.
2. `unmatched_receipts[].waits_for_statements`: `string[]` of card labels,
   e.g. `["Credit Card Chase Visa - 9693"]`. Present only when `reason_code`
   is `"statement_not_loaded_for_date"` or `"card_statement_not_loaded"`;
   ABSENT otherwise (never null, never `[]`).
3. `summary.n_receipts_waiting_statement`: number, always present. A SUBSET
   of `summary.n_receipts_need_charge`: how many of the receipts without a
   charge are only waiting for a statement.
4. `summary.receipts_waiting_cards`: `string[]` of card labels, the union of
   the lists in (2) over those receipts. ABSENT when the count is 0.

Auth stays the bearer token. No Supabase.

## Render rules

A. Wherever the workbench renders an unmatched receipt's reason from
   `wb.reason.receipt.<code>` (the long line and the `.short` chip), add the
   new code with the keys below. Look it up exactly like the other five.
   This includes the "Why:" breakdown under "Receipts without a charge"
   (`wb.reason.breakdown`): today it skips a code with no key, so on
   September it reads "Why: 1 next or previous month · 4 not a card
   payment" for 51 receipts. With the key it must also count the new code
   ("46 statement not loaded yet").

B. On an unmatched receipt that carries `waits_for_statements`, append the
   cards to the long reason line: `{reason} Waiting for: {cards}.` using key
   `wb.reason.receipt.waitsFor`, where `{cards}` is the list joined with
   ", ". When the list has more than 3 entries, show the first 3 and
   "+{n} more" (key `wb.reason.receipt.waitsForMore`). The chip stays the
   `.short` text only.

C. In the month summary where `sum.needCharge.one` / `sum.needCharge.many`
   renders "{n} receipts have no charge": when
   `summary.n_receipts_waiting_statement > 0`, render two parts instead of
   one:
   - `sum.waitStatement.one` / `.many` with `{n}` =
     `n_receipts_waiting_statement`
   - and, only if `n_receipts_need_charge - n_receipts_waiting_statement > 0`,
     `sum.needChargeLoaded.one` / `.many` with that difference as `{n}`.
   When `n_receipts_waiting_statement` is 0 or absent, keep the existing
   single `sum.needCharge.*` text exactly as it is today.
   If `summary.receipts_waiting_cards` is present, show it as a tooltip (or
   title attribute) on the waiting part: key `sum.waitStatement.cards` with
   `{cards}` joined by ", ".

## i18n keys (add to BOTH languages in `src/lib/i18n.tsx`)

EN:
- `"wb.reason.receipt.statement_not_loaded_for_date"`: `"The card's statement is not loaded up to this date yet; the charge appears when it is."`
- `"wb.reason.receipt.statement_not_loaded_for_date.short"`: `"statement not loaded yet"`
- `"wb.reason.receipt.waitsFor"`: `"Waiting for: {cards}."`
- `"wb.reason.receipt.waitsForMore"`: `"+{n} more"`
- `"sum.waitStatement.one"`: `"{n} receipt waits for a statement"`
- `"sum.waitStatement.many"`: `"{n} receipts wait for a statement"`
- `"sum.waitStatement.cards"`: `"Statements still to load: {cards}"`
- `"sum.needChargeLoaded.one"`: `"{n} receipt has no charge on any loaded statement"`
- `"sum.needChargeLoaded.many"`: `"{n} receipts have no charge on any loaded statement"`

PT:
- `"wb.reason.receipt.statement_not_loaded_for_date"`: `"O extrato do cartão ainda não foi carregado até esta data; a transação aparece quando for."`
- `"wb.reason.receipt.statement_not_loaded_for_date.short"`: `"extrato ainda não carregado"`
- `"wb.reason.receipt.waitsFor"`: `"Aguardando: {cards}."`
- `"wb.reason.receipt.waitsForMore"`: `"+{n} outros"`
- `"sum.waitStatement.one"`: `"{n} recibo aguarda um extrato"`
- `"sum.waitStatement.many"`: `"{n} recibos aguardam um extrato"`
- `"sum.waitStatement.cards"`: `"Extratos a carregar: {cards}"`
- `"sum.needChargeLoaded.one"`: `"{n} recibo sem lançamento em nenhum extrato carregado"`
- `"sum.needChargeLoaded.many"`: `"{n} recibos sem lançamento em nenhum extrato carregado"`

## Do not change

- The five existing `wb.reason.receipt.*` keys and their texts.
- `sum.needCharge.*` texts, and the single-part rendering when nothing waits.
- The Expenses tab's `expx.review.reason.waits_for_statement*` lines (they
  read `expenses[].review.waits_for_statements`, a different field).
- Any API call, route, auth or write. This prompt only renders fields.

## Check after publishing

On September 2026, open the workbench's unmatched receipts: receipts dated
15 to 24 September read "The card's statement is not loaded up to this date
yet..." with "Waiting for: ..." naming cards, not "next or previous month".
The month summary reads "46 receipts wait for a statement" beside
"3 receipts have no charge on any loaded statement" (counts at the time of
writing). August 2026 is unchanged: its 08-30/31 receipts still read "next
or previous month".
