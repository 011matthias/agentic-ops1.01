# Checkpoint: ECC Batch 2 Live Activation

**Date:** 2026-09-17
**Status:** Live. The pattern-rules gate fires in the harness; telemetry recording has started.

---

## Summary

Closed the one open item from the batch-2 checkpoint: the four merged ECC items were inert because the shared primary clone sat off `main`. It reached `main` through the brisken session's own ship chain; the gate was then driven live, and the stretch produced a sixth-session pattern rule and a digest fix from the rule miner's first real run.

---

## What Was Done This Session

### Activation
1. Answered "can I fast-forward while brisken sessions are working?" with a fresh read rather than the earlier one: 11 dirty expense-recon files, three sessions active within 80 s, and `docs/api-contract.md` both locally modified and changed on `main`, so git would have refused the merge.
2. Ran a check-then-act watcher (clean tree AND no sibling active in 5 min AND HEAD an ancestor of `origin/main`, else stop without switching branches). It found the clone already on `main` at `91f406a4` and exited with nothing to do.
3. Confirmed the clone contains #961, #964, #965, #966; `wire-hooks --check` 28/28.
4. Live drive: a harmless `echo "... git add -A ..."` produced `[PATTERN WARN: warn-git-add-all]` as a PreToolUse advisory in this session.

### Mechanism follow-through
1. New rule `warn-mutate-shared-primary-clone` from this stretch's friction (see register row), tested against the denied command.
2. First real rule-miner run on this session's digest: haiku returned an empty list, correctly (no user corrections occurred).
3. The run exposed a `digest` defect: harness `<task-notification>` blocks were counted as user turns. Stripped, test assertion added, bite-checked.

---

## Key Decisions Made

### Wait for the owning session instead of forcing the fast-forward
- **Choice:** poll for safe conditions; never switch the clone's branch autonomously.
- **Rationale:** a fast-forward of a tree with live uncommitted work either fails (overlapping file) or swaps files under a running session. If the branch had diverged, the approved operation would no longer exist.

---

## What Did NOT Work (and why)

- **Fast-forwarding the primary clone on the earlier safety read:** the read was about twenty minutes old. By the attempt, the tree held 11 dirty files and three live sessions, and one merge-affected file was locally modified. The auto-mode classifier denied it before git could.
- **`digest` as shipped in #966:** counted a harness `<task-notification>` as a user turn. The synthetic test transcript never contained one, so the suite could not see it.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/patterns/warn-mutate-shared-primary-clone.md` | new | stale-read mutation warn |
| `tools/pattern_rules.py` | edit | strip `<task-notification>` in `digest` |
| `tools/tests/test_pattern_rules_gate.py` | edit | pin the notification case |

---

## Current Status

Items 1, 4, 5, 8 active on this machine. Telemetry JSONL collection began with the live clone update; the stocktake and memory audit withhold Retire verdicts until ~2026-10-17. No client infrastructure touched.

---

## Next Steps

1. On or after 2026-10-17, run `uv run tools/skill_stocktake.py` and `uv run tools/memory_audit.py` as `/comd_system-dev` Phase 1 inputs.
2. Watch the ask rate of the W1 purpose check and the warn volume of the pattern rules in `.claude/hooks/hook-log.txt` (`pattern-rules-gate MATCH`, `file-placement-gate ASK w1-purpose`); retune any rule that fires on routine work.

---

## Context for Next Session

### Files to Read First
- `docs/2026-09-17 - ECC Port Batch 2 (items 1, 4, 5, 8)/Checkpoint.md`
- `.claude/patterns/`

### Open Questions
- Should `memory_audit.py` join the SessionStart sweep once it has data?

### Working Notes
- Pattern rules already in use by another session: the brisken checkpoint (#978) added `warn-attach-busy-cdp-9222` within the hour of #966 merging. Seven rules exist now.

### Reference Materials
- PRs #961, #964, #965, #966, #967

---

## How to Continue

Nothing is pending. New lessons with a regex signature go to `.claude/patterns/` via `pattern_rules.py new` plus `test --text` against the incident.

---

## Strategic Feedback

### What Worked Well This Session
- Treating the user's safety question as a trigger to re-measure instead of re-stating the earlier answer. The re-read reversed the recommendation from "run it" to "wait", and the watcher then showed waiting cost nothing.

### Suggestions
- `digest`'s strip list is hand-maintained against harness tags. A test transcript captured from a real session (sanitized) would catch the next unrecognized tag before a miner run does.

### System Health
- Autonomy: 1 human intervention (the concurrency question that led to the re-read).
- Dogfooding found one real defect within an hour of shipping, and the classifier held the one unsafe action. Both backstops worked; the rule written here moves the freshness check to decision time.
