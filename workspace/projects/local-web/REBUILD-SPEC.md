# Local Web — capability rebuild spec (v2)

Status: APPROVED approach, execution pending fresh session.
Reason for rebuild: v1 + guide HTML builds were aesthetically poor. Owner
directive 2026-05-18: rethink and rebuild the website-build capability;
prototypes become real apps on Fly.io, not single HTML files.

## Diagnosed failure modes (the next pass MUST avoid these)

1. Hand-rolled CSS from scratch → unrefined proportions/rhythm. Fix: stand
   on a designer-built foundation, never blank CSS.
2. CSS-gradient blocks where real photography belongs → looks unfinished.
   Fix: real imagery pipeline, gradients are never a final state.
3. No external taste anchor → generic. Fix: lock 2-3 best-in-class
   reference sites per vertical BEFORE building; design to that bar.
4. Self-imposed single-file/offline/no-asset constraints structurally
   capped quality. Fix: real build, real assets, Fly runtime. Offline
   leave-behind is a separate concern (export/screenshot), not a design
   constraint on the site itself.

## Locked decisions (owner, 2026-05-18)

- **Design foundation: Hybrid.** Premium template/theme base per vertical
  for structure + polish; bespoke hero and 1-2 signature sections per
  brand so it never reads as a recognizable theme.
- **Imagery: Both, per section.** Curated stock (Unsplash/Pexels) for
  literal subjects (food, interior, craft); AI-generated for hero
  atmosphere, textures, abstract brand elements. No fake people, no fake
  teams, no headset-smiler stock. One consistent treatment per brand.
- **Fly architecture: one repo, one Fly app, many sites.** Single Astro
  project serving all prototypes; one Fly app. Designed so any one site
  splits cleanly into the client's own structure at handoff.

## Tech

- **Astro** (latest) + Tailwind, content-first, minimal JS, per-vertical
  theme base. Node 24 / npm 11 confirmed available.
- Each prototype = its own Astro "site" (own routes, own theme tokens,
  own content collection): `/praxis-uslu`, `/coffee-boxx`, `/pronto-pronto`.
- Containerized (Dockerfile, `fly.toml`), deployed to one Fly app.
  flyctl install handled this session; **auth needs owner**: either
  `flyctl auth login` (interactive) or set `FLY_API_TOKEN`. This is a
  genuine credential step, surfaced as a real USER ACTION, not a defer.
- Repo location: `workspace/projects/local-web/app/` (new Astro project).
  Old `prospects/*/index*.html` kept as reference only, not shipped.

## Per-vertical creative brief (taste anchors set at build time)

For each: pick 2-3 award-tier real references (Awwwards/Godly/Httpster
class, same vertical), record URLs in `app/src/sites/{slug}/BRIEF.md`,
design to that bar. Direction seeds:

- **praxis-uslu (Hausarzt):** calm editorial-clinical, warm neutrals + one
  organic accent, humanist type, real warm practice/its-people imagery
  treatment, trust-forward. NOT medical-blue-gradient template.
- **coffee-boxx (Café):** warm independent-roaster editorial, big
  characterful serif, grain, real coffee/space photography front and
  centre, menu as first-class content.
- **pronto-pronto (Pizza Heimservice):** appetite-first, bold, real
  food photography hero, fast-order CTA, searchable menu, energetic but
  not the generic Lieferando-red template.

## Quality bar (definition of done — enforced, not hoped)

- Reference-parity check: build sits credibly next to its anchor sites.
- Real imagery in every section that implies a photo. Zero gradient
  placeholders in the shipped state.
- Lighthouse mobile >=95 P/A/BP/SEO, run on the deployed Fly URL.
- WCAG AA contrast (automated check), keyboard nav, semantic HTML.
- LocalBusiness JSON-LD per vertical, hand-written meta/titles.
- No em-dash / &mdash; (rule_deliverables); accurate data, `[BITTE
  PRÜFEN]` for unknowns (B4).
- Side-by-side vs the old build screenshot in the checkpoint.

## Operationalize (self-annealing — do not skip)

The aesthetic bar must be structural, not per-session goodwill:
- Create `.claude/skills/skil_web-build/` (or agent): the standard
  process — pick references, choose theme base, imagery pipeline,
  Astro+Fly scaffold, quality-bar gate. So every future client site is
  produced this way, not re-invented.
- Friction logged this pivot: `intent-misalignment` / `strategic-gap` —
  iterated within a low-ceiling format instead of surfacing that the
  format itself blocked quality.

## Next-session task order

1. `flyctl auth` (owner step) → confirm app target.
2. Scaffold Astro project in `app/`, Tailwind, multi-site structure.
3. Per vertical: lock references in BRIEF.md → choose theme base →
   bespoke hero + signature section → wire real content (from
   `prospects/{slug}/data.md`).
4. Imagery pipeline: Unsplash/Pexels fetch + treatment; AI hero/texture.
5. Dockerfile + fly.toml; deploy one Fly app; Lighthouse on live URL.
6. Quality-bar gate vs references; screenshot compare; checkpoint.
7. Write `skil_web-build` skill.
