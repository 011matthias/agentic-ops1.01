---
name: web-build
description: Build a bespoke, award-tier-quality marketing site for a local business on the local-web Astro 5 + Tailwind v4 + Fly stack. Use when building, adding, or revising a preemptive demo site or a client site in workspace/projects/local-web/. Enforces the reference-anchor + imagery + deliverable-rule + Lighthouse quality gates that the 2026-05-18 rebuild made structural.
---

# Web Build

The operationalized website-build capability. Born from the 2026-05-18
rebuild: the prior single-file HTML approach produced aesthetically poor
output because quality was per-session goodwill, not structural. This skill
makes the bar structural. **Build success is not aesthetic success** — a
site is not done until reference-parity is visually verified and Lighthouse
runs >=95 on the deployed URL.

Canonical contract: `workspace/projects/local-web/REBUILD-SPEC.md`.
Canonical implementation to match: `app/src/pages/praxis-uslu.astro`.

## The four failure modes (hard gate — never reproduce)

1. **Hand-rolled CSS from scratch.** Stand on the shared design foundation
   (`app/src/styles/global.css`: fluid type scale, 8px rhythm, a11y
   defaults, themed primitives). Never blank CSS.
2. **Gradient/placeholder where a photo belongs.** Real imagery pipeline.
   A designed `ImageSlot`/`Figure` slot is honest scaffolding pre-launch;
   a gradient pretending to be finished is the failure. Zero gradient
   placeholders in the shipped state.
3. **No external taste anchor.** Lock 2-3 award-tier real reference sites
   per vertical in `app/src/sites/{slug}/BRIEF.md` BEFORE building. The
   extracted design DNA + explicit anti-patterns are the binding contract.
4. **Self-imposed single-file/offline constraints.** Real Astro build,
   real assets, Fly runtime. Offline leave-behind (screenshot/export) is a
   separate concern, never a design constraint on the site.

## Process (in order)

### 1. Lock the BRIEF (anti-generic gate)
`app/src/sites/{slug}/BRIEF.md` with: 2-3 named award-tier references,
extracted design DNA, explicit anti-patterns (the clichéd vertical
template to avoid), full art direction (type pairing, hex palette, layout
system, motion), one bespoke signature section concept, imagery plan, B4
data rules. Add `app/src/sites/{slug}/theme.css` — brand tokens scoped
under `[data-site="{slug}"]` (paper/surface/ink/muted/line/accent/
accent-soft + display/body fonts). Self-host fonts via `@fontsource-variable/*`
(no Google Fonts request).

### 2. B4-safe data (`app/src/sites/{slug}/data.ts`)
Every field traces to `prospects/{slug}/data.md`. Sourced facts verbatim.
Anything unverified -> `CHECK = "[BITTE PRÜFEN]"` sentinel, rendered as a
visible `.tbc` chip. **Never invent** a price, menu item, email, phone,
team, or zone. Categories are often sourced even when items are not — list
the sourced layer, flag the rest.

### 3. Build the page to the praxis-uslu bar
Bespoke per BRIEF, reusing shared primitives (`.wrap`, `.btn`, `.card`,
`.eyebrow`) + `BaseLayout` (head/SEO/canonical/noindex/JSON-LD/`data-site`).
Type-led hero so the design stands without photos. Hand-written meta +
LocalBusiness-family JSON-LD per vertical (`MedicalClinic`,
`CafeOrCoffeeShop`, `Restaurant`, ...). One real bespoke signature section
that inverts the prospect's current biggest failure.

### 4. Imagery pipeline (`app/scripts/fetch-imagery.mjs`)
Curated stock per BRIEF art direction. **No people, no fake teams, no
headset-smiler stock.** One consistent treatment per brand. Add slot
entries to the `SLOTS` array (site, name, query, orientation). Run
`npm run imagery` (needs `PEXELS_API_KEY` in `app/.env`, gitignored).
Photos land in `src/assets/{site}/{name}.jpg`; attribution -> 
`src/sites/{site}/imagery.json`. Use `<Figure>` (not raw `<Image>`): it
auto-renders the optimized responsive photo when the asset exists, else
the honest slot — zero markup change when photos land. **Commit
`src/assets/`** so the Docker/Fly build is hermetic (no key at deploy).
Add a "Bilder: Pexels" footer credit.

