---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
state: active
updated: 2026-08-18
---

# Expense tool: improvement backlog (the one list)

Every improvement idea for the receipt-first expense tool lives HERE and
only here. The status file (`p1-expense-reconciliation.md`) records what
shipped; this file records what we think should happen next and why. When
an item ships, move it to the "Shipped" section at the bottom with its PR
number. New ideas from any session get appended here, never scattered
across checkpoints or chat.

Ranking rule (from the loop brief): wrong money beats wrong text, things
that stop the tool from learning beat cosmetics, and anything Criss would
have to hand-fix every month beats a one-off.

## Open

### 2. One receipt, one row? (needs a human call, not code)

**What happens today:** a receipt whose items belong to two different
expense accounts (the bakery run that was half beer, half sweets) becomes
TWO rows in the export, sharing one reference number, sums exact. That is
accounting-correct, and Zoho wants one account per expense row.

**Why it matters:** if Criss expects one row per piece of paper, two rows
will look like a duplicate and she will "fix" it. Nobody has asked her.

**The decision needed:** ask Criss (or Dirk) whether split rows are fine
or whether the tool should force one account per receipt (biggest item
wins, rest noted for her). Five-line change either way; the point is to
match her mental model, not to be cleverer than her.

**Status:** parked for an owner/Criss conversation.

### 3. Put the set-aside statement pages to work (later)

**What happens today:** statement pages found among the receipts are set
aside and that is the end of it.

**Why it matters (eventually):** those pages are exactly what the OTHER
half of the tool (statement reconciliation, Mode B) needs as input. Criss
uploading them "wrong" is actually her handing us the month-end statement
early.

**The fix, someday:** offer set-aside statements to the statement side of
the same batch instead of only quarantining them. Do this only after the
statement-attach flow is in daily use; until then it is speculative.

**Status:** idea, deliberately not scheduled.

### 4. Category flips on identical inputs (watch, do not build yet)

**What happens today:** the reading cache (shipped 2026-08-15) pins what
the AI SEES on each photo, but the categorize step still asks the AI
fresh every run. Across the August test runs the same PagBank receipt was
filed three ways on three days (no category, "Professional Services",
"Software & Subscriptions") while its money never moved. In the two
back-to-back runs after the cache shipped, categories came out identical
both times, so with pinned inputs the wobble may be rare in practice.
2026-08-16 check: a third smoke10 run (R7) came out byte-identical to
R6, categories included; the watch stays quiet. 2026-08-18 (round 5):
the May fresh-read pair showed one category change, but it was caused by
the item-6 vendor flip (bank-as-vendor carries no category signal), not
by categorize-call wobble on a pinned input — the watch condition has
still never fired.

**Why it might matter:** a category that flips between runs creates the
same trust problem as a vendor spelling that flips. But the merchant name
book and learned memory already outrank the AI for every merchant Criss
has corrected once, so the exposed surface shrinks on its own as she uses
the tool.

**The fix, if needed:** extend the same store to categorize calls (keyed
on the line-item descriptions + the account list). Only build this if a
flip is actually observed on cache-pinned inputs.

**Status:** watching; re-check the diff on the next loop iteration.

### 5. Stale "excluded" warning after a restore (cosmetic)

**What happens today:** when a reviewer restores a set-aside file, the
strip entry flips to "restored" but the original technical parse warning
("excluded from expenses, no row exported") stays in the issues list,
now contradicting the grid.

**Why it barely matters:** the strip is the surface Criss reads; the
issues list is ours. Fix only if the contradiction confuses someone in
practice.

**Status:** open, cosmetic, low priority.

### 6. Vendor must be the merchant, never the card-terminal bank

**What happens today (round-5 evidence, 2026-08-18):** on a French card
slip that prints both the shop and the acquiring bank, a fresh read
returned the BANK as the vendor (CREDIT AGRICOLE NORMANDIE) where the
2026-08-13 read of the same photo had returned the shop (ANNADA ROUEN).
Money, date, and currency were identical both times; the category also
degraded (Meals became uncategorized) because the bank name carries no
category signal.

**Why it matters:** a bank-as-vendor row teaches the merchant book the
wrong name and reads as obviously wrong to Criss. The extraction cache
already pins whichever answer the FIRST read lands on, so on the hosted
app this only bites once per photo; this item is about making that first
read land right.

