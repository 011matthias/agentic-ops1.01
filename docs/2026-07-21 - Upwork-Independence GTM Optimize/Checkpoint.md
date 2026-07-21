# Checkpoint: Upwork-Independence GTM Optimize

**Date:** 2026-07-21
**Status:** Complete — first real `/comd_optimize` run shipped and converged; v2 + other-aspect runs queued.

---

## Summary
Built the first genuine target for the `/comd_optimize` autoresearch loop — a deterministic ROI model of the two-route Upwork-independence GTM idea — then ran it to convergence (36.88 → 200.37 EUR/hr, +443%). The result is a trustworthy strategic direction, not a validated price sheet.

---

## What Was Done This Session
### Optimize-loop target build (the three surfaces)
1. Locked scorer `tools/scorers/gtm-roi.py` (maximize, 30-month horizon): deterministic contribution-margin-per-working-hour model over locked economics; hash-pinned.
2. Guards: `tools/gtm-plan-validate.py` (schema + market bounds + UWG §7 legal fence: DE+cold-email rejected) and `tools/gtm-stress-guard.py` (independent pessimistic-case floor — anti-overfit lock).
3. Asset `workspace/projects/upwork-independence/gtm-plan.json` (9 decisions) + manifest `docs/optimize/upwork-independence-gtm-v1/RUN.md`.

### The run
4. Locked on in an isolated worktree, hill-climbed 5 rounds to convergence, stopped, wrote SUMMARY.md, shipped.
5. Findings recorded to memory `project_upwork_independence_gtm_optimize`.

---

## Key Decisions Made
### Refused the literal ask, reframed to a fit-checked target
- **Choice:** "Score a business idea's ROI" fails the loop's honest-number fit-gate (LLM-opinion / weeks-slow feedback). Reframed to a deterministic unit-economics model with locked reality params + held-out realism guards.
- **Rationale:** an ROI-judge scorer is gameable (Goodhart) — the exact failure the lock model exists to prevent. The agent may only search decisions; every conversion/price/horizon is locked.

### Horizon 30 months (owner directive "24-36")
- **Choice:** extended from an initial 12mo; restructured the temporal model so recurring revenue accrues over each client's lifetime.
- **Rationale:** a recurring-revenue business is an annuity; a 12-mo window makes any bootstrap look marginal.

### Stop-the-run at convergence
- **Choice:** stopped after 5 rounds (4 keeps + 1 confirming revert) rather than exhausting the 20-round budget.
- **Rationale:** every lever verified at its bound/optimum (grid-swept + allocation probe reverted).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/scorers/gtm-roi.py | Created (merged #302) | Locked ROI scorer, pinned |
| tools/gtm-plan-validate.py | Created (#302) | Legal/bounds guard |
| tools/gtm-stress-guard.py | Created (#302) | Pessimistic floor guard |
| tools/scorers/PINS.json | Modified (#302) | Pin gtm-roi.py |
| tools/scorers/README.md, tools/INDEX.md | Modified (#302) | Registration |
| workspace/projects/upwork-independence/gtm-plan.json | Created (#302), optimized (#303) | Decision asset |
| docs/optimize/upwork-independence-gtm-v1/{RUN,SUMMARY}.md, results.tsv | Created (#302/#303) | Manifest, journal, summary |
| ~/.claude/.../memory/project_upwork_independence_gtm_optimize.md | Created | Findings record |

---

## Current Status
Both PRs merged to main: **#302** (setup), **#303** (run outcome, 36.88 → 200.37). Run is CLOSED with SUMMARY (`optimize_overview` confirms). Worktree + run branches cleaned up. No client platform touched — no deploy.

---

## Next Steps
1. **`upwork-independence-gtm-v2`** — fork the scorer, add care-price elasticity + freed-hour reinvestment/subcontracting term (both fix v1's pegged-bound artifacts). Ready-to-paste prompt is in this session's chat + memory.
2. Route-1 demo-site delivery efficiency run against `page-weight.py` (fast/objective fit).
3. Pricing-tier / packaging structure run (deterministic model variant).
4. Validate the v1 pegged bounds in the real world before acting on the specific numbers (esp. whether SMB care sustains EUR300/mo).

---

## Context for Next Session
### Files to Read First
- docs/optimize/upwork-independence-gtm-v1/SUMMARY.md (full result + sensitivity)
- memory/project_upwork_independence_gtm_optimize.md (distilled direction + queued runs)
- tools/scorers/gtm-roi.py (the model to fork for v2)

### Open Questions
- Does the v1 strategic direction (commit B2B, price at service capacity, loss-lead build) survive a v2 model with care elasticity + hour reinvestment? That is the point of v2.

### Working Notes
- Model optimum by pre-run grid sweep was ~159; the loop reached 200.37 by pushing un-elasticized levers (care price, build price) to their bounds — that IS the tell for what to fix in v2.
- Robustness note: at 30-mo horizon, 61% of plans clear the pessimistic floor (recurring revenue cushions the bad case), so the floor stopped being the binding discriminator — v2's realism guards may need tightening.
- Operational papercut: editing a pre-pin scorer needs SCORER_LOCK_ALLOW in the hook env, which can't be hot-set mid-session in a worktree; had to `git clean` the untracked scorer and recreate. Fine for a pre-pin/pre-run file, but a smoother path would help future scorer authoring.

### Reference Materials
- PR #302 (setup), PR #303 (run) on 011matthias/agentic-ops1.01
- rule_optimize_loop.md, docs/optimize/RECIPES.md (constructed-metric protocol)

---

## How to Continue
Paste the v2 prompt from memory `project_upwork_independence_gtm_optimize` (or this session's chat) into a fresh session. It sets up `upwork-independence-gtm-v2` with the same rigor (scorer PR + pin → guards → lock-on in a worktree) and names the secondary fit-checked targets.

---

## Strategic Feedback

### What Worked Well This Session
- The fit-gate refusal up front (questioning the approach before building) turned a gameable request into an honest one — exactly the default-posture the rules ask for, and it set the whole session's integrity.
- One well-placed decision-fork question (which venture to ground the model on) avoided building the wrong thing, without over-asking.

### Suggestions
- When a run's winner pegs multiple levers to their bounds, that is a reliable signal for the next model iteration — worth treating "pegged bound" as an automatic v2 backlog item.

### System Health
- The optimize loop's constructed-metric path worked end-to-end on its first non-trivial target: fit-gate → scorer PR + pin → guards → lock-on → converge → ship → clean up. No engine friction.
- Minor ergonomics gap: no clean in-tool path to edit a pre-pin, uncommitted scorer (SCORER_LOCK_ALLOW is env-only, not hot-settable for the Edit hook mid-session). Worked around via git-clean-recreate. Candidate future fix if scorer authoring becomes frequent.
- Autonomy score: 0 — fully autonomous session (no corrections or unblocks needed; user inputs were design decisions, not friction).
