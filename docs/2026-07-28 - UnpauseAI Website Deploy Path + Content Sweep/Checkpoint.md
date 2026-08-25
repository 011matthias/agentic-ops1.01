# Checkpoint: UnpauseAI Website Deploy Path + Content Sweep

**Date:** 2026-07-28
**Status:** Deploy path resolved and reusable; PRs #6–#10 merged, #6–#9 live on unpauseai.com, #10 pending Nico's promote

---

## Summary
Resolved the standing "how do I deploy to unpauseai.com" problem into a reusable path (branch → PR → green CI → merge → auto-promote), then shipped six content changes across five PRs on that path. The deploy method is now set up once and documented in memory so it never has to be re-derived.

---

## What Was Done This Session

### Deploy path (the load-bearing outcome)
1. Established that neither repo had a Vercel git integration (zero deployment records/statuses/bot comments); a GitHub collaborator invite grants repo WRITE only, so merging never auto-deployed.
2. Got Nico to connect the Vercel `platform` project to `akkton/unpauseai-web` (git integration, 2026-07-28). Confirmed the Hobby author-block: merge commits authored by 011matthias are refused as direct builds, but an owner-authored `publish: promote <sha>` step builds `main` (incl. the merge) and promotes it live in minutes–~1h. Verified across all five PRs.
3. Stood up the self-controlled preview: `vercel deploy --prod --scope matthias-neumanns-projects` → unpauseai-web.vercel.app (full public mirror; gated /docs + contact form dead there, fail-closed, no leak).

### Content changes (PRs #6–#10, all green CI)
1. **#6** — About: both co-founders (Matthias photo added, both labelled Co-Founder); pricing page deleted (route + header/footer/sitemap/home/compare); assessment made free (Stripe removed from `/api/assessment`, all `$1` CTAs reworded across 8 pages); JSON-LD founder array updated.
2. **#7** — Home people-card copy → "Co-founded by Nicolas Neumann and Matthias Neumann".
3. **#8** — Both founder cards put on eye level: matched two-paragraph bios, identical chip row (EU-Based / CET Timezone / GDPR-Compliant) on both.
4. **#9** — Matthias's bio sharpened to current work (AI/vision-driven reconciliation, agent-driven pipelines, full-stack delivery, quality-gate tooling).
5. **#10** — `/work` marketplace + custom-work pricing removed (cards keep category/name/tagline/tools; `/buy` flow and catalog data untouched); `matthias.neumann@unpauseai.com` added to the Contact "Email directly" card.

---

## Key Decisions Made

### Deploy via merge→promote, not a token in CI
- **Choice:** Rely on Nico's owner-authored promote pipeline after merge; keep the akkton Vercel token out of this machine and out of CI.
- **Rationale:** On Hobby, Vercel API tokens are account-wide (reach lydar-app) and readable from a workflow — the 17 July exposure. The git-integration + owner-promote path deploys with no stored secret.

### Both co-founders symmetric, no unverifiable location on Matthias
- **Choice:** Both labelled "Co-Founder"; identical chip row dropping the personal-location chip ("Karlsruhe, Germany") in favour of shared-true chips.
- **Rationale:** User chose symmetric co-founder framing; I have no sourced city for Matthias, so I won't stamp one (B4). Nicolas's Karlsruhe stays in his prose.

