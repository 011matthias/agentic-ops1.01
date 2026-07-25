---
project: upwork-independence
workstream: u2-aeo-content
group: uwi
spec:
state: active
updated: 2026-07-25
general_ref: status/uwi-general.md
---

# uwi / u2 — AEO / content inbound

**Repo moved 2026-07-25.** The website left `agentic-ops1/platform` and now
lives in its own repo, **`akkton/unpauseai-web`** (Nico's; 011matthias has
write). ALL website/content work targets that repo via PR, NOT this monorepo.
Merging there does NOT deploy: going live is Nico's own `vercel --prod` step
(`docs/publishing.md`), so "merged" never means "live" here — say so on the PR
if a piece needs publishing. Our earlier `platform/src/content/blog/` merges
never reached the live site.

The channel with the longest ramp (5 months). Blog publish mechanics live in
unpauseai-web (`src/content/blog/*.md` auto-discovered by `blog.ts` -> static
routes). Methodology in-repo (ai-seo skill), instrument built
(`workspace/projects/ai-visibility/ai_visibility_probe.py`). Starts FIRST among
the channels; largest slice of the weekly hours while cold email is
purchase-gated. Model: 0.178 effort, ~200h fixed corpus + ~120h marginal,
pool 25 (ASSUMPTION), EUR20k/client.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Sprint-zero AEO enablers | ported | Built in the old monorepo (#376), stranded when the site moved. Table renderer + sitemap post-enumeration + robots Sitemap line ported to unpauseai-web as **PR #2** (2026-07-25, CI-green local: tsc/eslint/build/cspell; build emits /sitemap.xml, 3 posts render <table>). NOT ported: llms.txt + pricing.md (Nico's positioning/pricing — surfaced on PR #2 for his call) | Nico reviews + takes PR #2 live | Nico review | `akkton/unpauseai-web` PR #2 |
| Editorial backlog | done | 33 pieces derived 2026-07-22 from icp.md demand taxonomy, buyer problem language, ranked intent x pool (P1 x8, P2 x19, P3 x6); sourcing rules embedded (prototypes only, no client data) | Re-rank as probe data arrives | — | `../context/editorial-backlog.md` |
| Corpus production | active | First 3 P1 pieces written 2026-07-22, ported to unpauseai-web as **PR #1** (open, CI-green; Nico's to review + take live). They depend on the table renderer in PR #2 to render correctly | Continue down P1 as PRs into unpauseai-web | Nico review + deploy | `akkton/unpauseai-web` PR #1 |
| Monthly probe loop | not-started | ai_visibility_probe.py baselined 2026-06, never re-run; needs schedule + PERPLEXITY_API_KEY; probe target is now the live unpauseai-web site | Schedule monthly run + JSON diff | — | `workspace/projects/ai-visibility/` |
| Author/entity decision | done, not applied in new repo | Owner decided 2026-07-22: per-post `author` frontmatter, new posts = 'Matthias Neumann', publisher = Organization UnpauseAI. unpauseai-web's `blog.ts` has NO author field yet and its JSON-LD hardcodes Nicolas, so the decision is not live there; surfaced on PR #2 as a small follow-up for Nico | Nico's call on per-post bylines in his repo | Nico | unpauseai-web `[slug]/page.tsx` |

## Open decisions / gates

- Nico owns review + go-live for both content PRs (#1 posts, #2 plumbing) in
  unpauseai-web; nothing is live until he runs `vercel --prod`.
- llms.txt + machine-readable pricing.md: content ready from the old repo,
  held back because they carry Nico's positioning/pricing. His call whether to
  publish them or use his own SEO setup (surfaced on PR #2).
- Local prototypes are citable AEO proof (5 live Karlsruhe sites, Lighthouse
  SEO 100), NOT a workstream — rule_platform_standards §7 sourcing applies.

## Pointers

- Publish target: `akkton/unpauseai-web` `src/content/blog/*.md` (auto-discovered
  by `src/content/blog.ts`); contribute via branch + PR, see its
  `docs/publishing.md`. Preview on your OWN free Vercel account (merge != deploy).
- Methodology: `.claude/skills/ai-seo/` (content-patterns, platform-ranking-factors).
- Instrument: `workspace/projects/ai-visibility/` (probe, targets, baseline reports).
- Model economics: leadgen-portfolio scorer lines 124-131.
- Repo-move detail: memory `reference_vercel_platform_team_scope`.
