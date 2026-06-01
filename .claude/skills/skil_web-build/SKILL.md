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

**Co-load:** when this skill activates, also load the `frontend-design`
plugin skill (`claude-plugins-official/plugins/frontend-design`). They
compose: `frontend-design` carries the bold-aesthetic-direction
discipline this skill assumes (anti-AI-aesthetics, typography choice,
spatial composition); this skill carries the local-web pipeline plus
the Kowalski-anchored motion specs in §3a.

## Session entry (cold-load reading order)

When this skill auto-loads on a fresh session with a web-build task,
read in this order BEFORE touching code (skip files already loaded
by `/comd_resume local-web`):

1. `workspace/projects/local-web/REBUILD-SPEC.md` — the contract
2. `workspace/projects/local-web/infrastructure.yaml` — deploy + gates
3. `app/src/pages/praxis-uslu.astro` — the quality reference to match
4. Latest `docs/{YYYY-MM-DD} - Local-Web …/Checkpoint.md` — last
   shipped state
5. `app/src/sites/{slug}/BRIEF.md` + `theme.css` for every site in scope
6. `prospects/{slug}/data.md` for every site in scope (B4 source)

Scope clarification is case-by-case, not a fixed pre-flight checklist.
Directive input ("rebuild the coffee-boxx hero with a new anchor")
executes; exploratory input ("what should the 4th site be?") asks one
or two targeted questions, not a mandatory six-part interrogation.
Per the input-interpretation rule (`rule_behaviors.md`), gating
directive work behind clarification theatre is friction.

When asking IS warranted (genuinely ambiguous scope), the high-value
forks are: (a) site scope — new prospect / rework / personalise /
cards / pipeline automation; (b) deploy posture — local dry build
vs live deploy (live still needs explicit ship order per
`rule_no_auto_commit`); (c) for a new prospect — vertical, city,
public sources, and any taste-anchor references already in mind.

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

### 3a. Taste anchors + motion craft (Kowalski + frontend-design)

The build steps above produce a page; this section is what makes it
*good*. Two anchor sources: Emil Kowalski's UI lessons
(`emilkowal.ski/ui/*`) and the `frontend-design` plugin skill that
this one co-loads. Award-tier quality is no longer per-session
goodwill once these rules are cited at decision time.

**Articulated-WHY in the BRIEF.** Every art-direction call (type
pair, palette, spacing, motion easing/duration, signature section)
gets a one-line *"why this, not the default"*. Kowalski's frame:
every taste decision has a logical reason; document it or you're
guessing (`emilkowal.ski/ui/developing-taste`, `…/agents-with-taste`).
The BRIEF must also name 1-2 references it is intentionally NOT
borrowing from (the anti-pattern direction); naming the rejection
sharpens what the chosen references actually carry.

**Typography hard bans.** Inter, Roboto, Arial, default system
stacks, and Space Grotesk are banned as primary type unless the BRIEF
explicitly justifies one on a non-default basis. Reach for
distinctive display + body pairings via `@fontsource-variable`.
Reason: these are the AI-default fonts; using them is the signature
of generic AI-generated UI (source: `frontend-design` plugin skill).

**Motion craft (quantified).** Vague motion guidance is the source
of janky-feeling animations. These rules are structural. Cite them
in PR descriptions or the BRIEF when a motion choice is non-obvious:

| Rule | Value | Source |
|------|-------|--------|
| Enter/exit easing | Custom `cubic-bezier`, not built-in `ease-out` (built-ins "usually not strong enough") | `…/7-practical-animation-tips` #4 |
| On-screen movement easing | `ease-in-out` | `…/great-animations` |
| Hover / colour easing | `ease` | Kowalski |
| Duration ceiling | ≤ 300ms; 180ms beats 400ms on perceived responsiveness | `…/great-animations` + tips #6 |
| Animated properties | ONLY `transform` + `opacity` (composite layer; no layout/paint cost) | `…/great-animations` |
| Initial scale | Never `scale(0)`; start from `0.95`+ | tips #2 |
| Button press feedback | `scale(0.97)` on `:active` | tips #1 |
| Transform origin | Per-element (popovers scale from trigger point, e.g. `var(--radix-…-transform-origin)`) | tips #5 |
| Interruptibility | Required (CSS transitions or Motion lib) | `…/great-animations` |
| Restraint | Never animate keyboard-initiated actions; skip animations on elements users see 100+×/day | `…/great-animations` + `…/you-dont-need-animations` |
| Escape hatch | `filter: blur()` to bridge state transitions when easing/duration alone cannot | tips #7 |
| Accessibility | `prefers-reduced-motion: reduce` always honoured | `…/great-animations` |

