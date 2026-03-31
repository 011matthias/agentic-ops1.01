---
id: a2
name: SAP Channel Ingest
type: automation
stage: spec
orchestrator: n8n
version: 0.2.0
created: 2026-03-20
updated: 2026-03-30
trigger: scheduled
systems:
  - gmail
  - sap-discovery-center
  - sap-store
  - n8n
last_changes: "Confirmed by Dirk (2026-03-30). Two distinct SAP channels: Discovery Center (missions/UCs) and SAP Store (rarer, higher value). Switched to n8n."
next_steps:
  - Get SAP notification email address(es) from client
  - Confirm if Discovery Center and SAP Store use the same inbox
  - Request sample notification emails from both channels
  - Confirm polling interval with client
---

> **CONFIRMED** (2026-03-30)
> Dirk confirmed both SAP Discovery Center and SAP Store as active lead channels.
> Discovery Center: various use cases, users start "missions" for specific UCs.
> SAP Store: rarer but more important, product inquiries.

# A2 -- SAP Channel Ingest

## Overview

SAP Discovery Center and SAP Store have **no public API for lead data**. When a prospect contacts Brisken via their SAP listings, SAP sends email notifications to a configured inbox. This workflow polls that inbox on a schedule, identifies SAP lead notification emails, parses the fields, tags the SAP channel (Discovery Center vs Store), and forwards to the A3 pipeline.

### Two SAP Sub-Channels

| Channel | Description | Volume | Priority |
|---------|-------------|--------|----------|
| **Discovery Center** | Various use cases; users start "missions" for specific UCs | Higher volume | Standard |
| **SAP Store** | Products in App Store; users request more info | Lower volume | **Higher value** |

## Trigger

Scheduled -- polls inbox every 10 minutes (600 seconds).

## Flow

```
[Every 10 minutes]
  -> n8n: Gmail node -- search inbox for unread SAP notification emails
  -> Filter: match sender pattern(s) (SAP notification address TBD)
  -> For each matching email:
      -> Detect channel: Discovery Center or SAP Store (by sender, subject pattern, or body content)
      -> Parse: extract lead fields from email body (regex or text parsing)
      -> Transform: map to standard lead schema with sap_channel field
      -> HTTP POST to A3 webhook
      -> Mark email as read (prevent reprocessing)
```

## Standard Lead Schema (output)

```json
{
  "source": "sap",
  "sap_channel": "discovery-center | store",
  "first_name": "",
  "last_name": "",
  "email": "",
  "company": "",
  "job_title": "",
  "phone": "",
  "message": "",
  "sap_listing_id": "",
  "use_case": "",
  "submitted_at": ""
}
```

`sap_channel` differentiates Discovery Center from SAP Store leads.
`use_case` captures the specific UC/mission (Discovery Center) or product (SAP Store).

## Requirements

- Gmail connection in n8n linked to the inbox that receives SAP notifications
- Sample SAP emails from both channels to build parsing templates
- Gmail search query to match SAP notification sender(s)

## SAP Caveat

SAP Discovery Center and SAP Store do not offer a programmatic API or webhook for lead data. Email polling is the only viable integration path as of 2026-03-30. If SAP releases a partner portal API in future, this workflow can be replaced with a direct API call.

## Edge Cases

- Empty inbox (no new SAP emails): workflow exits cleanly with 0 operations
- Malformed email (parsing fails): log the raw email for manual review
- Duplicate leads: handled by A3 deduplication (email + timestamp)
- Ambiguous channel detection: default to Discovery Center, flag for review

## Outstanding

- [ ] Email address(es) that receive SAP notifications
- [ ] Are Discovery Center and SAP Store notifications from the same sender?
- [ ] Sample notification emails from both channels (body format for parsing)
- [ ] Confirm SAP sender email/domain(s)
- [ ] Preferred polling interval (10 min default)
