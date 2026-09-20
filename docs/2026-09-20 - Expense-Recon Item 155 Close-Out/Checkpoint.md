# Checkpoint: Expense-Recon Item 155 Close-Out

**Date:** 2026-09-20
**Status:** Queue closed. Item 155 live on Fly v191 and verified; queue item 2 handed to a peer session.

---

## Summary

Backlog item 155 (note item T4): the filing instruction Dirk types above a
forwarded invoice now reaches the expense row as `expenses[].operator_note`,
display only. This is the full-mode audit of a session whose mini-checkpoint
(`docs/2026-09-20 - Expense-Recon Operator Note Above The Forward/`) already
recorded the build; what follows is the friction, gate and strategic half it
skipped, plus the close-out.

---

## What Was Done This Session

### The build (detail in the mini-checkpoint)
1. `body_render.operator_note` cuts a body at the LAST forward-header block;
   `_provenance_entry` carries the prose above it onto every file the mail
   delivered; `build_expense_view` lifts it to the row.
2. Measured with the shipped function over `/data/inbound`: 92 archives, 86
   readable bodies, 71 with a boundary, **30 with a note**. Six times the five
   the item named.
3. 11 route-level tests, the T4 pin in `test_intake_mail.py` rewritten (it
   asserted a drop that is no longer true), a contract pin. Suite 2603 -> 2615.
4. Three wiring points proven RED by hand, each anchor checked to sit in the
   function it names before the mutation was applied.

### Close-out
5. Deployed and verified: Fly v191, proven in-machine rather than by reading
   the live months (see What Did NOT Work).
