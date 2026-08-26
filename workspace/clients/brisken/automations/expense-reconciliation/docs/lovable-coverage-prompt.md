# Lovable prompt: the statement panel and per-card coverage

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Standalone; it does not depend on any other prompt and touches only the month
page and the statement workbench.

---

## What changed underneath, and why this screen is now wrong

A month used to take exactly one bank statement, and taking it CLOSED the
month. Neither is true any more.

`POST /api/expense-batches/{id}/statement` is repeatable. Criss loads one card
at a time, and usually twice per card: the mid-month partial the bank has
printed so far, then the closing cycle that re-prints everything plus the
rest. Receipts keep arriving into the month the whole time and the month
re-matches after each one.

The app has not caught up. It shows a month as having "a statement", singular,
offers one Download button for "the" workbook, and says nothing about which
CARDS have been loaded. On a month holding two workbooks the download silently
gives whichever one arrived last. On the real January 2026 month, 80 charges
span **three** different cards and the screen shows one flat unreconciled
figure of USD 20,228.68, which tells the reviewer nothing about which pile of
receipts to go and find.

Two new parallel fields answer both questions. Both are on the batch payload
(`GET /api/expense-batches/{id}`) and the run payload
(`GET /api/runs/{id}`), and for the same month they are identical, so render
them the same way on both screens.

## 1. `statements[]` — the uploads this month has taken

Oldest first. Empty on every month created before 2026-08-25, reconciling ones
included, so **empty means "not recorded", never "none loaded"**. `has_statement`
is still the answer to whether a month has one at all.

```json
{ "file": "statement-2.xlsx",
  "upload_name": "chase-april.xlsx",
  "card_key": "corp-1672",
  "account_id": "chase-2838-family",
  "sheet_name": null,
  "period_start": "2026-04-03",
  "period_end": "2026-04-28",
  "n_rows": 14,
  "n_new": 11,
  "uploaded_at": "2026-08-25T09:12:44",
  "writeback": true,
  "advisory": null }
```

Render a **Statements** panel on the month page, beside the existing "Attach
bank statement & reconcile" action, and the same panel on the workbench.

| Column | Source | Notes |
| --- | --- | --- |
| File | `upload_name` | what the operator actually sent. Two of Criss's per-card exports often share the bank's filename, so show `file` as a muted second line when it differs from `upload_name` |
| Period | `period_start` to `period_end` | both null means the file parsed no dated row; say "no dated rows", not a blank cell |
| Rows | `n_rows` | what the file held |
| New | `n_new` | what it added to the month |
| Uploaded | `uploaded_at` | |
| | `advisory` | see below |

`n_rows` minus `n_new` is charges the month already had. That is the ordinary
result of a partial followed by the full cycle, so do **not** render it as a
warning, a duplicate count, or a red anything. `n_new: 0` means the file was
re-uploaded and changed nothing; say "nothing new" in plain words.

Rename the existing "Attach bank statement & reconcile" action to **"Add a
statement"** and keep it available on a month that already has one. The button
is disabled today on a reconciling month; that refusal is gone from the backend
and the label is the last thing still saying the month is closed.

### `advisory` — show it, and do not act on it

A string, or null. When it is set, render it under the row it belongs to, in
the same style as an existing warning strip. Then stop: nothing was dropped,
merged, or refused, and the app must not offer to "fix" it. It fires when one
card was typed against two different account ids, or when an upload lands 100%
new over a period the same account already covers. In both cases the month
genuinely holds two readings of the same charges, and the sentence explains
which two files disagree. Surfacing the contradiction is the whole feature;
deduping it would silently pick whichever file arrived first.

## 2. The download selector

`GET /runs/{id}/statement-categorized.xlsx` takes an optional `?file=`,
matched against `statements[].file`, and 404s on a name the month never took.
Without the parameter it returns the current statement, exactly as today.

