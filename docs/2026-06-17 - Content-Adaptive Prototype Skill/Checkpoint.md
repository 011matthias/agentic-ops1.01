# Checkpoint: Content-Adaptive Prototype Skill

**Date:** 2026-06-17
**Status:** Shipped — `skil_prototype` + IA-slop rule clause merged to main (PR #190)

---

## Summary
Assessed the content-adaptive prototype blueprint against the existing web-prototype infrastructure, found ~two-thirds already owned (more rigorously) and ~one-third a real gap, then built and shipped a thin connective skill (`skil_prototype`) that fills the gap without forking the quality stacks.

---

## What Was Done This Session
### Assessment
1. Mapped the blueprint's 13 Part-A assets + Part-B workflow against `skil_web-build`, `rule_client_page_structure`, `rule_deliverables`, `rule_platform_standards`, and the tool gates.
2. Verdict: design-quality cluster (6–13) + honesty gate (5) already owned, some exceeding the blueprint (the dated/rotating saturation lists, the second-order slop test). Content-adaptive cluster (1–3) is the gap, and it only pays on content-rich work, not content-light local-web SMB.
3. Surfaced the structural fact: three disjoint prototype regimes (local-web Astro, client-page roster, single-file HTML) with no shared content-adaptive front end; the Brisken OnePilot prototype was hand-rolled with no skill backing it — the evidence the gap is real and recurring.

### Lens run on Brisken OnePilot prototype (read-only)
4. Ran the content-adaptive lens on `brisken-onepilot-website-prototype.html`. Verdict: IA already largely content-derived (passes the test). Four findings: (1) spine/naming drift — the 2026-06-17 Messaging Spine demotes OnePilot from umbrella to AI-layer, TreasuryCentral is the new flagship; the prototype frames OnePilot-as-platform; Dirk-gated, do not re-skin until confirmed; (2) hero "81%" oversells n=21 (use "17 of 21"); (3) `#why-now` three-symmetric-card tell; (4) "Book a demo" is a dead `#demo` self-anchor.

### Build + ship
5. Wrote `.claude/skills/skil_prototype/SKILL.md` — content-adaptive front end (intake → derive-IA → calibrate → plan-gate, Create/Elevate branch, substrate router table). Passes `check-skill-map.py`.
6. Added the IA-level structural-slop clause to `rule_anti_slop.md` (invented/padded sections), the structural sibling of the prose bans.
7. Shipped via an isolated worktree off `main` (current branch is the Brisken client branch with WIP) → PR #190 → all 4 CI checks green → merged. Restored the Brisken working tree afterward so the system change is not stranded on the client branch.

---

## Key Decisions Made
### Thin connective skill, not a fourth quality stack
- **Choice:** `skil_prototype` owns only the shared front end (IA derivation + thin-content discipline + Create/Elevate) and routes execution + hard gates to the existing per-substrate stacks.
- **Rationale:** The design-quality + honesty clusters already exist, in places more rigorously. Re-implementing them would fork the machinery `skil_web-build`'s "one home per rule" invariant warns against. The skill's own maintenance rule: "the day this file grows a second quality rubric, it has failed."

### Ship via worktree off main, not onto the Brisken branch
- **Choice:** Created `system/skil-prototype` in a temp worktree off `origin/main`, committed the two files there, opened/merged the PR, removed the worktree, restored the Brisken tree.
- **Rationale:** Current branch is `client/brisken/lead-gen-onepilot` (14 commits ahead of main + uncommitted WIP). Committing system infra there would be scope contamination and a polluted PR base. Verified first that the client branch never touched `rule_anti_slop.md` and the skill is new, so the worktree files were exactly main + my changes.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/skil_prototype/SKILL.md` | Created (on main) | Content-adaptive prototype front-end skill |
| `.claude/rules/rule_anti_slop.md` | Modified (on main) | IA-level structural-slop clause |
| `docs/2026-06-17 - Content-Adaptive Prototype Skill/Checkpoint.md` | Created | This checkpoint |

(The two `main` changes landed via PR #190; they are NOT on the Brisken client branch — the working tree was restored.)

---

## Current Status
`skil_prototype` and the IA-slop clause are live on `main` (verified by `git ls-tree`/`git grep` on `origin/main`; PR #190 state MERGED). The skill is registered and usable this session. No deploy surface (the change is `.claude/` files, not `platform/`), so no deploy-verification fetch applies. Brisken p2 work is untouched on its branch, WIP intact.

---

## Next Steps
1. Use `skil_prototype` on the next prototype build (its first real exercise) — the Brisken-owned rebrand edits queued for a fresh chat are a natural candidate.
2. Brisken p2 (unchanged, Dirk-gated): the OnePilot-as-umbrella vs TreasuryCentral-as-umbrella hierarchy question still blocks any site re-cut; the hero "81%"→"17 of 21" fix waits on the same review pass.
3. Optional: a future `validate-output.py` "padded-section" detector to enforce the new IA-slop clause structurally (currently agent discipline + downstream B4).

---

## Context for Next Session
### Files to Read First
- `.claude/skills/skil_prototype/SKILL.md` (the new skill)
- `.claude/rules/rule_anti_slop.md` (IA-slop clause at the end of the banned list)
- `content-adaptive-prototype-blueprint.md` (the source blueprint, repo root)

### Open Questions
- Whether the IA-slop clause warrants a structural detector (`validate-output.py`) or stays agent-discipline. Deferred until the skill has been exercised a few times.

### Working Notes
- The blueprint's value as a *general* skill is connective tissue, not a new quality system. ~one-third (content-adaptive front end) generalizes across local-web AND Brisken-class; ~two-thirds (quality/tells/gates/honesty/primitives/visual-critique) already exists and is routed to, not rebuilt.
- Reasoning-review on the B1→intent chain: my turn-1 close offered a 3-way "do you want me to" instead of acting. The stop-b1-gate caught it; I then ran the Brisken lens as the bounded action — which was a *narrower* read than the user's actual intent ("I mean in general as a prototype building skill"), so they had to re-steer scope. Transferable principle: when an assessment question triggers the B1 "act don't offer" correction, the right bounded action is usually to SHARPEN THE ASSESSMENT at the asked altitude, not to pivot into a specific build. Acting on the wrong altitude is still misalignment.
- Tooling trap (now in memory): `gh pr merge` / `gh-merge.sh` reports FAIL when a sibling worktree holds `main` checked out, even though the remote squash-merge succeeds; confirm with `gh pr view N --json state,mergedAt`.

### Reference Materials
- PR #190: https://github.com/011matthias/agentic-ops1.01/pull/190
- Brisken product catalog (spine reconciliation): `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md`

---

## How to Continue
The skill is shipped and on main. To put it to work, start a prototype task and invoke `skil_prototype` at intake; it will route to the right execution stack. The Brisken-owned rebrand edits (logo → BRISKEN, OnePilot demoted, feedback interface + Fly deploy) from the prior session's hand-off are the obvious first real exercise.

---

## Strategic Feedback

### What Worked Well This Session
- The single scope-clarification ("I mean in general as a prototype building skill") was high-leverage: it reframed a Brisken-specific critique into a reusable-infra decision in one line, which is exactly the input that justified building the skill rather than doing a one-off.

### Suggestions
- When the question is an assessment ("how much of X is advantageous"), a one-line up-front "I'm reading this as: general capability, not just the current build?" would have pre-empted the re-steer. Cheap altitude-check before drilling in.

### System Health
- Autonomy score: 1 human intervention this session (the scope re-steer). The recurring B1-deferral phrasing reflex fired once more (caught by the hook); it remains a generation-time habit the structural gate keeps catching but does not cure. The new `skil_prototype` is itself a system-health improvement: it converts a recurring ad-hoc build pattern (content-rich prototypes) into a backed capability.
