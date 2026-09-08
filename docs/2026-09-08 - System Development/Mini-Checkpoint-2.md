# Mini-Checkpoint: System Development

**Date:** 2026-09-08
**Status:** Round fully closed out. All three PRs merged, artifacts verified on origin/main, worktrees pruned.
**Type:** mini

---

## Summary

Closeout tail after the round's own checkpoint (PR #745). Verified every shipped artifact is actually present on `origin/main`, pruned the two worktrees the round created, and preserved the paid eval evidence before deleting the tree that held it.

## What Was Done

- **Verified on `origin/main`, not assumed:** `msys-mangle-gate.py` and its test module present, the instrument-validity sub-clause present in `rule_behaviors.md`, the hook registered twice in `wire-hooks.py` (CANONICAL_HOOKS + EXPECTED_HOOK_SCRIPTS), ledger last row dated 2026-09-08.
- **Worktree pruning done on the right instrument.** `git merge-base --is-ancestor` reported both round worktrees as NOT contained in `origin/main`, which looks like unmerged work but is just how squash-merge works: it creates a new commit, so the branch HEAD is never an ancestor. Re-checked by content instead (`git diff --name-only origin/main` restricted to the files I authored) and got an empty diff, proving the work had landed. Then removed `agentic-ops1-sweep` and `agentic-ops1-sysdev`.
- **Preserved the four paid eval runs** (base, head, and both `intent-violations --n 3` re-runs, with `grades.json`) into the primary clone's `.scratch/evals/` before deleting the worktree that held them. They are the evidence for the "RED at base" claim in PR #742 and for open next-step #3.
- **Logged the MERGE-NOT-LIVE / force-deploy gate-precision false positives** as a register row (shipped inside PR #745 before merge).
- Confirmed the shared primary checkout is back on the sibling session's branch with its dirty and untracked files intact, exactly as found.

## Current Status

`origin/main` carries the full round. Register at 281 rows / 169 actionable + 84 gate-held. Seven worktrees remain, none created by this round. System scope: no `infrastructure.yaml`, no comms log, so no ops status line applies.

Register is 205 KB and stays above the 200 KB band: the pre-flight advisory moves only 2 more resolved rows (to ~203 KB). The remainder is unresolved rows the archiver never moves, so size is not a rotation problem, it is the backlog itself.

## Next Steps

1. Human glance at the six medium-confidence register rows left open in PR #743: flip or confirm.
2. Investigate the `intent-violations` eval fixture, RED at base (0/3 at n=3 both sides); evidence preserved at `.scratch/evals/` in the primary clone.
3. Fix the `post-action-gate.py` false positives: re-check the merged PR file list when RE-surfacing a stored marker, require a command-position match for the deploy detector rather than a substring, and retarget the stale `vercel-force-deploy` remedy text.
4. Next cycle consolidates rules rather than adding: files over the 250-line ceiling went 3 to 4.
5. Decide whether Meji auto-purchase should be on ahead of September volume (`autoPurchasingActivated: false`, 27,198 of 40,000 ops unused to 2026-09-28).

## Files to Read First

- `docs/2026-09-08 - System Development/Checkpoint.md` (the full round record)
- `docs/anneal-ledger.md` (last row: verdict + the rising metric named)
- `.claude/hooks/post-action-gate.py` (next-step #3 target)
