# Audit Rules Reference

## Stage → Folder Mapping

| `stage` value | Expected folder | Notes |
|---|---|---|
| `spec` | `1-spec/` | Specification exists, no implementation yet |
| `build` | `2-build/` | Implementation in progress |
| `test` | `3-test/` | Testing in progress (local, dev, or production) |
| `live` | `4-live/` | Deployed and working in production |
| `deprecated` | `_archive/` | Superseded or absorbed into another spec |

## Skipped Paths

Do not audit files in these locations:
- `_archive/` — archived specs, no expectations
- `_checklists/` — testing checklists, not spec files
- `README.md` — index file, not a spec

## Required Frontmatter Fields

Every spec file must have:

```yaml
---
id: a1          # ID prefix: a{N} automation, a{N}.{M} sub-automation, app{N} frontend, be{N} backend, p{N} project, p{N}.{M} phase, fix{N} bug-fix
name: ...       # Human-readable name
type: ...       # automation | sub-automation | app | backend | project | phase | bug-fix
stage: ...      # spec | build | test | live | deprecated
orchestrator: ...  # trigger-dev | fastapi | n8n | none | tbd
---
```

## Valid Values

**type:**
- `automation` — background job/workflow
- `sub-automation` — child of parent automation
- `app` — frontend, dashboard, web UI
- `backend` — backend API, DB migration, infra
- `project` — multi-phase project container
- `phase` — implementation phase within a project
- `bug-fix` — tracked bug fix

**stage:**
- `spec` → `1-spec/`
- `build` → `2-build/`
- `test` → `3-test/`
- `live` → `4-live/`
- `deprecated` → `_archive/`

**orchestrator:**
- `trigger-dev` — Trigger.dev TypeScript tasks
- `fastapi` — Legacy FastAPI/Railway service
- `n8n` — n8n visual workflow
- `none` — multi-component or infrastructure
- `tbd` — not yet decided

## Decision Guide: Move vs Update frontmatter

When a file is misplaced, choose based on actual work state:

| Situation | Action |
|---|---|
| `stage: spec` but implementation exists | Update frontmatter to match actual progress, move to correct folder |
| `stage: build` but file is in `1-spec/` | Move file to `2-build/` |
| `stage: test` but file is in `1-spec/` | Move file to `3-test/` |
| `stage: deprecated` but file is in any spec folder | Move to `_archive/` |
| File in `4-live/` but `stage: build` | Ask user — did it actually go live? |

## README Update Rules

After moving files, update `workspace/clients/{client}/specs/README.md`:
- Change the **Stage** column value to match the new stage
- Update file **links** if they include the folder path (e.g. `1-spec/{id}.md` → `3-test/{id}.md`)
- Do not restructure the table — only update affected rows
