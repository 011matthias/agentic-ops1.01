---
id: p013
slug: ai-marketing-make-expert
prospect: AI Marketing Agency
contact: Noah
source: upwork
source_url: "https://www.upwork.com/jobs/~022037586283904672243"
project_title: "Make.com Expert for AI Marketing -- 8-Agent Autonomous System"
status: draft
track: 2
created: "2026-03-27"
sent: null
value_estimate: "$35.63/hr -- Phase 1 ~$4,300-5,700 (120-160 hrs)"
timeline: "16 weeks (Phase 1: 8 weeks, Phase 2: 8 weeks)"
tags: [Make.com, Claude API, Google Ads API, Marketing Automation, Multi-Agent, JSON Parsing, Guardrails]
access_code: aimarketing-2026
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "Marketing Agency (Noah)"
  prospect_industry: "Digital Marketing / Ad Management"
  prospect_location: "Gastonia, North Carolina, United States"
  prospect_contact: "Noah"
  prospect_systems: [Make.com, Claude API, Google Ads API, LinkedIn Ads, Meta Ads, Mailchimp API, WordPress REST API, ClickUp, Slack, Google Sheets]
  prospect_pain_points:
    - "Needs a multi-client autonomous marketing system built methodically -- 8 agents, 16 scenarios, 3-phase autonomy"
    - "Claude API JSON parsing reliability -- free-form text kills downstream modules"
    - "Guardrails must be structural (Make.com conditionals), not prompt-based"
    - "Previous bad experience with sloppy execution (tasks marked done that were not complete)"
  job_language_echoes:
    - "not a simple automation project"
    - "8-agent architecture"
    - "robust JSON parser with markdown fence stripping"
    - "hard-coded guardrails...cannot be reasoned around by the AI"
    - "one scenario at a time, testing before connecting to the next"
  location_advantage: "Skip -- US client"
  relevant_proof_points:
    - "Meji Media: 10+ production Make.com scenarios, multi-system orchestration"
    - "Warme Wimmer: Make.com audit and migration, scenario-by-scenario rebuild"
    - "Meta-proof: Our proposal pipeline runs on Make.com + Claude API"
  budget_gap: "No gap. Our rate ($35.63/hr) close to client avg paid ($37.23/hr). Also offering per-scenario fixed-price alternative."
  profile_cherry_picks:
    platforms: [Make.com, Claude API, Google Sheets]
    proof_points: [Meji Media multi-scenario architecture, Warme Wimmer audit methodology]
    reasoning: "Direct 1:1 match on Make.com + Claude API + multi-system orchestration. Our own pipeline is meta-proof."
---

## What We Understood

Noah is building a fully autonomous marketing agency system: 8 AI agents orchestrated through Make.com, with Claude API as the reasoning engine. The system reads data from Google Ads, LinkedIn, Meta, Mailchimp, and WordPress daily, reasons about performance, creates tasks in ClickUp, posts briefings to Slack, and eventually executes approved changes with hard-coded guardrails.

This is systems engineering, not standard Make.com work. The architecture manages multiple clients from a shared Google Sheets knowledge base, with each client configured by a single row. The same scenarios run for every client, calibrated by their configuration object.

## Key Technical Challenges

1. **Claude API JSON Parsing**: Every Claude response must return valid JSON with a defined schema. Free-form text breaks every downstream module silently. Requires markdown fence stripping and schema validation.

2. **Structural Guardrails**: 8 hard-coded guardrails implemented as Make.com conditional modules, not in the Claude prompt. Budget change ceiling (20%), branded keyword lock, minimum data threshold, delete lock (archive only), and phase-level execution controls.

3. **Multi-Client Architecture**: Scenarios must loop through a client list, adapt behavior per client configuration, and handle rate limits across multiple ad platform APIs.

## Our Proposed Solution

Scenario-by-scenario build following Noah's week-by-week plan. Each scenario gets built, tested, and validated individually before connecting to the next. Full documentation of environment variables, webhook URLs, and scenario blueprints at every step.

## Timeline

- **Phase 1 (Weeks 1-8)**: Scenarios 1-10. Analysis and task assignment only. No platform writes.
- **Phase 2 (Weeks 9-16)**: Scenarios 11-16. Controlled execution with hard-coded guardrails.

## Investment

- **Hourly**: $35.63/hr, estimated 120-160 hours for Phase 1
- **Fixed-price alternative**: ~$500/scenario for Phase 1 (10 scenarios = ~$5,000)
