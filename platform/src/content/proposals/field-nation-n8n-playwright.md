---
id: p014
slug: field-nation-n8n-playwright
prospect: Jamiane
contact: Jamiane
source: upwork
source_url: "https://www.upwork.com/jobs/~022037525757507537173"
project_title: "n8n + Playwright Workflow for Field Nation Work Orders"
status: draft
track: 2
created: "2026-03-28"
sent: null
value_estimate: "$150"
timeline: "3 days"
tags: [n8n, playwright, browser-automation, email-parsing, claude-api, vps, field-nation]
access_code: "fieldnation-2026"
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "Jamiane (individual contractor)"
  prospect_industry: "IT field services / gig marketplace"
  prospect_location: "Freeport, Bahamas"
  prospect_contact: "Jamiane"
  prospect_systems:
    - Field Nation
    - n8n
    - Playwright
    - Claude API
    - VPS
  prospect_pain_points:
    - "Manually reviewing and responding to Field Nation work order emails"
    - "Missing time-sensitive work orders due to manual processing delay"
    - "Need configurable business rules for accept/request/skip decisions"
  job_language_echoes:
    - "process incoming Field Nation work order emails"
    - "apply business rules"
    - "requesting or accepting jobs using browser automation"
    - "this is a test"
  location_advantage: ""
  relevant_proof_points:
    - "n8n workflow design with custom code nodes and structured error handling"
    - "AI classification systems with confidence-threshold routing"
  budget_gap: "$150 vs posted $120 fixed ($50 base + $50 bonus for 4hr delivery)"
  profile_cherry_picks:
    - "n8n primary expertise; exact match for job requirements"
    - "Claude API integration; optional email parsing with resilient format handling"
---

## What We Understood

You process incoming Field Nation work order emails and manually decide which jobs to accept, request, or skip. This takes time, and on a first-come-first-served marketplace, delay means missed work orders.

You want an automated pipeline: email comes in, business rules evaluate the job (pay rate, location, work type, travel distance), and Playwright takes action on the Field Nation website. The system runs on your VPS using n8n as the orchestrator, with optional Claude API for intelligent email parsing.

You mentioned this is a test project with ongoing work potential. The system I deliver is designed to be extended, not thrown away.

## Our Proposed Solution

A 5-stage pipeline built entirely in n8n with a Playwright automation layer:

**Stage 1; Email Ingestion:** n8n IMAP Trigger monitors your inbox for Field Nation work order notifications. Filters by sender domain, extracts the email body.

**Stage 2; Email Parsing:** Claude API extracts structured data from each work order email: job title, location, pay rate, work type, date/time, travel requirements. Falls back to regex parsing for standard email formats. Claude handles format changes gracefully; regex is faster but breaks when Field Nation updates their email templates.

**Stage 3; Decision Engine:** Configurable business rules in n8n (IF/Switch nodes). You set the thresholds: minimum pay rate, maximum travel distance, preferred work types, schedule conflicts, blacklisted companies. Output: ACCEPT, REQUEST, SKIP, or MANUAL_REVIEW.

**Stage 4; Browser Automation:** Playwright script logs into Field Nation, navigates to the work order, and executes the decision. Handles session persistence (cookie storage between runs), expired session re-authentication, and "already taken" detection.

**Stage 5; Logging:** Every decision and action logged to Google Sheets or SQLite. Notifications for manual review items. Daily summary of actions taken.

## Timeline & Milestones

- **Day 1:** Email parsing pipeline + decision engine (n8n workflow with Claude API integration)
- **Day 2:** Playwright browser automation with session management and error handling
- **Day 3:** Integration testing, VPS deployment, documentation

## Investment

**$150 fixed price** for the complete system. The $30 above the posted budget covers production-grade session persistence, race condition handling, and a documented n8n workflow you can maintain yourself.

## About UnpauseAI

I build n8n workflows professionally, including AI-powered email parsing, browser automation, and API integrations.
