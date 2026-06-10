# AI-visibility baseline: helmle-physio (helmle-physio.de)

Run date: 2026-06-10  
On-site AEO score: 1/7 graded checks passed

## On-site audit

| Check | Status | Detail |
|---|---|---|
| robots.txt | WARN | no robots.txt (all crawlers allowed by default) |
| sitemap.xml | FAIL | absent -- engines have no crawl map |
| llms.txt | WARN | absent -- no AI-context file (helps non-Google engines) |
| machine-readable-pricing | WARN | no /pricing.md|txt -- buying agents can't parse pricing |
| structured-data | FAIL | no JSON-LD -- no Organization/FAQ/Article schema for entity recognition |
| meta-description | PASS | present |
| freshness-signal | WARN | no visible last-updated date (engines weight recency) |

## Citation probe

No live engine key set. Citation probe skipped; activate by setting `PERPLEXITY_API_KEY` (cleanest, returns source URLs) or `AI_VISIBILITY_OPENAI_KEY`.
