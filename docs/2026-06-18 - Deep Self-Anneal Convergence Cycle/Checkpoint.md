# Checkpoint: Deep Self-Anneal Convergence Cycle

**Date:** 2026-06-18
**Status:** Shipped — PR #197 merged to main (CI green)

---

## Summary
Deep, adversarial self-anneal of the toolkit's most work-burdened fields (rules, skills, hooks, doc-drift). Resolved all 3 baseline-ledger drift items, cut the skill-map validator noise from 113 to 27 findings, single-sourced the duplicated voice-ban rules, and strengthened two gates, against the 2026-06-18 baseline. Verdict: converging.

---

## What Was Done This Session
### 1. Data-driven field ranking + adversarial audit
- Ranked work-burdened fields from `anneal-metrics`, `friction-watch`, 30-day churn, and session logs.
- Ran a parallel Workflow: 4 field auditors → per-finding adversarial refutation. 30 findings, 28 survived, 2 killed (a cross-ref to an upstream skill; a stop-b1 regex tightening that would have caused false negatives).
- Caught two red herrings the raw counts implied: the cd-cwd cluster (already killed 2026-06-09) and the B1-deferral cluster (gate already holds every time) — both got NO new gate.

### 2. Package A — drift (3 → 0)
- `CLAUDE.md`: Skills 51→34, Rules 12→15.
- Retired the 250/500-vs-2199 rules-LOC budget contradiction (DECISION-TREE, OVERVIEW-TEMPLATE, anneal-metrics) for a per-file ~250 soft ceiling + "no duplicated bans"; the tool now reports per-file overages as advisory, not drift.

### 3. Package B — rules consolidation
- `rule_anti_slop` is now the single canonical voice-ban list; deliverables / platform_standards / human_communication cross-reference it and keep only surface-specific deltas. Killed the real drift (e.g. `empower` enforced by the linter but missing from 2 rule copies).
- 45-abbrev gloss list deduped to human_communication §7 + a test asserting rule §7 == `validate-proposal.py`.
- Platform contact email aligned to `admin@` (already canonical in code); dropped dead "max 2 retired" notes; fixed 2 do-as-I-say exemplar em-dashes.

### 4. Package C — skill-map validator (113 → 27)
- Pack spines now mark their consolidation-stub modules reachable (−51 FP); vendored guide-doc example paths fenced (−26 FP).
- Repointed 9 real dead pointers in `skil_build` + `api-boilerplate`. + regression tests.

### 5. Package D — gate strengthening
- `instantly-invasive-gate`: a curl body flag (`-d`/`--data`/`-F`) with no `-X` now reads as POST (was slipping).
- New `tools/assert-live-origin.py`: stack-agnostic deploy-origin parity (the structural kill for the localhost-vs-deployed-origin class).

### 6. Ship
- Worktree off `origin/main` → committed → PR #197 → CI green (4 checks) → squash-merged. Worktree + branches cleaned up.

---

## Key Decisions Made
### Re-baseline against main, not the working tree
- **Choice:** When the worktree off `origin/main` showed 15 rules / 2199 LOC (not the 13 / 1939 my audit saw), I rebuilt every count and line number against the true merge base before editing.
- **Rationale:** The audit ran on the working tree, which had diverged from main. Editing against stale line numbers would have corrupted the change.

### Did not chase the LOC target
- **Choice:** Accepted −14 rules LOC (vs the estimated −55) rather than compressing the cross-references further.
- **Rationale:** The real B1 win is killing the divergence + locking it with a test. Over-compressing to hit a number Goodharts a fixed point ("fewer assets is a direction, not a number to game").

