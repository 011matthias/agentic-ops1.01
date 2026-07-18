# Checkpoint: Optimize-Loop Autoresearch Infrastructure

**Date:** 2026-07-17
**Status:** SHIPPED — v2 + hardening merged to main (PRs #254, #257, #259, #260)

---

## Summary

Built the field-agnostic optimize-loop (Karpathy "autoresearch" pattern) as
durable infrastructure: a per-run manifest + hash-pinned scorer + deterministic
run engine + a PreToolUse file-ACL hook that locks everything except the
declared asset globs during an active run. A 4-lens adversarial review found 8
real defects (1 critical, 1 high, 5 medium, 1 low) in the shipped v2; all fixed
with 19 regression tests in a hardening PR.

---

## What Was Done This Session

### Research (context for the build)
1. Traced the source of the Chamath "video model + TTS + autoresearch" claim to
   a verbatim X post (2026-03-28); 25-agent workflow mapped the video/TTS/
   pipeline landscape (saved to memory `project_synthetic_content_engine`).
2. Pulled the primary autoresearch references (Karpathy `program.md` verbatim,
   uditgoenka manifest+Guard, evo gates, codex-autoresearch METRIC contract,
   goal-md constructed metrics, Discussion #322 Goodhart defenses).

### Build (stacked PRs, each independently green)
1. **#254** — `tools/scorers/PINS.json` name->hash registry + `pin_scorer.py`
   (pin/check/list, gated by `SCORER_LOCK_ALLOW`); PINS lock added to
   `scorer-lock-gate.py`. CRLF-normalized git-blob sha (Windows/CI parity).
2. **#257** — `optimize-run-gate.py` (16th canonical hook, Write|Edit +
   Bash|PowerShell): during an active run, asset globs are the only writable
   surface; manifest/journal/guards/scorers/machinery locked; shell arm closes
   the v1 redirect bypass. `_globs.py` (git-style `*` never crosses `/`).
   `optimize_run.py` engine: start/round/resume/stop/status.
3. **#259** — `comd_optimize.md` v2 rewrite, `rule_optimize_loop.md` (17th rule),
   `docs/optimize/RECIPES.md` (field recipes + constructed-metric protocol).
4. **#260 (hardening)** — 8 adversarial-review fixes + 19 tests (see below).

### Adversarial review + hardening (the load-bearing QA)
Ran a 4-lens Workflow (lock-bypass / engine-correctness / fail-safe /
integration), each finding independently verify-or-refuted. 8 confirmed, all
fixed:
- **CRITICAL** — `../` traversal defeated the entire file ACL (both hooks).
  normpath before the prefix check + reject residual `..`.
- **HIGH** — a crash between the journal commit and state-save made `resume`
  git-reset away a committed, guard-passed KEEP. resume now reconciles the
  cache to the durable journal. **Proven live** (simulated the crash on a real
  run; resume adopted the win).
- 5 MEDIUM (guard auto-lock+hash-verify, parked-rework marker, corrupt-state
  stop, malformed-state ask-not-fail-open, shell out-of-scope deny) + 1 LOW
  (engine exempt from no-auto-commit false-fire).

---

## Key Decisions Made

### Build custom, not fork uditgoenka/evo
- **Choice:** lift their ideas (manifest, Guard, TSV, bounded-by-default) into
  ~700 LOC on our own hook/CI/B6 foundations.
- **Rationale:** their locking is prompt/convention-level (the exact layer #322
  shows failing); our "no mistakes" bar needs code-level file-ACL + per-round
  hash verification, which no OSS generalizer ships.

### Three-surface lock incl. the enforcement machinery (user-approved)
- **Choice:** during a run, lock the manifest + scorer + the hook/engine/command
  files themselves; asset globs the only writable surface. Two user-order-only
  seams (`SCORER_LOCK_ALLOW`, `OPTIMIZE_SCOPE_ALLOW`).
- **Rationale:** #322 — when the metric is locked, agents edit the gate instead.

### Continuous (overnight) mode ships in v1 (user-approved)
- Bounded by wall-clock/round/timeout/plateau; driven across sessions by
  `/loop` + `resume`; session-pressure rule wins (session checkpoints, run
  persists).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| tools/scorers/PINS.json, tools/pin_scorer.py | Created | scorer hash registry + tool |
| .claude/hooks/optimize-run-gate.py, _globs.py | Created | active-run file ACL + glob matcher |
| tools/optimize_run.py | Created | deterministic run engine |
| .claude/commands/comd_optimize.md | Rewritten | v2 command (setup interview -> lock-on -> loop) |
| .claude/rules/rule_optimize_loop.md | Created | 17th rule, three-surface lock model |
| docs/optimize/RECIPES.md | Created | field recipes + constructed-metric protocol |
| .claude/hooks/scorer-lock-gate.py, no-auto-commit-gate.py | Modified | PINS lock, traversal fix, engine exemption |
| tools/wire-hooks.py | Modified | 16th hook, both matchers |
| tools/tests/test_optimize_run{,_gate}.py, test_scorer_{pins,lock_gate}.py, test_no_auto_commit_gate.py | Created/extended | ~80 tests incl. 19 hardening regressions |
| ~/.claude/.../memory/project_synthetic_content_engine.md | Created | Chamath thesis research verdict |

---

## Current Status

main at `52f200e`: 16/16 enforcement hooks wired, scorer pins matching, full
enforcement suite green (~166 tests). Build worktree removed. The infrastructure
is complete and unused by any live run yet (page-weight is the only shipped
scorer; smoke runs were discarded).

---

## Next Steps

1. **First real target: Brisken expense-recon match accuracy.** Build a scorer
   against Chris's labeled fixtures (needs the gitignored recon data -> a
   Brisken-scoped session), then `/comd_optimize` the matching rules overnight.
