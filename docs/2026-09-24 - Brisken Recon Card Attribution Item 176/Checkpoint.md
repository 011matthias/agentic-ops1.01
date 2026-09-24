# Checkpoint: Brisken Recon Card Attribution Item 176

**Date:** 2026-09-24
**Status:** Item 176 shipped, deployed and verified live. Items 174, 175 and the doubled label are diagnosed and carried in one unpasted Lovable prompt. Item 185 opened from a note the backlog had not seen. Six PRs merged; nothing in flight.

---

## Summary

`can_mark_private` told every confirmed private row it could still be marked
private; it no longer does, and the route that writes the flag now lets an
already-private row correct who gets reimbursed. Reading the published SPA
bundle, and then driving the live page, answered three separate open
questions that the backlog had recorded as hypotheses, and corrected two of
them.

---

## What Was Done This Session

### Item 176, the fix (PR #1258, merge `43305aea`, deployed)

1. `can_mark_private` is `not private and (...)` in `resolve_batch_row_cards`.
2. `_paid_by_conflict` skips its company-card refusal on a row that is
   already private. Not cosmetic: the private route reads the same flag
   before it writes, so without this a correction of who gets reimbursed
   would have been refused with the wording "this expense was paid with the
   company card", about a row no company card paid.
3. Five route-level tests through `POST .../expenses/{doc}/private` and the
   generic field `PUT`; both wires regress-checked green to red to green.
   Module suite 3176 passed / 2 skipped. One pre-existing assertion flipped
   with the contract and says why inline.

### Verification

4. Live read-only API probe: both private rows in the estate (September 0046
   Luigi Buchholz, July 0028 Brauhaus Kühler Krug) read
   `can_mark_private: false`; all 15 `suggested_private` rows across the
   three months still read true, so the flag was narrowed and not flattened.
5. Cold Chrome drive of September row 0046: the badge and "Undo private card"
   both still render, which was this change's one real risk.

### What the bundle and the drive settled

6. **The doubled label is the Paid Through cell** (PR #1260, merge
   `80dffabb`): two elements in cell index 7 carrying the same value, a
   static `div.px-1.text-sm.text-foreground` and the `span` inside the
   account select's `role="combobox"` trigger. One row in 80 doubles.
7. **Item 174 is answered without a drive**: "From email" is
   `months.origin.intake` on the months list, off `created_by`, rendered in
   the statement badge's own cell.
8. **Item 175 has a harder half than option ordering**: the `reimburse_to`
   dialog is rendered inside the card picker, which returns `null` once
   `row.private` is true, so there is no way in the SPA to correct who gets
   reimbursed short of undoing the private mark.
9. All three land in `docs/lovable-private-reimburse-prompt.md` (not pasted),
   with a PROMPT-STATUS row.

### The feedback store

10. The app held **86 notes** against the backlog's 82. #83, #84 and #85 are
    category / GL-account and belong to the other session. **#86** (owner,
    `/months`) was unitemized and is card-attribution: a card-first status
    view across months. Recorded as **item 185** (PR #1264, merge
    `67555199`) with a live scoping pass.
11. **Item 108 corrected in the same PR.** It said cards 9693 and 1176 have
    never had a statement loaded. 1176 has one.

---

## Key Decisions Made

### Ship item 176 even though it changes nothing on screen

- **Choice:** ship the predicate fix despite proving it is invisible today.
- **Rationale:** the helper it feeds is the screen's whole answer to "may I
  offer the private control here", it answered yes on a row that is already
  private, and item 175 adds a private control to exactly that area. Fixing
  the contract before building on it is the cheap order.

### Correct the item's stated cause in the same PR rather than quietly fixing it

- **Choice:** record in the backlog, the commit and the PR that the filed
  diagnosis was wrong, with the evidence.
- **Rationale:** the next session would otherwise have inherited a shipped
  fix plus a false explanation, and would have looked for the duplicate in
  the wrong place.

### Do not build item 185 in this session

- **Choice:** scope and record it, raise the commercial question, stop.
- **Rationale:** it is a new surface rather than a defect fix, so it falls
  outside the licence's defect-class scope and is the owner's call before
  any code.

---

## What Did NOT Work (and why)

- **Item 176's filed diagnosis, that `can_mark_private` renders the doubled
  label.** The SPA reads it in one helper whose two callers already escape a
  private row for other reasons (the suggestion chip also needs
  `suggested_private`, false there; the card picker opens with
  `if (row.private) return null`), so the flip changes nothing on screen.
  Correct fix, wrong stated cause.
- **The first bundle scan, which reported the field absent from every
  chunk.** The probe was validated (it found `suggested_private` and
  `reimburse_to`) but the CORPUS was not: chunk names were harvested with
  `chunk-[A-Za-z0-9_-]*\.js`, which cannot match
  `chunk-expenses._batchId-7cO7KDYP.js` because of the dot, so the one file
  holding the grid was never downloaded.
- **`card_source` as item 174's cause.** That field never produces the
  string; "From email" appears exactly once in the whole bundle.
- **Item 108's claim that card 1176 has never had a statement.** August holds
  `20260804-statements-1176-.pdf` and the card reads `n_tx: 3`,
  `n_unmatched_tx: 1`.
