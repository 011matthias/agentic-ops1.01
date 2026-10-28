# Checkpoint: Brisken Recon Item 90 Declined And The Eligibility Lesson

**Date:** 2026-09-17
**Status:** p1 defect queue exhausted; every defect-covered backlog item is shipped and live

---

## Summary

The three queued items (103, 115, 130) were merged by sibling sessions while this
one was starting, and owner notes #65-#69 had already been applied to the SPA, so
the session became a verification and decision round: item 90 step 4 was offered
to the owner with measured numbers and declined, and item 139's "applied" status
was re-checked against the live picker rather than taken on report. No code
changed and nothing was written to the live tool.

---

## What Was Done This Session

### Item 90 step 4, offered and declined
1. Read the live state first: `GET /api/settings` holds exactly the two rates
   (`EUR:USD 1.162275`, `BRL:USD 0.192448`), and a read-only DB copy gave the
   per-month picture.
2. Measured the drift against the ECB table stored in the August month rather
   than quoting item 132's headline: EUR:USD +1.80% on July, BRL:USD -1.48%;
   August +0.26% and -0.92%.
3. Put the removal to the owner with its scope of effects and a recommendation.
   Answer: leave both rates. Recorded as declined, not to be re-asked.

### Two corrections to item 90's own text, both from live reads
1. `runs.config` `matching.fx_reference_rates` is present on July and August and
   **null on September, May, June and January**. `apply_master_data` folds
   Settings in with `setdefault`, at month creation and statement attach only
   (`service.py` 406 and 11243; `rematch_month` never calls it), so those four
   existing months take today's typed rates the next time a statement lands. The
   item read as though only future months were exposed.
2. Item 132's drift advisory reads zero on both live months because each stored
   summary predates the code, not because the gap is inside the band: July
   re-matched 16:59:25Z, August 11:35:23Z, v167 shipped 17:28:24Z.

### Items 139-142 re-verified
1. Drove the live SPA read-only four times (only non-GET request in any of them
   was the login) and read the shipped bundle.
2. 141 confirmed on screen: July Matching carries one control per output against
   the five-for-four the item recorded. 140 and 142 confirmed in the bundle.
3. 139 confirmed only after fixing the probe (see Key Decisions).
4. A sibling landed the same four on `main` first with a cold drive in EN and PT.
   Its rows won the merge; only the eligibility lesson was kept.

### One structural fix
`warn-git-exit-masked-by-pipe` widened to catch `$?` after the pipe, not just
`&&`. Tested: both incidents fire, three negatives stay silent.

---

## Key Decisions Made

### Re-check item 139 instead of recording the sibling's report
- **Choice:** Open the card picker on a row the API reports as
  `can_mark_private: true` before recording the item either way.
- **Rationale:** The first read opened whatever row came first, got nine cards
  with no private entry, and looked exactly like a regression. That row was
  ineligible, where nine is the correct rendering after the change as well as
  before, so the probe could not tell the two states apart. On an eligible row
  (July `0003`, `0004`) the picker shows ten options ending "Paid with a private
  card". Recording the first read would have filed a false regression against
  work the owner had already applied.

### Keep main's rows on the merge conflict and drop my own
- **Choice:** Main's headings for 139-142 win; my duplicate evidence paragraphs
  go; only the eligibility lesson survives.
- **Rationale:** The sibling's cold drive in both languages is the stronger
  verification, and two records of one fact is the kind of padding
  `rule_anti_slop` exists to stop.

---

## What Did NOT Work (and why)

- **`spa_drive4.py` (remove overlay nodes, loop every control):** hung with zero
  output for eleven minutes and had to be killed. Python buffers stdout when it
  is not a tty, so nothing showed progress, and removing React-managed nodes
  with `e.remove()` invites a re-render loop. The replacement used `python -u`,
  scoped to two named rows, and only set `pointer-events: none`.
- **Grepping the shipped bundle to locate the private-card control:**
  `expx.privateCard.mark` is in the build whether or not the control moved, and
  the i18n keys resolve at runtime, so no use site appears in the minified
  chunks. String presence cannot answer "where is this control mounted".
- **Opening the card picker on the first row on the page:** that row was
  ineligible, so its nine options were correct either way and the negative meant
  nothing. Eligibility has to come from the API first.
