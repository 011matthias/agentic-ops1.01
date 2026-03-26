# Cover Letter -- Alpha Research AI Document Processing + HITL (Job 2)

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

1) HITL architecture: n8n Wait node pauses the execution. An HTML email is generated showing the proposed change (before/after preview, source references). Two buttons link to signed webhook URLs (JWT tokens prevent unauthorized approvals). Clicking Approve resumes the execution and runs the markdown append. Clicking Reject logs the decision and skips. 7-day timeout with a day-3 reminder email. Works from any email client including mobile.

2) File management: a Code node reads the existing markdown file, identifies the target section using regex (e.g., "## Recent Findings"), and appends the new content below that heading. No overwriting. The original content stays intact. Each append includes a date stamp so you can trace when each update was added.

3) Time estimate: 12 working days for the complete system (both jobs combined). Thesis synthesis, news filter, and HITL specifically are Days 6-9 (Intelligence phase).

4) Cost estimate: two options on the Investment page. Option A: fixed price for the foundation build (5 pipelines, 5-10 site types) + hourly for ongoing scaling. Option B: full fixed project (50 site types, 2 weeks tuning, 30-day support).

On Tavily: included as one of four news sources alongside AlphaVantage, SerpAPI, and RSS. The relevance scoring compares articles against your Core Thesis, so the system ignores noise and flags material deviations for HITL review.

I also submitted a proposal for your Web Scraping Pipeline job. Both share infrastructure (company registry, cloud storage, error handling). Building them together means no duplicate storage logic and one place to debug.

The downloadable n8n workflow template on the site includes the complete thesis synthesis + news filter + HITL approval flow. Import it, plug in your API keys, it runs.

Best,
Nico
