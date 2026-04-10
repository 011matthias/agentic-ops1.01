# Brisken -- Work Items

## Overview

> **Updated 2026-04-10** -- Scope expanded significantly per call with Dirk. Lead nurturing remains Phase 1, but project is now a "universal communicator" platform (unified dashboard, invoice/AP routing, compliance emails, multi-tenant). Platform choice (n8n vs Firebase vs custom) is OPEN and must be resolved before build starts. Existing a0-a4 specs are still valid for lead nurturing logic but may need architectural revision depending on platform decision.

| ID | Name | Type | Stage | Trigger | Orchestrator | Status |
|----|------|------|-------|---------|--------------|--------|
| a0 | LinkedIn Lead Ingest | automation | spec | linkedin-lead-gen-forms | n8n | Unconfirmed |
| a1 | Website Form Ingest | automation | spec | webhook | n8n | **Confirmed** |
| a2 | SAP Channel Ingest | automation | spec | scheduled | n8n | **Confirmed** |
| a3 | Lead Follow-Up Pipeline | automation | spec | webhook | n8n | **Confirmed** |
| a4 | Reply Monitoring and Escalation | automation | spec | scheduled | n8n | **Confirmed** |

## New Specs Needed (from 2026-04-10 call)

| ID | Name | Type | Notes |
|----|------|------|-------|
| app1 | Unified Dashboard | app | Centralized interface for all channels, approvals, conversation history. Core requirement. |
| a5 | Invoice/AP Routing | automation | Forward invoices to approvers, track approval, reconcile. Same platform as lead nurturing. |
| a6 | Compliance Email Routing | automation | Channel compliance emails through tool. Lower priority than a5. |

> **Do not create these specs yet.** Platform decision (n8n vs Firebase vs custom) must be resolved first — it changes the spec shape entirely.

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
