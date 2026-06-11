---
name: web-build
description: Build a bespoke, award-tier-quality marketing site for a local business on the local-web Astro 5 + Tailwind v4 + Fly stack. Use when building, adding, or revising a preemptive demo site or a client site in workspace/projects/local-web/. Enforces the reference-anchor + imagery + deliverable-rule + Lighthouse quality gates that the 2026-05-18 rebuild made structural.
---

# Web Build

The operationalized website-build capability. Born from the 2026-05-18 rebuild: the
prior single-file HTML approach produced aesthetically poor output because quality was
per-session goodwill, not structural. This skill makes the bar structural.

**Build success is not aesthetic success**, and a green build is not a live site. A
site is not done until reference-parity is visually verified and Lighthouse runs ≥95
on the deployed `fly.dev` URL.

- Canonical contract: `workspace/projects/local-web/REBUILD-SPEC.md`
- Quality reference to match: `app/src/pages/praxis-uslu.astro`
- **Co-load** the `frontend-design` plugin skill
  (`claude-plugins-official/plugins/frontend-design`): it carries the bold-aesthetic /
  anti-AI-aesthetics / typography / spatial-composition discipline this skill assumes;
  this skill carries the local-web pipeline + the quantified gates.

## The four failure modes (hard gate — never reproduce)

1. **Hand-rolled CSS from scratch.** Stand on the shared foundation
   (`app/src/styles/global.css`: fluid type scale, 8px rhythm, a11y defaults, themed
   primitives). Never blank CSS.
2. **Gradient/placeholder where a photo belongs.** Real imagery pipeline. A designed
   `ImageSlot`/`Figure` slot is honest scaffolding pre-launch; a gradient pretending to
   be finished is the failure. Zero gradient placeholders in the shipped state.
3. **No external taste anchor.** Lock 2-3 award-tier real reference sites per vertical
   in the BRIEF BEFORE building. The extracted design DNA + explicit anti-patterns are
   the binding contract.
4. **Self-imposed single-file/offline constraints.** Real Astro build, real assets,
   Fly runtime. Offline leave-behind (screenshot/export) is a separate concern, never a
   design constraint on the site.

## Critical rules (always apply)

Each rule's detail lives in one place — follow the pointer.

- **One CTA per nav bar.** Four-zone structure, brand-traceable CTA colour. → `components/nav-bar.md`
- **Banned default fonts + selection procedure.** No Inter / Roboto / Arial / Space Grotesk / system stacks as primary type without a written non-default justification; the justification IS the 4-step selection procedure, and the saturated tier (Fraunces, Playfair, DM Sans, …) needs the same trace. → `modules/CONCEIVE.md` §3 + §6
- **Quantified design thresholds.** Tracking floor, hero clamp ceiling, line-length band, muted-text contrast, reveal-safety. → `references/design-thresholds.md`
- **No flat solid-colour primary sections** (background-depth rule). → `modules/CONCEIVE.md`
- **B4 data integrity.** Every field traces to `prospects/{slug}/data.md`; unverified → the data-layer `CHECK` sentinel, rendered quietly ("auf Anfrage" / omitted row), never the raw bracketed string on a pitchable page; never invent. → `modules/DATA.md`
- **Zero em-dash** (U+2014, `&mdash;`, `&#8212;`, typographic `--`). Fix at source; `validate-dist.py` enforces. → `modules/SHIP.md`
- **Motion envelope:** ≤300ms, custom `cubic-bezier`, `transform`/`opacity` only, `scale(0.97)` on `:active`, `prefers-reduced-motion` honoured. → `references/motion-craft.md`
- **"Live" = the `fly.dev` origin** serving this exact build, not a localhost render. → `modules/SHIP.md`
- **No auto-ship.** Edits stop at the staging boundary; deploy/commit need an explicit owner order. → `rule_no_auto_commit`

## Build procedure

Load ONE module per phase; do not preload all four.

| Step | Phase | Load |
|------|-------|------|
| 1 | Conceive — BRIEF, anchors, art direction, articulated-why | `modules/CONCEIVE.md` |
| 2 | Populate — B4-safe data | `modules/DATA.md` |
| 3 | Build — primitives, hero, signature section, motion, imagery, components | `modules/BUILD.md` |
| 4 | Verify & ship — deliverable gate, deploy, Lighthouse, a11y, live-origin | `modules/SHIP.md` |

## Session entry (cold-load reading order)

On a fresh session with a web-build task, FIRST run
`uv run tools/web-build-signals.py` (deterministic state probe: dirty site dirs,
dev-server, per-site BRIEF/TEST/dist presence, latest critique scores) and lead
with 2-3 pointed next-step picks derived from it — name the slugs and the phase
module, with the reason attached — instead of opening with scope questions.
Never auto-run the recommendation; propose, owner confirms.

