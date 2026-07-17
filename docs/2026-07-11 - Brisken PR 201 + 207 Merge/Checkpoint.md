# Checkpoint: Brisken PR 201 + 207 Merge

**Date:** 2026-07-11
**Status:** Both PRs MERGED to main. PR #207 = ec0bde2, PR #201 = d6d9c26 (conflict-resolved, CI green). Branch lifecycle for lead-gen-onepilot is closed.

---

## Summary

On the owner's "merge how you see fit": merged PR #207 directly (CI was green), then un-stuck PR #201, which had sat CONFLICTING with zero CI runs, by merging main into it in an isolated worktree, resolving 8 conflicts, fixing a Ruff failure the new CI linter surfaced, and merging on green.

---

## What Was Done This Session

### PR #207 (clean Calvin render + runbook)
1. Merged via `tools/gh-merge.sh 207` → squash `ec0bde2`. The wrapper's local-branch-deletion FAIL is the known worktree false-negative; MERGED state verified via `gh pr view`.

### PR #201 (the 99-commit lead-gen-onepilot integration branch)
1. Created worktree `agentic-ops1-pr201-merge` on a temp branch from `origin/client/brisken/lead-gen-onepilot`, so the main clone's uncommitted WIP (other sessions') stayed untouched.
2. `git merge origin/main` → 8 conflicts; hooks/tests auto-merged cleanly.
3. Resolutions: ledgers (friction-register, docs/INDEX) took main's G1-reunified supersets (the branch's one extra register row was a corrupted-byte duplicate main carries fixed); session log + BTP checkpoint took the branch (newer); p2-bant spec + lead-gen strategy HTML took the branch (0.4.1 hardening vs swept 0.3.0 copies); rule_instantly_invasive merged main's `Bash|PowerShell` designation with the branch's readiness-check section; tools/INDEX merged both sides' rows.
4. Verified the merged tree: pytest tools/tests **317 passed** (PR #208's PowerShell suites + the demo-material gate together), check-index 51/51.
5. Pushed → CI went **red**: the new "Ruff (real-bug ruleset)" step flagged an unused `import io` in `tools/validate-demo-material.py` (pre-existing; the linter step is newer than the file). Reproduced locally with the CI's exact command, removed the import, re-verified (ruff clean, 12 gate tests pass, tool runs end-to-end), pushed.
6. All 4 checks green → merged via `gh-merge.sh 201` → squash `d6d9c26`, verified at the top of `origin/main` after fetch.

### Cleanup
1. Removed the merge worktree + temp branch. The directory deletion first failed with a file lock that turned out to be this session's own Bash cwd sitting inside it (from the local Ruff repro); deleted via the PowerShell tool (separate process), restored the Bash cwd to repo root, pruned the worktree registry.

---

## Key Decisions Made

### Merge main INTO the branch, not rebase
- **Choice:** `git merge origin/main` on a temp branch in a worktree, pushed back to the PR branch.
- **Rationale:** Shared branch with 99 commits and multiple contributing sessions; a rebase would rewrite pushed history. The merge preserved everything and made CI runnable for the first time.

### Ledger conflicts resolve toward main
- **Choice:** friction-register and docs/INDEX took main's versions wholesale.
- **Rationale:** PR #209 (G1 reunification) had already swept the branch's ledger rows to main, fixing a corrupted byte in one row along the way; main was the strict superset. Verified by row-set diff (`comm -23`), not assumption.

### Red CI = stop and fix, not merge-anyway
- **Choice:** The Ruff failure was fixed and re-verified before any merge attempt.
- **Rationale:** B6 Band 2; also the failure was real (dead import), 1-line fix.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| PR branch `client/brisken/lead-gen-onepilot` | Merge commit d39bd84 + fix bdad3d7 | Conflict resolution + Ruff fix |
| `tools/validate-demo-material.py` | Modified (on the PR branch) | Dropped unused `import io` |
| main | Squashes ec0bde2 (#207), d6d9c26 (#201) | Landed both PRs |
| Worktree `agentic-ops1-pr201-merge` | Created + removed | Isolated merge workspace |

---

## Current Status

Platform: brisken `infrastructure.yaml` declares `tier: "unknown"` (custom SaaS build, no workflow-engine ops budget).

Main now carries the full lead-gen-onepilot line: BTP gate wiring + self-gating one-pager generator, the onepilot-site inquiry feature, the orbit/platform page work, and the reconciled ledgers. No platform/ files were in either PR's diff, so no Vercel deploy follows. The main clone still sits on the merged (now historical) client branch with other sessions' uncommitted WIP; next work should branch fresh off main.

---

## Next Steps

1. USER: vault the Vercel token (`uv run $HOME/vault.py add "Vercel Matthias"`) and rotate at its 30-day expiry (it appeared in chat).
2. Plan the OnePilot proto migration to a brisken.com home, then take `brisken-onepilot-proto` down (owner directive 2026-07-10).
3. Next Brisken session: branch fresh off main; the old client branch is merged and its WIP files in the main clone need triage onto new branches per G1.

---

## Context for Next Session

### Files to Read First
- `docs/2026-07-10 - Brisken BTP Removal H2-H4/Checkpoint.md` (the work these PRs carried)
- `.claude/rules/rule_branch_isolation_and_shared_ledger.md` (G1 — ledger edits now go to main via docs PRs only)

### Open Questions
- Where does the proto's brisken.com home live (Brisken Lovable vs their own infra)?

### Working Notes

**CI's Ruff step runs on `tools/ .claude/hooks tools/tests`** with a real-bug ruleset. Before pushing anything touching those paths, run the CI's exact command locally: `uv run --no-project --with ruff ruff check tools .claude/hooks tools/tests`. The hook pytest suite alone does not cover it (cost one red CI cycle this session).

**`gh-merge.sh` false-FAILs when any worktree holds the PR's branch** (local branch deletion fails after the remote merge succeeds). Always verify with `gh pr view --json state`; both merges this session showed the pattern.

**A worktree directory can be locked by your own shell's persisted cwd.** `rm -rf` fails "Device or resource busy" if a prior Bash call cd'd inside; delete from the PowerShell tool (separate process) or move the cwd out first.

### Reference Materials
- PR #201: https://github.com/011matthias/agentic-ops1.01/pull/201 (MERGED d6d9c26)
- PR #207: https://github.com/011matthias/agentic-ops1.01/pull/207 (MERGED ec0bde2)

---

## How to Continue

Nothing is in flight from this session. The Brisken lead-gen line continues from main; the proto-migration plan (owner directive) is the next substantive piece.

---

## Strategic Feedback

### What Worked Well This Session
- The isolated-worktree merge pattern: 8 conflicts resolved and verified without touching the shared clone's dirty tree, and the temp branch pushed straight onto the PR ref.
- Row-set diffing (`comm -23` on `| 2026-` lines) turned two 16-hunk ledger conflicts into a two-minute superset proof instead of a hand-merge.

### Suggestions
- The main clone still holds the stopped file-placement session's uncommitted hook/rule WIP, now partially landed on main via this merge (post-write-gate + _scope.py went in; em-dash/reference-anchor/auto-approve hook edits did not). A short triage session would either commit the rest onto a fresh branch or discard what main superseded.

### System Health
- The new CI Ruff step caught a real dead import the 317-test suite could not; the local-verification checklist for hook/tool pushes should include the ruff command (added to Working Notes here; candidate for the B6 Band-1 verification precondition text).
- Autonomy score: 2 human interventions this session (both self-caught friction, no user corrections).
