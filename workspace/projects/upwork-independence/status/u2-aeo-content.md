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
| Sprint-zero platform fixes | done | Merged as PR #376 (2026-07-22): sitemap/llms.txt coverage, renderer table support, validator blog scope, machine-readable pricing. NOT yet force-deployed to prod; owner order pending | Force-deploy on owner order | owner order | recon wf_fe3b27c9-aa5 |
| Editorial backlog | done | 33 pieces derived 2026-07-22 from icp.md demand taxonomy, buyer problem language, ranked intent x pool (P1 x8, P2 x19, P3 x6); sourcing rules embedded (prototypes only, no client data) | Re-rank as probe data arrives | — | `../context/editorial-backlog.md` |
| Corpus production | active | First 3 P1 pieces drafted 2026-07-22 (contractor-left takeover, no-replies diagnostic, SPF/DKIM/DMARC minimum); validate-platform-content.py 0 findings; PR merge gated on author/entity decision | Merge first-posts PR after author decision; continue down P1 | author decision | `platform/src/content/blog/` |
| Monthly probe loop | not-started | ai_visibility_probe.py baselined 2026-06, never re-run; needs schedule + PERPLEXITY_API_KEY | Schedule monthly run + JSON diff | — | `workspace/projects/ai-visibility/` |
| Author/entity decision | active | Article JSON-LD hardcodes 'Nicolas Neumann' sole author; surfaced to owner 2026-07-22 with recommendation (per-post author frontmatter, Organization publisher) | Owner answer; then apply in first-posts PR | owner | `[slug]/page.tsx` |

## Open decisions / gates

- Author entity for corpus pieces (JSON-LD currently Nicolas-only).
- Local prototypes are citable AEO proof (5 live Karlsruhe sites, Lighthouse
  SEO 100), NOT a workstream — rule_platform_standards §7 sourcing applies.

## Pointers

- Publish mechanics: `platform/src/content/blog/` + `blog.ts` loader.
- Methodology: `.claude/skills/ai-seo/` (content-patterns, platform-ranking-factors).
- Instrument: `workspace/projects/ai-visibility/` (probe, targets, baseline reports).
- Model economics: leadgen-portfolio scorer lines 124-131.
