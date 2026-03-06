# System Infrastructure Revision — Checkpoint

**Date:** 2026-02-25
**Scope:** Structural correctness and consistency audit of the entire `.claude/` instruction system
**Preceded by:** Token Efficiency Audit (same day — reduced per-session overhead by 78%)

---

## What Was Done

Following the token-efficiency audit, three explore agents audited all 25 skills, 9 agents, 18 commands, 5 rules, and CLAUDE.md for structural correctness. Nine issues were found and all were fixed across 5 phases.

### Phase 1: Fix Path References (~47 files)

| Fix | Scope |
|-----|-------|
| CLAUDE.md workspace diagram | Rewrote to show actual `workspace/` nesting, added `.agents/`, `playgrounds/`, `docs/` |
| `api-docs/` → `workspace/api-docs/` | 7 files |
| `clients/{client}/` → `workspace/clients/{client}/` | 47 files, ~170 occurrences |
| `templates/` → `workspace/templates/` | 10 files, 25 occurrences |

### Phase 2: Deduplicate Agent Content

| Fix | Impact |
|-----|--------|
| Orchestrator detection → shared rule in `automation-types.md` | 3 agents now cross-reference instead of duplicating |
| Testing sections in `build-orchestrator.md` collapsed | 857 → 700 lines. Phases 3, 3.5, 6 delegate to testing-agent |

### Phase 3: Resolve Architecture Ambiguities

| Fix | Files |
|-----|-------|
| Internal-agent banners added | `doc-generator.md`, `implementation-agent.md`, `project-manager.md` |
| Renamed `trigger-dev-task-writer.md` → `trigger-dev-expert.md` | Matches frontmatter name |
| CLAUDE.md agents section categorized | Orchestrator / User-invokable / Internal / Specialist |
| Trigger.dev skills documented | 5 symlinked skills added to CLAUDE.md |
| build-orchestrator listed | Was invoked but missing from agents list |

### Phase 4: Fix Consistency Issues

| Fix | Files |
|-----|-------|
| Command argument-hints standardized | 6 commands: `<client-name> [automation-id] [flags]` |
| Frontmatter added | `make-instances.md`, `n8n-instances.md` |
| `/spec-cleanup` removed from Commands table | It's a skill, not a command |
| `/export-client-docs` added | Was missing from CLAUDE.md |
| All 5 rules documented in CLAUDE.md | Rules table with purpose descriptions |

### Phase 5: Restructure CLAUDE.md

CLAUDE.md now 123 lines with:
- Correct workspace diagram
- Skills grouped by domain (7 categories, 26 skills)
- Agents categorized by invocation context (9 agents)
- Commands in 7-category table (18 commands)
- Rules table (5 rules)
- Every `.claude/` file represented

---

## Verification Results

| Check | Result |
|-------|--------|
| Bare `clients/{` references | 0 (excluding internal `app/clients/`, `api-clients/`) |
| Bare `api-docs/` references | 0 |
| CLAUDE.md diagram vs `ls workspace/` | Match |
| Every `.claude/` file in CLAUDE.md | All 18 commands, 9 agents, 26 skills, 5 rules accounted for |
| All `argument-hint` fields client-first | Confirmed |

---

## Key Files Modified

- `CLAUDE.md` — Complete rewrite (123 lines)
- `.claude/agents/build-orchestrator.md` — Testing sections collapsed (700 lines)
- `.claude/rules/automation-types.md` — Added canonical orchestrator detection command
- `.claude/agents/trigger-dev-expert.md` — Renamed from trigger-dev-task-writer.md
- `.claude/agents/doc-generator.md`, `implementation-agent.md`, `project-manager.md` — Internal agent banners
- `.claude/commands/fix-bugs.md`, `status-check.md`, `verify-live.md`, `test.md` — Argument order standardized
- `.claude/commands/make-instances.md`, `n8n-instances.md` — Frontmatter added
- ~47 files across `.claude/` — Path prefix fixes
- `.claude/skills/n8n-converter/SKILL.md` — Late-discovered bare path fix

---

## Combined Audit Impact (Token Efficiency + Infrastructure Revision)

| Metric | Before | After |
|--------|--------|-------|
| Always-loaded tokens | ~9,800 | ~2,150 |
| CLAUDE.md | 388 lines | 123 lines |
| Rules | 16 files / 2,528 lines | 5 files / 116 lines |
| build-orchestrator.md | 860 lines | 700 lines |
| Path correctness | 167+ wrong paths | 0 wrong paths |
| Documentation completeness | ~60% coverage | 100% coverage |
