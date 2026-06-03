---
id: p002
slug: genius-pr-ai-response-system
prospect: Genius PR
contact: ""
source: upwork
source_url: "https://www.upwork.com/nx/search/jobs/details/~022036457917371787564"
project_title: "AI Lead Response and Booking System"
status: draft
track: 2
created: "2026-03-25"
sent: null
value_estimate: "1500"
timeline: "7 days"
tags: [n8n, claude-api, hubspot, ai-classification, webhooks, crm, slack, calendly]
deliverables:
  letter: false
  video: false
  site: false
---

## What We Understood

Genius PR runs high-volume outbound campaigns across email (Instantly) and LinkedIn (HeyReach, Dripify) and needs the backend infrastructure to handle what happens after a lead responds. Right now, that response handling is manual: someone reads the reply, decides if the lead is hot, drafts a follow-up, and updates the CRM. At scale, that breaks. Leads fall through the cracks, response times slip, and your closers spend time on data entry instead of closing.

You need three things automated:

- **AI-powered reply classification and response.** When a lead replies to an outbound campaign, Claude classifies the intent (HOT, WARM, COLD, NOT INTERESTED) and generates a contextual follow-up. Hot leads get meeting slots and a Calendly link immediately. No human delay.

- **Booking confirmation pipeline.** When a lead books via Calendly, the system updates HubSpot, logs the meeting in Sheets and Notion, and alerts the closer via Slack with a full lead summary. The closer walks into the call already briefed.

- **Post-call intelligence.** After every Fathom-recorded call, Claude classifies the outcome (WON, FOLLOW UP, NOT QUALIFIED), writes structured notes to HubSpot, creates follow-up tasks, and alerts the team. Sales intelligence, not note forwarding.

What makes this interesting is that these are not three separate workflows. They are one system with three entry points. Every path converges on the same destinations: HubSpot, Google Sheets, Notion, and Slack. Designing them as a unified system means shared error handling, consistent logging, and no duplicate contacts across channels.

## Our Proposed Solution

The system is built as a unified pipeline in n8n with three webhook entry points. Each entry point handles a different trigger source but shares common infrastructure for CRM updates, logging, and alerting.

**Workflow 1: AI Reply Classifier (Priority)**

Webhook receives reply payloads from Instantly and HeyReach. Claude API classifies the reply using structured output (category + confidence score + suggested response). The classification routes through a confidence threshold gate: above 80% confidence, the system auto-responds; below 80%, it routes to manual review. Hot leads receive 2-3 proposed meeting slots with a Calendly booking link. Every reply and AI response is logged to Google Sheets and a Notion database. HubSpot contact status updates at each step.

Key design decisions:
- Structured JSON output from Claude (not free text) ensures reliable routing
- Confidence threshold prevents embarrassing auto-responses on ambiguous replies
- Deduplication check against HubSpot before creating new contacts
- Separate handling for Instantly vs HeyReach payloads (different webhook formats)

**Workflow 2: Booking Confirmation**

Calendly webhook fires on new booking. The workflow matches the booking to an existing HubSpot contact (or creates one), updates the deal stage to "Meeting Booked," adds a row to the Google Sheets booked meetings tab, creates a Notion page with the full lead summary, and sends a Slack alert to the assigned closer. The closer gets: lead name, company, campaign source, classification history, and all prior interactions.

**Workflow 3: Post-Call Intelligence**

Fathom webhook fires after every recorded call with the transcript, summary, and action items. Claude classifies the call outcome and generates a structured note with: outcome category, key objections or interests, next steps, and a priority score. The structured note is written to the HubSpot contact timeline. If the outcome is FOLLOW UP, a HubSpot task is auto-created with the correct priority and due date. Slack alert to the team with the outcome summary.

**Shared Infrastructure:**
- Error handling with Slack alerts on any workflow failure
- Retry logic for API rate limits (HubSpot, Google Sheets)
- Structured logging to a dedicated Google Sheet for debugging
- Contact deduplication across all three entry points

## Architecture

The three workflows share a common output layer:

```
Entry Points              Intelligence         Shared Outputs
-----------              ------------         --------------
Instantly webhook   -->                   --> HubSpot (contact update)
HeyReach webhook    -->   Claude API      --> Google Sheets (logging)
Calendly webhook    -->   Classification  --> Notion (database)
Fathom webhook      -->                   --> Slack (alerts)
```

## Timeline & Milestones

**Days 1-3: AI Responder (Workflow 1)**
- Day 1: n8n instance setup on Railway, webhook endpoints configured, Claude API prompt engineering for classification
- Day 2: Instantly and HeyReach webhook handling, classification routing logic, auto-response generation
- Day 3: HubSpot, Sheets, Notion, and Slack output nodes, confidence threshold tuning, error handling

**Days 4-5: Booking and Post-Call (Workflows 2 and 3)**
- Day 4: Calendly webhook integration, HubSpot deal stage automation, Sheets and Notion logging, Slack closer alerts
- Day 5: Fathom webhook integration, Claude call transcript classification, structured HubSpot notes, follow-up task automation

**Days 6-7: Testing and Hardening**
- Day 6: End-to-end testing with 5 real leads through the full pipeline, edge case handling, deduplication verification
- Day 7: Error handling audit, retry logic, monitoring setup, exported workflow JSONs, maintenance documentation

## Investment

**$1,500 fixed; all three workflows delivered and tested**

What is included:
- 3 production-ready n8n workflows on your Railway instance
- Claude API prompt engineering for reply classification and call outcome analysis
- All 11 integrations configured and tested (Instantly, HeyReach, Dripify, Calendly, HubSpot, Sheets, Notion, Fathom, Slack, Claude API, n8n)
- Confidence threshold for AI auto-responses (prevents sending on uncertain classifications)
- Contact deduplication across email and LinkedIn channels
- Error handling with Slack failure alerts
- 5 real leads processed through the full flow as acceptance test
- Exported n8n workflow JSON files
- Maintenance guide with troubleshooting steps

What the price reflects: this is 3 interconnected production pipelines with AI classification logic, not 3 simple A-to-B connections. The classification confidence gates, error handling, retry logic, and deduplication are what separate a system that runs reliably from one that breaks silently when the first API changes its response format.

## About UnpauseAI

We build automation infrastructure for businesses running at scale. Our systems process thousands of automated operations monthly across CRM, email, scheduling, and AI integrations. We work with n8n and Make.com daily, and Claude API is our primary AI tool, not something we are learning on the job. Every workflow we build includes error handling, structured logging, and documentation as standard. Based in Europe, remote worldwide.