### Bundle related small edits
- **Choice:** `/work` pricing removal + Contact email addition shipped as one PR (#10).
- **Rationale:** Two small public-page content edits; one CI/merge/deploy cycle instead of two.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| memory/reference_vercel_platform_team_scope.md | Edit | Lead with the WORKING deploy path; supersede the mid-day "no integration" finding |
| memory/MEMORY.md | Edit | Index line → the working deploy path |
| (akkton/unpauseai-web) src/app/(public)/about/page.tsx | via #6/#8/#9 | Two co-founders, eye-level cards, sharpened bio |
| (akkton/unpauseai-web) src/app/(public)/page.tsx | via #6/#7 | Pricing links/card removed, JSON-LD, home co-founded copy |
| (akkton/unpauseai-web) src/app/(public)/work/page.tsx | via #6/#10 | $1→free CTAs, marketplace + custom pricing removed |
| (akkton/unpauseai-web) src/app/(public)/contact/page.tsx | via #6/#10 | $1→free, Matthias email added |
| (akkton/unpauseai-web) src/app/api/assessment/route.ts | via #6 | Stripe removed, returns intake URL |
| (akkton/unpauseai-web) assessment/thank-you, compare, faq, blog, Header, Footer, sitemap, pricing/ | via #6 | Pricing removal + free-assessment sweep |

---

## Current Status
Deploy path is set up and proven (five PRs live/pending on it). unpauseai.com reflects everything through PR #9; PR #10 (work pricing + contact email) is merged on `main` (77eb149) and awaiting Nico's next promote. Mirror unpauseai-web.vercel.app is current. No workspace-client ops status (this is platform/website work, not a `workspace/clients/*` project).

---

## Next Steps
1. Confirm PR #10 live on unpauseai.com when the promote fires (poller armed on `/work` pricing + `/contact` email; bg_watch registered).
2. If any future domain promote stalls >~1h, ping Nico on the PR; the mirror is the instant stand-in.
3. Optional infra: a `tools/pr-merge-on-green.sh` that polls `gh pr checks --json` to a verdict then merges — kills both the manual watch dance and the watch-race false-green (see Friction).

---

## Context for Next Session

### Files to Read First
- memory/reference_vercel_platform_team_scope.md (the deploy path — READ THIS before any website change)

### Open Questions
- Is Nico's promote fully automatic (Actions deploy-hook) or a manual step? Observed reliable within minutes–~1h either way; hasn't needed a ping yet.

### Working Notes
- Deploy source of truth: `akkton/unpauseai-web`, NOT `agentic-ops1/platform` (site left the monorepo 2026-07-25).
- CI = 3 jobs: "Type check, lint, and build", "Spell check", "Playwright smoke tests". Pre-existing cspell reds live in the insurance-ai docs; our PRs all passed cspell, so a red on unrelated files is not yours — don't merge through it blindly.
- `git push`/commit on this Windows box logs harmless LF→CRLF warnings; diff stays minimal (verified numstat each time).
- PowerShell `Stop-Process` kill short-circuits a following `&&`/`;` git chain (exit 255) — kill the dev server in its own call.

### Reference Materials
- Mirror: https://unpauseai-web.vercel.app
- Live: https://unpauseai.com
- Vercel `platform` project: prj_xMUV3AVgiAq9uXC9YaX0tMxQdAvl (akkton team_uBLrEbyAGbPpU4wDrNpAcGm4)

---

## How to Continue
For any unpauseai.com change: branch off `origin/main` in `akkton/unpauseai-web`, edit, run tsc/eslint/`npm run build`/cspell + boot-and-curl, PR, watch CI to real green, `gh pr merge --merge`, then verify the domain (it promotes itself). Use the mirror for an instant preview.

---

## Strategic Feedback

### What Worked Well This Session
- Every ship gated on real behavior verification (build + boot + curl the changed endpoint/page), not just "it compiled" — caught the CI-watch false-green before it could merge anything bad.
- Turning a recurring pain (deploy) into a documented, reusable path instead of re-solving it per change, which is exactly what the owner asked for.

### Suggestions
- Build the `pr-merge-on-green.sh` helper (see Next Steps #3). The manual `gh pr checks --watch` → read → `gh pr merge` dance recurred six times this session and has a known race; a helper that gates merge on the JSON verdict removes both.

### System Health
- **Autonomy: 4 human interventions**, all directional/access corrections during the deploy-path resolution (the user knew their GitHub/Vercel access situation the machine couldn't see); the entire content-shipping half (five PRs) ran fully autonomous. Not elevated.
