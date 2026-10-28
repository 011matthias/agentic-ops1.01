# Checkpoint: Brisken Recon Item 98 One Currency

**Date:** 2026-09-18
**Status:** Item 98 shipped, deployed (Fly v179) and verified live; the p1 queue's next work is owner-gated or unstarted audit items

---

## Summary

The session opened on a stale ground rule and found it: the prompt carried
"covered-class defects only", but the owner had reversed that the evening
before, which put the highest-ranked unshipped item in the audit back in
scope. Item 98 was built, adversarially reviewed, fixed, shipped and driven
live: July's expense CSV now closes with one figure, USD 58,187.69, matching
the number predicted before a line was written.

---

## What Was Done This Session

### The scope correction that decided the work
1. The prompt's ground rules said items 98 / 104 / 120 / 123 / 125-128 were
   out of licence scope. The licence memory instead recorded an owner
   reversal, and the backlog showed siblings had already shipped operations
   items 119, 122 and 124 under it.
2. Confirmed from the owner's own words in a sibling transcript, 17:36:59Z:
   "no we build it all and then agree on the 600€ license. no functioning
   tool = no 600€license", item 120 excluded.
3. That made item 98 the highest-ranked unshipped item (audit rank 5 of 40;
   everything else unshipped ranks 11 or lower), so it was taken rather than
   re-asked.

### Item 98, built (PR #1076, Fly v179)
1. New pure module `output/single_currency.py`. Three rungs in order of how
   much they know: a USD row is itself; a receipt a reconciled USD charge
   settled converts at THAT CHARGE; anything else at the matcher's own
   `_reference_rate_for`.
