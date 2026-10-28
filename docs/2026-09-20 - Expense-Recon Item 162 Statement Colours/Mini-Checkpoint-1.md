# Mini-Checkpoint: Expense-Recon Item 162 Statement Colours

**Date:** 2026-09-20
**Status:** Shipped and deployed (PR #1151, merge `8e1b826c`, Fly v194). SPA half pending the owner's paste.
**Type:** mini

---

## Summary

One-item session on the owner's directive: *"dont attribute colors in the
statements or receipts any deeper meaning, all i need you to be able to do, is
get the classifier to read all these colors and more."* The statement reader
now names every fill it can read and still infers meaning from exactly two of
them. Zero live verdicts moved, measured rather than argued.

## What Was Done

- **`colour_family(r, g, b)`**, total over the RGB cube, returns one of twelve
  stable names (`white` `gray` `black` `red` `orange` `yellow` `olive` `green`
  `cyan` `blue` `purple` `pink`) from HSV hue bands, replacing the ad-hoc RGB
  inequalities. **`_FAMILY_ENTRY_STATUS`** maps only `yellow -> posted` and
  `gray -> subscription` and is the whole of the meaning; a newly named family
  is recorded and votes on nothing, which is what makes the widening safe by
  construction rather than by luck.
- **`rows[].fills[]`** carries `{column, index, hex, family}` per coloured
  cell, over EVERY column rather than only the mapped ones, because seeing is
  not voting. `entry_status`, its vote, its tie-break and its five consumers
  are untouched.
- 58 tests, six wiring points proven RED by hand with sha256-equal restores,
  `rows[].fills[]` pinned in `test_view_contract.py` and added to
  `RUN_MUST_COVER` with the fixture populating it. Suite 2651 -> 2709 passed /
  2 skipped (base measured by deselection, not arithmetic). Ruff clean.

**Three things the in-machine census settled that the item's brief had not.**
The colours are a **per-column** scheme with **three** channels, not row
highlighting: `Card` carries orange/blue/mid-gray, `Description` the light
gray, `Amount` the yellow. That decomposes July's live 85/27 split exactly
into 44 yellow-only + 41 tie-broken + 27 gray-majority, which is how the model
was confirmed rather than assumed. `_fill_rgb` is **not** hiding colours behind
unknown theme slots (every index either workbook uses is mapped and the counts
reconcile) — the brief flagged it as a suspect and it is not one. And the live
fills are mostly **theme**-typed, not rgb-typed (July: 190 vs 119), so an
rgb-only fixture would pass while exercising a path the data never takes; the
test asserts which path ran first.

## What Did NOT Work (and why)

- **Separating the yellow/orange boundary by hue alone:** `FFE699` (pinned
  `posted`) is hue 45.3 and `FFC000` (pinned not-posted) is 45.2 — the same
  theme colour two tints apart. Hue cannot split them; saturation does (0.40
  vs 1.00), which is what the amber carve-out uses.
- **Driving the dangerous divergence direction to zero by raising the yellow
  value floor:** swept 636,056 colours at floors 180-250. The residue only
  shrinks (650 -> 50) and shifts to lighter creams, never reaching zero. It is
  a one-unit artefact of the old `b <= min(r,g) - 40` cut, which admitted
  `FFFFCC` and excluded `FCF0C9` — the same cream. Kept the floor at 180 (the
  old `r >= 180`) and enumerated the divergence in the PR instead.
- **`page.fill()` on the SPA gate's access-code input:** the React controlled
  input never registered the value, so "Log in" stayed `disabled` and the drive
  timed out at 90s. `press_sequentially` with a per-character delay works.
- **`session_state.py --status` for context pressure:** printed a sibling
  (`6a59e831`, 492k) rather than this session. The real figure (384k) came from
  this session's own transcript `usage` record.

## Current Status

Deployed **Fly v194** and verified **in-machine**, which is the only instrument
that can answer here: a statement is parsed at UPLOAD, so a correct deploy
looks like a no-op on the live payloads. The deployed code names all eight live
hexes correctly, 225 rows carry at least one named fill, and **0 of 452 filled
cells change verdict**. Live July is unchanged at 112 rows / 85 `posted` / 27
`subscription`; August 114 / 1 / 45. `fills` is absent on both live months by
design. Cold Playwright drives of September and July's workbench render with no
error boundary and only the login writes.

A near-miss worth recording: the first staging produced a **530-line phantom
diff** on `p1-expense-reconciliation.md`, a whole-file line-ending flip hiding a
one-row append. `core.autocrlf` normalised every other touched file but not
that one. Caught before the commit and reduced to a 1-line diff; it would have
conflicted with every sibling touching that file.

## Next Steps

1. **Owner:** paste `docs/lovable-statement-colour-prompt.md` into Lovable,
   then re-run `tools/lovable-bundle-audit.py`. Two other prompts are also
   unpasted: `lovable-merchant-profile-prompt.md`,
   `lovable-chase-section-label-prompt.md`.
2. **Owner decision, not taken here:** the 1-1 tie-break. 41 of July's 112 rows
   (37%) read "already booked" because a yellow `Amount` and a gray
   `Description` tie and the tie resolves to `posted`. Changing it flips a third
   of the month and contradicts the shipped gray-recurring ruling (PR #1020).
3. **Criss:** July and August gain `rows[].fills` only when those months are
   next read. No agent-triggered re-read
   (`feedback_recon_no_live_writes_criss_acts`).
4. Two p2 status files are stale (`p2-product-decks` 59d, `p2-targeting` 60d).
   Not this workstream; left to their owner.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_xlsx.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (the item-162 section)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-statement-colour-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 162, Shipped row 109)