- **A 90-line `cat >> ... <<'OUTER'` heredoc** to append the continuation
  prompt: blocked at the shell-parse level, same rule as the Python
  triple-quote case, which was already written down in the prompt I was
  handed.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/service.py` | edit | `can_mark_private` predicate + its contract prose |
| `src/expense_recon/web/app.py` | edit | `_paid_by_conflict` skips an already-private row |
| `tests/test_private_not_reoffered_item_176.py` | add | five route-level tests |
| `tests/test_private_expense.py` | edit | one assertion flipped with the contract |
| `docs/lovable-private-reimburse-prompt.md` | add | items 175, 174, Paid Through duplicate |
| `docs/PROMPT-STATUS.md` | edit | its Not-applied row |
| `status/p1-improvement-backlog.md` | edit | items 176, 175, 174, 108 corrected; 185 added |
| `status/p1-expense-reconciliation.md` | edit | workstream roll-up |

---

## Current Status

Fly `brisken-expense-recon` serves merge SHA `43305aea`. September
`51a22ad72864`, August `074a7b8905d7`, July `50622baec444`; nothing was
written to Criss's months, because the flag is derived at read time in
`build_expense_view` and needed no re-match. Six PRs merged (#1258, #1260,
#1261, #1262, #1264, #1265); no branch or worktree of this session is left
open. brisken platform ops status: unknown plan, `~?/?` ops/mo, last
assessed unknown. comms-log 16 days stale.

---

## Next Steps

1. **Item 185**, the card-first status view, is the one real build left in
   this area. Raise the quote-separately question with the owner first: it
   is a new surface, not a defect fix.
2. **Item 108, the 1176 half**: find why August's 1176 statement is attached
   to the unattributed `?` coverage row instead of `card-1176`. Card 9693 is
   the real remaining gap and does need a statement that does not exist.
3. Hand the owner `docs/lovable-private-reimburse-prompt.md`.
4. Run `/ops-audit brisken`: `infrastructure.yaml` has no plan, no ops
   figure and no assessment date for the platform.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 108,
  174, 175, 176, 185)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-private-reimburse-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`resolve_batch_row_cards`)

### Open Questions
- Is item 185 in scope under the EUR 600 licence, or quoted separately?
- Should the Lovable prompt be pasted now or batched with the other
  unpasted ones?
- 16 days of Brisken conversations are unlogged.

### Working Notes

**Reading the SPA without a browser is the cheap instrument** and settled
three of this session's four findings. Fetch `https://expenses.brisken.com/`,
harvest asset names with a pattern that ALLOWS DOTS (the grid chunk is
`chunk-expenses._batchId-<hash>.js`), download every chunk, grep with
`grep -o ... | wc -l` because minified JS is one line and `grep -c` always
answers 1. Then validate the corpus, not just the probe, by requiring a field
the page must read.

The private controls in the published bundle:
`Zt(row) = typeof row.can_mark_private === "boolean" ? row.can_mark_private : row.card == null`,
two callers (the suggestion chip, and the card picker's
`__private_card__` option). The private row's own render is
`expx.private.badge` + `expx.reimburse.undo`, neither gated on the flag.

`coverage[]` per card per month already carries `card_key`, `label`, `known`,
`digits`, `entity`, `n_transactions`, `n_reconciled`, `n_unmatched_tx`,
`n_review`, `n_refunds`, `period_start`, `period_end`, `statements`,
`statement_ids`, `unreconciled_by_ccy`. Only 3 of 7 batches carry any
(April 10, August 10, July 9).

### Reference Materials
- Live SPA: `https://expenses.brisken.com` (Fly origin serves the API only)
- Feedback store: `GET /feedback.jsonl`, text field is `comment`

---

## How to Continue

`/comd_resume brisken`, then the continuation prompt appended to
`docs/2026-09-24 - Brisken Recon Private Control And Paid Through/Mini-Checkpoint-1.md`.
Nothing is half-finished; start at item 185 with the owner's answer on scope,
or at item 108's 1176 link if that answer has not come.

---

## Strategic Feedback

### What Worked Well This Session

- **Reading the deployed bundle instead of guessing at the SPA.** Three
  backlog hypotheses were settled for roughly the cost of one browser drive,
  and two of them were wrong. The backlog had been carrying `card_source` as
  item 174's likely cause and "cause unidentified" for the doubled label;
  both took minutes once the right file was in hand.
- **Driving the consumer found what neither the code nor the bundle would
  have.** The doubled label is two sibling elements with the same text. No
  amount of reading `service.py` would have produced it.

### Suggestions

- **Validate the corpus, not just the probe.** The B2 instrument-validity
  rule says to prove a probe on a state you already know, and I did: the
  scan found `suggested_private` and `reimburse_to`, so the grep worked. It
  still returned a confident, wrong absence, because the file that mattered
  was never in the corpus. The missing half of the rule is a completeness
  check: name a thing the corpus MUST contain (here, `document_id`, which
  sat alone in one unrelated chunk and was the tell) and refuse the negative
  until it does. Worth folding into the instrument-validity sub-clause as a
  third shape alongside "empty by design" and "silently ignored filter".

### System Health

- **Autonomy: 1 human intervention** (a `checkpoint` directive; no
  corrections to the work). Gates B1:0 B2:6 B3:1 B4:4, skipped:0 — the
  instrument lapse above fired B2 late rather than never, and was
  self-caught before it reached a deliverable.
- **The ship gate scans heredoc bodies.** Appending a continuation prompt
  that documents `gh pr merge` raised a `gate-fired-red-merge` candidate on
  a `cat >>` command. Harmless, but every session that writes a continuation
  prompt will trip it, so the candidate list will keep carrying a false
  positive until the gate distinguishes a command from a quoted document.
- **Two p2 status files are stale** (`p2-product-decks.md` 63d,
  `p2-targeting.md` 64d). Left untouched deliberately: this session has no
  knowledge of that workstream, and a fabricated `updated:` bump is worse
  than a visible staleness flag.
