---
project: upwork-independence
workstream: u2-aeo-content
group: uwi
spec:
state: active
updated: 2026-07-22
general_ref: status/uwi-general.md
---

# uwi / u2 — AEO / content inbound

The channel with the longest ramp (5 months) and the most complete substrate:
blog publish mechanics live (`platform/src/content/blog/` markdown -> static
routes), technical AEO base shipped (llms.txt, Organization JSON-LD, sitemap —
PR #86), methodology in-repo (ai-seo skill), instrument built
(`workspace/projects/ai-visibility/ai_visibility_probe.py`). Missing: the
operating layer. Starts FIRST among the channels; largest slice of the weekly
hours while cold email is purchase-gated. Model: 0.178 effort, ~200h fixed
corpus + ~120h marginal, pool 25 (ASSUMPTION), EUR20k/client.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Sprint-zero platform fixes | not-started | 4 pre-existing defects gate corpus visibility: sitemap.ts + llms.txt omit /blog /faq /pricing /compare; renderer lacks tables; validate-platform-content.py skips content/blog/**; no machine-readable pricing | One `platform/uwi-aeo-sprint-zero` PR | — | recon wf_fe3b27c9-aa5 |
| Editorial backlog | not-started | ~25-40 buyer-intent pieces derived from ICP via ai-seo content-patterns | Derive after `../context/icp.md` exists | icp.md | ai-seo skill references/ |
| Corpus production | not-started | The ~200h fixed build; blog blind spot in validator must close first | Start after backlog + sprint zero | sprint zero | `platform/src/content/blog/` |
| Monthly probe loop | not-started | ai_visibility_probe.py baselined 2026-06, never re-run; needs schedule + PERPLEXITY_API_KEY | Schedule monthly run + JSON diff | — | `workspace/projects/ai-visibility/` |
| Author/entity decision | not-started | Article JSON-LD hardcodes 'Nicolas Neumann' sole author | Owner decision before first new post | owner | `[slug]/page.tsx` |

## Open decisions / gates

- Author entity for corpus pieces (JSON-LD currently Nicolas-only).
- Local prototypes are citable AEO proof (5 live Karlsruhe sites, Lighthouse
  SEO 100), NOT a workstream — rule_platform_standards §7 sourcing applies.

## Pointers

- Publish mechanics: `platform/src/content/blog/` + `blog.ts` loader.
- Methodology: `.claude/skills/ai-seo/` (content-patterns, platform-ranking-factors).
- Instrument: `workspace/projects/ai-visibility/` (probe, targets, baseline reports).
- Model economics: leadgen-portfolio scorer lines 124-131.
