# Checkpoint: Expense-Recon Item 162 Statement Colours

**Date:** 2026-09-20
**Status:** Shipped and live (PR #1151, merge `8e1b826c`, Fly v194). SPA half and one owner decision outstanding.

---

## Summary

One-item session on the owner's directive: *"dont attribute colors in the
statements or receipts any deeper meaning, all i need you to be able to do, is
get the classifier to read all these colors and more."* The statement reader
now names every fill it can read and still infers meaning from exactly two.
Full checkpoint over the same session the mini (PR #1154) covered, adding the
friction audit, gate compliance and strategic feedback mini mode skips.

---

## What Was Done This Session

### The classifier
1. `colour_family(r, g, b)` is total over the RGB cube and returns one of
   twelve stable names (`white` `gray` `black` `red` `orange` `yellow` `olive`
   `green` `cyan` `blue` `purple` `pink`) from HSV hue bands, replacing the
   ad-hoc RGB inequalities it grew out of.
2. `_FAMILY_ENTRY_STATUS` maps only `yellow -> posted` and
   `gray -> subscription`. A newly named family is recorded and votes on
   nothing, so the widening is safe by construction rather than by luck.
3. `rows[].fills[]` carries `{column, index, hex, family}` per coloured cell
   over EVERY column, not only the mapped ones. `entry_status`, its vote, its
   tie-break and its five consumers are untouched.

### Evidence
4. In-machine census of both live workbooks, read-only, before any code
   changed. Three things it settled that the item's brief had not: the colours
   are a **per-column scheme with three channels** (`Card` orange/blue/mid-gray,
   `Description` gray, `Amount` yellow), which decomposes July's live 85/27
   split exactly into 44 yellow-only + 41 tie-broken + 27 gray-majority;
   `_fill_rgb` is **not** hiding colours behind unknown theme slots, so the
   brief's named suspect is clean; and the live fills are mostly **theme**-typed
   (July 190 vs 119 rgb), so an rgb-only fixture would pass while exercising a
   path the data never takes.
5. Whole-cube divergence sweep (636,056 colours at step 3) in both directions,
   enumerated in the PR rather than left implicit.

### Verification
6. 58 tests; six wiring points proven RED by hand, each anchor asserted to sit
   in its expected `def` first, each file restored sha256-equal. Suite
   2651 -> 2709 passed / 2 skipped, base measured by deselection. Ruff clean.
7. Deployed Fly v194 and verified **in-machine**, the only instrument that can
   answer here. Cold Playwright drives of September and July's workbench.

### System
8. `.claude/patterns/warn-tail-task-output-file.md`, from the third occurrence
   of a polling slow-path whose `documented` fix had already failed twice.

---

## Key Decisions Made

### One classifier, families decide verdicts
- **Choice:** a single `colour_family` whose output a frozen two-entry map
  turns into a verdict, rather than keeping the old predicate as the verdict
  test and bolting naming beside it.
- **Rationale:** two overlapping colour taxonomies drift, and the alternative
  produces rows that display "green" while behaving as `posted` — incoherent
  exactly where the SPA would surface it.

### The amber carve-out is saturation, not hue
- **Choice:** hue 45-52 at saturation >= 0.72 is `orange`, not `yellow`.
- **Rationale:** `FFC000` (pinned not-posted) and `FFE699` (pinned posted) are
  the same theme colour two tints apart, at hue 45.2 and 45.3. Hue cannot
  separate them; saturation (1.00 vs 0.40) can, and that is also what
  separates gold from a pale highlight perceptually, so the rule is not
  back-fitted to the test.

### Record every column, vote on the mapped ones
- **Choice:** `fills` covers unmapped columns too; the verdict does not.
- **Rationale:** July's `Memo` column carries a gray and a green the
  mapped-column scan never reached. Seeing is not voting, and the directive is
  about seeing.

### The tie-break was left alone
- **Choice:** not touched, and said so in the PR and the backlog.
- **Rationale:** 41 of July's 112 rows (37%) read "already booked" from a 1-1
  tie. Changing it flips a third of a month and contradicts the shipped
  gray-recurring ruling (PR #1020). That is an owner call, not a build call.

---

## What Did NOT Work (and why)

- **Separating the yellow/orange boundary by hue alone:** `FFE699` is hue 45.3
  and `FFC000` is 45.2. Hue cannot split them; saturation does.
- **Driving the dangerous divergence direction to zero by raising the yellow
  value floor:** swept floors 180-250 over 636,056 colours. The residue only
  shrinks (650 -> 50) and shifts to lighter creams, never reaching zero. It is
  a one-unit artefact of the old `b <= min(r,g) - 40` cut, which admitted
  `FFFFCC` and excluded `FCF0C9` — the same cream.
- **`page.fill()` on the SPA gate's access-code input:** the React controlled
  input never registered the value, the Log in button stayed `disabled`, the
  drive timed out at 90s. `press_sequentially` with a delay works.
- **`session_state.py --status` for this session's pressure:** printed a
  sibling (`6a59e831`, 492k) while this session sat at 384k.
- **The first EOL probe:** `git show` with `rev=":"` produced `::path`, so
  every lookup failed and it reported `staged_cr=-1` for all eleven files and
  `nothing to fix` — while one file carried a real 530-line CRLF flip.
- **Spawning the rule-miner agent:** the digest holds no user corrections at
  all, so there was nothing to mine.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../ingest/statement_xlsx.py` | edit | `colour_family`, `_hue`, `_FAMILY_ENTRY_STATUS`, `_row_fills`, theme slots 10/11 |
| `.../matching/types.py` | edit | `CellFill` frozen dataclass; `fills` on `Transaction` |
| `.../web/serialize.py` | edit | `fills` to/from the snapshot, tolerant of its absence |
| `.../web/service.py` | edit | `fills` onto `rows[]`; `_fills_view` helper |
| `.../tests/test_statement_fill_colours_item_162.py` | add | 58 tests |
| `.../tests/test_view_contract.py` | edit | `rows[].fills[]` pinned + `RUN_MUST_COVER` + fixture |
| `.../docs/api-contract.md` | edit | the item-162 section + element-table row |
| `.../docs/lovable-statement-colour-prompt.md` | add | SPA half (not applied) |
| `.../docs/PROMPT-STATUS.md` | edit | Not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 162 + Shipped row 109 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | element row |
| `.claude/patterns/warn-tail-task-output-file.md` | add | the polling slow-path, third occurrence |

---

## Current Status

Live on **Fly v194**. **0 of 452 live filled cells change verdict**, proven by
running both classifiers over every cell of both stored workbooks. 225 rows now
carry a named fill. July unchanged at 112 rows / 85 `posted` / 27
`subscription`; August 114 / 1 / 45. `fills` is absent on both live months by
design — a statement is parsed at UPLOAD, so a correct deploy looks like a
no-op on the live payloads, which is why the deploy was verified in-machine.

Ops status: `brisken` platform reads *unknown plan, ~?/? ops/mo, last assessed
?* — p1 is a self-hosted FastAPI app on Fly, not an orchestrator tenant, so the
`infrastructure.yaml` platform block does not describe it.

Feedback store: 72 notes, #72 already closed as item 161. No new notes.

---

## Next Steps

1. **Owner:** paste `docs/lovable-statement-colour-prompt.md` into Lovable,
   then re-run `tools/lovable-bundle-audit.py`. Two others are also unpasted:
   `lovable-merchant-profile-prompt.md`, `lovable-chase-section-label-prompt.md`.
2. **Owner decision:** the 1-1 tie-break (above). Not taken here.
3. **Criss:** July and August gain `rows[].fills` only when those months are
   next read. No agent-triggered re-read.
4. `p2-product-decks` (59d) and `p2-targeting` (60d) are stale. Not this
   workstream; left to their owner.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/statement_xlsx.py`
- `.../docs/api-contract.md` (the item-162 section)
- `.../docs/lovable-statement-colour-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 162, Shipped row 109)

### Open Questions
- Does the `Card` column's orange/blue/mid-gray mean anything to Criss? The
  tool now records it and deliberately concludes nothing. Ask her; do not infer.
- Should the SPA ever tint a row by its fill? The prompt says swatches only,
  because tinting re-attaches the meaning the directive removes.
- Is a whole-file line-ending flip worth a hook? `write-shrink-gate.py` sees
  shrink, not an EOL rewrite.

### Working Notes
- The verdict model, fully decomposed and confirmed against live: July's 112
  rows are 44 with a yellow `Amount` alone (`posted`), 27 with yellow + gray
  `Description` + mid-gray `Card` (2-1, `subscription`), 41 with yellow + gray
  `Description` (1-1, tie-broken to `posted`).
- Live census, both months: `FFFF00` 118/7, `D9D9D9` 68/16, `F4B183` 48/37,
  `B4C7E7` 45/43, `ADADAD` 27/40, `C9C9C9` 1/0, `FFFFCC` 1/0, `C6DEB5` 1/0.
- `flyctl` still answers "no access token available" while the token in
  `~/.fly/config.yml` is valid; read it out and pass `FLY_API_TOKEN`.
- The SPA gate is `#code` (password input) plus a submit button that stays
  `disabled` until React sees a real keystroke sequence.

### Reference Materials
- PR #1151 (code), #1154 (mini ledger), this PR (full ledger)
- `docs/2026-09-20 - Expense-Recon Item 162 Statement Colours/Mini-Checkpoint-1.md`

---

## How to Continue

Nothing here is blocked on an agent. The backend is live and verified; what
remains is the owner's paste, the owner's tie-break decision, and Criss's own
re-read of her months. A next session picking up p1 should read the live
`/feedback.jsonl` first (72 notes as of this checkpoint) and diff the count
before trusting "no new feedback".

---

## Strategic Feedback

### What Worked Well This Session
- **Measuring the premises before building.** The in-machine census overturned
  two of the brief's stated premises (the theme-slot suspect was clean; the
  fills are theme-typed not rgb-typed) and settled the per-column structure the
  brief had guessed at. Both changed the design. Ninety minutes of reading
  before the first edit was the cheapest part of the session.
- **Proving the safety claim as a property, not a list.** "No verdict moves"
  is asserted over the whole RGB cube in a test and measured cell-by-cell over
  the real workbooks, rather than spot-checked against the eight live hexes.
  The whole-cube sweep is also what surfaced the two divergence classes that
  went into the PR instead of staying invisible.

### Suggestions
- **A line-ending guard.** The 530-line phantom diff was caught by reading
  `--stat`, which is discipline, not a gate. `write-shrink-gate.py` already
  watches Write for material shrink; an EOL-flip check on the staged blob
  (staged CR count vs HEAD's) is the same shape and would have caught it
  deterministically. Worth building the next time a session touches that hook.

### System Health
- **Autonomy: 0 corrections** (two directives: the task, then "checkpoint") —
  fully autonomous session.
- The register's recurring theme is now unmistakable: three `verification-theater`
  rows in three days, all the same shape — a probe that is structurally blind
  returns a confident negative and nearly grounds a claim. This session added a
  fourth. The instrument-validity sub-clause exists and is being honoured
  (each was caught), but always by a human-shaped implausibility check
  ("-1 for EVERY file?"), never by the probe. The transferable move is to make
  probes assert their own reachability — a probe that cannot distinguish
  "absent" from "I could not look" should fail loudly rather than return a
  negative.
