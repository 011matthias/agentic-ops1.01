---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
updated: 2026-08-13
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

### 1. Same photo, same answer (NEXT UP)

**What happens today:** run the same receipt photo through the tool twice
and the money always comes out the same, but the words often do not. One
hardware-store receipt came back as "MEGA CENTER", "MEGA CENTRO", and
"MEGA CENTRE" across three runs of the identical image. Reference numbers
and tax labels wobble the same way.

**Why it matters:** the tool learns by remembering "this merchant posts to
that account". If the merchant's name is spelled differently every month,
each spelling starts its own memory and none of them reinforces the
others, so the tool never gets smarter. That quietly breaks the core
promise: less correction work every month, not the same amount.

**The fix:** remember the reading per photo. Once a photo has been read,
store the result keyed on the photo's fingerprint (its content hash) and
reuse it instead of asking the AI again. Re-runs become identical by
construction and cost nothing. Month-to-month spelling differences on NEW
photos remain the merchant name book's job (item 2 + the registry that
already exists). Explicitly ruled out: making the memory lookup "fuzzy" so
near-miss spellings match; that risks mixing up genuinely different
merchants.

**Size:** one focused loop iteration. **Status:** designed, not built.

### 2. Test runs should use the merchant name book too

**What happens today:** the live app consults the merchant name book (the
"registry" that maps every spelling of a merchant to one canonical name).
Command-line test runs on the dev machine skip it entirely, because the
CLI never loads it. So our offline quality checks judge the tool WITHOUT
the very feature built to fix naming, and understate what Criss actually
gets.

**Why it matters:** the improvement loop steers by these test runs. If the
test setup differs from the live app, we optimize the wrong thing.

**The fix:** let a local run config carry a merchants block (or a pointer
to one) so the CLI path builds the same registry the web app uses.

**Size:** small. **Status:** open.

### 3. Show set-aside files in the review screen

**What happens today:** when the tool decides an upload is not a receipt
(a bank-statement page, a report summary sheet), it sets the file aside
and notes it in a technical issues list. That is loud enough for us, but
Criss will not read an issues list.

**Why it matters:** trust. A tool that silently ignores something she
uploaded reads as broken. A tool that says "I set these 7 files aside,
they look like bank statements, tap here if I'm wrong" reads as careful.
This is the difference between her adopting the tool and her double-
checking it forever.

**The fix:** a small "set aside" strip in the review screen: file name,
reason in Portuguese, and a one-click "this really is a receipt" override
that re-adds it. Backend already exposes everything needed; this is a
Lovable (UI) prompt for the owner.

**Size:** small UI change + one backend override endpoint. **Status:** open.

### 4. One receipt, one row? (needs a human call, not code)

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

### 5. Put the set-aside statement pages to work (later)

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

## Related but tracked elsewhere (do not duplicate here)

- Merchant name book seed cleanup (merge the MEGA CENTER/CENTRE duplicate
  entries, fix the mislabeled construction-materials category): an owner
  task in the Merchants editor; noted in the status file row "Canonical
  merchant registry".
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
