# Guide-spec builds (`index-guide.html`) vs. v1 (`index.html`)

Second pass, built to the supplied "Local Business Website Builder" agent
guide. Saved next to each v1 equivalent in `prospects/{slug}/`.

## Deliberate deviation from the guide (stated, per guide "ask before irreversible")

The guide defaults to an Astro/Next + Tailwind + shadcn project. I kept the
**single self-contained HTML file** format instead, for one reason: this
initiative needs an offline-capable artifact for walk-in pitches and an
apples-to-apples comparison with v1. A multi-file framework project is not
comparable side by side and cannot be shown without a build step. Everything
in the guide that is *design and content quality* was applied; everything
that is *stack mechanics* is noted as not-applicable-in-one-file below.

## Phase 1 audit + differentiators (compressed; source data in `prospects/{slug}/data.md`)

**Praxis Dr. Sema Uslu.** Current site: host wouldn't even respond; no
structured data, no mobile story. Most Karlsruhe Hausarzt sites use the
clichéd medical-blue gradient template. Differentiators: editorial-calm
direction (warm paper, sage, Newsreader serif) that reads as a *practice
with time*, not a clinic CMS; credentials and languages surfaced; emergency
116117 / 112 explicit; MedicalClinic JSON-LD; Impressum/Datenschutz flagged
as legally required (not faked).

**Coffee Boxx.** Current site: Meinewebsite builder, Easter text as
homepage, menu hidden in a PDF, no socials. Local cafés mostly run
Instagram-only or the same builder look. Differentiators: warm magazine
direction (Fraunces display, grain texture, offset editorial gallery),
menu as real indexable HTML with leader rows, location + live open-state
above the fold, CafeOrCoffeeShop JSON-LD.

**Pronto-Pronto.** Current site: dense text, dated, no dish prices, weak
photography, no CTA hierarchy. Competing Lieferando-style pages look
identical to each other. Differentiators: appetite-driven direction
without the generic pizza-red template, **searchable** menu (real
filter, not a PDF), 10% online offer and order CTA above the fold on
mobile, delivery zones as scannable chips, Restaurant JSON-LD with
delivery method.

## What changed v1 -> guide build

| Area | v1 | Guide build |
|---|---|---|
| Type | system font stack | Newsreader/Fraunces display + Inter body pairing |
| Visual direction | clean utility | committed per-vertical art direction (editorial-calm / warm-magazine / appetite) |
| Layout | symmetric card grids | asymmetric, editorial lists, intentional whitespace |
| Semantics | div-based | `main`/`nav`/`article`/`address`, skip-link, focus-visible, reduced-motion |
| SEO | meta only | hand-written titles + LocalBusiness JSON-LD per vertical |
| Trust/legal | light | credentials, NAP consistency, emergency numbers, Impressum/Datenschutz flagged required |
| Menu (food) | static list / cards | real HTML menu; Pronto-Pronto menu is searchable |

## Before-you-declare-done checklist (honest status)

- [x] Semantic HTML, skip-link, visible focus, `prefers-reduced-motion`
- [x] WCAG-minded contrast (dark ink on warm paper; CTA white on saturated brand)
- [x] Mobile-first, single primary CTA above fold on mobile
- [x] No layout shift: aspect-ratio on all visual blocks, no async images
- [x] LocalBusiness JSON-LD per vertical, hand-written meta/titles
- [x] HTML structural validator passes; zero em-dash / `&mdash;`
- [x] Real copy in brand voice; unknowns marked `[BITTE PRÜFEN]`, never faked
- [ ] **Lighthouse >=95** — not runnable on a local single file here; needs the
  deployed URL + a Lighthouse run. Webfont via Google Fonts adds one request
  (v1 was offline-pure); self-hosting fonts is a real-build step.
- [ ] **next/image / srcset / AVIF** — N/A in single file; placeholders are
  art-directed CSS, real photos are a client-supplied build step.
- [ ] **Server-action form + spam protection, Plausible** — backend/stack
  features, not applicable to a static demo.
- [ ] Side-by-side screenshots — left to your visual review (both versions opened).

## Remaining client-supplied items (both versions)

Real photography, final menu + prices, email, Doctolib/jameda booking
(Uslu), Coffee Boxx 2nd location, legally reviewed Impressum/Datenschutz.
