# Brisken -- Work Items

## Overview

> **Updated 2026-05-24** -- Two separate projects in this folder; see `PROJECT-BOUNDARIES.md` for the binding ledger.
>
> **ACTIVE: Expense Reconciliation Platform (p1).** v2 functional spec landed 2026-05-24 at `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (revised against the 2026-05-20 Dirk call). Stack genuinely re-opened (Azure rejected, AWS-as-provider declined, Firebase/GCP candidate pending research per spec §38). Build phases begin after the stack decision; see spec §32 for the implementation order.
>
> **PAUSED: Lead Nurturing Platform (a0-a4, app1, a5, a6).** No work while paused per the `PROJECT-BOUNDARIES.md` swap history. The earlier 2026-04-10 universal-communicator scope expansion below applies if and only if this project resumes; existing a0-a4 specs carry `paused: true` and are frozen.

## Active project -- Expense Reconciliation (p1)

| ID | Name | Type | Stage | Trigger | Orchestrator | Status |
|----|------|------|-------|---------|--------------|--------|
| p1 | Expense Reconciliation Platform - Functional Specification | project | 2-build | n/a | tbd (§38 pending) | **v2.1 spec ready for Dirk; Phase 4 matching engine shipped + 9 tests green; other phases gated on §38 sign-off** |

Sub-IDs under `p1` will be added as the project decomposes (e.g., `p1.app1`, `p1.be1`, `p1.a1`, ...) per the namespace owned in `PROJECT-BOUNDARIES.md`.

### p1 build artifacts (active 2026-05-25)

- [`../automations/expense-reconciliation/`](../automations/expense-reconciliation/) -- Phase 4 deterministic matching engine + tests (v2 spec §15.1). See its README for run instructions and the data we need from Chris to validate against a real Brisken month.
  - `src/expense_recon/matching/types.py` -- domain types (Transaction, Receipt, Match, MatchOutcome)
  - `src/expense_recon/matching/deterministic.py` -- matcher (USD-on-USD exact, posting-date tolerance, EUR-on-USD short-circuit to LLM judgment layer, ambiguous detection, entity scope, reconciliation-guarantee invariant)
  - `tests/test_deterministic_matching.py` -- 9 tests, all green
- LLM judgment layer (`matching/judgment.py`): pending (§38.2 sign-off + Anthropic API access).
- Multi-tenant persistence, OCR, mobile-capture page, review UI: gated on §38 stack pick.

## Paused project -- Lead Nurturing (frozen)

| ID | Name | Type | Stage | Trigger | Orchestrator | Status |
|----|------|------|-------|---------|--------------|--------|
| a0 | LinkedIn Lead Ingest | automation | spec | linkedin-lead-gen-forms | n8n | Paused (Unconfirmed) |
| a1 | Website Form Ingest | automation | spec | webhook | n8n | Paused (Confirmed) |
| a2 | SAP Channel Ingest | automation | spec | scheduled | n8n | Paused (Confirmed) |
| a3 | Lead Follow-Up Pipeline | automation | spec | webhook | n8n | Paused (Confirmed) |
| a4 | Reply Monitoring and Escalation | automation | spec | scheduled | n8n | Paused (Confirmed) |

### Lead-nurturing scope expansion (from 2026-04-10 call) -- only relevant if the paused project resumes

| ID | Name | Type | Notes |
|----|------|------|-------|
| app1 | Unified Dashboard | app | Centralized interface for all channels, approvals, conversation history. Core requirement. |
| a5 | Invoice/AP Routing | automation | Forward invoices to approvers, track approval, reconcile. Same platform as lead nurturing. |
| a6 | Compliance Email Routing | automation | Channel compliance emails through tool. Lower priority than a5. |

> **Do not create these specs while the project is paused.** Platform decision (n8n vs Firebase vs custom) would also need to be resolved first if it resumes -- it changes the spec shape entirely.

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

### Active project (p1) -- Expense Reconciliation

See the Mermaid pipeline diagram in `specs/1-spec/p1-expense-reconciliation-functional-spec.md` §24 (Processing pipeline). Component separation locked: OCR / receipt-reading, deterministic matching engine, LLM judgment layer, and web / API framework are distinct components regardless of where they run.

### Paused project -- Lead Nurturing (for reference only while paused)

```
A0 (LinkedIn)  --+
A1 (Website)   --+--> A3 (Lead Follow-Up Pipeline) --> A4 (Reply Monitoring)
A2 (SAP)       --+
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
