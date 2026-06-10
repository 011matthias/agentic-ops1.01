# Checkpoint: Internal Muscle (CI Test Gates) + agentic-dev1 Spinout

**Date:** 2026-06-07
**Status:** Internal muscle DONE + live on main. agentic-dev1 spinout PLANNED, awaiting fresh-session execution.
**Type:** system-infra

---

## Summary
Decided to build software-engineering capability into agentic-ops first (internal muscle), then spin a separate repo for own-products. Shipped the internal-muscle layer (CI-gated hook/tool test suite + ruff + INDEX-membership gate + platform npm scripts) — all merged to main and verified green. Designed the next phase: a new repo `agentic-dev1` seeded from this harness, SWE-oriented, first product = CREW game.

---

## What Was Done This Session
### Strategic
1. Honest good/bad analysis of agentic-ops (grounded in the friction register): strong at self-annealing infra + client-facing artifact production; weak at recurring agent-deferred/verification-theater/Windows-shell friction, and memory not holding (only structural hooks do).
2. Mapped the 5 core implementation areas (automation building, the platform, proposals/prospecting, client comms, the governance substrate) + flagged doc drift (CLAUDE.md undercounts agents/commands).
3. Decision: build internal SWE muscle in agentic-ops first; then a SEPARATE repo for own-products (per openclaw/CREW precedent). New domain = "own products, a hub for several."

### Internal muscle (shipped to main)
1. **Slice 1** — enforcement test suite under `tools/tests/` (registry consistency + behavioral tests for no-auto-commit, cd-guard, instantly-invasive, em-dash-strip + session-state smoke wrapper). pytest config at root `pytest.ini`.
2. **Slice 2** — `ruff.toml` (real-bug ruleset E9,F; E741 style deferred to avoid churn) + fixed 7 F-class findings; `tools/check-index.py` (INDEX-membership gate) + backfilled 9 missing INDEX rows (37/37); `.pre-commit-config.yaml`; ci.yml `hooks` job runs ruff + check-index + pytest.
3. **Slice 3** — `platform/package.json` `typecheck` + `test` scripts.
4. The no-auto-commit gate was rewritten (by user/parallel work) from keyword-scan to a tiered 3-band model (autonomous feature-branch lane / CI-gated auto-merge / gated floor). The slice-1 no-auto-commit test was rewritten to match; verified 14/14 against the new gate.

### Next-phase design (agentic-dev1)
- Full seed/drop/add design produced (see How to Continue).

---

## Key Decisions Made
### Internal muscle before new domain
- **Choice:** Build SWE capability into agentic-ops first, then spin a new repo.
- **Rationale:** The valuable, reusable part is the self-annealing HARNESS, not the domain content. Prove/strengthen it here, then seed the new repo from it.

### New repo, not a monorepo addition
- **Choice:** Own-products live in a separate repo (`agentic-dev1`), not inside agentic-ops.
- **Rationale:** agentic-ops is an automation-consultancy ops system; SWE/product work is a different domain with different primitives. Precedent: openclaw + CREW already have their own repos. Mixing dilutes both + every SWE session would pay the consultancy context tax.

### Held the merge through a volatile, parallel-edited tree
- **Choice:** Did not force-push or merge security work blind; surfaced conflicts; committed only my own paths.
- **Rationale:** A parallel session was actively committing/editing this checkout (audit remediation incl. CVE/secrets, the tiered-gate rewrite). User ultimately resolved the ci.yml union (`ad4f9f1`) and landed everything via #78.

---

