# Checkpoint: Ruff Push Gate CI Prevention

**Date:** 2026-07-17
**Status:** SHIPPED — PR #267 merged to main, CI green

---

## Summary

Diagnosed a one-day cluster of CI `Enforcement hook tests` failures (6 red runs across PRs #201/#250/#257/#261/#264) as a single category — "passes locally, fails in the clean CI env" — and shipped a structural recurrence-kill: a `git push`-time ruff gate plus a one-command local CI-parity runner.

---

## What Was Done This Session

### Diagnosis
1. Reproduced the exact CI enforcement-hooks job locally (ruff + check-index + pytest); main was already green, so nothing was currently red.
2. Pulled the real failure logs for every red run since 07-16 (5 runs / 4 branches). All were "passes locally, fails clean CI":
   - lead-desk-cockpit (#250): ruff `F401` unused `io` + `F841` unused `core_r`
   - optimize-v2-engine (#257): ruff `F401` unused `pytest`
   - deck-foundation-v2 (#264): ruff `F401` unused `io`
   - optimize-multi-project (#261): pytest collection `ModuleNotFoundError: yaml`
   - (#201 lead-gen-onepilot was a stale "last week" run, already merged/green)
3. Root cause: a burst of new Python/test files pushed without running ruff / the isolated pytest locally. The opt-in `.pre-commit-config.yaml` ruff hook would catch the lint ones but is not installed.

### Build (user picked "blocking push gate")
1. `.claude/hooks/ruff-push-gate.py` — PreToolUse:Bash|PowerShell. On `git push`, when the push's diff touches a `.py` under `tools/` or `.claude/hooks/`, runs the exact CI ruff command; ruff clean → silent allow, ruff fails → `permissionDecision:"ask"` with the lint output inline. Mirrors no-auto-commit-gate.py (ask, never hard deny); `RUFF_PUSH_GATE_ALLOW=1` override; fail-open on any error/timeout.
2. `tools/preflight-hooks.py [--full|--pytest]` — one command reproducing the whole CI hooks job locally (ruff + INDEX + pytest). The `--full` half catches the pytest-collection class the fast gate can't.
3. Wired into `wire-hooks.py` (CANONICAL_HOOKS + EXPECTED_HOOK_SCRIPTS → 17 hooks); INDEX row added; `rule_no_auto_commit.md` Band-1 precondition documents both.
4. Tests: `tools/tests/test_ruff_push_gate.py` (11 cases).

---

## Key Decisions Made

### Blocking push gate over preflight-tool-only
- **Choice:** Ship the blocking `git push` hook, not just a documented runner.
- **Rationale:** User picked it (AskUserQuestion). Doctrine (self-anneal Layer 1) says recurrent + preventable → structural gate that can't be forgotten, not a rule/memory that failed by recall 5× in a day.

### `"ask"`, not hard `"deny"`
- **Choice:** Surface the lint failure to the human, don't block outright.
- **Rationale:** Consistent with no-auto-commit / instantly gates; forgiving of shared-tree false-positives (a sibling session's uncommitted broken file); the agent's correct response is to fix the lint, not approve.

### Ruff-only in the blocking gate; pytest in the runner
- **Choice:** Push gate runs ruff only (~1s); the slow pytest stays in CI + `preflight-hooks.py --full`.
- **Rationale:** 4/5 failures were ruff; keeps push latency low and under the 10s wired hook timeout. The 1 dep-class failure is already convention-mitigated (drive PEP-723 tools as subprocesses in tests) and covered by `--full`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/ruff-push-gate.py` | Created | The blocking git-push ruff gate |
| `tools/preflight-hooks.py` | Created | One-command local CI-parity runner |
| `tools/tests/test_ruff_push_gate.py` | Created | 11 gate regression tests |
| `tools/wire-hooks.py` | Modified | Wire the new hook (17/17) |
| `tools/INDEX.md` | Modified | Row for preflight-hooks.py |
| `.claude/rules/rule_no_auto_commit.md` | Modified | Band-1 precondition documents the gate + runner |

---

## Current Status

PR #267 squash-merged to main (`99a8167`) 2026-07-17 14:28Z. All CI green, including the Enforcement hook tests job (37s). Worktree removed. The local main tree still shows 16 wired hooks; a SessionStart `wire-hooks.py --ensure` re-wires to 17 once this session's main is pulled up to the merge.

---

## Next Steps
1. (Optional, user's call) Close the `git -C <path> push` blind spot in `no-auto-commit-gate.py` — `\bgit\s+push\b` misses `git -C X push`, so worktree-style pushes evade the ship gate. Its own small PR; higher blast radius (touches the tested ship gate shared by live sessions).
2. Nothing else pending; the fix is live.

---

## Context for Next Session
### Files to Read First
- `.claude/hooks/ruff-push-gate.py` (the gate)
- `tools/preflight-hooks.py` (the runner)
- `.claude/rules/rule_no_auto_commit.md` (Band-1 precondition, now documents both)

### Open Questions
- None. The `git -C` ship-gate gap (Next Steps #1) is a flagged fork, not a blocker.

### Working Notes
- CI hooks job = 3 steps: ruff (`uv run --no-project --with ruff ruff check tools .claude/hooks tools/tests`), `check-index.py`, pytest (`uv run --no-project --with pytest --with python-pptx pytest tools/tests`). The pytest env is a hardcoded, incomplete dep list — a test importing a new third-party dep breaks collection. House convention (already landed on main in `test_optimize_overview.py`): drive PEP-723 tools as subprocesses so their deps isolate, never `import yaml` at collection time.
- ruff on this machine: not on PATH; `uv run --no-project --with ruff` is ~1.5s cold / ~0.7s warm.
- Verified end-to-end (no mocks): clean tree → silent allow; a real `import io` → actual ruff returns `ask` with `F401 io imported but unused` inline. The gate's own dogfood caught an F401 in its first draft.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/267
- Merge commit: `99a8167`

---

## How to Continue

The fix is shipped and live. If picking up the optional follow-up, cut a `sys/` branch, tighten `no-auto-commit-gate.py`'s push regex to tolerate `git -C <path>` (and mirror it into `ruff-push-gate.py`'s `GIT_PUSH`), add a regression test row, PR it.

---

## Strategic Feedback

### What Worked Well This Session
- The AskUserQuestion on enforcement level (blocking gate vs runner-only vs CI-only) was a clean, real fork — the answer changed what got built, and it front-loaded the one high-blast-radius decision on a shared tree.

### Suggestions
- The `.pre-commit-config.yaml` ruff hook is opt-in and demonstrably not installed by whoever pushed the 5 red PRs. The new push gate makes it moot for the lint class, but if you want defense-in-depth, `pipx run pre-commit install` per clone would also catch it at commit time.

### System Health
- The CI pytest step's dep list (`--with pytest --with python-pptx`) is a hardcoded allowlist that silently breaks on a new import. The push gate doesn't cover that class (only `--full` preflight + CI do). If dep-class collection failures recur, the structural fix is to make the CI pytest env derive its deps or run collect-only in the gate.
- Autonomy score: 1 human-visible friction (a closing deferral caught by the B1 stop-hook), same recurring deferral-phrasing class the hook has held all day. No approach corrections.
