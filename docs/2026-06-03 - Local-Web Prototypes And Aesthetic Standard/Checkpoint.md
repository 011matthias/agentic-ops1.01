# Checkpoint: Local-Web Prototypes And Aesthetic Standard

**Date:** 2026-06-03
**Status:** 5 sites live + verified; aesthetic-standard upgrade staged as a handoff prompt (not yet executed)

---

## Summary
Reworked pronto-pronto (real logo, palette-fit filter, signage masthead), built the missing structural "ship local-web" tool, deleted the coffee-boxx prototype, and built + shipped 3 new bespoke Karlsruhe demo sites (Handwerk, Physio, Beauty). Then defined two aesthetic-standard lists (contextual + superficial), audited the live 5 against them, and produced a paste-ready prompt to (a) fix the 5 and (b) encode both lists into skil_web-build.

---

## What Was Done This Session

### pronto-pronto polish (3 ships)
1. Added the real Pronto-Pronto logo to the header (sourced from prontopronto-ka.de, transparent PNG). Commit `e671e6a`.
2. Warm-vintage cohesion rework: logo-derived theme (espresso/terracotta/brass/cream), Fraunces+Newsreader, vintage stamp offer, paper grain. §References re-anchored via a verification workflow. Commit `0f29505`.
3. Signage-masthead header (centered emblem + small-caps descriptor + brass rules + centered nav), chosen from 4 concepts via AskUserQuestion. Commit `e8659e2`.

### Structural fix (the "live" lesson)
4. Built `tools/local-web-deploy.py` — the canonical ship path: build → flyctl deploy → fetch each fly.dev URL and assert the live origin serves THIS build (content-hash match). Wired into skil_web-build §6 + §8 item 14, infrastructure.yaml deploy_cmd, tools/INDEX.md. Memory `feedback_live_means_deployed_origin.md`. (Root cause: declared the logo "live" off a localhost preview, never deployed; user caught it.)

### Roster change
5. Deleted coffee-boxx entirely (page, site tokens, assets, prospect, legacy site/ artifacts, refs in infra/README/HANDOFF/make_cards). `/coffee-boxx` 404s live. Commit `152826c`.
6. 3 new bespoke prototypes built + shipped (commit `e94c696`), each a real B4-traceable Karlsruhe business:
   - **meinzer-maler** — Michael Meinzer Malerfachbetrieb (Maler). Copper Werkstatt, Bitter + Source Sans 3, Meisterbrief-Werkbank band. Real logo.
   - **helmle-physio** — Helmle & Helmle Physiotherapie. Sage + clay, Fraunces + Hanken Grotesk, Behandlungsreise spine. Real logo.
   - **beauty-lounge** — Beauty Lounge Karlsruhe (Kosmetik + Nageldesign, no Friseur). Crème/mocha/rose-clay, Cormorant Garamond + Mulish, Drei-Bereiche tri-band. Typeset wordmark.
   Built by 3 parallel general-purpose agents from a research-workflow brief; main loop did imagery, gates, contrast fixes, ship.
7. Updated the index directory page to list all 5 current sites (was still showing coffee-boxx + missing the 3 new — user caught). Commit `392dd4b`.

