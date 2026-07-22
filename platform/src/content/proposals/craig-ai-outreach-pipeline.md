---
id: p004
slug: craig-ai-outreach-pipeline
prospect: Craig
contact: Craig
source: upwork
source_url: "https://www.upwork.com/jobs/~022036942990510570420"
project_title: "Claude API Outreach Pipeline"
status: draft
track: 2
created: "2026-03-26"
sent: null
value_estimate: "$3,500"
timeline: "2-3 weeks"
tags: [Claude API, Lead Generation, CRM Integration, Email Automation, AI Personalization, n8n]
deliverables:
  letter: true
  video: true
  site: true
---

## What We Understood

You run a marketing agency in Melbourne and sell web development projects. You want an automated outreach system that uses the Claude API to land new clients consistently.

The core problem is not sending more emails. You have already tried cold email outreach. The problem is that generic outreach does not convert because every message reads the same way to the recipient. What you need is a system that researches each prospect before writing a single word, so every message demonstrates that you understand their specific situation.

You need four things:
1. A pipeline that pulls leads from your CRM
2. Logic that researches each lead (industry, website, pain points) using Claude
3. Integration to send or queue messages via email or LinkedIn
4. A dashboard to review, approve, and track outreach activity

## Our Proposed Solution

We build a research-first outreach pipeline on n8n (open-source automation platform) with Claude API at its core.

**Phase 1: Core Pipeline ($2,000)**

The system starts when a new lead enters your CRM. A webhook triggers the pipeline, which:
- Scrapes the lead's website and social profiles
- Sends the scraped content to Claude API with a research prompt
- Claude analyzes the business: industry, services offered, recent activity, likely pain points
- Based on the research, Claude drafts a personalized outreach message tailored to that specific prospect
- The draft lands in an approval queue where you can review, edit, or approve with one click

**Phase 2: Delivery + Dashboard ($1,500)**

Once approved, the system:
- Sends via your email tool (Instantly, Smartlead, or SMTP) with proper warm-up and deliverability settings
- Queues LinkedIn messages for manual send or Dripify automation
- Logs every touchpoint in a tracking sheet: lead name, research summary, message sent, channel, status, response
- Provides a simple dashboard view of pipeline activity, response rates, and follow-up queue

**Key design decisions:**
- Approval gate before send: No message goes out without your review. This is not a blast tool.
- Research depth over send volume: Claude spends 10-15 seconds per lead doing real analysis, not template-filling.
- Multi-channel but not forced: Email is automated, LinkedIn is queued. You choose per lead.
- Your data, your infrastructure: n8n runs on your server. No vendor lock-in. Export workflows anytime.

## Timeline & Milestones

| Phase | Days | Deliverables |
|-------|------|-------------|
| Phase 1: Core Pipeline | Days 1-7 | CRM integration, Claude research engine, message generation, approval queue |
| Phase 2: Delivery + Dashboard | Days 8-14 | Email/LinkedIn send, activity tracking, dashboard, testing |
| Hardening | Days 15-17 | Edge case testing, prompt tuning, handover documentation |

Conditional on CRM access and email tool credentials being ready on Day 1.

## Investment

**Total: $3,500** (phased)

- Phase 1: $2,000; CRM pull + Claude research + message generation
- Phase 2: $1,500; Email/LinkedIn delivery + approval dashboard

Payable on Upwork. Milestone-based: Phase 1 payment on delivery, Phase 2 payment on delivery.

**Ongoing (optional):** $75/hr for iteration, optimization, new outreach channels, or prompt tuning.

## About UnpauseAI

We build automation infrastructure for agencies and service businesses. Our systems run on open-source tools (n8n, Make.com) with AI integration (Claude API, OpenAI). Every system we deliver includes error handling, testing with real data, and full documentation. You own the code.
