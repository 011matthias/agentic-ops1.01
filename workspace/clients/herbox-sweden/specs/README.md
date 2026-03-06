# Herbox Sweden Automations

## Overview

| ID | Name | Stage | Trigger | Systems | Orchestrator |
|----|------|-------|---------|---------|--------------|
| A1 | [Recurring Order Generator](3-test/a1-recurring-orders.md) | test | CRON 08:00 | Fortnox | n8n |
| A1.1 | [PeriodStart Logic Fix](3-test/a1.1-periodstart-fix.md) | test | CRON 08:00 | Fortnox | n8n |
| A2 | [Upsales Order Enrichment Pipeline](2-build/a2-crm-erp-sync.md) | build | CRON 5min | Upsales, Fortnox | n8n |
| A2-FastAPI | [Dashboard Enrichment Routing Changes](2-build/a2-fastapi-changes.md) | build | n/a (code change) | Fortnox | fastapi |
| A3 | ~~[Order Field Enrichment](_archive/a3-order-enrichment.md)~~ | deprecated | — | — | — |
| A4 | [Subscription Agreement Creator](1-spec/a4-subscription-creator.md) | spec | Webhook | Fortnox | tbd |
| A5 | [Reporting Sync](1-spec/a5-reporting-sync.md) | spec | CRON Hourly | Fortnox, Google Sheets | tbd |
| A6 | [List Building Orchestrator](4-live/a6-list-building.md) | live | Webhook | Airtable, Apify | fastapi |
| A6.1 | [Apify Scraper Starter](4-live/a6.1-apify-scraper-starter.md) | live | Webhook | Apify, Airtable | fastapi |
| A6.2 | [Lead Sourcing Completed](4-live/a6.2-lead-sourcing-completed.md) | live | Webhook | Airtable, Apify | fastapi |
| A6.3 | [Contact Enrichment & Verification](4-live/a6.3-contact-enrichment.md) | live | CRON 6h | Airtable, Leadmagic, Trykitt, Usebouncer | fastapi |
| A6.4 | [Data Cleaning](4-live/a6.4-data-cleaning.md) | live | CRON | Airtable | fastapi |
| A6.5 | [SmartLead Lead Sync](4-live/a6.5-smartlead-sync.md) | live | Webhook | Smartlead, Airtable | fastapi |
| A7 | [Smartlead Campaign Sync](4-live/a7-smartlead-campaign-sync.md) | live | CRON 10:00 | Smartlead, Airtable | fastapi |
| A8 | [Email Reply Handler](4-live/a8-email-reply-handler.md) | live | Webhook | Smartlead, Airtable, OpenAI, Heyreach | fastapi |
| A10 | [Freight Tiering System](1-spec/a10-freight-tiering.md) | spec | N/A (utility) | Fortnox | n8n |
| P1 | [Order Approval System](4-live/p1-order-approval-system.md) | live | Multi-component | Fortnox, N8N, FastAPI, Postgres | — |

## Open Bug Fixes

| Fix ID | Parent | Description | Stage |
|--------|--------|-------------|-------|
| [Fix1](2-build/fix1-a2-dashboard-missing-fields.md) | A2 | Dashboard missing period_end, interval, line items; update-fortnox-order webhook missing | build |
| [Fix2](2-build/fix2-a2-dashboard-delete-orders.md) | A2 | No way to delete orders from dashboard — requires DB reset for cleanup | build |
| [Fix3](2-build/fix3-a2-customer-info-sync.md) | A2 | A2 n8n — sync Upsales phone/address to Fortnox Customer + include customer_info in dashboard payload | build |
| [Fix4](2-build/fix4-a2-dashboard-customer-info.md) | A2 | Dashboard — customer info visibility (phone, email, delivery address panel on order detail) | build |
| [Fix5](1-spec/fix5-a1-dashboard-date-filter.md) | A1 | Dashboard — date range picker on Recurring Orders tab (defaults to current month) | spec |

## Archive

| ID | Name | Reason |
|----|------|--------|
| A2-Test | [Upsales-Fortnox Discovery Workflow](_archive/a2-test-workflow.md) | One-time discovery test, complete |
| A3 | [Order Field Enrichment](_archive/a3-order-enrichment.md) | Absorbed into A2 (2026-02-18) |

## Pipeline Stages

- **1-spec**: Specification exists, no implementation yet
- **2-build**: Implementation in progress
- **3-test**: Testing in progress
- **4-live**: Deployed and working in production
- **_archive**: Deprecated or superseded specs
- **_checklists**: Testing checklists (per automation)

## Quick Links

- [Context Notes](../context/)
- [Reference Materials](../reference/)
- [Automations Code](../automations/app/automations/)

## Adding New Automations

Use `/spec-creator` or `/build-automation herbox-sweden` to create new automation specs.

Specs follow the standard format defined in `templates/specs/automation-spec.md`.

## Migration Notes

- 2026-02-18: Migrated to v2 numbered stage structure (`1-spec/`, `2-build/`, `3-test/`, `4-live/`)
- 2026-02-16: Migrated from `specs/automations/` to `specs/pipeline/{stage}/` structure
- 2026-01-09: Specs migrated from combined `automation-workflows.md`
