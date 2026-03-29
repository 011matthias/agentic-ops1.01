# Video Script -- Alpha Research Pipeline Proposal

## Type C Walkthrough (~3:30) | Teleprompter Format

---

### Beat 1 -- Hook [0:00-0:25]

Hi there, Nico here. I build n8n data pipelines with AI-powered extraction and processing.

I saw both your job postings -- the web scraping pipeline and the AI document processing with HITL. I built a combined proposal because these are not two separate projects. They are one data extraction engine with five modes.

I'm going to walk through the proposal site now, which includes a live demo and two downloadable n8n workflow templates.

---

### Beat 2 -- Walkthrough [0:25-3:10]

**Overview [0:25-0:55]**
[Screen: Overview page]

The Overview shows the full system at a glance. Five pipelines, 300+ companies, 8+ data sources, JSON delivery.

The three zones -- Data In, AI Processing, Intelligence Out -- show how everything connects. Your company registry feeds into scraping and news monitoring. Claude handles the extraction and scoring. Output goes to cloud storage with human approval on anything that touches your thesis files.

**Brief [0:55-1:15]**
[Screen: Brief page, scroll slowly to bottom]

The Brief maps your requirements from both job postings. Scroll down to the bottom -- every single "To Apply" question from both postings is listed here, with a direct link to where it is answered in the proposal. Nine questions, nine answers, all cross-referenced.

**Solution [1:10-1:55]**
[Screen: Solution page, scroll through pipeline blocks]

Five pipeline blocks. Pipeline 1 is the dispatcher -- it reads your Google Sheets company registry, batches companies, and dispatches scraping jobs. Pipeline 2 is the scraper itself -- HTTP fetch, AI link extraction, dedup, cloud storage.

One honest note here: n8n does not have a native headless browser. For JavaScript-rendered sites, we use an external browser API like ScrapingBee. This is actually the production approach -- these services handle CAPTCHAs and proxy rotation better than self-hosted Puppeteer.

Pipelines 3 through 5 handle the intelligence side. Thesis synthesis from new analysis files, daily news filtering with relevance scoring, and the HITL email approval flow. Nothing modifies your core files without you clicking Approve.

**Workflow + Live Demo [1:55-2:45]**
[Screen: Workflow page, live demo section]

This is the live demo. I'm pasting HTML from an investor relations page into this box.

[Click "Extract Document Links"]

Claude reads the HTML and classifies every link. Annual reports, quarterly filings, presentations -- each one gets a type and a confidence score. Navigation links and privacy policies are filtered out into the rejected list.

This is the hardest technical problem in the project: reliably extracting document links from 300+ different website structures. The AI handles the variation that would break rule-based scrapers.

[Scroll to downloads]

Both workflow templates are downloadable right here. Import them into your n8n instance, add your API credentials, and they run.

**Timeline + Investment [2:45-3:00]**
[Screen: Timeline page briefly, then Investment page]

Three weeks, fifteen working days, three phases. Each phase delivers testable functionality.

Two pricing options: fixed initial build plus hourly ongoing, or a full project fixed price. Details on the Investment page.

**Onboarding [3:00-3:10]**
[Screen: Onboarding page]

The onboarding page has a day-1 kickoff checklist. Company list, API keys, thesis file locations, HITL preferences. Fill in what you have, we figure out the rest together.

---

### Beat 3 -- Close [3:10-3:30]

Both n8n workflow templates are yours to keep, regardless of whether we work together. Import them, plug in your keys, run them.

If we do work together, I tailor the LLM prompts to your specific company types, tune the relevance scoring against your actual thesis, and configure the scraper modules for your 300+ company list.

The access code is in the cover letter. Looking forward to hearing from you.