**Comparative-judgment gate (formal — match-then-exceed).** Before
deploy, place a screenshot of the candidate hero next to ONE named
BRIEF anchor. The anchor is a FLOOR, not a ceiling. Articulate *in
writing* (PR description or BRIEF appendix), region by region:

1. **Parity** — for each load-bearing region of the hero (type
   treatment, palette, layout structure, imagery role, motion,
   trust/info surfacing, primary CTA), does the candidate sit
   credibly next to the anchor? If not yet, name the gap.
2. **Exceed** — for each region that already reaches parity, name
   where the candidate can go BEYOND the anchor. The anchors are
   often years old, sometimes drifted (rebrands, acquisitions),
   and may carry their own anti-pattern violations the BRIEF was
   written against. Best-in-class is the target, not "looks like
   the reference."

Both passes are mandatory. A page that matches the anchor in every
region but exceeds in none is shipped at the floor of the quality
bar, not the ceiling. Sources: `emilkowal.ski/ui/train-your-judgement`,
plus owner directive 2026-06-01. The articulated judgment IS the
gate; "looks fine to me" is not, and neither is "matches the
reference."

**Background depth rule.** No flat solid-colour backgrounds in
primary sections. Pick one of: gradient mesh, noise/grain, layered
photography, geometric pattern, or the §4b depth-parallax hero.
Pages of plain white sections fail the impeccable bar unless the
BRIEF explicitly justifies the minimalism as the aesthetic direction
(luxury / editorial restraint). Source: `frontend-design` plugin
skill, "atmosphere + depth" rule.

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

### 4b. Motion & 3D-feel imagery (gate-budgeted)
The visuals should have depth and motion, never a flat photo wall. This
is an imagery quality bar, not an interactive-3D-scene mandate.

**Default tier (every site, ~0 perf cost, do this first):** CSS-driven
only -- Ken Burns slow zoom/pan on the hero photo, scroll-driven reveal
+ layered parallax, hover-tilt on cards (`vanilla-tilt`/Atropos, lazy).
Reads premium, zero WebGL, never threatens the gates.

**Budgeted WebGL hero (at most ONE element per site, optional):**
typically a depth-map parallax photo (one still + a grayscale depth map,
a small shader displaces it on mouse/gyro -> the image visibly pops into
layers) or a single `<model-viewer>` GLTF object. Permitted only with
ALL of:
- Lazy-init on idle/scroll (never blocks first paint or LCP)
- Static poster image as the no-JS / pre-init fallback
- `prefers-reduced-motion: reduce` -> render the static poster, no loop
- Mobile (<=768px) serves the static image, not the WebGL canvas
- Re-run the section-6 Lighthouse + axe gate AFTER adding it; a 3D
  canvas is a classic silent perf/a11y regression. Perf 100 / 0 WCAG2AA
  stays absolute -- if the hero can't pass, it ships as the poster.

Full multi-element interactive Three.js scenes are out of scope for this
stack; the gate is non-negotiable, the hero is the only WebGL budget.

**Implemented (2026-05-19, all 3 sites):** depth-map parallax via
`DepthHero.astro` (transparent enhancement of `<Figure>`; zero-dep
hand-rolled WebGL1 shader; poster `<Image>` stays the LCP + the entire
no-JS/pre-init/reduced-motion/<=768px/no-WebGL/Save-Data tree;
`canvas aria-hidden`). Depth maps: `app/scripts/depth-map.py`
(Depth-Anything-V2-Small ONNX, CPU, uv; PNGs committed -> hermetic
build). **Verify the live effect with `tools/depth-live.cjs`** (fresh
zero-cache profile, A/B pointer parallax, full-page
`captureBeyondViewport` capture). Hard lesson: a bespoke CDP-`clip`
screenshot probe reads the wrong region after `scrollIntoView` — use
the full-page capture path, and trust composited screenshots over a
`readPixels` of a non-`preserveDrawingBuffer` context (that read is
undefined post-composite and will false-fail).

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

