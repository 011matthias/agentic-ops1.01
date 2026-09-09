BEAT 1 -- REFRAME

SAY: Hi there, Nico here. I saw your posting for an n8n automation expert to build an accessibility audit and cold email outreach pipeline. You've written one of the most detailed job descriptions I've seen on Upwork -- guard rails included -- so I know you've thought this through.

>> Show job posting (highlight "500 URLs in one run" and "guard rails and caveats")

SAY: The real challenge here isn't running accessibility audits. axe-core handles that well. The challenge is building a pipeline that processes 500 URLs in a single run, handles every failure mode gracefully, and triggers cold emails only for the sites that actually fail -- all running on shared hosting. That's an orchestration problem, and that's what n8n is built for.


AUTHORITY

>> Show Upwork profile / portfolio

SAY: Quick background -- I'm Nico, based in Germany. I build n8n workflows daily, both self-hosted and cloud. Two relevant builds: a marketing analytics pipeline processing 600K+ weekly data points through external APIs, and a healthcare automation with multi-step API orchestration and error handling. Both self-hosted, both in production. I also work in the CET timezone, which gives us about 6 hours of overlap with Mississauga.


BEAT 2 -- WALKTHROUGH

>> Nav: Overview page / The Pipeline heading

SAY: Here's how the pipeline breaks down into four stages. Google Sheets input, axe-core audit via Puppeteer, results written back to the sheet, and Instantly.ai trigger for failures. Each stage has its own error handling -- nothing in stage three can break stage one.

>> Nav: Solution page / axe-core Audit Engine heading

SAY: The audit engine is the core of the workflow. An n8n Code node launches Puppeteer in headless mode, navigates to each URL with a 15-second timeout, injects axe-core into the page DOM, and runs the WCAG 2.1 AA ruleset. The output is a structured violation array -- rule ID, impact level, affected elements.

>> Nav: Solution page / n8n Self-Hosting on NameHero heading

SAY: Now here's something I want to be upfront about. You're running NameHero Silver NVMe, which is shared hosting. Shared environments often restrict headless browser execution -- process limits, memory caps, or outright blocks on Chromium. I'll test this on day one before building anything. If NameHero can't handle Puppeteer, the fallback is a cloud function that handles just the auditing step. n8n still orchestrates everything from your server. The FAQ page has the full breakdown.

>> Nav: Solution page / Error Handling heading

SAY: Every error type is caught and logged. Timeouts, bot detection blocks, DNS failures, Instantly API errors -- all get recorded in the sheet with a specific status code, and the pipeline continues to the next URL. A single failed URL never stops the remaining 499.


BEAT 3 -- EDGE CASES

>> Nav: Solution page / Instantly.ai Email Integration heading

SAY: For the Instantly integration, the workflow maps your audit data -- company name, URL, error count, top violation types -- into the API payload. Only sites that fail get sent to Instantly. Sites that pass or get blocked are skipped. Every triggered email is logged to a second sheet with a timestamp, campaign ID, and recipient.

>> Nav: FAQ page / Will Puppeteer actually run on NameHero shared hosting?

SAY: I want to come back to the hosting question because it's the biggest risk. The FAQ walks through three scenarios: it works on NameHero (best case), it needs a cloud function offload (small added cost per URL), or it needs a lightweight VPS (about $5 a month). Phase 1 of the timeline is specifically designed to resolve this before any workflow code gets written.


BEAT 4 -- PRICING AND TIMELINE

>> Nav: Investment page / Pricing heading

SAY: The price is $650 fixed, single milestone. That covers n8n installation, the complete workflow, Google Sheet template, Instantly.ai integration, Loom walkthrough, written docs, and full-scale testing on 500 URLs. Payment isn't released until you've tested it yourself on a live batch of 20 URLs -- your requirement, and I'm good with that.

>> Nav: Timeline page / 9-Day Build Plan heading

SAY: Nine days, four phases. Days 1-2 are setup and the Puppeteer compatibility test. Days 3-5 are the audit workflow build. Days 6-7 are Instantly integration. Days 8-9 are scale testing and handoff with the Loom recording. You'll see working results at the end of each phase.


BEAT 5 -- CLOSE

>> Nav: Onboarding page / Get Started heading

SAY: If this looks like a fit, the onboarding page collects what I need to get started: your NameHero access, Google Sheet, Instantly API key, and 5-10 sample URLs for initial testing. I'll have n8n installed and the Puppeteer test done within 48 hours. Looking forward to hearing your thoughts.


________________________________________

LOOM NOTES VERSION

BEAT 1 -- REFRAME
- Acknowledge detailed job posting and guard rails
- Real challenge: orchestration at 500 URLs, not the audit itself
- axe-core handles audits, n8n handles orchestration
- Error handling + shared hosting = the hard parts

AUTHORITY
- Germany-based, n8n daily (self-hosted + cloud)
- Marketing analytics pipeline: 600K+ weekly, external APIs
- Healthcare automation: multi-step API orchestration
- CET timezone, 6hr overlap with Mississauga

BEAT 2 -- SHOW SOLUTION
- Overview, The Pipeline (4 stages)
- Solution, axe-core Audit Engine
- Puppeteer headless, 15s timeout, axe-core injection, violation array
- Solution, n8n Self-Hosting on NameHero
- Be upfront: shared hosting risk with Puppeteer
- Fallback: cloud function for audit step only
- Solution, Error Handling
- Every error caught and logged, pipeline never stops

BEAT 3 -- EDGE CASES
- Solution, Instantly.ai Email Integration
- Only FAIL sites trigger email, PASS and BLOCKED skip
- Email log sheet: timestamp, campaign ID, recipient
- FAQ, Will Puppeteer actually run on NameHero?
- Three scenarios: works, cloud function, lightweight VPS
- Phase 1 resolves this before any code

BEAT 4 -- PRICING
- Investment, Pricing
- $650 fixed, single milestone
- Payment after client tests on 20 live URLs
- Timeline, 9-Day Build Plan
- 4 phases, results at end of each

BEAT 5 -- CLOSE
- Onboarding, Get Started
- Need: NameHero access, Google Sheet, Instantly key, sample URLs
- n8n installed within 48 hours
