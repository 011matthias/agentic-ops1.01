# Mini-Checkpoint: Optimize Loop S-Series Implementation

**Date:** 2026-07-22
**Status:** S-series shipped and checkpointed. Handoff prompt for the next GTM run written; nothing in flight.
**Type:** mini

---

## Summary

Continuation of session 10 after the full checkpoint (PR #347). Only new
artifact: the handoff prompt for re-running the GTM strategy optimization on
the hardened harness with a defensible comparison against
`upwork-independence-gtm-v2`.

## What Was Done

- Wrote the GTM v3-vs-v2 run prompt (scratchpad
  `prompt-gtm-v3-vs-v2.md`, also delivered inline to the owner). Its
  load-bearing constraints:
  - **Score comparability is binary.** The run must reuse the already-pinned
    `tools/scorers/gtm-roi-v2.py` byte-identical. Changing the model makes it
    v3 and makes the scores incomparable — v2's own SUMMARY already opens with
    "Not comparable to v1's score", and the prompt forbids repeating that
    silently.
  - **Task 0 is a prerequisite, not optional.** `--prior-art
    upwork-independence` currently returns nothing: all four GTM runs predate
    the `## Dead ends` / `## Sensitivities` contract shipped in PR #333. The
    v1/v2 SUMMARYs must be backfilled from their own existing content first.
    This is also the first real test of whether that contract is retrofittable
    rather than forward-only.
  - **A zero-keep result is the expected and valuable outcome** under the
    default baseline (v2's winner), since v2 converged with three confirming
    boundary probes. The prompt instructs shipping the journal regardless.
  - Carries forward v2's three tested boundaries (r6 allocation → 1.0 b2b,
    r7 build price → 1500, r8 care price → 250, all DISCARD) so they are not
    re-opened, and requires a pegged-at-bound check on every winning lever.
  - Repeats the standing honesty caveat: `gtm-stress-guard-v2.py` is a
    pessimistic re-run of the SAME model, not a RECIPES rule-3 held-out guard,
    and the SUMMARY must not claim otherwise.
- Verified the full checkpoint landed: PR #347 merged, `Checkpoint.md`, INDEX
  row, session-log entry and 6 friction rows all confirmed present on
  `origin/main`. Worktrees and branches from the S-series work removed.

## Current Status

Nine S-series PRs (#324 #325 #326 #327 #328 #329 #331 #333 #335) plus the
ledger PR #347 are all merged. Scoreboard on main: `asset kind 2/6 production`,
`scorer reuse page-weight.pyx2`, `6/6 with SUMMARY`, `checkout completeness
matches origin/main`. No optimize run is locked; no branches or worktrees
outstanding from this work.

S1 remains the one open structural item, deliberately unbuilt — see
`project_optimize_s1_recon_scorer_design.md` for the corrected metric.

## Next Steps

1. Run the GTM prompt in a fresh session (Task 0 first: backfill the v1/v2
   SUMMARY heading contract, ship as its own `docs/...` PR, confirm
   `--prior-art` surfaces it, then the run).
2. S1 — build `tools/scorers/recon-match-accuracy.py` against the corrected
   composite metric. Needs `SCORER_LOCK_ALLOW` and an explicit user order.
3. Decide on run 1's r4 full-CSS-minification (owner call; reverting costs
   9,516 B of the 36,775 and is one commit).

## Files to Read First

- `docs/2026-07-22 - Optimize Loop S-Series Implementation/Checkpoint.md`
- `~/.claude/projects/.../memory/project_optimize_s1_recon_scorer_design.md`
- `docs/optimize/platform-alpha-research-weight/SUMMARY.md` — the dead ends any
  future weight run must inherit
- `docs/optimize/upwork-independence-gtm-v2/SUMMARY.md` — the source material
  for the prompt's Task 0
