---
id: p008
slug: openwebui-email-compliance
prospect: "TBD"
contact: "TBD"
source: upwork
source_url: "https://www.upwork.com/jobs/~022037487280363523610"
project_title: "OpenWebUI + AI Email Compliance Monitor"
status: draft
created: "2026-03-27"
sent: null
value_estimate: "$3,250"
timeline: "4-5 weeks"
tags: [aws, anthropic, open-webui, email-monitoring, gdpr, nlp, compliance, uk-gdpr]
track: 2
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "TBD (UK enterprise, Halifax, 100-1000 employees)"
  prospect_industry: "Unknown (large enterprise)"
  prospect_location: "Halifax, United Kingdom"
  prospect_contact: "TBD"
  prospect_systems:
    - Amazon Web Services (AWS)
    - Microsoft 365 / Gmail
    - Anthropic API (Claude)
    - Open WebUI
    - Slack (optional alerts)
  prospect_pain_points:
    - "Need secure AI access for staff without external data retention"
    - "Need automated email monitoring for complaints, sentiment, legal risk"
    - "Previous attempt at email monitoring (Azure/OpenAI, $250) likely underscoped"
    - "GDPR compliance for processing personal email data through AI"
    - "System must run without developer reliance post-deployment"
  job_language_echoes:
    - "fully manageable in-house without reliance on the developer"
    - "GDPR-conscious handling of personal data"
    - "event-based architecture (not manual scripts)"
    - "no data is retained or used for training externally"
  relevant_proof_points:
    - "EU-based -- understands UK GDPR firsthand"
    - "Built compliance-grade automation pipelines for enterprise clients"
  budget_gap: "Client budget $600, proposed $3,250 -- 5x gap requires explicit justification"
---

## What We Understood

You're building two connected systems for a large UK team:

1. A secure AI chat interface so staff can use Claude (Anthropic) internally -- without any data leaking to external training sets or third-party storage.

2. An automated email monitoring pipeline that catches complaints, negative sentiment, urgent messages, and legal risk -- flagging them before they escalate.

The previous version of this (the Azure/OpenAI project) was likely a first pass. This time you want it production-grade: event-driven, self-healing, GDPR-compliant, and hands-off after deployment.

The part most proposals will underestimate: this isn't just an API integration. A 100+ person UK company routing customer emails through AI has real GDPR exposure -- international data transfers, automated decision-making rights, retention liability. That compliance layer is what separates a script from a system.

## Our Proposed Solution

### Pipeline 1: AI Chat (Open WebUI)
- Open WebUI deployed on AWS (EC2 or ECS, Docker-based)
- Connected to Anthropic API with zero data retention configured
- Staff authentication (SSO integration or managed user accounts)
- No email content, chat logs, or PII stored externally

### Pipeline 2: Email Compliance Monitor
- Email ingestion via Microsoft 365 Graph API (or Gmail API) -- near real-time webhooks
- Pre-processing: extract text, strip attachments, minimize data before AI analysis
- Anthropic API analysis per email: sentiment, complaint detection, key tags, severity score
- Results stored in encrypted RDS (AWS-managed, retention-automated)
- Alerts for high-risk emails via Slack and/or email notifications
- Automated retention engine: archive after X days, purge after Y days, full audit trail

### GDPR Compliance Layer
- Data Processing Impact Assessment (DPIA) template
- Data minimization at every pipeline stage
- Anthropic API configured for zero data retention
- International transfer documentation (UK to US for API calls)
- Subject access request procedures
- Role-based access controls with audit logging

## Timeline & Milestones

### Phase 1: Email Compliance Monitor + GDPR Framework (Weeks 1-3)
- Week 1: Email ingestion pipeline + Anthropic API integration + GDPR framework
- Week 2: Alert system + retention automation + structured storage
- Week 3: Testing with real email volume + DPIA documentation + compliance review

### Phase 2: Open WebUI + Hardening (Weeks 4-5)
- Week 4: Open WebUI deployment + auth + Anthropic API connection
- Week 5: Cost monitoring + billing alerts + documentation + handoff

## Investment

**Total: $3,250** (phased)

Phase 1 -- Email Compliance Monitor + GDPR Framework: **$1,850**
- Email ingestion pipeline (M365/Gmail)
- AI analysis with Anthropic API
- Structured storage with encryption
- Alert system (Slack + email)
- Retention automation
- DPIA template + compliance documentation

Phase 2 -- Open WebUI + Integration + Hardening: **$1,400**
- Open WebUI deployment on AWS
- Staff authentication system
- Cost monitoring + billing alerts
- Architecture documentation
- Handoff guide

Post-deployment: included in scope -- no time-limited support window.

## About UnpausAI

We build automation systems for companies that need things to work reliably in production, not just in demos. EU-based, which means we understand UK GDPR requirements firsthand -- not as a checkbox, but as a design constraint that shapes the architecture from day one.
