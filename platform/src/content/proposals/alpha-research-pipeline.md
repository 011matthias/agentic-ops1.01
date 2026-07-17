---
id: p003
slug: alpha-research-pipeline
prospect: Alpha Research
contact: ""
source: upwork
source_url: "https://www.upwork.com/jobs/~022036468953555137858"
source_url_2: "https://www.upwork.com/jobs/~022036483665457814623"
project_title: "AI-Powered Investment Research Pipeline"
status: draft
track: 2
created: "2026-03-26"
sent: null
value_estimate: "10000-22000"
timeline: "12 working days + ongoing"
tags: [n8n, claude-api, web-scraping, google-sheets, google-drive, hitl, ai-classification, news-filtering, document-processing]
deliverables:
  letter: false
  video: false
  site: false
---

## What We Understood

You are building an automated, AI-powered personal investment research engine to track 300+ target companies and macroeconomic sources. You posted two related jobs that share infrastructure: a web scraping pipeline (data ingestion) and an AI document processing + news filtering + HITL pipeline (the processing brain).

Together, this is one system with five interconnected pipelines:

- **Web Scraping Dispatcher.** Scheduled workflow reads a master Google Sheets database of 300+ companies, dispatches URLs in controlled batches to scraping sub-workflows. Prevents IP bans and workflow timeouts.

- **Modular Document Scrapers.** Sub-workflows scrape investor relations pages, use AI to identify the latest financial documents (earnings presentations, BOP numbers, monthly bulletins), and download them to cloud storage with standardized naming. Fallback to external headless browser API for JS-heavy sites.

- **AI Document Synthesis.** When a new analysis file appears, the workflow fetches it alongside 4 existing thesis files (memo.md, pulse.md, news.md, meetings.md) and uses an LLM to synthesize what needs updating.

- **News Intelligence Filter.** Daily scheduled run pulls news from AlphaVantage, SerpAPI, and RSS for priority tickers, then compares breaking news against Core Thesis sections to flag material deviations. Ignores general market noise.

- **Human-in-the-Loop Approval.** Nothing overwrites core files automatically. Email with AI-proposed diffs and Approve/Reject/Edit buttons. Wait node pauses until human decision, then cleanly appends to markdown files.

Delivery model: sandbox environment with dummy Google Workspace. Final delivery is exported n8n JSON workflow files.

## Our Proposed Solution

Five pipelines built as one unified n8n system. Shared infrastructure: Google Sheets company registry, cloud storage layer, LLM processing patterns, error handling with notification.

Architecture:
```
Data Sources              AI Processing            Intelligence Out
-----------              -------------            ----------------
Google Sheets (300+)  -->  Dispatcher           --> Cloud Storage (organized)
Web Pages/IR Sites    -->  LLM Link Extract     --> Thesis Updates (.md)
News APIs (3+)        -->  Relevance Scoring    --> News Digest (JSON)
File Watcher (.md)    -->  Thesis Synthesis     --> HITL Email Approval
```

Key design decisions:
- External browser API (ScrapingBee/Bright Data) for JS-rendered pages. n8n orchestrates, external service handles browser rendering. Production-grade approach with proxy rotation and CAPTCHA handling.
- HITL via n8n Wait + Webhook nodes. Email contains HTML buttons that call n8n webhooks to resume paused execution. No automatic file overwrites.
- Deduplication via hash comparison against existing files before download.
- Batch processing with configurable delays between groups to prevent IP bans.

## Timeline

**Phase 1: Foundation (Days 1-5)** -- Dispatcher, scrapers, browser API integration, dedup, cloud storage
**Phase 2: Intelligence (Days 6-9)** -- Thesis synthesis, news filter, LLM relevance scoring, HITL approval
**Phase 3: Testing & Delivery (Days 10-12)** -- E2E testing with 5-10 real companies, prompt tuning, JSON export, documentation

## Investment

Two options:

**Option A: Foundation + Ongoing (Recommended)**
- Phase 1 fixed: all 5 pipelines for first 5-10 site types, fully tested in sandbox
- Ongoing hourly: additional scrapers, prompt tuning, new data sources, maintenance

**Option B: Full Project Fixed**
- All 5 pipelines for 50 site types, 2 weeks prompt tuning, 30-day support

## About UnpauseAI

We build automation infrastructure for businesses running at scale. Our systems process thousands of automated operations monthly across CRM, email, scheduling, and AI integrations. We work with n8n daily, and Claude API is our primary AI tool. Based in Europe, remote worldwide.
