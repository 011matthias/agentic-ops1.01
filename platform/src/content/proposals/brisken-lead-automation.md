---
id: p022
slug: brisken-lead-automation
prospect: Brisken
contact: Dirk
source: direct
source_url: null
project_title: "Multi-Channel Lead Automation Pipeline"
status: draft
track: 2
created: "2026-03-31"
sent: null
value_estimate: "$3,200 fixed (3 phases)"
timeline: "6-8 weeks (phased delivery)"
tags: [automation, n8n, lead-management, ai-response, hitl, email-parsing]
access_code: "brisken-2026"
deliverables:
  letter: false
  video: false
  site: true
research:
  prospect_company: "Brisken"
  prospect_industry: "SAP Consulting / Technology"
  prospect_location: "Germany (CET)"
  prospect_contact: "Dirk"
  prospect_systems: [SAP Discovery Center, SAP Store, Website Forms, LinkedIn, Gmail]
  prospect_pain_points:
    - "Leads arrive from 4 channels in different formats with no unified view"
    - "Manual processing means slow response times and inconsistent follow-up"
    - "No systematic way to prioritize high-value leads over low-quality inquiries"
    - "Second responses require human review but there is no structured escalation"
  scope_estimate:
    description: "5 n8n workflows across 3 phases: ingest layer (A0-A2), follow-up pipeline (A3), reply monitoring (A4)"
    proposed_price: 3200
    hours: 62
    rate: 65
  posted_budget: null
  competitor_research: null
  value_hook: "Unified lead pipeline with AI-drafted first responses and quality-based routing"
design_decisions:
  orchestrator: n8n
  pages: [index, solution, timeline, investment, faq]
  pricing_model: "Scope-based, phased delivery"
  notes: "Backwards proposal for existing client. Scoping artifact, not sales pitch."
---

# Brisken Lead Automation Pipeline

Multi-channel lead capture from SAP Discovery Center, SAP Store, website forms, and LinkedIn. AI-powered lead ranking, personalized response drafting, and human-in-the-loop review gates. Built on n8n with phased delivery.

## Context

Brisken is an existing client. This proposal site was created as a scoping and alignment artifact, not as a sales pitch. Dirk provided confirmed requirements via email on 2026-03-30.

## Phases

- Phase 1: SAP + Website ingest, basic pipeline, n8n setup
- Phase 2: LinkedIn ingest, lead ranking, AI response drafting, HITL review
- Phase 3: Reply monitoring, mandatory human escalation
- Phase 4 (Future): Accounting/invoice automation
