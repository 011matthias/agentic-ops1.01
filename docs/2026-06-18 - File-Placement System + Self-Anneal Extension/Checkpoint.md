# Checkpoint: File-Placement System + Self-Anneal Extension

**Date:** 2026-06-18
**Status:** Shipped — 4 PRs merged to main, all CI-green

---

## Summary

System-infra session: built a repo-specific file-placement system (rule + skill + PreToolUse gate), hardened it against an adversarial review, de-duplicated the hooks' file-location mapping, then extended `/comd_system-dev` with convergence measurement + toolkit introspection (the "self-anneal" capability). All shipped to `main` via worktree PRs.

---

## What Was Done This Session

### File-placement system (PRs #193, #194, #195)
1. **#193** — `rule_file_placement.md` (W2) + `skil_file-placement` + `file-placement-gate.py` (PreToolUse(Write): deny root-writes / never-commit-into-tracked / scratch-into-non-gitignored; advise on unknown dirs) + `/.scratch/` gitignored home + wired into `wire-hooks.py` CANONICAL_HOOKS (12→13). 22 tests.
2. **#194** — hardening from a multi-agent adversarial review (19 verified defects): `.env.example`/templates no longer false-denied; durable source with scratch-ish prefix passes; ROOT_ALLOWLIST widened; word-boundary secret match; now denies yaml/p12/pfx/id_rsa/service-account secrets; token-dotfile + PII-export advisories; double-slash root-deny bypass closed; git-down static fallback mirrors the client-secret home. +45 tests (62 total).
3. **#195** — de-dup: extracted `.claude/hooks/_scope.py` (single source for the deliverable/comms path→category segments that were hand-copied across 4 hooks and had drifted); regrouped `rule_file_placement.md` §2 home map by parent home. Behavior byte-identical (all per-hook tests pass) + 18 `_scope` unit tests.

### Self-anneal extension (PR #196)
4. **#196** — extended `/comd_system-dev` (NOT a new `/anneal` command) with: `tools/anneal-metrics.py` (deterministic convergence + drift metrics, reuses `friction-watch.py` parser), `docs/anneal-ledger.md` (cycle-over-cycle record), Fixed-points section, Phase 1.5 Toolkit-Introspection Audit, Phase 4 CONSOLIDATE/DELETE/EXTEND/CREATE direction, Phase 6.5 Convergence Measurement, `--metrics-only`. +8 tests.

---

## Key Decisions Made

### File-placement: scratch home + deny floor
- **Choice:** `/.scratch/` at root; deny-floor + advisory hook strictness.
- **Rationale:** dot-prefixed reads as ephemeral; deny only the unambiguous cases, advise the rest (avoids false-blocks under bypassPermissions).

