# Checkpoint: Website-Build Capability Rebuild

**Date:** 2026-05-18
**Status:** Execution started. Stack scaffolded, design system + 3 reference BRIEFs locked, praxis-uslu built as the proof page (builds clean, deliverable-rule compliant). Visual reference-parity + Lighthouse NOT yet verified (gated on Fly deploy).

> Supersedes the earlier same-day planning checkpoint. The pivot rationale and locked decisions are permanent in `workspace/projects/local-web/REBUILD-SPEC.md` and unchanged.

---

## Summary
Rebuilt the website-build capability on a real stack: a single Astro 5 + Tailwind v4 multi-site project in `workspace/projects/local-web/app/`, a shared hybrid design foundation, locked award-tier reference anchors per vertical, and one fully-built bespoke proof page (praxis-uslu) that builds clean and passes the deliverable rules. Visual quality vs the reference bar is explicitly NOT yet proven (needs the Fly deploy + browser + Lighthouse).

---

## What Was Done This Session
### Stack scaffold (REBUILD-SPEC step 2)
1. `app/` Astro 5.18.1 project: `package.json`, `astro.config.mjs` (Tailwind v4 via `@tailwindcss/vite`, static output, remote-image domains), `tsconfig.json` (path aliases), `.gitignore`.
2. `npm install` (316 pkgs); Astro telemetry disabled; clean build verified twice.
3. Self-hosted variable fonts via `@fontsource-variable` (Inter shared body; Newsreader / Fraunces / Space Grotesk per vertical) — Lighthouse-friendly, no Google Fonts request.