### Aesthetic standard
8. Articulated two standard lists in conversation: **List A** (contextual/strategic: recognition, register-fit, don't-out-dress, findability, authenticity, type+colour leverage, "it just works", calibrated craft; north-star = "would the owner pay + would their customer act"). **List B** (superficial/visual: big confident non-default type, whitespace, one accent on warm neutrals, one well-graded photo, crisp render; plus scale-contrast, alignment/rhythm, quiet depth; and a cheap-tells ban list).
9. Audited the live 5 against both lists (screenshots). Wrote a paste-ready handoff prompt that fixes the 5 + amends skil_web-build §3a/§8 to encode both lists.

---

## Key Decisions Made

### Beauty cluster consolidated to one prototype
- **Choice:** User named 5 niches (Handwerk, Physio, Friseur, Nagelstudio, Kosmetik) but asked for "3 more prototypes." Built 3 distinct registers; folded Friseur/Nagel/Kosmetik into one full-service Beauty salon.
- **Rationale:** Three near-identical beauty sites = low portfolio diversity; 3 distinct registers (trades/health/beauty) is the stronger demo set. Beauty Lounge does Kosmetik+Nageldesign only (NOT Friseur) — built hair-free per B4.

### Real businesses, not generic demos
- **Choice:** Sourced a real Karlsruhe business per niche with a dated current site (good pitch target), real verified data, `[BITTE PRÜFEN]` for unverified.
- **Rationale:** Matches the Pronto/Praxis approach; directly pitchable.

### "Live" = deployed origin, structurally enforced
- **Choice:** Built a tool that can't return green without fetching the production URL.
- **Rationale:** A localhost preview proves the build, never the deploy (verification theater). See memory.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| app/src/pages/pronto-pronto.astro | Modified | logo, palette filter, masthead |
| app/src/assets/pronto-pronto/logo.png | Created | real brand logo |
| tools/local-web-deploy.py | Created | canonical build+deploy+live-verify |
| .claude/skills/skil_web-build/SKILL.md | Modified | §6 canonical ship path, §8 item 14 live-origin parity (user also editing) |
| tools/INDEX.md | Modified | deploy tool entry |
| app/src/pages/{meinzer-maler,helmle-physio,beauty-lounge}.astro | Created | 3 new sites |
| app/src/sites/{3 slugs}/{data.ts,theme.css,BRIEF.md,imagery.json} | Created | 3 new sites' content+tokens |
| app/src/assets/{3 slugs}/* | Created | real logos + Pexels imagery |
| prospects/{3 slugs}/data.md | Created | B4 source notes |
| app/scripts/fetch-imagery.mjs | Modified | SLOTS for 3 new sites (dropped coffee-boxx) |
| app/package.json | Modified | 5 fonts + chrome-remote-interface/axe-core devDeps |
| infrastructure.yaml, README.md, make_cards.py, index.astro | Modified | roster: drop coffee-boxx, add 3 |
| coffee-boxx (page/site/assets/prospect/site-artifacts) | Deleted | prototype removed |
| memory/feedback_live_means_deployed_origin.md | Created | "live = deployed origin" |
| memory/project_local_web_three_new_prototypes.md | Created | 3-prototype project state (shipped) |

---

## Current Status
5 sites live + verified at https://local-web-ka.fly.dev/ (praxis-uslu, pronto-pronto, meinzer-maler, helmle-physio, beauty-lounge). Per site: validate-dist clean, zero em-dash, axe-core 0 WCAG2 A/AA (local+live), Lighthouse mobile P 99-100 / A 100 / BP 96 / SEO 100 on the deployed URL. Index directory lists all 5; coffee-boxx 404s. The aesthetic-standard upgrade (fix-the-5 + encode-into-skill) is staged as a handoff prompt, NOT executed. Note: user is actively editing skil_web-build/SKILL.md (a nav-bar.md component file was opened) — the skill amendment may be in progress on their side.

Branch: system/no-auto-commit-prototype-carveout (local-web commits bypass B6 via the prototype carve-out). Still uncommitted in the tree from earlier system work: the local-web-deploy.py npm-resolution fix + skil_web-build/INDEX wiring (flagged, not swept into prototype commits), plus unrelated platform/brisken/suderman dirty files (leave them).

---

## Next Steps
1. Run the staged aesthetic-standard prompt (fix the 5 sites to Lists A+B; amend skil_web-build §3a/§8 to encode both lists). The prompt is in the conversation; key gaps it must close: hero type too timid, set reads as one template, photography ungraded/weak (praxis masked-stock, meinzer grey), `[BITTE PRÜFEN]` chips visibly render on pitch pages (re-treat as quiet "auf Anfrage"), logo/palette mismatch (helmle teal-vs-sage, meinzer primaries-vs-grey-copper).
2. QR leave-behind cards need a real contact line per prospect before any walk-in pitch.
3. Decide whether to commit the dangling local-web-deploy.py fix + skill/INDEX wiring (system files, outside the carve-out — needs explicit order).

---

## Context for Next Session

### Files to Read First
- `.claude/skills/skil_web-build/SKILL.md` (§3a taste, §6 deploy, §8 definition of done — the standard being amended)
- `workspace/projects/local-web/app/src/pages/pronto-pronto.astro` (the strongest reworked reference)
- `tools/local-web-deploy.py`, `tools/axe-check.cjs`, `tools/local-web-shot.cjs` (ship + QA tooling)
- `workspace/projects/local-web/app/src/sites/{slug}/BRIEF.md` per site
- memory: `feedback_live_means_deployed_origin.md`, `project_local_web_three_new_prototypes.md`

### Open Questions
- Should the roster live in a single source of truth? It is duplicated across infrastructure.yaml, README, make_cards.py, index.astro, and fetch-imagery SLOTS — the index-page miss this session came from that duplication.
- Should `[BITTE PRÜFEN]` ever render on a pitchable page, or always be a quiet/elegant treatment?

### Working Notes
- Aesthetic audit (start point for the upgrade): the SET reads as one template (praxis+helmle share a layout; pronto+meinzer share another); hero type is "nice" not confident-big; photography is the weakest ungraded layer (pronto's pizza is the only strong shot); `[BITTE PRÜFEN]` superficially reads as broken to an owner; helmle/meinzer logos fight their site palettes.
- Tooling: fonts installed (bitter, source-sans-3, hanken-grotesk, mulish variable + cormorant-garamond static, plus fraunces/newsreader/inter). chrome-remote-interface + axe-core now pinned as devDeps (font install had pruned them, breaking the shot+axe tools).
- Ship loop that works: edit → `npm run build` (validate-dist postbuild) → preview via background `npx astro preview` → `tools/local-web-shot.cjs` + `tools/axe-check.cjs` for QA → `uv run tools/local-web-deploy.py` → `npx lighthouse <live-url>`.

### Reference Materials
- https://local-web-ka.fly.dev/ (the 5 live sites)
- Real business sources: malerfachbetrieb-meinzer.de, helmle-physio.de, beauty-lounge-karlsruhe.de (expired SSL)

---

## How to Continue
Paste the staged aesthetic-standard prompt into a fresh session (it carries Lists A+B verbatim, the audit, the fix-the-5 + amend-skill tasks, and the operational gotchas). Or pick up directly: read skil_web-build SKILL.md, then work one site at a time against Lists A+B, shipping each via `tools/local-web-deploy.py` with axe + Lighthouse on the live URL.

---

## Strategic Feedback

### What Worked Well This Session
- The AskUserQuestion concept-fork (4 header concepts with ASCII previews) let the masthead direction get chosen in one turn instead of build-then-redo.
- Delegating the 3 site builds to parallel agents kept main-loop context lean while producing 3 shippable sites; the main loop kept the visual-QA + gates where judgment matters.

### Suggestions
- The roster duplication (5 places) is a real trap; a single `sites.ts` consumed by index.astro + fetch-imagery + a generated infra block would have prevented the index miss.
- Pinning dev-only tool deps (chrome-remote-interface, axe-core) in package.json from the start avoids the silent-prune class.

### System Health
- The relative-path PreToolUse hook bug is now a 3+ session regression (2026-05-20, 2026-06-01 brisken, this session) and it ALSO broke all 3 build subagents (they fell back to serena/PowerShell). The documented "use absolute paths" fix has not held. This warrants a structural fix: make the hook wrapper resolve `.claude/hooks/*` against the repo root, not the shell cwd.
- Autonomy score: 6 human interventions this session (elevated — run /system-dev to close gaps). Two were user-caught (live-off-localhost; index roster miss), the rest were B1 hook-catches on closing-offer phrasing + self-caught tooling drift.
