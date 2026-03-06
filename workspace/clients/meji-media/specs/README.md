# meji-media — Work Items

## Overview

| ID | Name | Type | Stage | Trigger | Orchestrator |
|----|------|------|-------|---------|--------------|
| a1 | Enquiry Follow-Up Sequence | automation | test | webhook | make |
| a2 | Reply Detection & Stop | automation | test | cron (5min) | make |
| a3 | Scheduled Follow-Up Steps | automation | test | cron (15min) | make |

## Open Bug Fixes

| Fix ID | Parent | Description | Stage |
|--------|--------|-------------|-------|
| — | — | — | — |

## Pipeline Stages

- **1-spec/** — Specifications, no implementation yet
- **2-build/** — Actively being implemented
- **3-test/** — Testing in progress
- **4-live/** — Deployed and working in production
- **_archive/** — Deprecated or superseded specs
- **_checklists/** — Testing checklists (per work item)

## Work Item Types

- `a{N}` — Automation (background job, n8n workflow, cron task)
- `a{N}.{M}` — Sub-automation (child of parent automation)
- `app{N}` — App/frontend (dashboard, web UI)
- `be{N}` — Backend service (API, DB migration, infra)
- `p{N}` — Project container (multi-phase)
- `p{N}.{M}` — Project phase
- `fix{N}` — Bug fix (tracked against a parent automation via `fix{N}-{parentId}-{description}.md`)

Use `/spec-creator` to add new work items.

## Quick Links

- [Context Notes](../context/README.md)
- [Reference Materials](../reference/)
