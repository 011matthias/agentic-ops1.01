# Checkpoint: Unified Decision Framework

**Date:** 2026-02-26
**Status:** Complete — all 7 changes implemented, rules budget verified at 141/250

---

## Summary

Ran `/system-dev` audit focused on the capability creation decision process. Found that "what primitive should I create?" was answered in 3 disconnected places with 3 different vocabularies. Unified them under a single canonical source (DECISION-TREE.md) with workspace-specific criteria, replaced all generic examples with real workspace primitives, and fixed broken template paths.

---

## What Was Done This Session

### Friction Audit (Phase 1 — 2 parallel explore agents)
1. Full inventory of meta-builder skill (4,078 lines, 15 files) and its decision framework
2. Mapped all 3 locations where primitive-selection logic lived (operationalization-loop rule, DECISION-TREE.md, system-dev command)
3. System health check: rules budget, MEMORY.md staleness, skill overlap, checkpoint inventory

### Core Implementation
4. **Added "Agentic Ops Decision Criteria" section** to DECISION-TREE.md — the canonical source for all primitive-selection decisions. Contains:
   - Rule vs. Skill Module litmus test ("needed every session regardless of domain? rule. Only when in that domain? skill module.")
   - Rules budget reminder (250 lines, check before proposing)
   - Agent sub-types documentation (user-invokable vs. orchestrator-internal)
   - Extend vs. Create preference (module in existing skill > new skill)
   - Friction-to-Primitive Mapping table (bridges error categories to primitive types)
5. **Replaced all generic examples** in DECISION-TREE.md with real workspace primitives (flowchart, Examples by Primitive, Hybrid Patterns, Common Scenarios)
6. **Simplified operationalization-loop rule** — replaced 5-line inline primitive mapping with single reference to DECISION-TREE.md
7. **Simplified system-dev command Phase 4** — same reference pattern

### Bug Fixes
8. **Fixed broken template paths** in 4 files — all referenced `workspace/templates/` which doesn't exist; corrected to `templates/` (relative to skill root)
9. **Added Kunde Inc** to Current Clients in automation-types.md (was missing)
10. **Deleted duplicate user-preferences.md** — content was fully covered by MEMORY.md User Preferences section

---

## Key Decisions Made

### Single canonical source for primitive selection
- **Choice:** DECISION-TREE.md is the sole authority; the rule and command defer to it
- **Rationale:** Three competing frameworks with different vocabularies caused the agent to mentally bridge frameworks every time it operationalized. One source eliminates the mismatch. The rule triggers the reflex ("should I operationalize?"), the tree handles the selection ("what should I create?").

### Litmus test for Rule vs. Skill Module
- **Choice:** "Would the agent need this even when NOT working in the relevant domain?"
- **Rationale:** This is the clearest discriminator. "filterRows needs empty-row guard" is only needed during Make.com work (skill module). "Always verify outcomes" is needed every test cycle regardless of orchestrator (rule).

### Keep Phase 2 friction table in system-dev
- **Choice:** Only Phase 4's primitive-selection logic was simplified; Phase 2's friction categorization table stays
- **Rationale:** Phase 2's table serves a different purpose — categorizing friction, not selecting primitives. It feeds into the DECISION-TREE as input.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/meta-builder/modules/DECISION-TREE.md` | Modified | Added "Agentic Ops Decision Criteria" section + replaced all examples |
| `.claude/rules/operationalization-loop.md` | Modified | Replaced inline mapping with DECISION-TREE reference (-4 lines) |
| `.claude/commands/system-dev.md` | Modified | Phase 4 defers to DECISION-TREE |
| `.claude/skills/meta-builder/SKILL.md` | Modified | Fixed template paths (`workspace/templates/` -> `templates/`) |
| `.claude/skills/meta-builder/modules/SKILL-GUIDE.md` | Modified | Fixed template paths (2 locations) |
| `.claude/skills/meta-builder/modules/COMMAND-GUIDE.md` | Modified | Fixed template path |
| `.claude/skills/meta-builder/modules/AGENT-GUIDE.md` | Modified | Fixed template path |
| `.claude/rules/automation-types.md` | Modified | Added Kunde Inc to n8n clients |
| `memory/user-preferences.md` | Deleted | Content fully duplicated in MEMORY.md |
| `memory/MEMORY.md` | Modified | Updated rules budget (141), added decision framework note, removed user-preferences.md link |

