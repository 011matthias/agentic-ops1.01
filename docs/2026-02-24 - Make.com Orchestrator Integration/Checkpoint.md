# Checkpoint: Make.com Orchestrator Integration

**Date:** 2026-02-24
**Status:** Complete

---

## Summary
Added Make.com as the 4th automation orchestrator to the Agentic Ops workspace. Created 4 new files and modified 10 existing files. Purely additive — zero regressions to n8n, Trigger.dev, or FastAPI functionality. Verified all cross-references and consistency.

---

## What Was Done This Session
### New Files Created
1. `.claude/rules/make/project-setup.md` — Make.com rules (principles, error handling, data mapping, naming conventions, infrastructure.yaml format)
2. `.claude/skills/build/modules/MAKE-BUILD.md` — Implementation workflow (Architecture → Spec Review → Build in UI → Test → Activate → Document)
3. `.claude/skills/spec-creator/modules/MAKE-SECTIONS.md` — Spec section templates (scenario info, connections, modules, testing)
4. `.claude/commands/make-instances.md` — `/make-instances` command for tracking Make.com orgs in infrastructure.yaml

### Existing Files Modified
1. `.claude/rules/automation-types.md` — Added Section 2 for Make.com, renumbered Trigger.dev/FastAPI
2. `.claude/skills/build/SKILL.md` — Added detection row, bash detection, Make.com branch, module table entry
3. `.claude/skills/spec-creator/SKILL.md` — Added Make.com throughout all 7 steps + modules table
4. `.claude/skills/spec-creator/prompts/gather-requirements.md` — Added detection, questions, parsing fields for Make.com
5. `.claude/skills/spec-creator/modules/EDGE-CASES.md` — Appended Make.com-specific edge cases (module errors, connections, data handling, scenario execution)
6. `.claude/skills/spec-creator/modules/TESTING-SECTION.md` — Appended Make.com testing section (Run once, visual verification, idempotency)
7. `.claude/skills/spec-creator/modules/MERMAID-PATTERNS.md` — Added Make.com diagram patterns, naming conventions, trigger table column
8. `workspace/templates/specs/automation-spec.md` — Added `make` to enum, 3 Make.com commented sections
9. `.claude/commands/new-client.md` — Added Make.com to orchestrator table, template step, environment step, output summary
10. `CLAUDE.md` — Updated intro, workspace tree, frontmatter enum, commands table, quick reference

---

## Key Decisions Made
### Interaction Model
- **Choice:** Manual UI + Specs (no MCP server, no programmatic API)
- **Rationale:** Make.com has no official MCP server and limited API. Specs serve as blueprints that the implementor follows when building in the Make.com UI.

### Skill Depth
- **Choice:** Lean start — core infrastructure only
- **Rationale:** Avoids over-engineering. Deeper Make.com skills (like expression syntax helpers or module catalogs) can be added later as needed.

### Detection Pattern
- **Choice:** `infrastructure.yaml` with `type: make` entry
- **Rationale:** Make.com clients don't have code files to detect (no trigger.config.ts, no railway.toml). infrastructure.yaml was already used by n8n for instance tracking, so extending it was natural.

### Terminology Mapping
- **Choice:** Established consistent mapping: workflow→scenario, node→module, connection→route, credential→connection, expression→mapping, trigger node→trigger module
- **Rationale:** Prevents confusion across docs and ensures Make.com sections use correct terminology

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/make/project-setup.md` | Created | Make.com rules and principles |
| `.claude/skills/build/modules/MAKE-BUILD.md` | Created | Implementation workflow |
| `.claude/skills/spec-creator/modules/MAKE-SECTIONS.md` | Created | Spec section templates |
| `.claude/commands/make-instances.md` | Created | Instance management command |
| `.claude/rules/automation-types.md` | Modified | Added Make.com as orchestrator type |
| `.claude/skills/build/SKILL.md` | Modified | Added Make.com detection and branch |
| `.claude/skills/spec-creator/SKILL.md` | Modified | Added Make.com to all steps |
| `.claude/skills/spec-creator/prompts/gather-requirements.md` | Modified | Added Make.com questions |
| `.claude/skills/spec-creator/modules/EDGE-CASES.md` | Modified | Appended Make.com edge cases |
| `.claude/skills/spec-creator/modules/TESTING-SECTION.md` | Modified | Appended Make.com testing |
| `.claude/skills/spec-creator/modules/MERMAID-PATTERNS.md` | Modified | Added Make.com patterns |
| `workspace/templates/specs/automation-spec.md` | Modified | Added `make` to enum + sections |
| `.claude/commands/new-client.md` | Modified | Added Make.com orchestrator option |
| `CLAUDE.md` | Modified | Updated top-level docs |

---

## Current Status
Implementation is 100% complete and verified. All 14 planned changes have been applied. Verification confirmed:
- Zero regressions to n8n/Trigger.dev/FastAPI files
- All cross-references resolve correctly
- Orchestrator enum includes `make` everywhere
- Detection logic consistent across build and spec-creator skills

---

## Next Steps
1. Use the integration: run `/new-client` with Make.com orchestrator to test the full flow
2. Create a first Make.com spec with `/spec-creator` for a real client to validate templates
3. Consider adding deeper Make.com skills later (module catalog, error handler patterns) if needed

---

## Context for Next Session
### Files to Read First
- `.claude/rules/make/project-setup.md` — Core Make.com rules
- `.claude/skills/build/modules/MAKE-BUILD.md` — Build workflow
- `.claude/skills/spec-creator/modules/MAKE-SECTIONS.md` — Spec templates
- `.claude/rules/automation-types.md` — All orchestrators overview

### Open Questions
- None — implementation is complete

### Reference Materials
- Plan file: `C:\Users\neuma\.claude\plans\fuzzy-hugging-kahn.md`
- Make.com terminology mapping in `.claude/rules/automation-types.md` Section 2

---

## How to Continue
The Make.com integration is complete. To use it:
1. Run `/new-client {name}` and select Make.com as orchestrator
2. Run `/spec-creator` to create a Make.com automation spec
3. Follow the spec as a blueprint to build the scenario in the Make.com UI
4. Run `/make-instances` to manage Make.com org tracking
