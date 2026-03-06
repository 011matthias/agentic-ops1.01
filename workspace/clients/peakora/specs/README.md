# Peakora Automations

## Overview

| ID | Name | Stage | Trigger | Systems | Orchestrator |
|----|------|-------|---------|---------|--------------|
| A1 | [Fix Closed Won Slack Notifications](pipeline/live/a1-fix-closed-won-notifications.md) | live | Webhook (HubSpot deal stage) | HubSpot, Google Sheets, Slack | n8n |
| A2 | [Client Handover — Sales to Delivery](pipeline/spec/a2-client-handover.md) | spec | Sub-workflow (from Onboarding PT.1) | HubSpot, Slack | n8n |
| A3 | [Client Check-in Brief V2](pipeline/spec/a3-client-checkin-brief-v2.md) | spec | Webhook + CRON (Monday) | HubSpot, Slack | n8n |
| A4 | [Meeting De-Brief](pipeline/spec/a4-meeting-debrief.md) | spec | Sub-workflow (from Fathom Meetings) | Fathom, Slack | n8n |

## Pipeline Stages

- **Spec**: Specification exists, no implementation yet
- **Build**: Implementation in progress
- **Test**: Testing in progress
- **Live**: Deployed and working in production

## Quick Links

- [Context Notes](../context/README.md)
- [Reference Materials](../reference/)

## Adding New Automations

Use `/spec-creator` to add new automations.

## Migration Note

2026-02-16: Migrated from `specs/automations/` to `specs/pipeline/{stage}/` structure.
