# Cover Letter -- Alpha Research Web Scraping Pipeline (Job 1)

## Upwork Plain Text (copy-paste ready)

Hi, I built a combined proposal for both your n8n job postings (web scraping + AI document processing):
https://unpauseai.com/clients/alpha-research/
Access code: alpha-2026

Walkthrough video:
[VIDEO_LINK]

The site includes:
- 8-page technical proposal covering all 5 pipelines as one unified system
- a live demo where you paste any IR page HTML and Claude extracts + classifies document links in real time
- 2 downloadable n8n workflow JSON templates (one for scraping, one for thesis/news/HITL)
- day-by-day timeline, two pricing options, FAQ, and onboarding checklist

On your specific questions:

1) Technical approach for diverse website structures: dispatcher-worker pattern. A scheduler reads your Google Sheets company registry, splits into batches, and dispatches each to a scraper sub-workflow. Static sites use HTTP Request + Code node. JS-rendered sites use an external browser API (ScrapingBee or Bright Data) via HTTP Request. Each company scrapes independently, so one failure never blocks the other 299.

2) Edge cases (Cloudflare, dynamic content, rate limiting): the browser API handles Cloudflare and JS rendering. It includes CAPTCHA solving and proxy rotation. Rate limiting is managed by configurable batch sizes and Wait nodes between batches. Failed companies are logged and retried on the next run.

3) AI-assisted parsing: Claude API classifies HTML links by document type (Annual Report, Quarterly Filing, etc.) with confidence scores. You can try it yourself on the Workflow page. The prompt is tunable per site type for edge cases.

4) Time estimate: 12 working days for the complete system (both jobs combined). The scraping pipeline specifically is Days 1-5 (Foundation phase).

5) Cost estimate: two options on the Investment page. Option A: fixed price for the foundation build (5 pipelines, 5-10 site types) + hourly for ongoing scaling. Option B: full fixed project (50 site types, 2 weeks tuning, 30-day support).

I also submitted a proposal for your AI Document Processing + HITL job. Both share infrastructure, so building them as one system means one storage layer, one error handling pattern, and one place to debug.

The downloadable n8n workflow template on the site is a working starting point. Import it, plug in your API keys, it runs.

Best,
Nico