### Shared design foundation (the "hybrid base")
4. `src/styles/global.css` — fluid clamp type scale, 8px spacing rhythm, radius/elevation tokens, a11y defaults (focus-visible, reduced-motion, skip-link, selection), themed primitives (`.btn`, `.card`, `.wrap`, `.eyebrow`). Brand slots are CSS vars overridden per site.
5. `src/layouts/BaseLayout.astro` — head/SEO/canonical/noindex, JSON-LD slot, `data-site` body attr for scoped theming.
6. `src/components/ImageSlot.astro` — honest pending-image component (designed dashed slot, NOT a gradient — satisfies REBUILD-SPEC failure-mode #2 without faking finished imagery).

### Reference anchors locked (REBUILD-SPEC step 3, failure-mode #3 fix)
7. `src/sites/{praxis-uslu,coffee-boxx,pronto-pronto}/BRIEF.md` — each with 3 named award-tier reference sites, extracted design DNA, explicit anti-patterns (the clichéd vertical template to avoid), full art direction (type pairing, hex palette, layout system, motion), bespoke/signature section concept, imagery plan, B4 data rules.
8. `src/sites/*/theme.css` — per-vertical token overrides scoped under `[data-site]`.

### praxis-uslu proof build
9. `src/sites/praxis-uslu/data.ts` — typed content, every field traced to `prospects/praxis-uslu/data.md`; unverified fields (email, team, Kassen, languages) use `CHECK` → render as `[BITTE PRÜFEN]`, never fabricated.
10. `src/pages/praxis-uslu.astro` — bespoke editorial-calm page: type-led hero, "Auf einen Blick" card, hairline service list (not a card grid), signature "In der Praxis" band, precise Sprechzeiten/Anfahrt data block, emergency 116117/112 callout, MedicalClinic JSON-LD with OpeningHoursSpecification, progressive open-now state.
11. `src/pages/index.astro` — internal noindex demo directory.

### Deliverable-rule fix (see Friction)
12. Caught at B2 verify: em-dash (U+2014 ×5) and `--` comment delimiters in the built HTML/CSS deliverable. Fixed at source (title string, HTML comments → JSX comments, CSS-comment em-dashes). Re-verified: zero `—`, zero `&mdash;`, zero typographic `--` across all shipped files (remaining `--` are required CSS custom-property syntax).

---

## Key Decisions Made
### One proof page, not just a bare scaffold
- **Choice:** Build praxis-uslu fully (not only scaffold + theme tokens).
- **Rationale:** The rebuild's entire purpose is proving aesthetic quality. A scaffold with no real page proves nothing. praxis-uslu is the quality reference for the other two; within REBUILD-SPEC step 3.

### Honest image slots instead of gradient placeholders
- **Choice:** `ImageSlot.astro` renders a clearly-labeled designed slot ("Bildplatz · kuratiertes Foto folgt"), and the hero is type-led so the design stands without photos.
- **Rationale:** REBUILD-SPEC bans gradient placeholders as a finished state. Real imagery is step 4 (next session). A labeled slot is honest scaffolding; a gradient pretending to be done is the exact failure being rebuilt away.

### Hybrid foundation operationalized as shared CSS + per-site token override
- **Choice:** Shared structure/rhythm/a11y in `global.css`; brand identity (fonts, palette, surface) as `[data-site]`-scoped vars in per-site `theme.css`.
- **Rationale:** Directly implements the locked "hybrid foundation" decision: never blank CSS, never generic.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| app/package.json, astro.config.mjs, tsconfig.json, .gitignore | Created | Astro 5 + Tailwind v4 scaffold |
| app/src/styles/global.css | Created | Shared hybrid design foundation + tokens + a11y |
| app/src/layouts/BaseLayout.astro | Created | Shared head/SEO/JSON-LD/theming shell |
| app/src/components/ImageSlot.astro | Created | Honest pending-image slot (not a gradient) |
| app/src/sites/{praxis-uslu,coffee-boxx,pronto-pronto}/BRIEF.md | Created | Locked reference anchors + art direction |
| app/src/sites/*/theme.css | Created | Per-vertical scoped brand tokens |
| app/src/sites/praxis-uslu/data.ts | Created | Typed sourced content, B4-safe |
| app/src/pages/praxis-uslu.astro | Created | Bespoke proof page (the quality reference) |
| app/src/pages/index.astro | Created | Internal noindex directory |

---

## Current Status
Capability rebuilt and one proof page builds clean + passes deliverable rules. **NOT done:** visual reference-parity vs the BRIEF anchors, real imagery, Lighthouse ≥95, coffee-boxx + pronto-pronto pages. These need the Fly deploy + a browser and are the next gate. Build-success ≠ aesthetic-success — the original quality problem is not declared solved until seen against the references.

local-web is an internal initiative — no `infrastructure.yaml`, no `platform` section, no comms log. Ops/comms/reconciliation checks N/A.

---

## Next Steps
1. **Owner action (genuine credential step, not a defer):** Fly.io auth — `flyctl auth login` OR set `FLY_API_TOKEN`. Blocks deploy (step 5) only; not design work.
2. Imagery pipeline (REBUILD-SPEC step 4): Unsplash/Pexels fetch + one consistent per-brand treatment; AI hero/texture. Replace `ImageSlot` usages with real `<Image>`.
3. Build coffee-boxx (Fraunces, warm-magazine, menu-as-HTML signature) and pronto-pronto (Space Grotesk, dark appetite, searchable-menu signature) pages to the praxis-uslu quality bar, wiring `prospects/{slug}/data.md`.
4. Dockerfile + fly.toml; deploy one Fly app; **Lighthouse ≥95 on the live URL**; reference-parity gate vs each BRIEF; screenshot compare vs old webvorschau-ka prototypes.
5. Build `tools/validate-dist.py` (or extend validate-html.py) + wire an Astro postbuild check so the deliverable em-dash/`--` rule is structurally enforced on `dist/` output — closes the regression below.
6. Write `.claude/skills/skil_web-build/` so this process is structural, not per-session.

---

## Context for Next Session
### Files to Read First
- `workspace/projects/local-web/REBUILD-SPEC.md` (the contract; failure modes + quality bar)
- `workspace/projects/local-web/app/src/sites/*/BRIEF.md` (locked references + art direction per vertical)
- `workspace/projects/local-web/app/src/pages/praxis-uslu.astro` (the quality reference to match)
- `workspace/projects/local-web/prospects/{coffee-boxx,pronto-pronto}/data.md` (content to wire next)

### Open Questions
- Premium theme/template base per vertical: still designing from references directly rather than buying a theme. Decide if a purchased base is warranted before scaling beyond 3 sites.
- Fly app name + region; throwaway custom domain later (owner accepted that model).
- Leave-behind QR cards still need owner's real name + contact line (deferred, not fabricated).
- praxis-uslu approach copy is factual from sourced specializations only; practice must personalize before any real pitch (flagged in-page).

### Working Notes
- Astro 5.18.1, Tailwind 4.3.0, Node 24.15. Build: `npm --prefix workspace/projects/local-web/app run build` → `dist/` (1.4s, 2 pages).
- Tailwind v4: no config file; `@import "tailwindcss"` + `@theme` in global.css; per-site overrides via `[data-site]` CSS vars (works because primitives consume `var(--color-*)`).
- Vite minifies CSS in prod but the em-dash fix was done at source for certainty — do NOT rely on minifier stripping for rule compliance.
- BRIEF.md reference URLs are knowledge-anchored taste targets, not live-curated; the extracted design DNA is the binding contract. Human may swap URLs.
- Old prototypes still live (reference only) at `webvorschau-ka.vercel.app/{slug}` (+ `-guide`).

### Reference Materials
- REBUILD-SPEC.md (in repo) · prospects/*/data.md · BRIEF.md per site
- Old build for screenshot-compare: https://webvorschau-ka.vercel.app/praxis-uslu

---

## How to Continue
`/resume local-web`, read REBUILD-SPEC.md + the three BRIEF.md + praxis-uslu.astro. Get Fly auth from owner (next step 1) — but imagery pipeline and the other two pages can proceed without it. Treat the BRIEF anti-patterns + REBUILD-SPEC failure modes as a hard gate. Nothing is "done" until reference-parity is visually verified and Lighthouse ≥95 runs on the deployed URL.

---

## Strategic Feedback

### What Worked Well This Session
- "Do what you recommend" after a clearly-scoped recommendation let the session run autonomously end-to-end with zero mid-course interventions. The single upfront reference-anchor step (the thing missing last session) is now structural in BRIEF.md, so the generic-output failure mode is closed at the source.

### Suggestions
- Decide the theme-base question (design-from-references vs buy a premium base) before scaling past 3 sites — it changes the per-site cost model and the eventual `skil_web-build` skill shape.

### System Health
- **Enforcement gap (regression):** the 2026-05-08 structural fix built validate-html.py / the post-write hook to make rule_deliverables enforcement structural, but it does not scan Astro `dist/` output. A known-banned em-dash reached a built deliverable and was caught only by manual B2 grep, not by tooling. Next-step #5 closes it. Until then, deliverable-rule enforcement for framework-built sites depends on agent diligence, which is exactly the fragility the original fix was meant to remove.
- Autonomy score: 0 — fully autonomous session (one deliverable-rule miss, self-caught at B2 verify, no human intervention).
