# Brisken -- Work Items

## Overview

> **Updated 2026-03-30** -- Dirk confirmed lead automation requirements via email. Specs upgraded from hypothesis to confirmed where applicable. Orchestrator switched from Make.com to n8n.

| ID | Name | Type | Stage | Trigger | Orchestrator | Status |
|----|------|------|-------|---------|--------------|--------|
| a0 | LinkedIn Lead Ingest | automation | spec | linkedin-lead-gen-forms | n8n | Unconfirmed |
| a1 | Website Form Ingest | automation | spec | webhook | n8n | **Confirmed** |
| a2 | SAP Channel Ingest | automation | spec | scheduled | n8n | **Confirmed** |
| a3 | Lead Follow-Up Pipeline | automation | spec | webhook | n8n | **Confirmed** |
| a4 | Reply Monitoring and Escalation | automation | spec | scheduled | n8n | **Confirmed** |

## Open Bug Fixes

| Fix ID | Parent | Description | Stage |
|--------|--------|-------------|-------|
| -- | -- | -- | -- |

## Pipeline Stages

- **1-spec/** -- Specifications, no implementation yet
- **2-build/** -- Actively being implemented
- **3-test/** -- Testing in progress
- **4-live/** -- Deployed and working in production
- **_archive/** -- Deprecated or superseded specs
- **_checklists/** -- Testing checklists (per work item)

## Architecture

```
A0 (LinkedIn)  ──┐
A1 (Website)   ──┤──> A3 (Lead Follow-Up Pipeline) ──> A4 (Reply Monitoring)
A2 (SAP)       ──┘
```

- A0, A1, A2: Ingest channels, normalise leads into standard schema
- A3: Unified pipeline -- ranking, enrichment, AI response drafting, HITL review
- A4: Reply detection -- stops sequences, escalates to human review

## Work Item Types

- `a{N}` -- Automation (background job, n8n workflow, scheduled task)
- `a{N}.{M}` -- Sub-automation (child of parent automation)
- `app{N}` -- App/frontend (dashboard, web UI)
- `be{N}` -- Backend service (API, DB migration, infra)
- `p{N}` -- Project container (multi-phase)
- `p{N}.{M}` -- Project phase
- `fix{N}` -- Bug fix (tracked against a parent automation)

Use `/skil_spec-creator` to add new work items.

## Quick Links

- [Context Notes](../context/README.md)
- [Reference Materials](../reference/)
