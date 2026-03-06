---
id: p1
name: Order Approval System
type: project
stage: live
needs_fixes: false
version: 1.0.0
created: 2026-02-13
updated: 2026-02-18
orchestrator: none
systems:
  - fortnox
  - n8n
  - fastapi
  - postgres
owner: riccardo
phases:
  - p1.1
  - p1.2
  - p1.3
  - p1.4
  - p1.5
  - p1.6
next_steps:
  - p1.6 (Testing): End-to-end validation of the full approval flow
stage_history:
  - stage: spec
    date: 2026-02-13
  - stage: build
    date: 2026-02-13
  - stage: live
    date: 2026-02-16
---

# Order Approval System

Adds a human-in-the-loop approval step between order generation and Fortnox creation. The A1 n8n workflow stores pending orders in Postgres; Rebecca reviews them in the FastAPI dashboard and approves/denies/edits them before they are created in Fortnox.

## Problem

Rebecca spends ~60% of her time manually checking contract due dates and creating recurring orders. The previous A1 workflow created Fortnox orders with no review step and was missing administration fee, freight, remarks, and correct period start.

## Solution

1. A1 generates and enriches orders → stores as `pending` in Postgres
2. Dashboard (`/orders`) lets Rebecca review, edit, approve, or deny
3. On approval → FastAPI triggers n8n webhook → order created in Fortnox

## Phases

| Phase | Name | Stage |
|-------|------|-------|
| p1.1 | Database Models | live |
| p1.2 | Webhook Receiver | live |
| p1.3 | Modify A1 Workflow | live |
| p1.4 | Dashboard UI | live |
| p1.5 | Order Creator | live |
| p1.6 | Testing & Validation | spec |

## Reference

Full PRD with DB schema, API contracts, and n8n workflow details: [_archive/prd-order-approval-system-original.md](../_archive/prd-order-approval-system-original.md)