### Self-anneal: extend, do not create
- **Choice:** Fold the missing 20% (measure-convergence + introspection + consolidate-direction) into `/comd_system-dev` rather than adding a parallel `/anneal` command + skill. (User chose "extend-only" over my recommended standalone.)
- **Rationale:** the repo already had ~80% of the cycle (friction-watch + register + system-dev's design/approve/build). A new command would duplicate the build loop — the exact anti-pattern the file-placement work just fought. Metrics made deterministic via a tool so they can't drift or be hand-fudged.

### Adversarial review before declaring done
- **Choice:** ran a multi-agent workflow to stress the file-placement gate after it shipped green.
- **Rationale:** an enforcement gate's false positives/negatives don't show up in the tests you wrote. The review found 19 real defects (secrets passing, committable templates denied) — "shipped green" was not "correct."

---

## Files Modified

All merged to `main` via worktree PRs (feature branch → PR → CI-green auto-merge):

| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_file_placement.md` | Created | W2 home map + placement rules |
| `.claude/skills/skil_file-placement/SKILL.md` | Created | classify→map→default-safe→announce procedure |
| `.claude/hooks/file-placement-gate.py` | Created | PreToolUse(Write) placement floor |
| `.claude/hooks/_scope.py` | Created | shared path→category scope predicates (de-dup of 4 hooks) |
| `.claude/hooks/{post-write,em-dash-strip,reference-anchor,auto-approve-protected}-gate.py` | Modified | import shared `_scope` |
| `tools/wire-hooks.py` | Modified | wire file-placement-gate (13 hooks) |
| `tools/anneal-metrics.py` | Created | convergence + toolkit-drift metrics |
| `docs/anneal-ledger.md` | Created | cycle-over-cycle convergence record |
| `.claude/commands/comd_system-dev.md` | Modified | fixed-points + Phase 1.5 introspection + Phase 6.5 convergence + direction classification + --metrics-only |
| `tools/tests/test_{file_placement_gate,scope,anneal_metrics}.py` | Created | regression suites |
| `tools/INDEX.md` | Modified | rows for prompt-queue-ui (pre-existing gap) + anneal-metrics |
| `.gitignore` | Modified | `/.scratch/` |

---

## Current Status

All four PRs merged to `main`, post-merge `main` CI green (`e92efd8`). Full enforcement suite 179 tests green. The file-placement gate is live this session (wired at 13/13). No open branches; both temp worktrees removed. Working tree is still on `client/brisken/lead-gen-onepilot` with the (now-merged) system files present as untracked copies — harmless, identical to `main`, will reconcile when that branch next takes `main`. Do NOT delete those untracked copies (the live hooks read from the working tree).

---

## Next Steps

1. **Run the first real `/comd_system-dev` anneal cycle** — it will append a second ledger row and compute the first convergence delta against the 2026-06-18 baseline, and surface the introspection findings to act on.
2. **Resolve the baseline drift findings** (the audit's own first targets): CLAUDE.md advertises 51 skills (actual 34), 12 rules (actual 15); rules-LOC 2,199 over the stated 500 budget. Resolve by consolidation + a realistic budget decision, not silent count edits.
3. **Deep self-anneal of the most work-burdened fields** (rules layer, friction recurrence, client-comms/deliverable rules, web-build aesthetics) — the user requested a fresh-chat prompt for this; see the prompt produced alongside this checkpoint.

---

## Context for Next Session

### Files to Read First
- `docs/anneal-ledger.md` — the baseline convergence row + its 3 drift findings
- `.claude/commands/comd_system-dev.md` — the extended anneal loop (Phase 1.5 / 6.5)
- `tools/anneal-metrics.py` — what's deterministic vs judgment
- `.claude/rules/rule_file_placement.md` — W2, the file-placement source of truth

### Open Questions
- The rules-LOC budget: is the real target 250 (DECISION-TREE), 500 (system-dev), or "no budget"? A user decision, surfaced as a drift finding.
- The CLAUDE.md skill count (51): which denominator is canonical — 34 `skil_` dirs or 53 total? The vendored/non-`skil_` skills muddy it.

### Working Notes
- **`anneal-metrics` is working-tree-sensitive.** The first baseline row was computed from the brisken working tree (13 rules/216 register rows) but `main` had diverged (15/200). Caught at ship-time by re-running in the worktree off `origin/main`; regenerated before commit. Lesson: compute ledger/metrics artifacts from the merge-target tree, not the feature-branch working tree.
- **The "comms-log drift" was NOT a bug.** During the de-dup review I flagged em-dash-strip's exclusion of `comms-log.md` as drift; it is intentional (that hook MUTATES, so it must not rewrite the verbatim sent-message record — 2026-05-15 scope correction). Verified before shipping a behavior-changing "fix"; `_scope.py` now documents why each predicate differs.
- The file-placement gate's biggest residual: it's path-pattern-based, so an innocuously-named dump (`analysis-results.json`) into a tracked dir still passes silently — documented as the agent's W1 responsibility.

### Reference Materials
- PRs: #193, #194, #195, #196 on `011matthias/agentic-ops1.01`
- Plan file: `C:\Users\neuma_p1qrsic\.claude\plans\here-you-go-linked-perlis.md`

---

## How to Continue

Start a fresh chat for the deep self-anneal (the prompt is provided in this session). For the file-placement system, it is live and needs nothing further. To watch the anneal loop work, run `/comd_system-dev --metrics-only` for the cheap convergence read, or a full `/comd_system-dev` to act on the introspection findings.

---

## Strategic Feedback

### What Worked Well This Session
- The worktree-off-`main` ship pattern kept four system PRs cleanly isolated from the busy brisken branch, and caught the working-tree-divergence bug in the anneal baseline before it shipped.
- Plan-mode + AskUserQuestion on the genuine forks (scratch home, positioning) meant the build matched intent first time.

### Suggestions
- Consider a one-time reconciliation of the brisken working tree with `main` (it's now 15+ commits behind on system files), so future system work doesn't recompute against a stale tree.

### System Health
- The repo's anti-duplication ethos held under pressure: every task this session resolved toward consolidation (one `_scope.py`, one extended command) rather than new parallel primitives. The new anneal loop makes that pressure measurable.
- Autonomy score: 0 human interventions this session (the user's inputs were design decisions and approvals, not corrections). Two process near-misses (anneal baseline wrong-tree, comms-log mis-flag) were both agent-caught before shipping.