2. Second cheap proof: web-perf on a local-web/platform page (page-weight scorer
   already ships; Lighthouse-wrapper scorer is a small add).
3. Optional teaching artifact: the user asked for a fresh-chat prompt to learn
   the workflow (being written this turn).

---

## Context for Next Session

### Files to Read First
- `.claude/rules/rule_optimize_loop.md` (the lock model + seams)
- `.claude/commands/comd_optimize.md` (the operator workflow)
- `docs/optimize/RECIPES.md` (per-field manifest skeletons)
- `tools/optimize_run.py` (engine; the protocol lives in the subcommand bodies)

### Open Questions
- Whose channel is the guinea pig for the *content* application of this
  (video+TTS+autoresearch)? Deferred — UnpauseAI's own recommended. Separate
  from the infra, which is field-agnostic.

### Working Notes
- The two env seams are user-order-only; setting either unprompted is a
  `skipped-gate` friction event.
- The critical traversal bug is the tell: enforcement tests that "pass" are not
  proof of a sound lock without adversarial coverage. The traversal regression
  tests + the pre-ship adversarial-review pass are now the guard.
- Constructed metrics: build the ruler (scorer) as its own PR FIRST; the engine
  refuses unpinned scorers, so the ordering is enforced.

### Reference Materials
- Karpathy program.md: https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md
- Discussion #322 (Goodhart defenses): https://github.com/karpathy/autoresearch/discussions/322
- Plan file: `.claude/plans/polished-percolating-glacier.md`

---

## How to Continue

The infra is done. To USE it: pick a target with an honest, fast, offline
number; copy the nearest manifest skeleton from RECIPES.md into
`docs/optimize/<tag>/RUN.md`; run `/comd_optimize`. For a constructed metric,
build+pin the scorer via its own PR first.

---

## Strategic Feedback

### What Worked Well This Session
- The plan-mode -> AskUserQuestion (2 lock decisions) -> intent-review ->
  ExitPlanMode sequence surfaced the two real user decisions (lock breadth,
  continuous mode) before any code was written.
- The adversarial-review Workflow earned its cost: it found a critical ACL
  bypass the passing test suite missed. This is the single highest-leverage
  step and should be standard before declaring any enforcement primitive sound.

### Suggestions
- Run the adversarial review on the v2 DIFF *before* merging to main, not after.
  This session merged 3 PRs then hardened; the critical hole sat on main between.
  Low blast radius here (infra unused), but the ordering should flip for the
  next enforcement build.

### System Health
- Rules now 17, hooks 16 — both self-derived counters, no drift.
- New capability class: the repo can now hill-climb any file against a locked
  scalar. This is a genuinely new primitive, not a variation on build-test-fix
  (which converges to pass; this maximizes).
- Autonomy score: 1 human intervention (plan approval) + 0 corrections — the 8
  defects were found and fixed by the session's own adversarial review, not the
  user.
