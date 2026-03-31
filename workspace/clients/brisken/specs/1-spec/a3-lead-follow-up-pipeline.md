---
id: a3
name: Lead Follow-Up Pipeline
type: automation
stage: spec
orchestrator: n8n
version: 0.2.0
created: 2026-03-20
updated: 2026-03-30
trigger: webhook
systems:
  - n8n
  - TBD-crm-or-sheets
  - gmail
  - openai
last_changes: "Major update from Dirk's confirmed requirements (2026-03-30). Added: lead ranking, contact enrichment, AI response drafting, HITL review gate. Switched to n8n."
next_steps:
  - Confirm destination system (Google Sheets, CRM, or email-only)
  - Confirm outbound email address / domain
  - Define email templates or brief for first response
  - Confirm who reviews leads flagged for human review
  - Define lead scoring thresholds
---

> **CONFIRMED** (2026-03-30)
> Dirk provided detailed process requirements including ranking criteria, enrichment step, AI-drafted responses, and human-in-the-loop review gates.

# A3 -- Lead Follow-Up Pipeline

## Overview

Unified entry point for all leads arriving from A0 (LinkedIn), A1 (website), and A2 (SAP channels). Receives the normalised lead payload, scores/ranks the lead, enriches contact data, logs to destination, drafts a personalised first response via AI, and routes through optional human review before sending.

## Trigger

n8n Webhook node -- receives POST from A0, A1, or A2 with the standard lead payload.

## Flow

```
Webhook receives standard lead payload
  -> 1. Validate required fields (email must be present)
  -> 2. Deduplicate: check if lead email already logged (within 24h window)
  -> 3. Lead Ranking (see scoring criteria below)
  -> 4. Log lead to destination (Sheets / CRM / TBD)
  -> 5. Contact Enrichment: retrieve background info on the contact
  -> 6. AI Draft Response: generate personalised first response
  -> 7. HITL Gate: route based on lead quality score
       -> HIGH quality: queue for human review before sending
       -> LOW quality: auto-send (or skip, based on threshold)
       -> MEDIUM: auto-send with notification to reviewer
  -> 8. Send first response email
```

## Lead Ranking (confirmed by Dirk)

Score leads based on the quality of information provided:

| Signal | Score Impact | Example |
|--------|-------------|---------|
| Gmail/free email only, no other info | Very Low | `user@gmail.com`, no company, no message |
| Company email domain | +High | `dirk@brisken.com` |
| Company name provided | +Medium | Company field filled |
| Additional comment/message | +Medium | Detailed inquiry text |
| Job title provided | +Low | Role context available |
| Phone number provided | +Low | Direct contact available |
| SAP Store source (higher-value channel) | +Medium | `sap_channel: store` |

### Score Tiers

| Tier | Criteria | Action |
|------|----------|--------|
| **High** | Company email + company name + message | Human review before sending |
| **Medium** | Company email OR (free email + detailed message) | Auto-send with notification |
| **Low** | Free email only, minimal info | Auto-send (templated response) or skip |

## Contact Enrichment (Step 5)

Before drafting a response, attempt to gather background info on the contact:

- Company website lookup (from email domain)
- LinkedIn profile search (if name + company available)
- Previous lead history check (have they contacted before?)

Implementation: n8n Code node with HTTP requests or dedicated enrichment API (Clearbit, Apollo, or similar). Start simple (domain lookup), expand later.

## AI Response Drafting (Step 6)

Use OpenAI (via n8n AI nodes) to draft a personalised first response:

**Response elements (from Dirk's requirements):**
1. Acknowledge the inquiry / thank them for their interest
2. Reference their specific product/use case interest
3. Provide relevant additional information
4. Ask a clarifying question to move the conversation forward
5. Attach relevant documents (if applicable)

**AI prompt inputs:**
- Lead source and channel
- Lead's message/inquiry text
- Product/use case they expressed interest in
- Enrichment data (company background)
- Response templates/guidelines from Brisken

**Output:** Draft email ready for review or auto-send.

## HITL Review Gate (Step 7)

Route the drafted response based on lead quality score:

| Quality | Action | Notification |
|---------|--------|-------------|
| High | Hold for human review | Email/Slack to reviewer with draft + lead details |
| Medium | Auto-send | Notification to reviewer (FYI, already sent) |
| Low | Auto-send (template) | No notification (logged only) |

**Review workflow:** Reviewer receives email/Slack with draft, can approve, edit, or reject. Approval triggers send. Rejection flags lead for manual handling.

## Standard Lead Payload (input)

```json
{
  "source": "linkedin | website | sap",
  "source_detail": "",
  "sap_channel": "discovery-center | store",
  "first_name": "",
  "last_name": "",
  "email": "",
  "company": "",
  "job_title": "",
  "phone": "",
  "message": "",
  "use_case": "",
  "submitted_at": ""
}
```

## Destination Options

| Option | Pros | Cons |
|--------|------|------|
| Google Sheets | Full visibility, easy audit, Brisken can see everything | Manual review needed for CRM-like features |
| HubSpot CRM | Contact management, deal pipeline | Requires HubSpot account |
| n8n internal DB | No external dependency | Limited reporting |

## Requirements

- Destination system confirmed + connected in n8n
- Outbound email address (client's domain preferred)
- Email templates or guidelines for AI drafting
- OpenAI API key (for response drafting)
- Reviewer notification channel (email or Slack)
- Who is the reviewer? (Dirk? Matthias? Sales team?)

## Outstanding

- [ ] **Destination system** (Google Sheets? Which CRM?) -- BLOCKER
- [ ] Outbound email domain and address
- [ ] Email templates or brief for first response style
- [ ] Who reviews leads flagged for human review?
- [ ] Lead scoring thresholds (how strict?)
- [ ] Enrichment API choice (start with domain lookup? Use Clearbit/Apollo?)
- [ ] Document attachments: which documents for which products/use cases?
