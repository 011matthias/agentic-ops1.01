# Platform / unpauseai.com

Moved here from CLAUDE.md on 2026-10-29 (repo layout plan W1-5), so the
always-loaded file carries only the one-line pointer.

**The live unpauseai.com is served from the separate repo `akkton/unpauseai-web`, NOT from `platform/` here** (the site left this monorepo on 2026-07-25). To PUBLISH a website change, follow memory `reference_vercel_platform_team_scope` (the proven path): edit `akkton/unpauseai-web` on a `content/<slug>` branch, PR, merge. Vercel Hobby only builds commits authored by the owner (akkton), so the merge is promoted by an akkton-authored commit, automatic via that repo's `publish.yml` when GitHub Actions is healthy and a manual owner-run promote when it is not. Verify live: `unpauseai.com/api/version` must equal the deployed SHA AND the changed page must actually serve the new content. Do NOT publish unpauseai.com via `tools/vercel-force-deploy.sh` or the `platform/` Vercel project.

`platform/` (Next.js 15 + Tailwind + TypeScript) is the LEGACY monorepo source, retained for local proposal generation; it no longer deploys the live domain.

- **Proposals:** Markdown files in `platform/src/content/proposals/` with YAML frontmatter. Statically generated at build time.
- **Modules:** Automation modules push data via `/api/modules/{name}`. Registry in `src/modules/registry.ts`.
- **Dev:** `npm run dev` in `platform/`
- **Build:** `npm run build` in `platform/`

Brand names and the public contact address: `.claude/rules/rule_platform_standards.md` §1.
