---
id: p022
slug: brisken-lead-automation
prospect: Brisken
contact: Dirk
source: direct
source_url: null
project_title: "Unified Automation Platform"
status: draft
track: 2
created: "2026-03-31"
sent: null
value_estimate: "WIP - pricing excluded pending scope finalization"
timeline: "TBD - depends on platform decision"
tags: [automation, lead-management, ai-response, hitl, email-parsing, unified-dashboard, multi-tenant, invoice-routing]
deliverables:
  letter: false
  video: false
  site: true
research:
  prospect_company: "Brisken"
  prospect_industry: "SAP Consulting / Technology"
  prospect_location: "Germany (CET)"
  prospect_contact: "Dirk"
  prospect_systems: [SAP Discovery Center, SAP Store, Website Forms, LinkedIn, Outlook, Zoho CRM]
  prospect_pain_points:
    - "Leads arrive from 4 channels in different formats with no unified view"
    - "Manual processing means slow response times and inconsistent follow-up"
    - "No systematic way to prioritize high-value leads over low-quality inquiries"
    - "Invoice routing requires 15 min/day of manual email forwarding"
    - "Multiple tools (Outlook, LinkedIn, CRM) with no central management interface"
    - "No visibility into which leads were contacted, which responded, which went cold"
  scope_estimate:
    description: "Unified platform: lead nurturing (Phase 1-3), then invoice/AP routing, compliance emails, LinkedIn management (Phase 4+). Platform choice TBD."
    proposed_price: null
    hours: null
    rate: null
  posted_budget: null
  competitor_research: null
  value_hook: "One dashboard for all channels, all approvals, all conversations - starting with lead nurturing"
design_decisions:
  orchestrator: "TBD (evaluating n8n vs Firebase/Firestore vs custom)"
  pages: [index, solution, timeline, faq]
  pricing_model: "WIP - excluded from current scope page"
  notes: "Project scope page for existing client. Expanded from lead automation to unified platform after 2026-04-10 call. Dirk owns IP, multi-tenant required, Upwork routing planned."
---

# Brisken Unified Automation Platform

Centralized lead nurturing, email management, and business process automation. One dashboard for all channels, all approvals, all conversation history. Lead nurturing is the first use case; invoice routing, compliance, and LinkedIn management follow on the same platform.

## Context

Brisken is an existing client. This scope page was created as a scoping and alignment artifact, not as a sales pitch. Scope expanded significantly after 2026-04-10 call with Dirk. Platform choice (n8n vs Firebase vs custom) is open and must be resolved before build starts. Pricing is WIP and excluded from the site.

## Phases

- Phase 1: SAP + Website ingest, basic pipeline, platform setup
- Phase 2: LinkedIn ingest, lead ranking, AI response drafting, HITL review
- Phase 3: Reply monitoring, mandatory human escalation, unified dashboard
- Phase 4+: Invoice/AP routing, compliance emails, LinkedIn management, multi-tenant