## Files Modified (this session, all merged to main via #78)
| File | Action | Purpose |
|------|--------|---------|
| pytest.ini | Created | root pytest config (not pyproject, to avoid uv project-mode) |
| tools/tests/* (8 files) | Created | enforcement-layer regression suite |
| ruff.toml | Created | real-bug ruleset (E9,F) |
| tools/check-index.py | Created | INDEX-membership CI gate |
| .pre-commit-config.yaml | Created | local ruff + INDEX gate |
| tools/INDEX.md | Modified | backfilled 9 missing tool rows (37/37) |
| .github/workflows/ci.yml | Modified | `hooks` job: ruff + check-index + pytest |
| platform/package.json | Modified | typecheck + test scripts |
| tools/{build-hours-tracker,build-warme-wimmer-doc-site,handoff-readiness,make-api,openclaw-sandbox-init,rename-chat}.py | Modified | ruff F-fixes (unused imports, empty f-strings) |

---

## Current Status
- Internal muscle: **DONE, on main, CI green** (the "Enforcement hook tests" job ran ruff + check-index + pytest and passed on main's latest CI run).
- agentic-dev1: **planned, not started.** Awaiting a fresh session to scaffold.

---

## Next Steps
1. **New session:** scaffold `agentic-dev1` (see How to Continue — the continuation prompt). Public repo under 011matthias at `~/Repo/agentic-dev1/`.
2. First product: **CREW game** — integrate/connect its existing phase-1 work into the hub the best way possible (see `project_crew_game` memory).
3. The hub's entire agent infrastructure must be **SWE/product-dev oriented** (move away from automations): seed the harness, drop the consultancy layer, add SWE gates.

---

## Context for Next Session
### Files to Read First
- This checkpoint
- `MEMORY.md` → `project_crew_game.md` (CREW concept locked), `project_openclaw_container_workspace.md` (separate-repo precedent)
- agentic-ops harness to seed from: `.claude/hooks/`, `tools/wire-hooks.py`, `tools/tests/`, `pytest.ini`, `ruff.toml`, `tools/check-index.py`, `.github/workflows/ci.yml` (the `hooks` job), the rules `rule_no_auto_commit.md` + `rule_anti_slop.md`

### Working Notes
- **Windows git-read gotcha (cost real friction this session):** `git show <rev>:<path>` and `git cat-file -e <rev>:<path>` get MANGLED by Git-Bash on this machine (`origin/main:...` → `origin\main;...`, silent empty output under `2>/dev/null`). This produced a FALSE "main is missing the CI wiring + pre-commit" alarm across two turns. Use `git ls-tree <rev> -- <path>` and `git cat-file -p <blob-sha>` instead — those don't mangle.
- The tree was volatile all session (parallel session committing/editing between turns). Trust `ls-tree`/blob reads over `show <rev>:<path>`.
- The no-auto-commit gate is now the TIERED 3-band model on main. Feature-branch commit/push/PR-create = autonomous; merge auto-allows on CI-green; main/force/deploy/tag = gated floor.

### Open Questions
- agentic-dev1: foundation-first vs CREW-first ordering? (User said CREW is the first product to integrate, so likely scaffold foundation + bring CREW in together.)
- How is CREW's existing phase-1 work stored/where? Locate it before integrating.

### Reference Materials
- PRs this session: #77 (gate + test suite), #78 (audit remediation + my slices, merged as `af4ef6d`).

---

## How to Continue
Start a new chat and paste the continuation prompt (also delivered in chat). Core: found `agentic-dev1` (public, `~/Repo/agentic-dev1/`), seed the SWE harness from agentic-ops, integrate the CREW game as the first product.

**Seed** (domain-agnostic harness): hook enforcement layer + `wire-hooks` pattern; self-annealing loop (friction register, memory, checkpoint/resume, session-pressure meter); CI-gated pytest+ruff pattern; tiered no-auto-commit gate; anti-slop voice discipline.
**Drop** (consultancy-specific): Make/n8n/Trigger skill packs; proposal + client-comms systems; client-page + platform-standards rules; Instantly gate; `clients/{client}/specs` workflow.
**Add** (product-shaped): code-review agent + verification-before-completion gate; `products/{name}/` self-contained layout; release/dependency-hygiene rules.
**Layout:** `CLAUDE.md` (hub charter) + `.claude/{rules,hooks,agents,skills}` + `tools/` + `products/crew/` + `docs/` + `memory/`.

---

## Strategic Feedback

### What Worked Well This Session
- Holding the line on not force-pushing / not merging security work blind through a volatile parallel-edited tree prevented a bad bundle to main. Committing only explicit paths kept my work cleanly separable.

### Suggestions
- When two sessions edit the same checkout, expect file-modified-since-read collisions on shared files (ci.yml, docs/INDEX.md). Prefer new files + explicit-path commits; avoid the shared, actively-edited files.

### System Health
- Recurring Windows path-mangling friction (now in a new `git show <rev>:<path>` manifestation) is worth a structural note or a tiny `tools/` git-read wrapper — it caused verification-theater this session. Autonomy score: 1 human-relevant friction event (self-detected verification-theater from the git-read mangling).
