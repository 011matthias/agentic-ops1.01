# Project Container Spec Sections

Use these section templates when `type: project` — for multi-phase projects where each phase is independently trackable. The project container is a high-level overview; each phase gets its own spec.

---

## Frontmatter Template

```yaml
---
id: p{N}
name: {Project Name}
type: project
stage: spec                      # Update as phases progress: build once started, live once all done
needs_fixes: false
version: 1.0.0
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
orchestrator: none               # Projects don't run; phases do
systems:
  - {system1}
  - {system2}
owner: owner@client.com
phases:
  - p{N}.1
  - p{N}.2
  - p{N}.3
next_steps:
  - Implement p{N}.1: {Phase 1 name}
stage_history:
  - stage: spec
    date: {YYYY-MM-DD}
---
```

---

## Goal Section

```markdown
## Goal

**Problem:** {What problem this project solves — the big picture}

**Solution:** {What we are building — the end state}

**Business Value:**
- {Benefit 1}
- {Benefit 2}
- {Benefit 3}
```

---

## Phases Table

```markdown
## Phases

| Phase | Name | Description | Depends On | Stage |
|-------|------|-------------|------------|-------|
| p{N}.1 | {Phase 1 Name} | {Brief description} | — | spec |
| p{N}.2 | {Phase 2 Name} | {Brief description} | p{N}.1 | spec |
| p{N}.3 | {Phase 3 Name} | {Brief description} | p{N}.2 | spec |
```

Each phase has its own spec in `specs/1-spec/p{N}.{M}-{name}.md`.

---

## Architecture Overview Section

```markdown
## Architecture Overview

{High-level description of the system being built — components, how they connect}

```mermaid
flowchart TD
    A[{Component 1}] --> B[{Component 2}]
    B --> C[{Component 3}]
```
```

---

## Success Criteria

```markdown
## Success Criteria

- [ ] {Measurable outcome 1}
- [ ] {Measurable outcome 2}
- [ ] {Measurable outcome 3}
```

---

## Reference

```markdown
## Reference

{Links to any detailed PRD, external docs, or design files}

- [PRD / Reference](context/{name}.md)
- [Related Automation](./a{N}-{name}.md)
```

---

## Conventions

- The project container spec's `stage` reflects the overall project status:
  - `spec` → planning, no phases started
  - `build` → at least one phase in build/test/live, not all done
  - `live` → all phases are live
- When the project is done, move both the container AND all phase specs to `4-live/`
- Individual phase specs live in the folder matching their own `stage` field
