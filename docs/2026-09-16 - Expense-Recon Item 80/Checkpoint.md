# Checkpoint: Expense-Recon Item 80

**Date:** 2026-09-16
**Status:** Backend live (PR #902, Fly v134); owner pasting `lovable-date-gap-prompt.md` into Lovable, not yet published or audited

---

## Summary

Item 80 (note #44) is shipped and deployed end to end under the parallel-round
protocol, and the SPA prompt is being applied by the owner. This checkpoint
supersedes `Mini-Checkpoint-1.md` in the same folder, which holds the full
build record (live read, tests, regress proofs, deploy, drive); only what
changed since, and the session audit, is added here.

---

## What Was Done This Session

### Since the mini checkpoint

1. Mini checkpoint shipped as #904 (`fb720fc9`); worktrees `item80`,
   `ckpt-item80`, `deploy-item80` and both branches removed, three cleanup
   outputs empty.
2. Re-handed the Lovable prompt in one four-backtick block after the owner
   asked for a copy-pastable form (friction row below).
3. Owner started the paste in Lovable.
4. Memory `feedback_prompts_are_pasteable_text.md` gained the render rule:
   a prompt with inner fences goes in a FOUR-backtick fence.

---

## Key Decisions Made

### The lag note reads only the chosen candidate
- **Choice:** the prompt mirrors `getRowWarnings`, which reads
  `is_chosen`; no per-candidate note in `CandidateRow`.
- **Rationale:** the owner's spec scoped the change to the row chip and
  said not to touch the date ScoreBar. Consequence, stated in the prompt:
  August's only `lag` pair (ANTHROPIC 50.52) sits on an undecided row and
  shows nothing. Left as an open question, not built.

### Hand matches carry the zone
- **Choice:** the synthesized `manual` candidate gets `date_gap_*` too.
- **Rationale:** "every `rows[].candidates[]` entry". It has `date_pct: null`
  and never warned before, so a hand match 8+ days out newly shows
  "date mismatch"; the prompt names this as intended.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit (#902) | `DATE_GAP_ZONES`, `date_gap_zone()`, `_candidate_date_gap()`, two spreads |
| `.../tests/test_date_gap_zone.py` | new (#902) | 19 route-level tests incl. manual-match |
| `.../tests/test_view_contract.py` | edit (#902) | `test_date_gap_zone_is_absent_or_enum_never_null` |
| `.../docs/api-contract.md`, `PROMPT-STATUS.md`, `lovable-date-gap-prompt.md` | edit/new (#902) | contract section, Not-applied row, the prompt |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edit (#902) | item 80 marked shipped, row 46, status row |
| `docs/2026-09-16 - Expense-Recon Item 80/*` + ledger | new (#904, this PR) | checkpoints |
| memory `feedback_prompts_are_pasteable_text.md` + `MEMORY.md` line | edit | four-backtick rule |

---

## Current Status

Backend: v134 serves `date_gap_days` / `date_gap_zone` on both live months
(July 38/38 `none`; August 11 `none` + 1 `lag`; 0 `mismatch`). SPA: paste in
progress; PROMPT-STATUS still lists the prompt under Not applied, which is
correct until the bundle audit reads it. `status/p1-expense-reconciliation.md`
still says "pending owner paste"; not bumped for an in-progress paste.
Brisken ops status: `platform: unknown plan` (no `platform` block; the p1 app
is FastAPI on Fly, not an orchestrator plan, so no feasibility step).

---

## Next Steps

1. After the owner publishes: `uv run tools/lovable-bundle-audit.py`, assert
   `date_gap_zone`, `wb.dateGap.chargedAfter`, `wb.dateGap.receiptAfter`
   present AND `API_BASE` still `https://api.expenses.brisken.com` (the
   prompt's header wrongly names `brisken-expense-recon.fly.dev`, copied from
   the house template; a sibling flagged it after the paste had started).
   Move the PROMPT-STATUS row to Applied and correct the header line in
   `lovable-date-gap-prompt.md` in the same `client/brisken/...` PR.
2. Browser-drive July `/runs/50622baec444` cold (own `--session`): zero
   "date mismatch" titles, GOOGLE Workspace and the three ANTHROPIC rows
   chip-free, AMAZON / MP read "AMOUNT MISMATCH" with no "+1", Warnings only
   23. Bump the status row to live.
3. System: close the consumer-gate hole below (auto-backgrounded timeout
   still closes the marker).
4. Protocol §9 / §11: say "in one four-backtick fenced block" so the
   pasteable-prompt rule stops depending on recall.

---

## Context for Next Session

### Files to Read First
- `docs/2026-09-16 - Expense-Recon Item 80/Mini-Checkpoint-1.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-date-gap-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

### Open Questions
- Should the lag note also show on an undecided row's candidates?

### Working Notes
- The warning count after publish was simulated, not guessed: replaying
  `getRowWarnings` over the 2026-09-16 July payload gives 27 -> 23. The
  "six fewer" first draft was wrong because AMAZON and MP keep
  "amount mismatch"; the chip shows `warnings[0]` plus "+N", so their date
  warning was the hidden "+1".
- `checkpoint_scaffold.py`: `--root` is a GLOBAL flag (before `finalize`),
  and mini numbering is recomputed at finalize, so writing the prose file
  first (as the skill orders) makes finalize point at `-2`. Fixed by hand
  in #904.
- The first agent-browser `open` hung 120s with no session registered;
  a bounded `timeout 90` retry worked immediately.
- Sibling state at close: item 73 merged (#905), items 74 / 76 / 77 / 81
  worktrees live.

### Reference Materials
- PR #902, PR #904; Fly releases v133 (item 79 backend) / v134 (this item)

---

## How to Continue

Run `/resume brisken`. If the owner reports the Lovable publish, do Next
Steps 1-2 in one pass: bundle audit first, drive second, then a small
`client/brisken/...` PR moving the PROMPT-STATUS row and the status row.

---

## Strategic Feedback

### What Worked Well This Session
- Splitting the offset loop into parametrized ids before the regress run:
  the first proof's red set could not show that the +1 assertion itself went
  red (0d failed first); after the split the output named `[plus1d]` and
  `[plus3d]` directly, which is what the brief asked the proof to show.
- Reading the SPA source before writing the prompt found two things the
  brief did not say: the chip reads only the chosen candidate, and manual
  candidates never warned (`parseFloat(null)` is NaN).

### Suggestions
- Fix `backgrounded()` in `.claude/hooks/deploy-consumer-gate.py` to also
  treat a tool response that reports an auto-background on timeout as not
  observed, with a test through the hook's PostToolUse path.

### System Health
- Autonomy: 1 human intervention (the copy-pastable prompt request).
- B4 skipped once: the prompt header's backend host came from the house
  template (`brisken-expense-recon.fly.dev`), not from the SPA's `API_BASE`
  (`api.expenses.brisken.com`), although `api.ts` was open for the
  `Candidate` type. A sibling session caught it after the paste started.
- The consumer gate closed on a drive that read nothing back; the agent did
  not rely on it, but the advisory text would have read as evidence to a
  less careful turn.