- **`flyctl ssh sftp get` with a POSIX local path:** MSYS rewrote the remote
  `/data/recon-web.sqlite` to `C:/Program Files/Git/data/...`; `MSYS_NO_PATHCONV=1`
  then broke the LOCAL path instead, because flyctl is a Windows binary. The
  working shape is `MSYS_NO_PATHCONV=1` plus a backslash Windows local path.
- **`git merge ... | tail -6` followed by `echo "MERGE_EXIT=$?"`:** reported
  `MERGE_EXIT=0` on a merge that had stopped on a conflict. The pipe's last
  command is what `$?` reads. Caught because the conflict was visible in the
  output above the line.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | Item 90 heading, the decision and the two corrections; item 139's eligibility lesson; item 142's tooltip location |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | Element row for item 90 step 4's decision |
| `.claude/patterns/warn-git-exit-masked-by-pipe.md` | edit | Widened to `$?` after the pipe |

---

## Current Status

Every backlog item tagged `licence: defect, covered` is shipped and live; the
remaining unshipped items are `new function`, `operations`, or owner data. Live
release is Fly v177, backend healthy, nothing processing, `/feedback.jsonl` holds
69 notes with the last one already recorded. PR #1070 merged. No deploy was made
or needed this session: only status files and a pattern rule changed.

brisken platform line from `pre`: unknown plan, `~?/?` ops/mo, last assessed `?`.

---

## Next Steps

1. Wait on new owner or Criss feedback; the defect queue has nothing left in
   licence scope.
2. Item 90 step 4 stays open and owner-gated. Do not re-ask; the four rate-less
   months are the standing exposure if it is never taken.
3. Watch for item 132's advisory to appear on July at its next re-match. It is
   the first live proof of that code and nobody has seen it fire.
4. `/ops-audit brisken` would fill the unknown platform plan line.
5. p2 status files `p2-product-decks.md` (56d) and `p2-targeting.md` (57d) are
   stale; they belong to the lead-gen sessions, not this one.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

### Open Questions
- Does item 132's drift advisory actually render for Criss when it fires? The
  code path has route tests and no live sighting.
- The four rate-less months freeze a stale typed rate on their next statement
  attach. The owner has declined the removal; is a narrower guard wanted, or is
  this accepted?

### Working Notes
- Live drift, measured off the August month's stored ECB table: EUR:USD typed
  1.162275 against 1.141748 (July) and 1.159310 (August); BRL:USD typed 0.192448
  against 0.195341 and 0.194241.
- Band defaults live in `deterministic.py`: `fx_reference_match_pct` 0.03,
  `fx_ecb_match_pct` 0.02. The advisory fires when a typed rate drifts past the
  1% between them.
- Eligible-row ids for a future 139 check: July `0003__rendered-body.pdf`,
  `0004__invoice-IUS25300.pdf`. Fifteen eligible rows on July in total.
- SPA drive recipe that worked: headless `channel="chrome"`, code from
  `context/.env`, 4 s then fill then Enter then 8 s, 12 s after the route load,
  set `pointer-events: none` on the fixed full-screen overlay (it intercepts
  clicks), then `force=True` on the combobox. Run with `python -u`.

### Reference Materials
- PR #1070
- `%TEMP%\claude\recon-probe\api.py` for authenticated GETs

---

## How to Continue

There is no queued defect work. Read `/feedback.jsonl` first; a new note from
Criss outranks anything else. If nothing new has landed, the open items are the
owner-gated ones above.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live system before offering item 90 step 4 turned a ledger summary
  into a correction: the four rate-less months are the real exposure, and the
  offer carried the owner's own numbers rather than a headline figure.
- Refusing to record item 139 on either the sibling's report or my own first
  read. Both were wrong in the same direction, and the tiebreaker was asking the
  API which rows the control is even supposed to appear on.

### Suggestions
- The 139 near-miss has a general shape worth naming: when a control renders
  conditionally, a probe that does not first establish the condition returns a
  confident negative. The instrument-validity clause in `rule_behaviors.md`
  covers filters and endpoints but not conditional UI. One sentence there would
  extend it.

### System Health
- Sibling contention is now the dominant cost on this backlog. Three of four
  queued items were gone before the session read them, and the fourth was
  re-verified twice by two sessions within an hour. A claim marker in the
  backlog heading, written at start rather than at ship, would cut the
  duplication the per-item re-check cannot.
- Autonomy: 1 human intervention (the item 90 step 4 decision, a genuine
  decision point rather than a deferral).