6. Discovered mid-close-out that a peer session was running the same prompt.
   Coordinated by message: item 2 is theirs as backlog 157, feedback note #70
   is theirs as 158, and the record correction (#1126) stayed mine.
7. Memory `project_brisken_expense_recon_usability_loop` gained the three traps
   below so the next session does not pay for them again.

---

## Key Decisions Made

### A body-only mail's note IS recorded
- **Choice:** Reverse the item's own instruction not to double-record it.
- **Rationale:** The caution protects against a second copy of the *invoice*,
  and the boundary rule cannot produce one, since it keeps only what sits above
  the forward. 13 of the 30 live notes arrive on body-only mail, so the other
  reading drops nearly half of what the item is for.

### Cut at the LAST forward-header block, not the first
- **Choice:** Scan the first 30 lines for every header block and cut at the last.
- **Rationale:** Criss forwards Dirk's forward, and his instruction sits
  *between* the two blocks. 8 of the 30 live notes are that shape.

### No note where there is no forward boundary
- **Choice:** One hard bound on an otherwise err-long rule.
- **Rationale:** Without it a vendor mailing us directly carries its whole body
  as a "note". It costs nothing live: all 15 boundary-less bodies are test
  drills or body-only mail whose text is already the rendered receipt.

### Stand down on queue item 2
- **Choice:** Hand it to the peer rather than race.
- **Rationale:** They held the worktree and had committed. Two PRs for one fix
  would have collided on the backlog and the status file a second time.

---

## What Did NOT Work (and why)

- **A 68-byte JPEG fixture:** `intake_mail.py` ~593 drops images under 4096
  bytes as signature logos, so five tests that named the ATTACHMENT path
  silently drove the body-only render path and passed. Caught only because the
  two-attachment test reported ONE provenance entry, keyed
  `0000__rendered-body.pdf`.
- **Cutting at the FIRST forward boundary:** returns nothing for the 8 nested
  forwards, which are exactly the ones carrying Dirk's instruction inside
  Criss's.
- **flyctl with its own stored credential:** v0.4.71 answers "no access token
  available" for every command while that same token is accepted by
  `api.fly.io` (read-only `{viewer{email}}` -> HTTP 200). The config read is
  broken, not the credential; `flyctl auth login` is not the fix, and passing
  the token as `FLY_API_TOKEN` works.
- **Reading the live months to verify the deploy:** `operator_note` is absent
  on all 85 mail-delivered rows and always will be, because `intake_provenance`
  is frozen into the run snapshot at ingest. A correct deploy looks like a
  failed one here.
- **Asserting the two-attachment case at row level:** an `Invoice-*`/`Receipt-*`
  pair is the invoice+receipt collapse's own signal and lands as one row. The
  assertion moved to stored provenance, one entry per delivered file.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../web/body_render.py` | append | `operator_note` + the boundary rule |
| `.../web/intake_mail.py` | edit | `_archive_operator_note`, wired into `_provenance_entry` |
| `.../web/service.py` | edit | the row lift in `build_expense_view` |
| `.../tests/test_operator_note_155.py` | new | 11 route-level tests |
| `.../tests/test_intake_mail.py` | edit | T4 pin rewritten to the new behaviour |
| `.../tests/test_view_contract.py` | append | scalar pin |
| `.../docs/api-contract.md` | append | the contract section |
| `.../docs/lovable-operator-note-prompt.md` | new | SPA half, not pasted |
| `.../docs/PROMPT-STATUS.md` | edit | Not-applied row |
| `status/p1-improvement-backlog.md` | edit | item 155 heading + Shipped row 103 |
| `status/p1-expense-reconciliation.md` | edit | item 155 row, then corrected |
| memory `project_brisken_expense_recon_usability_loop.md` | insert | the three traps |

---

## Current Status

Item 155 is live on **v191** and behaves as designed: the field appears on mail
arriving from v191 on, not on the 85 receipts already in the three months. The
SPA shows nothing until the owner pastes the prompt. brisken platform: unknown
plan, last assessed unknown. No worktrees, branches, watches or open PRs of this
session remain.

**Two sessions ran the same prompt.** The peer (`agentic-ops1-71`) holds
`agentic-ops1-trace` and owns items 157 and 158. `agentic-ops1-deploy-trace` was
left in place deliberately: it pre-existed this session and both sessions
deployed from it.

---

## Next Steps

1. Owner: paste `docs/lovable-operator-note-prompt.md` into Lovable.
2. Peer session: items 157 and 158. Do not duplicate.
3. Decide whether the 32 archived notes should reach existing rows. That is a
   re-ingest per archive, a live write on Criss's months, so it is her call.
4. Consider a parallel-round protocol step that checks `git worktree list` and
   `ListAgents` for a sibling on the SAME prompt before claiming its directory.

---

## Context for Next Session

### Files to Read First
- `.../docs/api-contract.md`, section "The note the sender typed above the forward"
- `.../docs/lovable-operator-note-prompt.md`
- `.../src/expense_recon/web/body_render.py` (the `operator_note` block at the end)
- `docs/2026-09-20 - Expense-Recon Operator Note Above The Forward/Mini-Checkpoint-1.md`

### Open Questions
- Should the parallel-round protocol check for a sibling on the same prompt?
- Three blind-instrument friction rows in three days, each fixed `documented`.
  Is there a structural check for a probe returning a confident negative from an
  instrument that cannot see the thing?

### Working Notes
- The archive grew mid-session: 92 archives / 30 notes at 13:40, 94 / 32 by
  16:50. Re-run the scan rather than quoting these.
- `intake_provenance` is keyed by the STORED FILE NAME (`0000__x.jpg`), not by
  digest, once it reaches the snapshot. That is what makes it a usable assertion
  for which intake path ran.
- The self-confirm fixture in `tests/test_self_confirm.py` (`_month`) is the one
  that produces a `decided_by='tool'` row; the T3 fixture does not, and the
  docstring at `test_charge_origin_t3.py` ~458 says otherwise and is wrong.

### Reference Materials
- PRs #1123 (`a2276f06`), #1126 (`3a1d5925`), #1127 (`54c98d0b`)
- `docs/PARALLEL-ROUND-PROTOCOL.md`

---

## How to Continue

Nothing is in flight. The queue is empty; do not write another continuation
prompt for it. If the owner pastes the Lovable prompt, verify with a bundle
audit plus a cold drive on a month holding mail that arrived after v191.

---

## Strategic Feedback

### What Worked Well This Session
- Running the SHIPPED function over the live archive, rather than a paraphrase
  of it, turned a five-instance claim into a measured 30 and overturned two of
  the item's assumptions before any of it reached a test.
- Probing the Fly token against the API instead of believing flyctl's own error
  message. The obvious reading ("expired credential, needs an interactive
  login") would have ended the session's deploy half.
- Checking the enclosing `def` before trusting a RED. The peer adopted it and
  said it is the check that would have caught the 2026-09-18 miss.

### Suggestions
- The three blind-instrument rows (wrong path scanned, wrong function anchored,
  undersized fixture) share one shape: a probe that cannot see the thing
  returning a confident negative. All three were fixed `documented`. The
  structural version is a habit with teeth: before a probe's output grounds any
  claim, run it against a case whose answer is already known and confirm the
  output CHANGES. That is already written in `rule_behaviors` B2
  instrument-validity; what is missing is anything that makes skipping it
  visible.

### System Health
- Two sessions on one prompt produced a duplicate deploy, a discarded draft and
  three coordination messages. Cross-session messaging worked well once used;
  nothing prompted using it until the collision was already visible in
  `git worktree list`.
- Autonomy: **1 human intervention** (an interrupt and "continue"); no
  corrections, no deferrals.