2. `expenses.csv` fills the EXISTING `Exchange Rate` column, empty on all 57
   live rows since the export existed, and states the month's total under the
   rows. The month report prints each figure and rate as a small second line
   under the amount (item 65's device), so no tenth column reopens the page
   width item 143 had to fix.
3. Predicted the live effect BEFORE building the documents, off a read-only
   DB copy plus the live payload: July USD 58,187.69, August USD 2,808.91.
   Both matched the deployed output to the cent.

### The adversarial review, which found a dead rung
1. A background reviewer read the diff and returned ten findings with the
   commands that produced them. Four were real: the ECB rung never fired
   (`ecb_monthly_rate` takes a `date` or "YYYY-MM" and was handed the
   listing's ISO date cell, so rung 3 had silently become
   typed-rates-only); the CSV named rows by a listing number it does not
   print and which is not the report's; a blank amount parsed as zero and
   took a rate; rung 2 was an `elif` that blocked the fallback.
2. It also refuted one of my own docstrings: the CSV and the report do NOT
   always total the same, and should not, because the CSV exports every
   expense and the report lists company expenses only.
3. All fixed, each with a test proven red by hand.

### Scope narrowed in exactly one place
`EXPENSE_COLUMNS` was left untouched. The item asked for a new USD column;
the header is a live import contract whose target system the owner has
explicitly left open (item 23), and the column that already exists means
exactly this. Recorded in the backlog as the one narrowing, with the
one-line follow-up named if the owner wants the literal column.

---

## Key Decisions Made

### Treat the licence reversal as standing rather than re-asking it
- **Choice:** Build item 98 without putting the scope question to the owner.
- **Rationale:** The ground rules say an owner ruling found in the record is
  used, never re-asked. The ruling was in a memory, in the owner's own
  transcript words, and in three shipped operations items. Asking again
  would have re-litigated a settled decision and cost the session's best
  item.

### Fill the existing Exchange Rate column instead of adding one
- **Choice:** No new CSV column; fill `Exchange Rate` and add a footer total.
- **Rationale:** The consumer of this CSV is an open question the owner
  reserved. A column that already exists cannot break a mapping that a new
  one might, and `Exchange Rate` is the column the format already provides
  for this exact number. The narrowing is recorded so it can be reversed in
  one line.

### Print nothing when the figure repeats what the document already says
- **Choice:** Three gates; a month already in one currency, a month that
  priced nothing, and a month where nothing converted all render exactly as
  before.
- **Rationale:** The first build added a "Total in USD" beside an identical
  "USD 2,033.86" on every single-currency month, which broke 24 existing
  tests. The tests were right: a second heading restating one number teaches
  the reader to skim. After the gates, zero pre-existing tests needed
  changing, which is the signal the scope was finally correct.

### Label a partial figure as partial, in the heading
- **Choice:** A month that priced only some rows reads "Partial total in
  USD: 108.00 (3 of 4 expenses...)", never "Total".
- **Rationale:** A figure headed "Total" that leaves an expense out is the
  failure item 65 exists to prevent, and a parenthetical cannot undo a
  heading, because the heading is what a reader carries away.

---

## What Did NOT Work (and why)

- **Asserting the PDF row caption with an exact-text needle:** the caption
  renders correctly but wraps inside the 54-point Amount column, so the
  extractor returns "= USD 56.00 at\n1.12, the charge". The needle reported a
  caption missing that was on the page; same shape as the previous session's
  "Guess"/"GUESS" miss. The helper now flattens whitespace before matching.
- **Patching service.py with Python `read_text` / `write_text(newline="")`:**
  text mode translated CRLF to LF on read and wrote LF back, flattening the
  whole file's line endings and turning a 173-line addition into a
  whole-file diff. Byte-mode (`read_bytes` / `write_bytes`) is the only safe
  way to patch these CRLF sources.
- **`total_line` reading "excludes 1 expense with no rate" beside a "Total"
  heading:** honest in the parenthetical and misleading in the heading. The
  first fixture that hit it (EUR 32 + USD 15, no EUR rate) would have printed
  "Total in USD: 15.00" for a month that cost more than that.
- **Editing the worktree while the adversarial reviewer was reading it:** it
  caught an inconsistent save mid-review and had to re-verify everything
  against hashes of the final files. Its findings survived, but the review
  cost more than it needed to.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/output/single_currency.py` | create | The conversion: rungs, allocation, the notes and the silence gates |
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `settled_charge_amounts`, `usd_reference_rate`, `single_currency_for_export`, and the two document call sites |
| `automations/expense-reconciliation/src/expense_recon/output/zoho_expense_export.py` | edit | The `single_currency` callback, the Exchange Rate fill, multi-line footers |
| `automations/expense-reconciliation/src/expense_recon/output/month_report_pdf.py` | edit | Per-row caption, the header figure, per-section figures, the footer note |
| `automations/expense-reconciliation/tests/test_single_currency_item_98.py` | create | 19 tests, route-level through both documents |
| `automations/expense-reconciliation/docs/api-contract.md` | edit | The item 98 section, including the ECB date trap |
| `status/p1-improvement-backlog.md` | edit | Item 98 heading, Shipped paragraph, Shipped row 85 |
| `status/p1-expense-reconciliation.md` | edit | Element row |

---

## Current Status

Item 98 is live on Fly v179 and driven on the real consumer: July's CSV
carries a rate on 34 of 56 rows and closes `Total in USD: 58,187.69`;
August closes `2,808.91`. Both rungs are visibly firing (Amazon.de reads
1.143002 off its own charge against the typed 1.162275). PRs #1076 and #1077
merged; the worktree is removed and the read-only DB copy deleted.

The p1 defect queue remains empty. What is left in the audit is either
owner-gated (108, 118, 129 need a UI paste or owner data; 121's remaining
half needs owner data) or unstarted operations/new-function items that the
reversal put back in scope: 104, 123, 125, 126, 127, 128. Item 120 stays
excluded by the owner. `/feedback.jsonl` holds 69 notes, last recorded #69.

brisken platform line from `pre`: unknown plan, `~?/?` ops/mo, last assessed
`?`.

---

## Next Steps

1. Any new feedback note past #69, Criss's first.
2. Item 104 is the highest-ranked item now unshipped (audit rank 11): a
   decision history. Its credential half (rotating the shared code, which
   logs everyone out) is outward-facing and needs its own owner yes; the
   history half does not.
3. Items 123, 125, 126, 127, 128 are in scope under the reversal. 126 asks
   Criss to close a month and is an owner action, not code.
4. Watch for item 132's drift advisory on July's next re-match; still no
   live sighting.
5. brisken comms-log is 10 days stale. Not asked this session: no human was
   present in the loop, and a blocking question would have stalled the
   checkpoint. Worth one ask at the next interactive turn.
6. `/ops-audit brisken` would fill the unknown platform plan line.
7. p2 status files `p2-product-decks.md` (57d) and `p2-targeting.md` (58d)
   are stale; they belong to the lead-gen sessions, not this one.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (the item 98 section carries the ECB date trap)

### Open Questions
- Does the owner want a literal `USD Equivalent` column in `expenses.csv`?
  It was deliberately not added, because `EXPENSE_COLUMNS` is an import
  contract whose target system is still item 23's open question. One line if
  he does.
- Item 90 step 4 stays declined; the four rate-less months (September, May,
  June, January) still take today's typed rates on their next statement
  attach.

### Working Notes
- Live rates in play: Settings holds `EUR:USD 1.162275` and `BRL:USD
  0.192448`, both "configured", which outranks ECB. July's frozen config has
  NO ECB table; August's does. So item 98's ECB rung is correct but dormant
  on both live months, and fires first on a month with no typed rate.
- July's largest converted row is Konsultancy Finance, EUR 15,972.00 at the
  typed rate (USD 18,563.86), because no card charge settled it. That single
  row is a third of the month's figure and rides a rate nobody has checked
  against the ECB.
- The month report PDF route WRITES render outcomes into the run (item 67),
  so it cannot be fetched on a live month. The CSV can, and was.
- Nine wiring points were proven red by hand this session using a copy-aside
  script in the scratchpad rather than `regress_check.py`, which reports
  "RED (no pytest summary line)" even for a green suite.

### Reference Materials
- PRs #1076 (the build) and #1077 (the record)
- `%TEMP%\claude\recon-probe\api.py` for authenticated GETs

---

## How to Continue

Read `/feedback.jsonl` first; a new note from Criss outranks everything. If
nothing new has landed, item 104's history half is the highest-ranked
unshipped work, and the reversal means it no longer needs a scope question.

---

## Strategic Feedback

### What Worked Well This Session
- Checking the prompt's own ground rules against the record instead of
  obeying them. The prompt said item 98 was out of scope; the owner had said
  otherwise twelve hours earlier, and the session's entire deliverable came
  from noticing that.
- Predicting the live figure before building the documents, then comparing
  the deployed output against it. USD 58,187.69 matched to the cent, which
  turned "the code runs" into "the number is right".
- Letting 24 failing tests change the design rather than the tests. The
  failures were telling me the feature fired on months it had nothing to say
  about; after the gates, zero pre-existing tests needed touching.

### Suggestions
- The adversarial reviewer earned its cost twice over here (a dead rung no
  test covered), but it read a moving target. Worth a small protocol: commit
  before dispatching the review, and treat the review as reading that SHA.
  It would have caught the same four findings without re-verifying hashes.

### System Health
- **Autonomy: 0 human interventions** — fully autonomous session, from the
  scope correction through deploy and record.
- Sibling contention stayed cheap this round: one append-vs-append conflict
  in `api-contract.md`, resolved main-first, and one version number I got
  wrong because a sibling deployed v178 between my merge and my deploy.
  Reading `flyctl releases` rather than assuming is the habit that caught it.
