# Checkpoint: System Development

**Date:** 2026-09-08
**Status:** Round complete. PRs #742 (sys) + #743 (docs) merged; anneal ledger current for the first time in 50 days.

---

## Summary

First full `/comd_system-dev` round since 2026-07-20. Triggered by the weekly synthesis flagging a 261-row unresolved backlog and a 49-day anneal gap. The backlog turned out to be mostly bookkeeping debt: a verified sweep took actionable from 207 to 162, and the register itself was found structurally broken (a mid-file table had been swallowing ~100 rows since 2026-07-17).

---

## What Was Done This Session

### Audit before acting
1. Four read-only agents audited the friction register, the anneal cadence, the last two weeks of session logs, and the ops items, so the triage call rested on measured state rather than the synthesis headline.
2. Established that 73% of unresolved rows predate 2026-07-22 (the day the B1 primer and several gates shipped) and that the "agent-deferred x79" headline was mostly containment records: 54 of 63 explicitly hook-held rows are that type.

### PR #742 — three structural fixes
1. `msys-mangle-gate.py`: new advisory PreToolUse:Bash hook flagging `<ref>:<path>` pathspecs and leading-slash args, naming `MSYS_NO_PATHCONV=1`. Memory had failed this class three times in one day (2026-08-24); a fifth instance was logged by a sibling session while the hook was being written. 14 tests, negatives as the contract.
2. `rule_behaviors.md` instrument-validity B2 sub-clause: consumer-drive proves you looked at the right thing, not that the probe can see the thing at all. Covers the empty-by-design endpoint, the silently-ignored filter, and the stale-but-once-true artifact.
3. Memory-load rule made followable: the rule ordered bulk-loading a store it budgeted at ~1,800 tokens; measured 128 files / 659,126 bytes (~165k tokens). Replaced with index-first plus targeted load in both `rule_session-start.md` and `comd_resume.md`.

### PR #743 — register sweep and repair
1. 46 verified row flips (29 to Yes, 17 to canonical gate-held), each verified against the artifact on disk by seven adversarial verifiers defaulting to LEAVE. Six medium-confidence candidates deliberately left open; ten verdicted LEAVE.
2. Repaired the register as a document: removed the stray rule and moved the `## Agentic Backlog` 4-column table below the register, rejoined a row split by a lost `\v` in `$HOME\vault.py`, corrected `docs/sessions/2026-09-07.md` frontmatter (3 to 5 sessions, 3 to 6 friction events).
3. Archive rotation: 24 resolved rows older than 2026-07-10 moved out; unresolved counts unchanged across the rotation, which is the check that only resolved rows moved.
4. Phase 6.5 anneal-ledger row filled with an honest verdict.

### Ops
1. Removed two merged-and-clean worktrees (`agentic-ops1-deploy`, `-deploy-r2`) after verifying both HEADs were ancestors of `origin/main` with no tracked, untracked, or ignored content at risk.
2. Meji Make.com credit cliff checked live and found already resolved: Core tier, unpaused, cycle reset 2026-08-28, 27,198 of 40,000 operations unused. Residual: `autoPurchasingActivated: false`.

---

## Key Decisions Made

### Full round, not `--audit-only`
- **Choice:** Ran Phases 0 through 7 rather than the recommended `--audit-only`.
- **Rationale:** The session's own audit fan-out had already produced what Phases 0-3 would, and a third consecutive round without a Phase 6.5 ledger row was the actual defect. The 2026-07-20 row explicitly staged "the first honest read" for the next cycle.

### Applying sweep verdicts by script, not by hand
- **Choice:** Verdicts applied only where the quoted row text matched exactly once, with the new line rebuilt from the original so only the Resolved cell could change.
- **Rationale:** One verifier did try to rewrite a second cell. The rebuild made that structurally impossible rather than relying on review to catch it.

### Locating the Resolved cell by content, not column index
- **Choice:** Find the changed cell and require it to look like a Resolved cell, instead of hardcoding index 4.
- **Rationale:** Rows carrying an unescaped `|` in the description shift every later column; `2026-05-20` keeps Resolved at index 5. Positional editing would have corrupted exactly those rows while appearing to work everywhere else.

### Leaving six medium-confidence rows open
- **Choice:** Only high-confidence verdicts applied.
- **Rationale:** The verifiers hedged for stated, readable reasons. A register that flips on the agent's benefit of the doubt is the failure the sweep exists to correct.

