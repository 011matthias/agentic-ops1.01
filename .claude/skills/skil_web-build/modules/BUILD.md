# Module: BUILD

Load at **Build Procedure step 3**. Detail behind Definition-of-Done items 4, 5, 7, 8
in `SKILL.md`. This is where the page gets built to the praxis-uslu bar.

Companion references (load when the specific need arises):
- `references/motion-craft.md` — the quantified motion table (every animation obeys it)
- `references/depth-hero.md` — the budgeted WebGL depth hero (at most one per site)
- `components/{element}.md` — per-element standards (e.g. `components/nav-bar.md`)

## 0. Open the TEST.md plan

Before writing page code, create `app/src/sites/{slug}/TEST.md` with the planned
gate inventory (plan pass) — see `modules/SHIP.md` §3b. The evidence pass appends
at ship time. Two minutes now; it is what makes DoD item 23 checkable later.

## 1. Build the page to the praxis-uslu bar

Bespoke per BRIEF, reusing shared primitives (`.wrap`, `.btn`, `.card`, `.eyebrow`) +
`BaseLayout` (head/SEO/canonical/noindex/JSON-LD/`data-site`). Type-led hero so the
design stands without photos. Hand-written meta + LocalBusiness-family JSON-LD per
vertical (`MedicalClinic`, `CafeOrCoffeeShop`, `Restaurant`, ...). One real bespoke
signature section that inverts the prospect's current biggest failure.

**Never hand-roll CSS from scratch.** Stand on the shared design foundation
(`app/src/styles/global.css`: fluid type scale, 8px rhythm, a11y defaults, themed
primitives). This is failure mode #1 — see `SKILL.md`.

## 2. Motion craft (quantified)

Every animation matches the table in `references/motion-craft.md`: custom
`cubic-bezier` (never built-in `ease-out`), ≤300ms, `transform`/`opacity` only,
never `scale(0)`, `scale(0.97)` on `:active`, per-element transform origin,
interruptible, `prefers-reduced-motion: reduce` always honoured. Cite the relevant
row in the PR description or BRIEF when a motion choice is non-obvious.

## 3. Imagery pipeline (`app/scripts/fetch-imagery.mjs`)

Curated stock per BRIEF art direction. **No people, no fake teams, no headset-smiler
stock.** One consistent treatment per brand. Add slot entries to the `SLOTS` array
(site, name, query, orientation). Run `npm run imagery` (needs `PEXELS_API_KEY` in
`app/.env`, gitignored). Photos land in `src/assets/{site}/{name}.jpg`; attribution
-> `src/sites/{site}/imagery.json`. Use `<Figure>` (not raw `<Image>`): it
auto-renders the optimized responsive photo when the asset exists, else the honest
slot — zero markup change when photos land. **Commit `src/assets/`** so the
Docker/Fly build is hermetic (no key at deploy). Add a "Bilder: Pexels" footer credit.

A designed `ImageSlot`/`Figure` slot is honest scaffolding pre-launch; a gradient
pretending to be finished is failure mode #2. Zero gradient placeholders in the
shipped state.

## 4. Motion & 3D-feel imagery (gate-budgeted)

The visuals should have depth and motion, never a flat photo wall. This is an imagery
quality bar, not an interactive-3D-scene mandate.

**Default tier (every site, ~0 perf cost, do this first):** CSS-driven only — Ken
Burns slow zoom/pan on the hero photo, scroll-driven reveal + layered parallax,
hover-tilt on cards (`vanilla-tilt`/Atropos, lazy). Reads premium, zero WebGL, never
threatens the gates.

**Budgeted WebGL hero (at most ONE element per site, optional):** see
`references/depth-hero.md` for the full implementation contract and the live-verify
method. Permitted only with ALL of: lazy-init on idle/scroll, static poster fallback,
`prefers-reduced-motion` → poster, mobile (≤768px) serves the static image, and a
re-run of the §SHIP Lighthouse + axe gate AFTER adding it. Perf 100 / 0 WCAG2AA stays
absolute — if the hero can't pass, it ships as the poster. Full multi-element
interactive Three.js scenes are out of scope for this stack.
