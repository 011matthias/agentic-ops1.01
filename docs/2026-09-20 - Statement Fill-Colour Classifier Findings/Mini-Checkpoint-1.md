# Mini-Checkpoint: Statement Fill-Colour Classifier Findings

**Date:** 2026-09-20
**Status:** Investigation complete, item 162 specified and prompted, no code written.
**Type:** mini

---

## Summary

Feedback note #69 asked, of the hint "This charge is marked yellow in your
statement workbook, so it is already booked", **"where do you get this
information from?"** The answer is the fill colour of cells in the operator's
own uploaded workbook. Measuring what that reader actually sees turned up a
gap the note did not name, and the owner then ruled the shape of the fix.

---

## What Was Done

### The trace
- The chain, all in `ingest/statement_xlsx.py`: `_fill_rgb` (146) takes the
  solid fill with the OOXML tint formula; `_classify_rgb` (121) buckets it
  (**yellow -> `posted`**: `r >= 180` and `g >= 0.8r` and `b <= min(r,g) - 40`;
  **gray -> `subscription`**: spread `<= 24`, mean 110-224); `_row_entry_status`
  (196) takes a majority over the MAPPED columns and **breaks a tie toward
  `posted`**; `posted` becomes `ALREADY_BOOKED` (`unmatched_reasons.py:65`) and
  closes the receipt requirement (`service.py:8051`).

### The census (live, in-machine, read-only, `/data/runs/50622baec444/July2026.xlsx`)

| Fill | Cells | Reader's verdict |
|---|---|---|
| `#FFFF00` yellow | 118 | `posted` |
| `#D9D9D9` light gray | 68 | `subscription` |
| `#F4B183` orange | 48 | **nothing** |
| `#B4C7E7` blue | 45 | **nothing** (9 are the header row) |
| `#ADADAD` mid gray | 27 | `subscription` |
| `#C9C9C9` gray | 1 | `subscription` |
| `#FFFFCC` cream | 1 | `posted` |
| `#C6DEB5` green | 1 | **nothing** |
| no fill | 708 | - |

- Joined to the live payload on `rows[].source_row` (item 152, shipped
  2026-09-18): **84 of 112 rows carry a colour the reader ignores** (48 orange,
  35 blue, 1 blue+green), and every one still resolves to `posted` from a
  yellow cell elsewhere in the same row. **Zero rows** depend solely on an
  unreadable colour, so nothing is currently unclassified.
- How each row got its verdict: 44 yellow majority, 27 gray majority, **41 from
  a 1-1 TIE resolved to `posted` by rule**, 0 unclassified. That is 37% of the
  month reading "already booked" from a coin-flip the screen does not mention.
- Each data row carries exactly ONE orange or blue cell, which reads like a
  per-COLUMN scheme rather than whole-row highlighting. Not confirmed visually.

### The owner's ruling and the prompt
- Owner, 2026-09-20: *"dont attribute colors in the statements or receipts any
  deeper meaning, all i need you to be able to do, is get the classifier to read
  all these colors and more."*
- Continuation prompt for **backlog item 162** handed in chat: hue-based
  classification so every shade is caught and every family named; record the
  observed fill on the row as a parallel field; tell "coloured but unnamed"
  apart from "not coloured"; and **new families are RECORDED but do NOT vote**,
  which is what makes "no live verdict moves" true by construction rather than
  by luck, and is the literal reading of the directive. The tie-break is
  explicitly out of scope.
- `docs/lovable-operator-note-prompt.md` (item 155) re-handed verbatim from
  `main`, with the correction that its own Verify section overstates: existing
  rows will show nothing, because provenance is frozen at ingest.

---

## What Did NOT Work (and why)

- **Answering note #69 from the code alone:** the code says yellow means
  posted, which is true and useless. The question was about the SOURCE, and
  that is the operator's own formatting. Only reading the stored xlsx showed
  five more colours in use and 84 of 112 rows carrying one the reader ignores.
- **Treating "every July row has an entry_status" as evidence the reader
  works:** all 112 classify, so the output looks complete. The join to the
  sheet shows 84 of those verdicts came from a different cell than the one the
  operator coloured. A complete-looking output hid an incomplete input.
- **Reading item 142 as having closed note #69:** it is marked SPA APPLIED +
  VERIFIED, but it only reshaped the hint's wording to name the workbook and
  the rule. The question was never answered and the gap behind it never looked
  at.

---

## Current Status

No code changed. Item 155 remains live on Fly v191 with its SPA prompt unpasted.
brisken platform: unknown plan, last assessed unknown. Item 162 is specified in
a chat prompt only; its backlog number is claimed by whoever builds it, after a
merge from main (161 was the highest on 2026-09-20).

---

## Next Steps

1. Build item 162 from the handed prompt: read every colour, record it, let
   only the two existing families vote.
2. Owner: paste `docs/lovable-operator-note-prompt.md`.
3. Owner decision: what orange and blue mean in the July workbook.
4. Owner decision: the 1-1 tie-break, which sends 41 of 112 July rows to
   `posted`. Out of item 162's scope on purpose; changing it contradicts the
   gray-recurring ruling (PR #1020) and moves a third of the month.

---

## Files to Read First

- `.../src/expense_recon/ingest/statement_xlsx.py` (lines 105-110 thresholds,
  121 `_classify_rgb`, 146 `_fill_rgb`, 196 `_row_entry_status`, 439 call site)
- `.../src/expense_recon/unmatched_reasons.py` (line 65, `ALREADY_BOOKED`)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 142, the
  note-#69 copy fix that did not touch this)
- `docs/2026-09-20 - Expense-Recon Item 155 Close-Out/Checkpoint.md`
