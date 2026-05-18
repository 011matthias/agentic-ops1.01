---
id: p024
slug: ai-shipment-support-bot
prospect: "German E-Commerce Shop"
contact: TBD
source: upwork
source_url: ""
project_title: "AI Customer Support Bot for Shipment Tracking"
status: sent
track: 2
created: "2026-05-18"
sent: "2026-05-18"
value_estimate: "$2,500 core phase, $4,000 full build, optional monthly retainer"
timeline: "Core phase 2 weeks, full build 4 to 5 weeks"
tags: [n8n, python, ai, llm, customer-support, ecommerce, erp-integration, amazon-sp-api, email-automation, german, wismo]
access_code: "ai-shipment-support-bot-2026"
deliverables:
  letter: true
  video: true
  site: true
  artifact: true
research:
  prospect_company: "German E-Commerce Shop"
  prospect_industry: "Online retail / e-commerce"
  prospect_location: "Germany (Worldwide per Upwork posting, German-only customer base)"
  prospect_contact: "TBD"
  prospect_systems: ["ERP interface/API", "All-Inkl Webmail", "Amazon Message Center", "Amazon Selling Partner API"]
  prospect_pain_points:
    - "Repetitive 'Where is my shipment?' (WISMO) tickets eating support time"
    - "Follow-up correction requests on tracking that need a fast accurate reply"
    - "Tracking data already exists in the ERP but a human has to look it up and paste it every time"
    - "Two separate inboxes to monitor: All-Inkl email and Amazon Message Center"
    - "Replies must be exclusively German and on-brand"
    - "Wants a reliable long-term partner, not a one-off script that breaks silently"
  job_language_echoes:
    - "Where is my shipment?"
    - "Correction / update requests related to shipment tracking"
    - "We already have an ERP interface/API"
    - "exclusively German"
    - "All-Inkl Webmail"
    - "Amazon Message Center"
    - "reliable long-term partner for future AI automations"
  location_advantage: ""
  relevant_proof_points:
    - "Targeted small-LLM calls for the judgment parts (intent, extraction, phrasing) plus deterministic code for everything that must be exact"
    - "Tracking number, link, and carrier injected verbatim from the ERP, never model-generated, so the bot cannot invent a shipment status"
    - "Confidence gating with human handoff: low-confidence or out-of-scope messages become a drafted reply for a person, never an auto-send guess"
    - "Every build ships with documentation, a runbook, and a handoff so the client is not dependent on the developer to keep it running"
    - "Primary stack: n8n orchestration, Python, OpenAI / Claude small models, PostgreSQL"
  budget_gap: "No budget posted; proposal sets a scope-based phased price and offers hourly as an alternative"
  profile_cherry_picks:
    - "Lead with the grounding answer in the first 3 lines: tracking facts come from the ERP, never the model"
    - "Answer their four required proposal questions (time, technical approach, language/LLM/model, similar work) structurally across the site"
    - "Name the Amazon Message Center policy constraint explicitly, it is the edge case most applicants will miss"
  scope_estimate:
    description: "Phase 1 core (2 intents, All-Inkl email channel, ERP grounding, German replies, human handoff) fixed at $2,500. Phase 2 full build (Amazon Message Center channel, correction write-back, audit log) brings the total to $4,000. Optional monthly retainer for the long-term-partner relationship and future automations."
    proposed_price: "$2,500 to $4,000 phased, hourly available on request"
    hours: null
    rate: null
  posted_budget: "Not stated"
  value_hook: "The tracking facts come from your ERP, never the model. Here is exactly how I'd build a German support bot that cannot invent a shipment status."
design_decisions:
  orchestrator: "n8n + Python + small LLM (GPT-4o-mini / Claude Haiku class)"
  pages: [index, solution, workflow, timeline, investment, faq, onboarding, gdpr]
  pricing_model: "Phased fixed-price, optional retainer, hourly available"
  notes: "Centerpiece is solution.html (grounding architecture) plus workflow.html (visual pipeline). Artifact is a runnable n8n workflow skeleton JSON. GDPR page included because the bot processes EU customer and Amazon buyer personal data."
---

# AI Customer Support Bot for Shipment Tracking

A proposal for a German-language AI support bot that answers "Where is my shipment?" and tracking-correction requests across All-Inkl email and Amazon Message Center, grounded in the client's existing ERP API.

## Centerpiece

The core idea: the bot's tracking facts come from the ERP, never from the language model. A small LLM call handles the judgment parts (which order is this about, what is the customer asking, phrase the reply in natural German). The tracking number, link, carrier, and status are injected verbatim from a deterministic ERP lookup. If the ERP returns nothing, the bot does not guess, it hands off to a person.

Full architecture on the [Solution page](/clients/ai-shipment-support-bot/solution). Visual pipeline on the [Workflow page](/clients/ai-shipment-support-bot/workflow). Runnable n8n skeleton downloadable from the site.

## Track

Track 2. Full HTML site so the grounding architecture, the Amazon Message Center policy handling, and the phased pricing are concrete and reviewable before any code is written. Cover letter and video script in `workspace/proposals/ai-shipment-support-bot/`.