Today's single "Download statement with accounts" button is wrong on a
multi-statement month: it hands back one workbook with no indication which.
Replace it with one download control per statement row, on rows where
`writeback` is `true`, linking to
`/runs/{id}/statement-categorized.xlsx?file={encodeURIComponent(file)}`.
On a row where `writeback` is `false` the file is a CSV or PDF, which the
annotator cannot write into: render nothing, or a muted "not an Excel
workbook". Do not disable-and-tooltip; there is nothing to enable.

Each workbook comes back annotated for exactly the charges IT contains, at the
rows it puts them on. A charge printed by both the partial and the closing
cycle is annotated in both.

## 3. `coverage[]` — which cards, how far along

One entry per card the month knows about. `[]` on a month that has taken no
statement, which is the same thing an empty `statements[]` says.

```json
{ "key": "corp-1672",
  "card_key": "corp-1672",
  "label": "Corporate card (Chase)",
  "entity": "Corporate Services",
  "digits": ["2838", "1672"],
  "known": true,
  "statements": ["statement.xlsx", "statement-2.xlsx"],
  "period_start": "2026-04-03",
  "period_end": "2026-04-28",
  "n_transactions": 45,
  "n_reconciled": 30,
  "n_review": 2,
  "n_unmatched_tx": 12,
  "n_refunds": 1,
  "unreconciled_by_ccy": { "USD": "1,204.55" } }
```

Render a **Coverage by card** panel above the Statements panel, one row per
entry, in the order the API returns them (already sorted: cards with charges
first, then cards with nothing).

| Column | Source | Notes |
| --- | --- | --- |
| Card | `label` | always renderable text. Render it as-is; never fall back to `key`, which is a machine value |
| | `known` | `false` means the card registry has never met this card. Show a muted chip, "not in your card list", linking to Settings. It is a real finding, not an error |
| Entity | `entity` | empty string means unassigned; show a dash |
| Statements | `statements` | the upload file names that covered this card |
| Period | `period_start` to `period_end` | the first and last charge dates the month holds FOR THIS CARD, which is narrower than the month |
| Charges | `n_transactions` | |
| Matched | `n_reconciled` | |
| Needs a look | `n_review` | |
| No receipt | `n_unmatched_tx` | |
| Unreconciled | `unreconciled_by_ccy` | a map of currency to a pre-formatted string. Render `USD 1,204.55`; do not parse the number |

An entry with `n_transactions: 0` and `statements: []` is a card in the
registry that this month has loaded nothing for. **That row is the point of
the panel**, so render it rather than filtering it out: it is the only place
the reviewer can see which of her cards she still has to load. Style it muted
and put "nothing loaded yet" where the counts would be.

`n_refunds` is credits, money coming back. Leave it out of the table; a card
whose only activity is a refund still reads correctly, because refunds are
counted in `n_transactions` and excluded from `unreconciled_by_ccy`.

### The arithmetic has to survive on screen

Per row, `n_reconciled + n_review + n_unmatched_tx + n_refunds` equals
`n_transactions`. Down the column, each of those sums to the run summary's
field of the same name. That is guaranteed by the backend and pinned by its
tests, so a reviewer WILL add the panel up against the header. Do not round,
re-derive, or compute a percentage of your own; if a total needs showing, sum
the column.

## 4. Do not change

- The expense grid, the card-review strip, the set-aside strip, the stat row,
  the action row, Settings, Memory, Compare, `/inbound`, `/months`.
- The reconciliation PDF and expense PDF downloads.
- `has_statement`, which still answers "is this month reconciling".

## 5. Render defensively (the standing rule)

Both new fields are lists of objects. Type-check every element before
rendering it and degrade to plain text on anything unexpected, so a stale or
unfamiliar payload cannot take the page down. On 2026-08-22 the batch page
died on React error #31 for every batch that had a parse issue, because
`parse_issues` ships objects and the renderer was typed `string[]`. Both lists
here are empty on every month that predates them, so a month showing no panel
is correct and must not read as an error.
