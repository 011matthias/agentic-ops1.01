# Checkpoint: Friction Rule Gaps

**Date:** 2026-06-12
**Status:** Shipped — two rules merged to main (PR #146)

---

## Summary
Read the full friction register (132 entries) against the 14 existing rules to find recurring patterns with no Layer-1 coverage, then drafted and shipped the two the owner selected: a new B7 enumerate-before-build gate and a platform-merge-is-not-live sub-clause on the Deploy verification gate.

---

## What Was Done This Session
### Analysis
1. Swept `docs/friction-register.md` (132 rows) + the 13→14 rules in `.claude/rules/`, classified recurring friction by coverage.
2. Separated the genuinely uncovered, rule-shaped gaps from the high-frequency patterns already operationalized at the hook layer (closing-offers, cd-drift, branch/stash isolation) where more rule prose has repeatedly failed to move the generation reflex.
3. Surfaced three candidates, ranked; owner picked two via AskUserQuestion.

### Rules shipped (PR #146, squash-merged, all CI green)
4. **New `rule_enumerate_before_build.md` (B7)** — decision-time gate consolidating two recall-dependent memories. E1: query existing client infra before proposing new. E2: read an external connector/action's real capability surface + prerequisites before building around it.
5. **`rule_behaviors.md` Deploy-verification gate sub-clause** — a platform merge to `main` is not live until `vercel-force-deploy.sh` runs + re-fetch; a post-merge 404/stale is "not force-deployed yet" (B3 attribution), not "CDN cache".

---

## Key Decisions Made
### Which patterns become rules
- **Choice:** Only B7 + the deploy sub-clause. Explicitly did NOT rule the closing-offer, cd-drift, or branch-isolation classes.
- **Rationale:** Those three are already at the hook/rule layer; the residual is generation reflex or freshly-ruled (G1). Adding rule text where a hook already fires is redundant per the self-annealing ladder (tool > rule > memory).

### Branch hygiene for system-wide edits
- **Choice:** Authored both the rule PR and this checkpoint in isolated worktrees off `origin/main`, landed via `docs/` PRs.
- **Rationale:** The session ran on `client/brisken/lead-gen-onepilot`. The G1 rule (the one open in the IDE) forbids system-wide config + ledger landing on a client branch. Worktree keeps the active brisken tree untouched.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_enumerate_before_build.md` | Created | New B7 enumerate-before-build gate |
| `.claude/rules/rule_behaviors.md` | Modified | Platform-merge-is-not-live sub-clause on the Deploy verification gate |
| `docs/2026-06-12 - Friction Rule Gaps/Checkpoint.md` | Created | This checkpoint |
| `docs/sessions/2026-06-12.md` | Modified | Session 6 log entry |
| `docs/sessions/2026-06-12-context.yaml` | Created | Session context for /resume |
| `docs/INDEX.md` | Modified | System-section index row |
| `docs/friction-register.md` | Modified | 1 slow-path row (here-string commit slip) |

---

## Current Status
Both rules are on `main` (merged via PR #146 at afe725a-ancestry; CI green: build, lint, hook tests, spell, Playwright). No deploy involved — rules are always-loaded prose, live on next session start. The brisken working tree was never disturbed (still on `client/brisken/lead-gen-onepilot` at 43e9f0b).

---

## Next Steps
1. Optional: build the structural form of the deploy gate — a post-merge hook that marks platform-path PR merges not-live until `vercel-force-deploy.sh` runs (named as a structural candidate in the new sub-clause).
2. Optional: the third candidate not selected — a "category-first" clause in the input-interpretation rule for genre-ambiguous terms — remains a documented note if it recurs.
3. CLAUDE.md still says "Rules (12)"; actual count is now 15. A trivial count-sync pass when convenient (not done here to avoid coupling CLAUDE.md into the rule PR).

---

## Context for Next Session
### Files to Read First
- `.claude/rules/rule_enumerate_before_build.md` — the new B7 gate
- `.claude/rules/rule_branch_isolation_and_shared_ledger.md` — G1, governs where ledger/system edits land

### Open Questions
- Should the deploy-gate sub-clause be promoted to an actual PreToolUse/PostToolUse hook, or is the rule clause sufficient given the existing deploy-verification gate?

### Working Notes
- The friction register read confirmed the system is mature: most recurring friction is already hook-covered. The honest finding was "few real rule gaps," not "many." Avoided bulk-adding redundant rules.
- B7 numbering follows B5 (instantly-invasive) and B6 (no-auto-commit) as the next decision-boundary code.
- Self-caught shell slip: PowerShell here-string (`@'...'@`) does not parse in the Bash tool, and `-m '...'` breaks on an apostrophe ("action's"). Use `git commit -F - <<'EOF'` heredoc for multi-line messages in the Bash tool.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/146

---

## How to Continue
The rules are live. If the owner wants the deploy-gate enforced structurally (not just as a rule clause), build the post-merge platform-path hook. Otherwise nothing is pending from this session.

---

## Strategic Feedback

### What Worked Well This Session
- The AskUserQuestion to pick which candidates to rule kept scope tight and avoided shipping the weak third candidate. Direction-decision gating (not execution gating) is the right use of the question tool.

### Suggestions
- A periodic "friction-register → rule-coverage" sweep (this session, run ad hoc) could be a `/system-dev` sub-step: it cheaply surfaces which recurring classes still lack Layer-1 coverage vs which are already hook-held.

### System Health
- The rule layer is dense (15 rules) and well-deduplicated; the harder problem now is generation-reflex patterns (closing-offers) that no rule reduces — the hooks carry them. Net: rule coverage is near-complete; enforcement effort is better spent on the few remaining structural-candidate hooks than on new rules.
- Autonomy score: 0 human interventions — fully autonomous (1 self-caught shell slip, no human correction).
