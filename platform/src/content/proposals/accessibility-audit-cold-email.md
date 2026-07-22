---
id: p010
slug: accessibility-audit-cold-email
prospect: "TBD"
contact: "TBD"
source: upwork
source_url: "https://www.upwork.com/jobs/~022037371665870462363"
project_title: "n8n Accessibility Audit & Cold Email Outreach Pipeline"
status: draft
track: 2
created: "2026-03-27"
sent: null
value_estimate: "$650 fixed"
timeline: "9 days"
tags: [n8n, accessibility-testing, cold-email, google-sheets, instantly-ai, puppeteer, axe-core]
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "Digital marketing agency (name TBD)"
  prospect_industry: "Digital Marketing"
  prospect_location: "Mississauga, Ontario, Canada"
  prospect_contact: "TBD"
  prospect_systems:
    - "n8n (self-hosted on NameHero)"
    - "axe-core via Puppeteer (headless Chrome)"
    - "Google Sheets"
    - "Instantly.ai"
    - "NameHero Silver NVMe (cPanel shared hosting)"
  prospect_pain_points:
    - "Needs automated WCAG 2.1 AA accessibility auditing at scale (500 URLs per run)"
    - "Wants cold email outreach triggered automatically by audit failures"
    - "Must self-host n8n on NameHero shared hosting, not cloud"
    - "Needs graceful error handling for headless browser blocking and timeouts"
    - "Requires Loom walkthrough and written docs for independent maintenance"
  job_language_echoes:
    - "guard rails and caveats"
    - "headless browser blocking"
    - "500 URLs in one run without manual intervention"
    - "scheduled batch job, not a real-time trigger"
    - "what breaks and how to fix it"
  location_advantage: "6-hour overlap with Ontario business hours (CET to EST)"
  relevant_proof_points:
    - "n8n workflow design; production self-hosted workflows with custom code nodes"
    - "Marketing analytics pipeline; understands lead gen and cold email context"
  budget_gap: "$10 placeholder budget, avg bid $427; proposed $650"
  profile_cherry_picks:
    - "n8n primary; exact match for self-hosted n8n requirement"
    - "Google Sheets data layer; direct experience"
    - "Marketing ops background; understands cold email deliverability"
---

## What We Understood

You run a digital marketing agency and need a one-time n8n workflow that reads company websites from a Google Sheet, runs WCAG 2.1 AA accessibility audits using axe-core via headless Puppeteer, writes pass/fail results back to the sheet, and triggers personalized cold email sequences through Instantly.ai for sites that fail.

The workflow needs to handle 500 URLs in a single batch run without manual intervention, gracefully skip sites that block headless browsers or time out, and log every triggered email with timestamps. You want n8n self-hosted on your NameHero Silver NVMe shared hosting, not n8n cloud.

## Our Proposed Solution

A 4-phase n8n workflow with error handling at every step:

1. **Google Sheets Reader**: Pulls company name, URL, and contact email from a structured spreadsheet template
2. **axe-core Audit Engine**: Launches headless Puppeteer, injects axe-core, captures WCAG 2.1 AA violations per URL with fallback logging for blocked or timed-out sites
3. **Results Writer**: Updates the source sheet with pass/fail status, total error count, and top 3 error types per URL
4. **Instantly.ai Trigger**: Sends audit summary and contact data to Instantly via API for sites that fail, logs each triggered email to a second sheet with timestamps

## Timeline & Milestones

- **Days 1-2:** n8n installation on NameHero + Google Sheets template setup
- **Days 3-5:** axe-core audit workflow build with error handling and browser blocking fallbacks
- **Days 6-7:** Instantly.ai API integration + email logging sheet
- **Days 8-9:** Full-scale testing (500 URLs), Loom walkthrough recording, written documentation, handoff

## Investment

$650 fixed price, single milestone. Includes n8n installation, complete workflow, Google Sheet template, Instantly.ai integration, Loom walkthrough (10-15 min), written troubleshooting documentation, and all credentials stored in n8n credentials manager.

## About UnpauseAI

We build automation workflows on n8n and Make.com for agencies and SaaS companies. Self-hosted n8n with custom code nodes, API integrations, and batch processing at scale is what we do daily.