### Deferrals, with reasons
- **Stop-b1 closing-offer reflex:** gate holds 100% across ~12+ occurrences; the primer is the ceiling of prose fixes and re-tuning it is accretion.
- **Gate-precision detector false positives (3):** advisory-only, candidate fixes named and ready if they recur.
- **Stale-prod-after-platform-merge:** zero instances in the audit window; no platform work occurred at all.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/msys-mangle-gate.py` | created | MSYS path-mangle advisory gate |
| `tools/tests/test_msys_mangle_gate.py` | created | 14 tests; negatives are the contract |
| `tools/wire-hooks.py` | edited | wired into CANONICAL_HOOKS + EXPECTED_HOOK_SCRIPTS |
| `.claude/rules/rule_behaviors.md` | edited | instrument-validity B2 sub-clause |
| `.claude/rules/rule_session-start.md` | edited | step 6 memory load: index-first, targeted |
| `.claude/commands/comd_resume.md` | edited | Step 5.5 aligned so the two cannot contradict |
| `docs/friction-register.md` | edited | 46 verified flips + structural repair |
| `docs/friction-register-archive.md` | edited | 24 resolved rows rotated in |
| `docs/sessions/2026-09-07.md` | edited | frontmatter counts + session renumbering |
| `docs/anneal-ledger.md` | edited | Phase 6.5 row, first since 2026-07-20 |

---

## Current Status

Both PRs merged on green CI (6/6 checks each). Register: 280 rows, 165 actionable + 83 gate-held (post-merge basis, includes sibling rows added during the round). Drift 0. Enforcement layer at 25 hooks.

System scope; no `infrastructure.yaml` and no comms log, so no ops status line applies.

---

## Next Steps

1. Human glance at the six medium-confidence rows left open in the sweep (listed in PR #743) — flip or confirm.
2. Next cycle consolidates rules rather than adding to them: files over the 250-line ceiling went 3 to 4 (`rule_human_communication` 275, `rule_client_page_structure` 273, `rule_platform_standards` 267, `rule_no_auto_commit` 251).
3. Investigate the `intent-violations` eval fixture, RED at base (0/3 at n=3 on both sides of #742) — the behavioural eval gate currently ships with a known-red fixture.
4. Consider a structural guard for the shared-checkout branch switch (see Friction below); the sibling-session registry already knows which checkouts have live sessions.
5. Decide whether Meji auto-purchase should be enabled ahead of September volume (`autoPurchasingActivated: false`, 27,198 ops remaining to 2026-09-28).

---

## Context for Next Session

### Files to Read First
- `docs/anneal-ledger.md` (last row states the verdict and the rising metric to watch)
- `docs/friction-register.md` (post-sweep; the honest actionable count)
- `.claude/hooks/msys-mangle-gate.py` (newest gate)

### Open Questions
- Should the six medium-confidence rows flip, or do they want narrower fixes first?
- Is the `intent-violations` fixture red because the agent regressed, or because the fixture's expectations drifted from the agent's current contract?
- Does the shared main checkout have a canonical resting branch? The weekly sensor runs its code from there, so a feature branch left checked out means the scheduled run executes stale code.

### Working Notes
- The register's `Resolved?` cell is **not** reliably at column index 4. Rows with an unescaped `|` in the description shift it. Any future sweep must locate it by content shape.
- The eval harness needs `grade RUN_DIR` before `compare`; `compare` alone fails with a bare `FileNotFoundError` on `grades.json`, which reads like a broken run rather than a missing step.
- The first two background fan-outs of this session were launched without a `bg_watch` registration; the second died wholesale on the session rate limit and I learned of it from the harness notification rather than my own watch. The relaunch was watched properly.
- `anneal-metrics.py` reports `actionable (+held)`; the sweep's effect is visible only in that split, not in the raw unresolved count.

### Reference Materials
- PR #742: https://github.com/011matthias/agentic-ops1.01/pull/742
- PR #743: https://github.com/011matthias/agentic-ops1.01/pull/743

---

## How to Continue

The round is closed; nothing is mid-flight. Pick up from Next Steps. A future sweep should reuse the method rather than the script: verify each row against the artifact on disk, apply only exact unique matches, rebuild the line so only the Resolved cell can change, and leave hedged verdicts open.

---

## Strategic Feedback

### What Worked Well This Session
- Auditing before recommending changed the answer. The synthesis headline said 261 unresolved; the measured reality was ~160 actionable plus containment records, and acting on the headline would have meant "triaging" rows that were already closed.
- The applier's own guards caught two real problems mid-run: an agent rewriting a second cell, and the column-shift on pipe-carrying rows. Both would have been invisible in review of a 46-row diff.
- Re-running the one red eval fixture at n=3 on both sides turned an ambiguous "extra failure in head" into a confident "pre-existing, not mine".

### Suggestions
- Make the register's same-PR flip convention structural. It has now failed twice at scale (18 stale rows found in the 07-20 sweep, 29 more today). A ship-flow step that greps the register for rows naming an artifact the PR touches would catch most of them at the moment the fix lands.

### System Health
- The enforcement layer is doing its job unprompted: cd-guard blocked two `cd X && ...` compounds, the hook-registry test caught a missing `EXPECTED_HOOK_SCRIPTS` entry before CI, and `regress_check` proved the new tests bite. The gaps found today were in the ledger and the register, not in the gates.
- **Autonomy: 2 human interventions** (both nudges to continue after an interruption; neither was a correction of direction).
