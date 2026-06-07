# AI-visibility baseline: UnpauseAI (unpauseai.com)

Run date: 2026-06-07
On-site AEO score: 2/8 graded checks passed

This is the dogfood baseline. It proves the service shape on our own site
before we sell it: the on-site audit is the gradeable deliverable, the
citation probe is the proof-of-presence loop. Re-run monthly; diff the JSON.

## On-site audit

| Check | Status | Detail |
|---|---|---|
| ai-crawler-access | PASS | all AI crawlers may fetch the site root |
| robots-sitemap-ref | WARN | robots.txt does not reference a sitemap |
| sitemap.xml | FAIL | absent, engines have no crawl map |
| llms.txt | WARN | absent, no AI-context file (helps non-Google engines) |
| machine-readable-pricing | WARN | no /pricing.md or .txt, buying agents can't parse pricing |
| structured-data | FAIL | no JSON-LD, no Organization/FAQ/Article schema for entity recognition |
| meta-description | PASS | present |
| freshness-signal | WARN | no visible last-updated date (engines weight recency) |

## Discoverability baseline (interim, WebSearch proxy)

Pending a live engine key, an organic search for the brand plus category is
the proxy for whether engines can even find us. Searching "UnpauseAI
automation consultancy":

- The only unpauseai.com URL that surfaces is `/login`, not the homepage or
  any service page. Indexing is shallow.
- The rest of the page is competitors: automaly.io, ascentient.com,
  ltimindtree.com, onemagnify.com.
- A name collision sits one slot down: **PauseAI**, the AI-safety activist
  organisation. For an LLM resolving "what is UnpauseAI", that collision is a
  real citation hazard; the engine may conflate or hedge the entity.

## Prioritised remediation (highest leverage first)

1. **Organization + Service JSON-LD on the public site.** Single biggest fix.
   Gives engines a machine-readable identity (legal name, founder, Karlsruhe
   location, the six service pillars, `sameAs` links) and directly addresses
   the PauseAI collision by asserting what UnpauseAI is and is not. Implement
   in `platform/src/app/layout.tsx`; use the `schema` skill. Today the only
   JSON-LD anywhere in the repo is an internal portal page.
2. **Sitemap.** Add `platform/src/app/sitemap.ts` so Next emits
   `/sitemap.xml`, then reference it in `robots.txt`. Surfaces the ~26
   proposal pages and service pages to crawlers; cheap.
3. **`/llms.txt`.** One file at the site root summarising what UnpauseAI does,
   who it serves, and links to key pages. Helps ChatGPT, Claude, Perplexity;
   ignored harmlessly by Google.
4. **Entity disambiguation vs PauseAI.** Beyond schema `sameAs`, state the
   distinction once in plain prose on the About page and in `llms.txt`. This
   is the finding a generic AEO vendor misses.
5. **Freshness + machine-readable pricing.** Add last-updated stamps on
   content pages. Pricing is not published (fixed-fee, scoped per proposal),
   so a `/pricing.md` should state the engagement model as a capability, not
   invent numbers.
6. **Third-party presence (the real ceiling).** Brands are cited far more
   often via third-party sources than their own domain. UnpauseAI has almost
   no third-party footprint (no Clutch/G2 profile, no founder content, no
   roundup mentions). On-site fixes lift us from invisible to citable; the
   third-party work is what wins share of voice. Out of scope for an on-site
   pass, in scope for the service.

## Citation probe

No live engine key set; the probe is built and skips cleanly.

LIMITATION: no AI-engine key is provisioned for citation tracking.
USER ACTION NEEDED: set `PERPLEXITY_API_KEY` (a ~$5 credit covers months of
monthly probes and returns source URLs natively) to activate live
share-of-voice tracking across the 11 target queries. A dedicated
`AI_VISIBILITY_OPENAI_KEY` adds the ChatGPT-search engine; do not reuse a
client's key (Dirk's Brisken `OPENAI_API_KEY` is off-limits).

Once keyed, this section fills with a per-query, per-engine cited/not-cited
table plus the competitors surfacing in our place, which becomes the
month-over-month metric.