### 8. Definition of done (consolidated ship checklist)

A site is shippable only when ALL of these are true. Re-read the list
before declaring done; the gates in §1–§6 are the source of truth, this
is the consolidation. If this list and an upstream section disagree,
the upstream section wins.

1. **BRIEF.md complete** — 2-3 named award-tier anchors, extracted
   design DNA, explicit anti-patterns, articulated-WHY per major
   art-direction call, 1-2 references intentionally NOT borrowed from
   (§3a).
2. **B4 data integrity** — every fact on the page traces to
   `prospects/{slug}/data.md`, or carries the `[BITTE PRÜFEN]` chip
   (§2). No invented prices, menus, emails, phones, teams, hours,
   addresses.
3. **Deliverable-rule gate** — zero em-dash U+2014, `&mdash;`,
   `&#8212;`, or typographic `--` in source; `npm run build` →
   `tools/validate-dist.py ./dist` passes (§5). Fix at SOURCE.
4. **Real imagery in every photo slot** — no gradient placeholders in
   the shipped state (§4). `src/assets/{slug}/` committed (hermetic
   build, no Pexels key at deploy). `imagery.json` carries attribution.
   "Bilder: Pexels" footer credit present.
5. **Background depth rule honoured** — no flat solid-colour primary
   sections unless the BRIEF explicitly justifies the minimalism (§3a).
6. **Typography matches BRIEF** — banned defaults (Inter / Roboto /
   Arial / Space Grotesk / system stacks) only appear if §3a
   non-default justification is written down (§3a).
7. **Motion craft** — every animation matches the §3a quantified
   table: custom cubic-bezier (no built-in `ease-out`), ≤300ms,
   `transform`/`opacity` only, never `scale(0)`, `scale(0.97)` on
   `:active`, per-element transform origin, interruptible,
   `prefers-reduced-motion: reduce` honoured.
8. **Depth hero (if used)** — at most ONE per site; poster fallback
   verified on no-JS, `prefers-reduced-motion`, viewport ≤768px,
   no-WebGL, and `Save-Data`; depth maps committed; `tools/depth-live.cjs`
   confirms live parallax in a fresh zero-cache profile (§4b).
9. **nginx config locked** — `absolute_redirect off; port_in_redirect
   off; server_name_in_redirect off;` and the
   `try_files $uri $uri/index.html $uri.html $uri/ =404;` chain (§6).
   No 301s ever — cached 301s are persistent and unfixable
   client-side.
10. **Performance gate** — Lighthouse mobile ≥95 on Performance,
    Best Practices, SEO on the DEPLOYED Fly URL (not localhost). SEO
    `is-crawlable` waived only for intentionally `noindex` pages (§6).
11. **Accessibility gate** — axe-core via CDP returns zero WCAG 2 A/AA
    violations on the deployed URL. Lighthouse CLI a11y output is NOT
    authoritative in this env (§6 quote block).
12. **Comparative-judgment paragraph** — a written articulation in the
    PR description (or BRIEF appendix) of why the candidate hero
    matches ONE named BRIEF anchor, or where it does not yet (§3a).
    "Looks fine to me" is not the gate.
13. **Owner ship order** — explicit go-ahead in the current
    conversation. Edits stop at the staging boundary per
    `rule_no_auto_commit`; no auto-deploy, no auto-PR, no auto-merge.

If any item is open, the site is not shipped. Surface what is open and
wait.

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
- **Kowalski + frontend-design taste anchors integrated 2026-05-26.**
  Quantified motion craft, typography bans, comparative-judgment gate,
  and background-depth rule now live in §3a. The "award-tier bar" the
  prior failure mode named is operationally citable, not per-session
  goodwill. Co-load instruction added at the top of the skill.