**The fix:** one line in the extraction prompt ("when a receipt shows
both the merchant and a card-terminal/acquiring bank, the vendor is the
merchant, never the bank"), which bumps the cache fingerprint. Cheap;
bundle it with the next code round rather than shipping alone.

**Status:** open, small, waiting to ride along with the next code change.

### 7. Round-5 fresh-read drift record (evidence, no action)

Two fresh reads of Criss's May folder 5 days apart (2026-08-13 vs
2026-08-18, no cache in the local config): all 20 rows kept identical
amounts, currencies, and dates, and the statement quarantine held 7 of 7
both times. All drift was in text fields: the item-6 vendor flip, one
vendor spelling (Enimove vs Enilive, real brand Enilive), tax-label and
reference noise, and one row that lost its card-hint Paid-Through
resolution. Set 6 (13 never-tested receipts: Uber email-forwards, MBTA,
DB tickets, BRL service invoices) produced exact sums against every
source total spot-checked (three Uber trips to the cent, DB 6.65 EUR);
its misses were vendor names only ("CIV" instead of DB AG, "Uber
Receipts" instead of Uber). Conclusion: money is stable across fresh
reads; residual noise is text-field-only and shrinks as the merchant
book grows.

## Related but tracked elsewhere (do not duplicate here)

- Merchant name book seed cleanup (merge the MEGA CENTER/CENTRE duplicate
  entries, fix the mislabeled construction-materials category): an owner
  task in the Merchants editor; noted in the status file row "Canonical
  merchant registry". Round 5 adds the non-BRL vendor families the book
  does not know yet: DB AG (one ticket read the "CIV" tariff marker as
  the vendor), Uber (email-forwards read as "Uber Receipts"), Enilive
  (read once as "Enimove").
- Three parked design questions from the r1 feedback round (entity from an
  upload column, currency guessing, one merchant with different categories
  per entity): status file row "Zoho import headers + card-first fix".
- Remaining Lovable halves (confirm-all queue rendering, folder-attach
  picker, paid-through cell): each named in its status file row.

## Shipped (loop history)

| Iteration | What | Why it mattered | Shipped |
|---|---|---|---|
| 1 | Non-receipt quarantine: the tool now recognizes bank-statement pages and report summary sheets among the uploads and sets them aside loudly instead of inventing an expense from them | Criss's real May folder had 7 statement PDFs among 27 files; a report summary page had become a phantom 8,796.35 BRL "expense" | PR #516, Fly v58, 2026-08-13 |
| 2 | The word "null" can no longer appear as an expense account in the export; those rows now show the honest "(uncategorized - assign)" placeholder | The AI sometimes answers "no category" as the literal word "null", which Zoho cannot import and Criss would trip over monthly | PR #518, Fly v58, 2026-08-13 |
| 3 | Same photo, same answer: once a photo has been read, the reading is stored keyed on the photo's content fingerprint and reused instead of asking the AI again; re-runs are identical by construction and cost nothing | The identical image had come back MEGA CENTER / CENTRO / CENTRE across runs, and the 2026-08-15 baseline added a BRL-to-EUR currency flip and a tax drift; every new spelling fragmented learned memory. Verified: smoke10 run twice on the fixed code, the two CSVs byte-identical, second run made zero extraction calls | PR #536, 2026-08-15 |
| 3b | Test runs use the merchant name book too: a run config can carry expense.merchants (inline) or expense.merchants_path (JSON file or full settings dump), and the exported CSV now shows the canonical merchant name over the raw OCR spelling | Offline quality runs were judging the tool WITHOUT the canonicalization Criss actually gets, so the loop was steering on the wrong signal | PR #536, 2026-08-15 |
| 4 | Set-aside strip: the review screen now gets a first-class list of what the quarantine set aside (file, reason code for PT wording, restored state) plus a one-click "this is a receipt" restore that reuses the stored reading (no second AI read) and runs the normal categorize pass. Mid-month exclusions survive later adds; the May run derives its strip from the old warnings. Lovable UI half handed to the owner (`docs/lovable-set-aside-prompt.md` in the module) | Trust: a tool that silently ignores an upload reads as broken; one that says "I set these aside, tap here if I'm wrong" reads as careful. Also closed a real hole: a mid-month exclusion vanished from view on the NEXT add | PR #538, 2026-08-16 |
