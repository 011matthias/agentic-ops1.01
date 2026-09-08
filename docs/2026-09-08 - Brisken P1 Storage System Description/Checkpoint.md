# Checkpoint: Brisken P1 Storage System Description

**Date:** 2026-09-08
**Status:** Item 48 G7 closed (PR #733). Round 1's storage verdicts corrected. Backlog item 49 opened. All merged, all worktrees removed.

---

## Summary

Wrote the examiner-facing electronic-storage-system description Rev. Proc.
97-22 4.01(5) requires, and in doing so discovered that this morning's
criteria matrix graded three storage criteria Satisfied on a code path that
does not run in the deployed system. The correction is the more important
half of the session.

---

## What Was Done This Session (second half)

### Owner answers recorded (PR #725)

1. US filing applies to at least one entity, so the criteria bind. Business
   purpose is captured per merchant, learned once. Both recorded with the
   rejected alternatives and their reasons, so the decision is not
   re-litigated.

### The correction (PR #733)

2. A six-agent audit of the deployed code paths found that `ReceiptStore`,
   the content-addressed store whose SHA-256 addressing I cited as the basis
   for D1/D2/D5 "Satisfied", is instantiated only in `cli.py` behind an
   optional `hosting:` config block. Nothing under `web/` imports it. I
   verified this myself before acting rather than taking the agent's word.
3. The deployed upload paths compute a truncated SHA-1 for de-duplication
   and discard it, so no digest survives and nothing in the running system
   can detect that a stored receipt changed. `extracted_receipts`, the
   second leg of the D2 grade, has one writer on the statement-attach path
   and silently returns current values elsewhere.
4. D2 and D3 moved Satisfied to Missing; D1, D5, D6, D7, D9 downgraded; A3
   split; D12 (4.01(7)) and D13 (4.01(9)) added; G2b, G3b, G4b, G12 added to
   the gap list, with G2b promoted to lead beside G1. All 15 gap anchors
   verified to resolve.

### The G7 deliverable (PR #733)

5. `docs/electronic-storage-system-description.md`, 914 lines: a section per
   lifecycle stage, a paragraph-by-paragraph status table, and a disclosed
   20-item non-compliance register. Draft pending owner and CPA review.
6. Eight reviewers then tried to refute it, defaulting to "refuted" when
   uncertain, with an adjudicator told to be as skeptical of the skeptics as
   they were of the document. 97 challenges, 53 confirmed, 7 rejected as
   misreadings. Five were flat false statements in my first draft. All 53
   applied; the file is revision 2 and states the size of its own
   correction.

### Backlog item 49 (PR #733)

7. Correctness defects the audit surfaced that have nothing to do with US
   law, filed separately so they are not buried in a compliance document.

### Infrastructure facts gathered directly (read-only)

8. One machine, one region, one 1 GB volume, encrypted at rest, scheduled
   snapshots with 5-day retention. Confirmed the hosted app writes no run
   log: `runlog.py` is imported only by `cli.py` and `runlog_cli.py`.

---

## Key Decisions Made

### The correction leads the commit, the PR and the chat message

- **Choice:** Present the error before the deliverable, in all three places.
- **Rationale:** I had told the owner a false thing in chat that morning
  ("storing each receipt at the hash of its own bytes means an altered
  receipt is detectable"). Burying the correction under a new deliverable
  would have left that standing.

### G2b leads beside G1 rather than replacing it

- **Choice:** Two co-leaders, with the reasoning, instead of a forced rank.
- **Rationale:** G1 is the more certain harm on a defined set of expenses;
  G2b is broader because it goes to whether the records qualify as records
  at all. Forcing an order would be false precision, so the file says which
  to fix first under which objective.

### The description discloses rather than omits

- **Choice:** A 20-item non-compliance register inside a document written to
  be handed to the IRS, and an explicit statement that originals may not yet
  be destroyed.
- **Rationale:** 4.01(5) requires a COMPLETE description. An omission is a
  defect and an overstatement is a false statement to the Service, so the
  drafting rule was: describe what the code does, not what it was designed
  to do. That rule is also what made the eight-reviewer pass necessary.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/docs/electronic-storage-system-description.md` | created | The 4.01(5) description, revision 2 |
| `automations/expense-reconciliation/docs/us-substantiation-criteria.md` | corrected | Revision 2: D-section correction note, 7 rows re-graded, D12/D13, 4 new gaps, owner answers, G7 closed |
| `status/p1-improvement-backlog.md` | edited (items 48, 49) | Round-1 correction recorded; item 49 opened |

---

## Current Status

Three PRs merged today on green CI (#722 research round, #723 checkpoint,
#725 owner answers, #733 description + correction). All worktrees removed;
none of mine remain. The tool is untouched: no backend code, no report
change, no deploy, no writes to the live app.

Six p2 status files remain stale (47 to 79 days). Deliberately not touched:
p2 is lead-gen and editing them from a p1 session would put lead-gen edits
on a p1 branch.

---

## Next Steps

1. **Owner + CPA read the description.** Two blanks to fill before it can go
   anywhere: which entities file US, and the deployed access-code
   configuration. Three statements about the revenue procedure's own text
   (4.02(2), the section 7 deletion limb, section 3.03) need CPA
   confirmation because they cannot be established from code.
2. **Ask Criss whether anyone is binning paper.** Section 7's conditions are
   not met, so the answer changes urgency materially.
3. **Item 49's two worth doing regardless:** the float-summed report totals
   that silently drop an unparseable row, and the two paths that rewrite the
   period record without the batch lock.
4. **Item 48 round 2** when the owner picks: five rendering-only changes as
   one round, business-purpose capture as a separate round.
5. Retention period decision, which gates the G2 remediation.

---

## Context for Next Session

### Files to Read First

- `automations/expense-reconciliation/docs/electronic-storage-system-description.md`
- `automations/expense-reconciliation/docs/us-substantiation-criteria.md` (the section 4D correction note first)
- `status/p1-improvement-backlog.md` items 48 and 49

### Open Questions

- Which entities file US (scopes the criteria, does not decide applicability).
- Retention period, and whether deleting a period should be blocked or recorded.
- Whether anyone is already discarding paper.
- Business gifts through these cards (closes G10 if no).

### Working Notes

**The error to not repeat.** A module docstring describes what a module
does, not whether anything calls it. Before crediting a system with a
component's properties, grep for the import from the DEPLOYED entry point.
`hosting/store.py` describes its content addressing accurately and is dead
code in production; `runlog.py` is the same shape.

**Adversarial verification paid for itself twice.** The map fan-out caught
the ReceiptStore error in work I had already merged. The refute fan-out
caught five false statements in a document I had written to be careful.
Both defaulted to "refuted" when uncertain, which produces false positives
on purpose; the adjudicator rejected 7 of 97, which is the trade working as
intended. For a document whose failure mode is a false statement to a
regulator, this is the right shape and worth the cost.

**Research routes that worked** (unchanged from the morning checkpoint):
eCFR 302-blocks automated fetch, Cornell LII serves the same sections; IRS
PDFs come back as raw structure from WebFetch but the bytes are saved and
`pypdf` extracts them; Pub. 463's Table 5-1 never fetches cleanly, use
1.274-5T(b) instead.

**Fly facts** (read-only, 2026-09-08): app `brisken-expense-recon`, one
machine `48ee133c363758` in fra, volume `vol_4m3p65dn1nqkowzv` (`recon_data`,
1 GB, encrypted, created 2026-09-04), scheduled snapshots on, 5-day
retention, four existing. `flyctl ssh sftp` into the machine is blocked by
the sandbox classifier; the code answers the "readable without the app"
question adequately without it.

### Reference Materials

- irs.gov/pub/irs-tege/rp-97-22.pdf (extract locally with pypdf)
- law.cornell.edu/cfr/text/26/1.274-5T, /1.6001-1, /1.62-2
- Workflow transcripts: `subagents/workflows/wf_9ace1923-a6b` (map), `wf_b4fa7ec8-5df` (refute)

---

## How to Continue

Nothing is blocked on me. The description and the criteria matrix both need
a human read before anything is built or handed over. If the next session is
picking up item 48, start at section 6 of the criteria file (the proposed
delta) and section 12 of the description (the remediation register); those
two lists are the work.

---

## Strategic Feedback

### What Worked Well This Session

- Verifying the agent's headline finding by hand before acting on it. The
  ReceiptStore claim would have been embarrassing to propagate wrongly in
  either direction, and one grep settled it.
- Instructing the skeptics to default to "refuted" and then putting an
  adjudicator behind them who was told to reject over-eager findings. 53 of
  97 confirmed is a healthy ratio; a pass that confirmed everything would
  have meant the skeptics were rubber-stamping.
- Filing item 49 separately. The float-total bug has nothing to do with tax
  law and would have died inside a compliance document.

### Suggestions

- The two documents now cross-reference each other heavily and both carry
  correction notes. If a third round lands, consider making the description
  the single source for "how the system behaves" and having the criteria
  file cite it, rather than both restating the mechanics.

### System Health

- **Autonomy: 0 corrections. One decision point raised deliberately**
  (`AskUserQuestion`, two answers) after the B1 gate correctly caught me
  phrasing a real decision as an open offer.
- The B1 stop-gate fired once and was right: "What I would change, if you
  want it" was an open offer where the brief forbade building. Re-put as a
  decision with a recommendation, it got answered in one turn.
- The heredoc size gate fired twice more today across sessions. It keeps
  working, and the cost is now one call each time instead of a corrupted
  payload.
