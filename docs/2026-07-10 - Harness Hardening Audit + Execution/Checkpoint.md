# Checkpoint: Harness Hardening Audit + Execution

**Date:** 2026-07-10
**Status:** All four PRs merged to main (#208, #209, #210, #211); three user actions pending

---

## Summary

Ran a 10-agent adversarially-verified audit of the system's prompt/context/harness/loop engineering (verdict: loop=frontier, other three strong; 24/25 gaps confirmed), then executed the approved three-phase fix plan end to end: PowerShell gate coverage, ledger reunification, anneal-cadence infrastructure, and the agent behavioral-eval harness — each as its own worktree branch, shipped through the B6 autonomous lane on CI-green auto-merge.

---

## What Was Done This Session

### Audit (Workflow, 10 agents, every gap adversarially verified)
1. Five dimension audits + verify passes; headline confirmed gaps: PowerShell tool invisible to all five command gates (real `vercel.cmd deploy --prod` bypass on record), no behavioral eval layer, anneal synthesis stalled since 2026-06-18, register fragmented across lineages.
2. One claim refuted by the verifier: hook-log.txt IS a structured 25k-line gate-fire store (only an aggregator is missing).

### PR #208 — PowerShell gate coverage (merged 827575d)
1. CANONICAL_HOOKS matchers `Bash` → `Bash|PowerShell` (2 spots); settings.local.json self-heals via SessionStart `--ensure`.
2. New `.claude/hooks/_shell.py` matching-view normalizer (PS call-operator strip, `.cmd/.exe/.bat/.ps1` → stem, backslash→slash) + unit suite pinning both recorded live bypasses.
3. cd-guard PowerShell arm (`Set-Location|chdir|sl|cd`, `-Path/-LiteralPath`, PS here-string + `<#...#>` masking, `Push-Location` exempt); no-auto-commit/post-action/gate-skip match on the normalized view; gate-skip readonly anchor survives PS statement prefixes.
4. Instantly gate: `-Method POST|PUT|PATCH|DELETE` signal + Layer-A reorder closing the `analytics && POST activate` compound bypass.
5. First behavioral suites for post-action-gate + gate-skip-detector; 269 tests green.

### PR #209 — Ledger reunification, G1 (merged 0f03540)
1. Union merge: register 200→354 rows, INDEX 161→235 (both sides insertion-only, so conflict-free by construction), chronologically re-sorted.
2. Swept in 73 checkpoint files that existed in NO commit anywhere (working-tree only) — 0 new dead INDEX links vs pristine main (58 pre-existing March-era dead links untouched).
3. New git-hygiene register row documenting the fragmentation.

### PR #210 — Anneal cadence infra (merged 64cfd39)
1. friction-watch: prefix-match unresolved counting (`No (caught by hook)` = unresolved, separate hook-contained bucket; stale excludes, concentration keeps) — kills the Goodhart-flattering 67-vs-true undercount.
2. New cadence signal (ledger >21d stale / reviews never written → SessionStart advisory); verified firing live on the real 22-day gap pre-merge.
3. New `tools/weekly_synthesis.py`: deterministic no-LLM Monday sensor, reads origin/main blobs in `--scheduled` mode, emails via send_email.py, writes no file, `--print-registration` carries the version-controlled Register-ScheduledTask command. 18 new tests.

### PR #211 — Agent eval harness (merged 224b1ef)
1. `tools/eval-agents.py` run/grade/compare/list; CLI spike verified 2.1.205 flags + the neutral-cwd trap (project scratchpad tree auto-loads repo context; `%TEMP%\agentic-eval-*` does not); fixtures sanitized (they embed answer keys).
2. Deterministic graders per agent output contract ride CI over synthetic samples (test_agnt_evals.py); generation is local-only by design (agents read machine-local memory files).
3. comd_system-dev Phase 5 step 6: agent-affecting changes require base/head eval compare in the PR body.
4. Real before/after demo (13 sonnet generations): **first genuine baseline finding** — intent-reviewer consistently RED on its violations fixture (classifies `exploratory` vs expected `pushback`, misses `[paraphrase-drift]`); research-blocked adjudicated FLAKY at N=3 (defensible extra `[invocation]` blocker).

### Housekeeping
1. recon-main worktree pulled to merged main; psgate + anneal worktrees removed; agent-eval worktree kept (holds eval transcripts + serves as future head-worktree).
2. Memory `project_harness_hardening_2026-07-10` written; MEMORY.md compacted 20.5KB → 14.1KB (all entries kept, hooks tightened).

---

## Key Decisions Made

### Include the Instantly Layer-A reorder in PR #208
- **Choice:** Ship the compound-command fix in the same PR as its own commit.
- **Rationale:** ~6 lines in a file the PR already touched; highest-blast-radius gate; deferring doubles churn.

### Union merge instead of patch-apply for the ledgers
- **Choice:** Line-union with chronological re-sort + row-set asserts, plus a sweep of the 73 never-committed checkpoints.
- **Rationale:** Both sides appended since the merge base (patch would conflict); G1 requires INDEX rows and their checkpoints in the same PR.

### Eval generation local-only; CI runs graders only
- **Choice:** No eval.yml workflow; pytest grades committed synthetic samples.
- **Rationale:** Agents read machine-local memory files — CI would measure the degraded missing-memory path; plus the org ITPM cap and spend-cap history.

### Merge-of-main instead of force-push after the rebase conflict
- **Choice:** `rebase --abort` → `merge origin/main` → resolve → push.
- **Rationale:** Force-push is Band-3 gated floor; the merge keeps everything in Band 1 (PR squashes anyway).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| tools/wire-hooks.py, .claude/hooks/{_shell,cd-guard,no-auto-commit-gate,post-action-gate,gate-skip-detector,instantly-invasive-gate}.py | Modified/Created (merged via #208) | PowerShell gate coverage + normalizer |
| tools/tests/{test_shell_normalize,test_post_action_gate,test_gate_skip_detector}.py + 3 extended suites | Created/Extended (#208) | Behavioral pinning incl. both real bypasses |
| docs/friction-register.md, docs/INDEX.md, docs/sessions/*, 77 checkpoint files | Merged (#209) | G1 ledger reunification onto main |
| tools/friction-watch.py, tools/weekly_synthesis.py + 2 test suites | Modified/Created (#210) | Corrected counting, cadence signal, weekly sensor |
| tools/eval-agents.py, tools/tests/test_agnt_evals.py, tools/fixtures/agnt-evals/*, comd_system-dev.md | Created/Modified (#211) | Behavioral eval harness + system-dev eval gate |
| .claude/rules/rule_no_auto_commit.md, rule_instantly_invasive.md, tools/tests/README.md, tools/INDEX.md | Modified (#208/#210/#211) | Enforcement wording, coverage ledger, tool rows |
| ~/.claude/.../memory/project_harness_hardening_2026-07-10.md + MEMORY.md | Created/Compacted | Project state + index under size limit |

---

## Current Status

Main (224b1ef) carries all four fixes. CI green on every PR. The primary clone remains on `client/brisken/lead-gen-onepilot` with pre-#208 hooks in its tree — PS gate coverage activates there only after the branch syncs with main (or in any main-based session). The cadence nag now fires at SessionStart until the RUN cycle produces ledger row 3.

---

## Next Steps

1. **USER — live PS-gate proof** in a main-based session: PowerShell-tool `Set-Location platform` → expect cd-guard block; `vercel.cmd deploy --help` → expect B6 ask (cancel); allowlist-interaction check per PR #208 body. If the allowlist pre-empts the hook, escalate (stale `PowerShell(...)` allow rules need pruning).
2. **USER — register the weekly sensor**: `git worktree add --detach ..\agentic-ops1-cadence origin/main` (NOTE: `--detach`, plain `main` is held by recon-main — plan deviation), fresh `RESEND_API_KEY` (rotate old `re_B7qD1off_...`) + `BRIEFING_TO`, `--preflight`, paste `--print-registration`, verify forced run → `LastTaskResult 0` + email.
3. **USER + agent — the interactive `/comd_system-dev` RUN cycle** (Phase-4 approval gate): pre-step delete the stale untracked `docs/anneal-ledger.md` + `tools/anneal-metrics.py` from this clone (verify `??` first); produces ledger row 3 (Top Finding MUST note the Unres basis change — parser-true 82+7 hook-contained; trend restarts), first `docs/reviews/` file via `/comd_review --save`, backlog triage by type-cluster; seed Phase 1.5 with the surviving audit findings (B6 negation-blind auth scan, PS Set-Content Write|Edit bypass, post-write-gate untested dispatcher, intent-reviewer pushback-classification gap).
4. This checkpoint + register rows + session log reach main via the next `docs/...` PR per G1 (do NOT commit them on the client branch).

---

## Context for Next Session

### Files to Read First
- ~/.claude/.../memory/project_harness_hardening_2026-07-10.md (pending actions + gotchas)
- tools/eval-agents.py module docstring (verified CLI facts, neutral-cwd trap)
- PR bodies #208-#211 (verification evidence + tracked out-of-scope gaps)

### Open Questions
- Does the permission allowlist pre-empt PreToolUse hooks under bypassPermissions? (The one unverified dependency — live-proof step 1 answers it.)
- research-blocked FLAKY boundary: relax the `no-invocation-blocker` assertion to informational, or tighten the fixture/agent? (system-dev decision.)

### Working Notes
- The audit's full output: `.../tasks/wpl59ur5r.output` (session temp); plan file `~/.claude/plans/compile-a-plan-for-glowing-russell.md`.
- gh-merge false-FAILed on all four merges (sibling worktree holds main); remote merge succeeded each time — verify via `gh pr view N --json state`.
- Eval transcripts + graded runs live in `agentic-ops1-agent-eval/.scratch/evals/` (3 runs: head, base, flake-adjudication); the determinism test re-grades the newest one.
- Bash-tool heredocs collapse `\\` to `\` (produced vertical-tab bytes in test strings); write test code via Write/Edit tools.
- Piping a command to `tail` masks its exit code — a chained `rebase && pytest && push` pushed mid-conflict; keep ship-chain commands unpiped.

### Reference Materials
- PRs: https://github.com/011matthias/agentic-ops1.01/pull/208 …/209 …/210 …/211

---

## How to Continue

Start a session on main (any main worktree). The SessionStart cadence nag will point at the RUN cycle. Execute Next Steps 1-2 (user), then run `/comd_system-dev` for step 3. The intent-reviewer baseline gap is the first candidate for an eval-gated agent-prompt fix (`eval-agents.py run --label base` before touching it).

---

## Strategic Feedback

### What Worked Well This Session
- One-word scope answers at the two decision points ("All three, phased"; plan approval) unlocked ~4 hours of autonomous execution with zero mid-flight questions — the plan-then-execute contract worked exactly as designed.

### Suggestions
- The client branch has been diverged from main since pre-06-18 and its tree now lags the enforcement layer by four merged PRs; landing or rebasing `client/brisken/lead-gen-onepilot` soon would re-unify the hook layer on your primary clone and prevent a second ledger fragmentation.

### System Health
- Autonomy score: 0 human interventions — fully autonomous execution (3 self-caught friction events: 1 hook-contained closing-offer, 2 tool-quirk slow-paths, all resolved in-session).
- The eval harness closed the audit's frontier gap on day one with a real finding; the remaining discipline-only gates (B6 auth-scan negation-blindness, PS file-writes vs Write|Edit hooks, post-write-gate dispatcher tests) are queued as seeded findings for the RUN cycle.