### Built the deploy-parity tool, deferred the brisken-recon wiring
- **Choice (user default #3):** Shipped `assert-live-origin.py` as a system tool this cycle; wiring it into the brisken-recon Fly deploy is deferred to the brisken session.
- **Rationale:** It can be tested against the live origin where the deploy script lives.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `CLAUDE.md` | Modified | Skills 51→34, Rules 12→15 |
| `.claude/rules/rule_anti_slop.md` | Modified | Canonical voice-ban home; +union item |
| `.claude/rules/rule_deliverables.md` | Modified | Cross-ref voice bans + gloss list; drop max-2 |
| `.claude/rules/rule_platform_standards.md` | Modified | §2 cross-ref; contact email → admin@ |
| `.claude/rules/rule_human_communication.md` | Modified | §2 cross-ref; 2 exemplar em-dashes fixed |
| `.claude/skills/skil_meta-builder/modules/DECISION-TREE.md` | Modified | Budget → per-file ceiling + no-dup-bans |
| `.claude/skills/skil_system-digest/modules/OVERVIEW-TEMPLATE.md` | Modified | Drop /250 budget literal |
| `.claude/commands/comd_system-dev.md` | Modified | Phase 6 budget discipline updated |
| `.claude/skills/skil_build/modules/{MAKE,TRIGGER-DEV}-BUILD.md` | Modified | Repoint 6 dead rule-paths |
| `.claude/skills/skil_api-boilerplate/SKILL.md` | Modified | Fix template path (skil_ prefix) |
| `.claude/hooks/instantly-invasive-gate.py` | Modified | curl body-flag implies POST (H5) |
| `tools/anneal-metrics.py` | Modified | Per-file ceiling advisory; drop budget drift |
| `tools/check-skill-map.py` | Modified | Pack-module reachability + example-path fences |
| `tools/assert-live-origin.py` | Created | Stack-agnostic deploy-origin parity (H6) |
| `tools/INDEX.md` | Modified | Row for assert-live-origin.py |
| `tools/tests/test_{anneal_metrics,check_skill_map,instantly_invasive_gate}.py` | Modified | Cover new behavior |
| `tools/tests/test_{voice_ban_consistency,assert_live_origin}.py` | Created | Lock the consolidation + parity tool |
| `docs/anneal-ledger.md` | Modified | Phase-6.5 convergence row |

---

## Current Status
PR #197 merged to `main`. Convergence row recorded: drift 3→0, rules 2199→2185 LOC, net asset +1 (the one cited tool), 0 new rules/skills, verdict **converging**. `uv run pytest -q` → 193 passed.

---

## Next Steps
1. **Wire `assert-live-origin.py` into the brisken-recon Fly deploy** (deferred to the brisken session — test against `brisken-expense-recon.fly.dev`).
2. **Per-file rule ceiling**: 3 rules now flagged as split candidates by anneal-metrics (`rule_client_page_structure` 273, `rule_human_communication` 273, `rule_platform_standards` 267) — owner-judgment splits for a future cycle.
3. **skill-map residual (27)**: the deferred S8 bare-prose paths inside *deprecated* stub skills + genuinely-stale proposal paths — fold into the eventual stub removal, not worth touching in isolation.
4. **gate-skip-detector precision**: widen its validation-lookback so a pytest/check-skill-map run earlier in a long session is credited before a publish (see friction row).

---

## Context for Next Session
### Files to Read First
- `docs/anneal-ledger.md` — the convergence trend (this cycle is the new reference row).
- `.claude/commands/comd_system-dev.md` — the self-anneal loop (Phase 1.5 + 6.5).
- `tools/anneal-metrics.py` — per-file ceiling advisory is the new bloat signal.

### Open Questions
- Should the 3 oversized rules be split, or is the per-file 250 ceiling too tight for genuinely load-bearing rules? (Owner judgment.)

### Working Notes
- The adversarial audit's full output is in the workflow transcript; 2 findings were killed (S6 sales-third-party is an upstream skill; H3 stop-b1 tightening regresses real catches).
- Re-baseline gotcha: `origin/main` was ahead of the working tree (15 rules incl. `rule_branch_isolation_and_shared_ledger`, `rule_enumerate_before_build`, `rule_file_placement`). Always branch off main and recount in the worktree.
- `gh pr merge --delete-branch` false-FAILs the LOCAL branch delete when a sibling worktree holds main; the remote merge still succeeds (verified via `mergedAt`). Known memory.
- LOC consolidation was modest (−14) because cross-references are nearly as long as the compact one-line lists they replace; the win is drift-elimination + the consistency test, not raw LOC.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/197

---

## How to Continue
The system change is fully merged and verified. Next system-dev cycle should read `docs/anneal-ledger.md` (Phase 0 backlog), pick up the per-file-ceiling split question and the gate-skip-detector precision item. The brisken-recon deploy wiring belongs in a brisken session.

---

## Strategic Feedback

### What Worked Well This Session
- The plan-gate (ranked fields + concrete diffs + convergence read) before any edit made approval a single "Go" and kept the whole cycle on rails.
- Re-baselining against the actual merge base before editing prevented a corrupted change set — the working-tree-vs-main divergence would have silently broken every line-number-dependent edit.

### Suggestions
- The per-file rule ceiling (250) now flags 3 rules. Decide once whether those are genuine split candidates or whether the ceiling should be raised for hard-constraint rules, so the advisory does not read as permanent noise.

### System Health
- Validator signal sharpened hard: `check-skill-map` 113→27 means real routing drift is no longer buried under 77 false positives. The residual 27 is honest (deprecated-stub prose + stale proposal paths).
- The `gate-skip-detector` fired a false positive on this session's publish despite a clean `pytest` run earlier — its validation-lookback is buffer-limited (a known gate-precision class; logged).
- Autonomy score: 0 human interventions — fully autonomous session (1 self-detected gate-precision observation logged).
