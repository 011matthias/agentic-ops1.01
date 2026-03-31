---
id: a0
name: LinkedIn Lead Ingest
type: automation
stage: spec
orchestrator: n8n
version: 0.1.0
created: 2026-03-20
updated: 2026-03-30
trigger: linkedin-lead-gen-forms
systems:
  - linkedin-lead-gen-forms
  - n8n
last_changes: "Switched to n8n orchestrator (2026-03-30). Still unconfirmed — Dirk referenced 'other channels' but did not name LinkedIn explicitly."
next_steps:
  - Confirm with Dirk whether LinkedIn is an active lead source
  - If yes: confirm LinkedIn Lead Sync API access
  - Get Ad Account ID and Lead Gen Form IDs
  - Wire to A3 webhook once A3 is built
---

> **HYPOTHESIS — pending discovery**
> This spec was drafted based on pre-discovery information shared in the initial setup conversation, not confirmed by the client.
> Lead sources, integrations, and requirements must be validated in the discovery call before any building begins.

# A0 — LinkedIn Lead Ingest

## Overview

Captures lead submissions from LinkedIn Lead Gen Forms in real time and normalises them into a standard lead payload, which is then forwarded to the A3 follow-up pipeline webhook.

## Trigger

LinkedIn Lead Gen Forms module — instant trigger fires when a lead submits a form attached to a LinkedIn ad campaign.

## Flow

```
LinkedIn Lead Gen Form submitted
  → Make.com: LinkedIn Lead Forms module (new lead trigger)
  → Transform: map LinkedIn fields to standard lead schema
  → HTTP POST to A3 webhook (unified lead pipeline)
```

## Standard Lead Schema (output)

```json
{
  "source": "linkedin",
  "first_name": "",
  "last_name": "",
  "email": "",
  "company": "",
  "job_title": "",
  "phone": "",
  "message": "",
  "form_id": "",
  "campaign_id": "",
  "submitted_at": ""
}
```

## Requirements

- LinkedIn Lead Sync API access (separate application via LinkedIn Developer Hub — may take days/weeks to approve)
- OAuth connection in Make.com with `r_marketing_leadgen_automation` scope
- Ad Account ID and Lead Gen Form IDs from client

## Edge Cases

- Form fields may differ per campaign — map available fields, leave empty string for missing
- Duplicate lead submissions: handle via deduplication in A3 (by email + timestamp)

## Outstanding

- [ ] LinkedIn Lead Sync API access confirmed?
- [ ] Ad Account ID
- [ ] Lead Gen Form IDs
- [ ] Test lead submission (LinkedIn provides a test lead feature in Campaign Manager)
