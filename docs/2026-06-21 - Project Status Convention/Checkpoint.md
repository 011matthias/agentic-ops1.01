# Checkpoint: Project Status Convention

**Date:** 2026-06-21
**Status:** Shipped to `main` (3 PRs merged); Brisken pilot live

---

## Summary

Built a per-project "status-of-elements" convention for client work: each
workstream gets one maintained status file (a roll-up of its elements + where
each stands), with shared group context lifted to a group general reference.
Shipped in three merged PRs across one session, then hardened against its own
two failure modes (duplication, stale-by-recall).

---

## What Was Done This Session

### Convention + tooling (PR #198, merged 7f0b0e7)
1. `tools/project_status.py` (+ 19 tests): zero-dep scaffold + date-based staleness/malformed `--check`.
2. `skil_project-status` + `rule_project_status.md`: the convention (tracked `status/` home, element-vs-shared-context test, templates, supersession).
3. Wired `/comd_resume` (loads `status/*.md`), `/comd_checkpoint` (updates touched), `/comd_new-client` (scaffolds `status/`).
4. Brisken pilot: `status/p2-lead-gen-general.md` + p1 / p2-rome / p2-outreach / p2-onepilot-site / p2-targeting.

### Trim to pointers (PR #199, merged 1c2223b)
5. After a usefulness review, trimmed the pilot files so they INDEX the authoritative docs (`BLUEPRINT.md`/`ANNEALING.md` for p1, `dirk-go-live-sheet.md` for p2 gates) instead of restating them. Kills the duplicate-source-of-truth risk.

### Auto-surface staleness (PR #200, merged 0885a8d)
6. `project_status.py --sweep-stale [--once-per-day]` + SessionStart wiring in `wire-hooks.py`: stale/malformed files surface automatically every session, fail-open. Moves detection from Layer 3 (recall) to Layer 1 (fires on its own).

---

## Key Decisions Made

### Granularity: per-workstream + group general reference
- **Choice:** One status file per workstream; shared context (OnePilot vision, marketing plan) in `p2-lead-gen-general.md`, not duplicated.
- **Rationale:** Matches the user's general-vs-specific split; avoids restating shared context N times.

### Non-blocking by design, but detection automated
- **Choice:** No blocking hook on updates (agent discipline); a SessionStart sweep auto-detects rot.
- **Rationale:** User declined enforcement, but the repo's own history says recall-dependent maintenance doesn't hold; splitting "update" (manual) from "detect" (automatic) keeps it honest without a tripwire.

### Worktree-off-main for every PR
- **Choice:** Built each change in a throwaway worktree off `origin/main`, never the dirty primary tree.
- **Rationale:** Primary tree is ~56 commits ahead of main with unrelated WIP (W2 file-placement, prompt-queue, the 2026-06-20 reorg) entangled in `tools/INDEX.md` + `PROJECT-BOUNDARIES.md`; isolation kept each PR a clean off-main diff and left the Brisken WIP untouched.

---

## Files Modified
All landed on `main` via PR (not in the primary working tree).

| File | Action | Purpose |
|------|--------|---------|
| `tools/project_status.py` | Created | scaffold + `--check` + `--sweep-stale` |
| `tools/tests/test_project_status.py` | Created | 26 tests (check, scaffold, sweep, once-per-day) |
| `.claude/rules/rule_project_status.md` | Created | the convention policy |
| `.claude/skills/skil_project-status/SKILL.md` | Created | the procedure |
| `tools/wire-hooks.py` | Modified | SessionStart sweep wiring |
| `.claude/commands/comd_{resume,checkpoint,new-client}.md` | Modified | load / update / scaffold wiring |
| `tools/INDEX.md` | Modified | project_status row |
| `workspace/clients/brisken/status/*.md` | Created | pilot (general ref + 5 workstreams + README) |
| `workspace/clients/brisken/PROJECT-BOUNDARIES.md` | Modified | pointer to `status/` |

---

## Current Status

Convention live on `main`. Brisken pilot files in place, trimmed to pointers, and
auto-monitored for staleness. Primary working tree untouched (still on
`client/brisken/lead-gen-onepilot` at 27df8b8 with the prior sessions' OnePilot
WIP). No client-facing action taken.

---

## Next Steps

1. On next `/resume brisken`, the `status/` files load; correct any element state I pitched too optimistically (p1 was kept conservative, pointing to BLUEPRINT for slice truth).
2. When the W2 file-placement system (currently uncommitted on the user's tree) lands, add a `status/` row to the W2 home map in `rule_file_placement.md` (noted inline in `rule_project_status.md`).
3. Roll the convention to other active clients (meji, wimmer) on next touch, or via an explicit pass — not back-filled now.

---

## Context for Next Session

### Files to Read First
- `.claude/rules/rule_project_status.md` — the convention (loaded at session start anyway)
- `workspace/clients/brisken/status/` — the pilot files
- `tools/project_status.py` — the tool (`--check`, `--scaffold`, `--sweep-stale`)

### Open Questions
- Will the files actually get maintained? The SessionStart sweep answers "are they stale"; the response to a flag is update-in-place or delete (W1 §4), never nurse.

### Working Notes
- Three merged PRs: #198 (convention), #199 (trim to pointers), #200 (auto-sweep). All squash-merged; branches + worktrees cleaned up.
- The `--sweep-stale` hook is a `tools/` script in SessionStart (like `friction-watch.py`), so it is NOT in `EXPECTED_HOOK_SCRIPTS` and does not affect the hook-registry test.
- `tools/INDEX.md` and `PROJECT-BOUNDARIES.md` carry the user's unrelated WIP in the primary tree; that is why all work was done in worktrees off main and the primary versions were reverted to their pre-task (WIP-only) state.

### Reference Materials
- PRs: github.com/011matthias/agentic-ops1.01/pull/{198,199,200}
- Plan file: `~/.claude/plans/start-agentic-ops-i-soft-mitten.md`

---

## How to Continue

The convention is self-describing: `rule_project_status.md` + `skil_project-status`
load at session start, and the SessionStart sweep flags anything stale. To work a
Brisken workstream, edit its `status/` file in place. To add a workstream:
`uv run tools/project_status.py --client brisken --scaffold {slug} --group {group} --spec {id}`.

---

## Strategic Feedback

### What Worked Well This Session
- The "how useful is this?" question forced an honest second pass that produced the two hardening PRs (trim + auto-sweep). Asking for a candid assessment mid-build is a good lever; it caught the duplication and recall-dependence before they bit.

### Suggestions
- When a feature is approved against a plan that assumes a clean branch, sanity-check the actual tree state first (this tree's 56-commit gap + entangled WIP changed the whole ship approach). Surfacing that up front, as happened, saved a tangled PR.

### System Health
- Autonomy score: 0 user-correction interventions (2 self/structural frictions logged below).
- The B1 "deferral phrasing" reflex recurred again (stop-b1-gate caught it on the "how useful" close). The gate holds every time, but the generation-time phrasing habit is now a long-running cluster (2026-05-26 → 2026-06-21) that no structural fix has dissolved — it is a phrasing reflex, not a gate gap.
- New convention adds a 4th status surface (alongside PROJECT-BOUNDARIES, infrastructure.yaml, specs). Trimming to pointers kept it from competing with the docs that own the detail; watch that it stays an index, not a parallel record.