Then read in this order BEFORE touching code
(skip files already loaded by `/comd_resume local-web`):

1. `workspace/projects/local-web/REBUILD-SPEC.md` — the contract
2. `workspace/projects/local-web/infrastructure.yaml` — deploy + gates
3. `app/src/pages/praxis-uslu.astro` — the quality reference to match
4. Latest `docs/{YYYY-MM-DD} - Local-Web …/Checkpoint.md` — last shipped state
5. `app/src/sites/{slug}/BRIEF.md` + `theme.css` for every site in scope
6. `prospects/{slug}/data.md` for every site in scope (B4 source)

Scope clarification is case-by-case, not a fixed checklist. Directive input ("rebuild
the coffee-boxx hero with a new anchor") executes; exploratory input ("what should the
4th site be?") asks one or two targeted questions. Gating directive work behind
clarification theatre is friction (`rule_behaviors.md`). When asking IS warranted, the
high-value forks are: (a) site scope — new prospect / rework / personalise / cards /
pipeline; (b) deploy posture — local dry build vs live deploy (live needs an explicit
ship order); (c) for a new prospect — vertical, city, public sources, taste anchors.

## Definition of done (the single gate)

This checklist IS the contract — re-read it before declaring done. Each item is one
line; the *how* lives in the linked module/reference. There is no competing checklist.

1. **BRIEF complete** — 2-3 named anchors, design DNA, anti-patterns, articulated-WHY per call, 1-2 references intentionally NOT borrowed from, AND the second-order slop test passed (category + anti-reference must not predict the design lane). → `modules/CONCEIVE.md` §2
2. **B4 data integrity** — every fact traces to `data.md` or carries `[BITTE PRÜFEN]`; no invented prices/menus/emails/phones/teams/hours/addresses. → `modules/DATA.md`
3. **Deliverable-rule gate** — zero em-dash forms in source; `npm run build` → `validate-dist.py ./dist` passes; fix at source. → `modules/SHIP.md`
4. **Real imagery, real-work, one grade** — every photo slot filled (no gradient placeholders); favour real-work/real-place over headset-smiler stock; ONE consistent warm grade across the page; `src/assets/{slug}/` committed (hermetic); `imagery.json` attribution; "Bilder: Pexels" credit. → `modules/BUILD.md`
5. **Background depth honoured** — no flat solid-colour primary sections unless the BRIEF justifies the minimalism. → `modules/CONCEIVE.md`
6. **Typography matches BRIEF** — banned defaults only with a written non-default justification. → `modules/CONCEIVE.md`
7. **Motion craft** — every animation matches the quantified table. → `references/motion-craft.md`
8. **Depth hero (if used)** — at most ONE; poster fallback verified on no-JS / reduced-motion / ≤768px / no-WebGL / Save-Data; `depth-live.cjs` confirms live parallax. → `references/depth-hero.md`
9. **nginx config locked** — `absolute_redirect off; port_in_redirect off; server_name_in_redirect off;` + the `try_files … =404` chain; no 301s ever. → `references/deploy-internals.md`
10. **Performance gate** — Lighthouse mobile ≥95 P/BP/SEO on the DEPLOYED Fly URL; SEO `is-crawlable` waived only for intentional `noindex`. → `modules/SHIP.md`
11. **Accessibility gate** — `tools/axe-check.cjs` returns zero WCAG 2 A/AA violations on the deployed URL (runs inside `local-web-deploy.py`); Lighthouse CLI a11y is NOT authoritative here. → `references/a11y-verify.md`
12. **Comparative-judgment paragraph** — written match-then-exceed articulation vs ONE named anchor. "Looks fine to me" is not the gate. → `modules/CONCEIVE.md`
13. **Owner ship order** — explicit go-ahead in the current conversation; no auto-deploy/PR/merge. → `rule_no_auto_commit`
14. **Live-origin parity + rendered behavior** — `uv run tools/local-web-deploy.py` reports `VERIFIED LIVE: … serves the current build` AND its post-deploy probes pass (hero actually paints, brand fonts loaded, no dead chrome); a localhost render never satisfies this. → `modules/SHIP.md`
15. **Nav bar passes its component standard** — the 10-item acceptance checklist (one CTA, non-default type, brand-traceable CTA colour, full-screen mobile overlay, zero bar contrast violations, comparative-judgment paragraph). → `components/nav-bar.md`
16. **Confident-big hero type** — the display face set BIG (scale + weight + tight tracking), sized to fill its column; reads confident, not "nice". → `modules/CONCEIVE.md` §0 (List B1)
17. **One accent on a justified base** — single disciplined accent; the base palette (warm / cool / dark / editorial white) is a per-site BRIEF-justified choice, never the unexamined cream default; no multi-accent, no pure-black-on-white. → `modules/CONCEIVE.md` §0 (List B3) + §6
18. **Per-SET hero diversity** — a new or reworked site does not clone an existing site's hero *structure*; the set reads as N singular businesses, not one template. → `modules/CONCEIVE.md` §0 (List A1)
19. **Logo / palette harmony** — the site accent echoes (or deliberately reconciles) a real brand mark's hue. → `modules/CONCEIVE.md` §0 (Logo / palette harmony gate)
20. **No raw sentinel on a pitchable page** — every `CHECK` field renders as a quiet "auf Anfrage" / "wird ergänzt" or an omitted row, never the bracketed `[BITTE PRÜFEN]` string; `data.ts` keeps `CHECK` as the source of truth. → `modules/DATA.md`
21. **Quiet-depth detail polish** — hairline borders, one shadow tier, no flat slab. → `modules/CONCEIVE.md` §0 (List B5)
22. **German-sober tone** — no exclamation-marketing, no hype; calibrated craft over spectacle. → `modules/CONCEIVE.md` §0 (List A8)
23. **TEST.md plan-then-evidence** — the site's `TEST.md` lists the planned gates BEFORE the verify run and carries the appended verbatim tool output after; a gate with no evidence block is an open gate. → `modules/SHIP.md`

Items 16-23 are mechanically pre-screened (advisory) by `tools/audit-local-web-aesthetics.py`, which also covers the `references/design-thresholds.md` floors/ceilings, the motion envelope, and the §6 saturation bands; `tools/local-web-deploy.py` runs the hard gates (aesthetics strict, axe, rendered-behavior probes) as part of the ship chain. Neither replaces the visual call — they free the eyeball pass to focus on grade, register, and "would the owner pay". A skipped or unrunnable check is a FAILED gate, never a waived one.

If any item is open, the site is not shipped. Surface what is open and wait.

## Module / reference / component index

Load the smallest unit that answers the current need.

| When | Load | Kind |
|------|------|------|
| Step 1 — BRIEF, anchors, art direction, comparative-judgment | `modules/CONCEIVE.md` | module |
| Step 2 — B4-safe data | `modules/DATA.md` | module |
| Step 3 — build, motion, imagery | `modules/BUILD.md` | module |
| Step 4 — deliverable gate, deploy, a11y, live-origin | `modules/SHIP.md` | module |
| The quantified motion table | `references/motion-craft.md` | reference |
| Type/colour floors + ceilings, reveal-safety | `references/design-thresholds.md` | reference |
| The axe-core-via-CDP a11y method | `references/a11y-verify.md` | reference |
| Fly + nginx deploy internals, cached-301 trap | `references/deploy-internals.md` | reference |
| The budgeted WebGL depth hero | `references/depth-hero.md` | reference |
| Per-element standard: navigation bar | `components/nav-bar.md` | component |
| Why a rule exists / debugging a regression | `incidents.md` | log |

## Quick reference (file map)

| Need | Where |
|---|---|
| Contract / failure modes / quality bar | `workspace/projects/local-web/REBUILD-SPEC.md` |
| Quality reference implementation | `app/src/pages/praxis-uslu.astro` |
| Shared design foundation | `app/src/styles/global.css` |
| Per-site brief + tokens | `app/src/sites/{slug}/BRIEF.md` + `theme.css` |
| Image primitive (auto photo-or-slot) | `app/src/components/Figure.astro` |
| Imagery pipeline | `app/scripts/fetch-imagery.mjs` (`npm run imagery`) |
| Deliverable-rule gate | `tools/validate-dist.py` (npm `postbuild`) |
| Deploy + live-origin verify (canonical) | `uv run tools/local-web-deploy.py` |
| Deploy internals | `app/Dockerfile`, `app/fly.toml`, `app/nginx.conf` |
| Depth-hero live verify | `tools/depth-live.cjs` |
| a11y gate (axe-core via CDP, committed) | `tools/axe-check.cjs` |
| Rendered-behavior probes (hero paint, fonts, motion) | `tools/verify-rendered.cjs`, `tools/local-web-shot.cjs` |
| Advisory List-B pre-ship checklist (per site) | `tools/audit-local-web-aesthetics.py` (`--persist` snapshots, `--trend` score history) |
| Session-entry state probe | `tools/web-build-signals.py` |

## Maintaining this skill (keep it from rotting back into a monolith)

Three invariants. Breaking one is how the skill drifts back to a 400-line dump.

1. **One home per rule.** A rule lives in exactly one module/reference/component; the
   spine links to it, never restates the detail. Two copies = drift.
2. **Growth routes itself.** A new recurring element → `components/{element}.md` + a
   Definition-of-Done item (same change). A new war-story → `incidents.md`, dated. New
   method detail → a `references/` file. None of these get inlined into the spine.
3. **The Definition of Done is the only gate.** Modules explain how to pass items;
   they never become a second checklist with its own tie-breaker.