---

## Current Status

All changes implemented. The decision framework is now:
- **Operationalization-loop rule** (auto-loaded) triggers the "should I create something?" reflex
- **DECISION-TREE.md** (loaded on-demand via meta-builder) answers "what should I create?"
- **`/system-dev` command** categorizes friction, then defers primitive selection to DECISION-TREE

Rules budget: **141/250** (56%) — saved 4 lines from previous 145.

---

## Next Steps

1. **Live test during next build session** — Does the operationalization loop correctly reference DECISION-TREE.md when it fires? Does the agent land on the right primitive?
2. **Address Meji Media open items:**
   - S0 blueprint metadata bug (missing `metadata.designer.orphans` and `metadata.scenario.dataloss`)
   - Production readiness (connection swap to client accounts, delete UTIL scenarios)
3. **Herbox Sweden A2 fixes** — 4 interlinked specs with `needs_fixes: true`
4. **Deferred system health items:**
   - n8n-node-configuration SKILL.md at 785 lines (refactor into modules)
   - Skill overlap audit (n8n validation guides, webhook inspectors)
   - MEMORY.md Pipeline Config DS field count verification (34 vs actual)

---

## Context for Next Session

### Files to Read First
- `.claude/skills/meta-builder/modules/DECISION-TREE.md` — the "Agentic Ops Decision Criteria" section (lines 21-66)
- `.claude/rules/operationalization-loop.md` — simplified step 4 now references DECISION-TREE
- `.claude/commands/system-dev.md` — Phase 4 now references DECISION-TREE

### Open Questions
- Will the operationalization loop's reference to DECISION-TREE.md actually cause the agent to load it? The meta-builder skill auto-triggers when building primitives, but the reference is to a specific module — the agent needs to read the file, not just invoke the skill. Monitor on next firing.

### Reference Materials
- Plan: `C:\Users\neuma\.claude\plans\cheerful-whistling-candle.md`
- Previous checkpoint: `docs/2026-02-26 - Outcome Verification & Proactive Operationalization/Checkpoint.md`
- Friction audit explored: meta-builder (4,078 lines), all 5 rules (141 lines), 27 skills, 9 agents, 19 commands

---

## How to Continue

Run `/resume` for any client or start a new `/system-dev` session. The decision framework changes are passive — they'll be exercised naturally when the operationalization loop fires after a fix or build. The true test is: does the agent follow the DECISION-TREE reference and land on the correct primitive type?

For Meji Media work: `/resume meji-media` — the S0 metadata bug and production readiness are the priority items.

---

## Strategic Feedback

### What Worked Well This Session
- The 2-agent parallel explore pattern gave comprehensive coverage (meta-builder internals + system health) in a single round
- Plan mode forced clean thinking about the 3-source vocabulary problem before diving into edits

### Suggestions
- Consider running `/system-dev --audit-only` periodically (e.g., every 5 sessions) even without a specific friction complaint. This session surfaced broken template paths that had been silently broken since the meta-builder was created — they would have caused errors on the next primitive creation attempt.

### System Health
- The meta-builder skill (4,078 lines) is now the largest skill and the canonical decision authority. Its accuracy directly affects all capability creation. If the "Agentic Ops Decision Criteria" section drifts from reality (e.g., new agent sub-types, changed rules budget), the entire decision chain degrades. Consider adding a `/system-dev` pre-check that verifies DECISION-TREE.md's agent list and rules budget match the actual files.