### 5. Deliverable-rule gate (structural)
`npm run build` runs `postbuild` -> `tools/validate-dist.py ./dist`:
fails on em-dash U+2014, `&mdash;`/`&#8212;`, or typographic `--` in
visible HTML. A failing build must not deploy. Fix at SOURCE, never rely
on the minifier. (This closes the 2026-05-08 regression where dist/ was
unscanned.)

### 6. Deploy + the real quality gate
One Astro project, one Fly app (`app/Dockerfile` -> nginx, `app/fly.toml`,
`app/nginx.conf`). `flyctl deploy {app-abs-path} --config {fly.toml} --remote-only`.
**`nginx.conf` MUST keep `absolute_redirect off; port_in_redirect off;
server_name_in_redirect off;`** — nginx behind the Fly TLS edge only sees
`http` on `:8080`, so without these the trailing-slash 301 leaks
`http://host:8080/...` and every `/<slug>` page dies with
`ERR_CONNECTION_RESET` in-browser (server-side curl still 200s — verify by
following redirects, not just status). Regression class, 2026-05-18.
Stronger: `try_files $uri $uri/index.html $uri.html $uri/ =404;` so the
no-slash URL serves the index DIRECTLY (200, no 301) and link the
slash form in nav — a 301 gets cached persistently by browsers, so once
a bad target is cached no server fix can evict it; the only safe state
is emitting no redirect at all. A cached-redirect bug is invisible to
curl (no cache): reproduce the client path or use a fresh profile, never
declare it fixed on a server-side 200 alone.
Then, non-negotiable:
- **Lighthouse mobile >=95** P/A/BP/SEO on the deployed Fly URL.
- **Reference-parity gate:** does the build sit credibly next to its
  BRIEF anchor sites? Screenshot-compare vs the old build.
- WCAG AA contrast, keyboard nav, semantic HTML.
Only after these pass is the site "done".

> **A11y verification — use axe-core via CDP, not the Lighthouse CLI.**
> The Lighthouse CLI is unreliable in the Windows dev env (silently
> re-parses stale JSON across deploys; disagrees with `curl`/CDP). The
> authoritative check is axe-core (the same engine Lighthouse uses) run
> directly: launch headless Chrome with a **forward-slash** binary path
> (`C:/Program Files/...`) — backslashes get mangled through bash
> heredocs — connect via `chrome-remote-interface`, inject
> `axe-core/axe.min.js`, run `axe.run` with `wcag2a/2aa/21a/21aa`. For a
> contrast root-cause, `CSS.getMatchedStylesForNode` +
> `getComputedStyleForNode` give ground truth in one shot — read the
> computed style, never theorize a fix from axe's HTML snippet (that is
> verification theater; cost a 3-iteration breach on 2026-05-18).
> SEO `is-crawlable` failing is expected if a page is intentionally
> `noindex`; gate it as "all non-noindex SEO audits pass", do not strip
> noindex to chase the number unless the owner directs it.

### 7. Handoff readiness
Each site owns its route, theme tokens, content, JSON-LD — designed to
split cleanly into the client's own repo at handoff. No shared business
data between sites.

## Quick reference

| Need | Where |
|---|---|
| Contract / failure modes / quality bar | `workspace/projects/local-web/REBUILD-SPEC.md` |
| Quality reference implementation | `app/src/pages/praxis-uslu.astro` |
| Shared design foundation | `app/src/styles/global.css` |
| Per-site brief + tokens | `app/src/sites/{slug}/BRIEF.md` + `theme.css` |
| Image primitive (auto photo-or-slot) | `app/src/components/Figure.astro` |
| Imagery pipeline | `app/scripts/fetch-imagery.mjs` (`npm run imagery`) |
| Deliverable-rule gate | `tools/validate-dist.py` (npm `postbuild`) |
| Deploy | `app/Dockerfile`, `app/fly.toml`, `app/nginx.conf` |

## Decision log (carry forward)

- **Design-from-references vs buy a premium theme base:** still designing
  from references directly. Revisit before scaling past ~3 sites — it
  changes the per-site cost model and this skill's shape. (Open question
  from the 2026-05-18 checkpoint.)
- Leave-behind QR cards need the owner's real name + contact line — never
  fabricated.
