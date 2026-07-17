# Checkpoint: System-Dev Sibling-Session Guard

**Date:** 2026-07-12
**Status:** Complete — two PRs merged to main (#214, #215)

---

## Summary
A full `/comd_system-dev` self-anneal cycle: audit → build → ship. Shipped the long-deferred live-sibling-session guard plus three companion fixes (CLAUDE.md drift, `edge_cdp.py`, Dirk mailbox watcher) in PR #214, then closed the last open item (first `docs/reviews/` artifact) in PR #215.

---

## What Was Done This Session
### Audit (Phase 0-3)
1. Ran anneal-metrics + friction-register analysis; ranked friction by ROI. User chose audit-only, then greenlit "fix all."

### Build + ship — PR #214 (merged, commit 5027295)
1. **A — live-sibling-session guard:** `tools/session_registry.py` (per-session heartbeat keyed on the git working-tree root; separate worktrees don't trip it) + `.claude/hooks/sibling-session-gate.py` (14th canonical hook, SessionStart advisory) + heartbeat refresh in `session-pressure-meter.py` + `wire-hooks.py` registration + `test_session_registry.py` (13 tests, incl. gate end-to-end).
2. **B — CLAUDE.md count drift → 0:** 29→30 cmds, 34→35 skills, 15→16 rules.
3. **C — `tools/edge_cdp.py`:** raw-CDP Edge helper (targets/eval/shot/token), promoted from proven `.scratch/cdp.py`+`grabtoken.py`; `select_target` unit-tested.
4. **D — `tools/brisken-mailbox-watch.py`:** READ-ONLY 3-surface (Drafts/Sent/Calendar) Dirk mailbox watcher.
5. INDEX rows for all 3 tools; anneal-ledger convergence row appended (Phase 6.5).

### Close-out — PR #215 (merged, commit 9b7952c)
1. Verified the guard is live on main (`HOOK_COUNT=14`, wired, on disk).
2. First `docs/reviews/` artifact (`docs/reviews/2026-07-12.md`) — silences the reviews-never-written cadence signal, sets the baseline.

### Memory hygiene
Updated `project_harness_hardening_2026-07-10` (STATUS → shipped), added tool pointers to `reference_user_edge_cdp_9222` (edge_cdp.py) and `reference_dirk_outlook_com_drafts` (brisken-mailbox-watch.py), trimmed the MEMORY.md index line.

---

## Key Decisions Made
### Work in isolated worktrees off origin/main, never the shared client clone
- **Choice:** All three PRs (build, review, this checkpoint) authored in throwaway worktrees off `origin/main`, committed with explicit pathspecs, then cleaned up.
- **Rationale:** The primary clone sits on `client/brisken/lead-gen-onepilot`, 79 commits behind main, with 40+ unrelated modifications and live sibling sessions. Building there would sweep in a sibling's WIP and guarantee stale-base merge conflicts. Dogfoods the exact pattern the sibling-guard promotes.

### Guard keyed on the working-tree root, not the shared .git
- **Choice:** `session_registry` matches siblings by identical working-tree root.
- **Rationale:** Worktrees have distinct roots and isolated indexes, so they don't collide; only two sessions in one working tree do. This makes "use a worktree" the exact remediation the advisory recommends, and keeps properly-isolated parallel work silent.

### C and D promoted but not live-verified
- **Choice:** Built `edge_cdp.py` / `brisken-mailbox-watch.py` from proven `.scratch/` code, unit-tested the pure parts, and explicitly flagged the CDP/COM live paths as unverified this session.
- **Rationale:** No live Edge-on-:9222 or Dirk-mailbox available; asserting they "work" would be verification theater. Honesty over a false green.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/session_registry.py | Created | Sibling-session heartbeat sensor |
| .claude/hooks/sibling-session-gate.py | Created | SessionStart collision advisory (14th hook) |
| .claude/hooks/session-pressure-meter.py | Modified | Heartbeat refresh each tool call |
| tools/wire-hooks.py | Modified | Registered the 14th hook |
| tools/tests/test_session_registry.py | Created | 13 registry + gate tests |
| tools/edge_cdp.py | Created | Raw-CDP Edge helper |
| tools/tests/test_edge_cdp.py | Created | select_target unit tests |
| tools/brisken-mailbox-watch.py | Created | 3-surface Dirk mailbox watcher |
| tools/INDEX.md | Modified | Rows for the 3 new tools |
| CLAUDE.md | Modified | Count drift → 0 (30/35/16) |
| docs/anneal-ledger.md | Modified | Phase 6.5 convergence row |
| docs/reviews/2026-07-12.md | Created | First review artifact (PR #215) |

---

## Current Status
Both PRs merged to main; CI green on all four jobs each. Three throwaway worktrees created and cleaned up. The sibling-guard is deployed on main and self-wires (14/14) at SessionStart on any up-to-date tree. No platform/ files changed, so no Vercel deploy surface.

---

## Next Steps
1. **Live-verify** `edge_cdp.py` against a real Edge on :9222 and `brisken-mailbox-watch.py` against the live Outlook profile before trusting a token capture or mailbox-placement claim.
2. From the harness-hardening memory (still open, not this cycle's scope): the live PowerShell-gate proof on a main session, and the weekly-synthesis scheduled-task registration (`--detach` worktree + fresh Resend key).
3. Optional next `/system-dev`: the 3 rule files over the 250-line per-file ceiling (split candidates); a "verify behavior, not state" gate for the recurring verification-theater class (17 unresolved).

---

## Context for Next Session
### Files to Read First
- docs/reviews/2026-07-12.md — the review + baseline metrics
- docs/anneal-ledger.md — convergence trend
- .claude/hooks/sibling-session-gate.py + tools/session_registry.py — the new guard

### Open Questions
- Should `anneal-metrics` / `comd_system-dev` Phase 1 read `origin/main` blobs (like `weekly_synthesis.py`) so an audit run from a far-behind branch doesn't yield stale findings? (See friction below.)

### Working Notes
- The audit's Finding B initially reported a stale "rules-LOC 500 budget / drift 4" problem because it ran against the client-branch working tree (79 behind main). The real main state was drift 3, per-file 250 ceiling — the 500-budget model was already retired upstream. Discovered only when the build worktree was cut off origin/main. Lesson: verify base currency before presenting system metrics.
- `gh pr merge` returns empty output but succeeds (the sibling-worktree false-FAIL noted in `reference_repo_tooling_gotchas`); the remote PR state is the source of truth — confirmed MERGED for both.
- The gate-skip-detector's "pre-publish, no validation in buffer" reminder is a false positive on multi-step ship flows: it only sees the immediate command buffer, not the pytest + CI validation that ran earlier in the session.

### Reference Materials
- PR #214: https://github.com/011matthias/agentic-ops1.01/pull/214
- PR #215: https://github.com/011matthias/agentic-ops1.01/pull/215

---

## How to Continue
The guard activates automatically next session on an up-to-date tree. To close the remaining harness-hardening items, run a session from a clone on main and do the PowerShell-gate proof + weekly-synthesis registration. To act on the review, live-verify the two client-specific tools.

---

## Strategic Feedback

### What Worked Well This Session
- The audit-then-greenlight rhythm ("fix all") let the whole cycle run autonomously without per-step approvals. The AskUserQuestion at the Phase-4 gate captured the one real decision cleanly.

### Suggestions
- Running system-dev from the primary clone while it sits 79 commits behind main cost a stale-base audit. Consider running `/comd_system-dev` from a fresh `origin/main` worktree (or having its metrics read origin/main blobs) so the analysis reflects live state.

### System Health
- The self-anneal loop is converging behaviorally: the two loudest register buckets (B1 closing-offers, `cd`-slow-paths) are now hook-handled and fired correctly this session; the one loud unbuilt item (sibling-guard, 4 register occurrences) is now shipped. `docs/reviews/` is no longer empty.
- Autonomy score: 1 human intervention this session (a "continue" nudge after network diagnostics; see friction).
