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

Engine: Claude (`claude-haiku-4-5` + web-search tool). Run: 2026-06-08, 11
buyer-intent queries. We used Anthropic because the credits already existed;
this measures Claude's citations specifically, one engine of several. Adding
the engines buyers use more (ChatGPT, Perplexity, Google AI Overviews) is the
next coverage step.

**Result: 0 of 11 queries cited unpauseai.com.** Not the 9 category and
use-case queries, and not the 2 branded ones.

The branded query is the sharp one. A re-run of "what is UnpauseAI" did surface
a single unpauseai.com source, and it was `/login`, never a value page; the
rest of what Claude cited was PauseAI (the anti-AI advocacy org): its Wikipedia
entry, pauseai.info, pauseai-us.org, its Instagram. Claude's own answer hedged
in plain text: "Your search query could also relate to PauseAI (spelled
differently) ... a separate entity." So even when we appear, the entity is
muddy and the page is wrong.

Two things this confirms:

- The PauseAI collision is real and active in a live model answer, not
  hypothetical. It is the strongest argument for remediation items 1 and 4
  (Organization schema with `sameAs`, plus explicit disambiguation).
- Presence is unstable: the same branded query flipped between no-citation and
  a `/login`-only citation across two runs minutes apart. Answer-engine probing
  is noisy run to run, which is why the monthly metric should also track the
  Perplexity Search API retrieval rank (more stable) once that key exists.

This 0/11 is the before number. Re-run after the on-site remediation ships;
the delta is the case study.
