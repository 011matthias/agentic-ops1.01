# Capability: navigation bar (top bar)

Canonical location: `.claude/skills/skil_web-build/components/nav-bar.md`
Referenced from `SKILL.md` (Module index), and gated by `SKILL.md` Definition of done item 15.

## What this is

The top navigation bar is the first impression of every site this skill produces. Most local business sites get it wrong in the same three ways: multiple competing CTAs, dead generic sans-serif wordmark, and a sticky shadowed bar that screams template. This document defines the structural and typographic rules that produce a bar reading as professional, authentic, and visibly above the local-competitor baseline, while flexing to each vertical's commercial reality.

The rules below are mandatory unless explicitly justified in writing in the site's BRIEF.md.

## Structural pattern (always)

A nav bar built under this skill has exactly four zones, in this order, left to right:

1. **Wordmark zone.** Brand name as expressive type, optional one-line category tagline directly under it.
2. **Slack zone.** Empty whitespace. Not negotiable; it carries the editorial feel.
3. **Nav-item zone.** Three to five text links, right-aligned, restrained styling.
4. **CTA zone.** Exactly one primary call to action. Pill, soft-rectangle, or stamp shape, brand-derived colour.

A site has *one* CTA in the bar. Not two, not three. The CTA is the single most commercially valuable action for that vertical (book, reserve, order, call). Every other action goes into the page body or footer.

Logo as image is permitted only when the prospect has a real brand mark. If the wordmark is doing the work, it stays as live text in the chosen display face, never as a flat PNG.

## Typography contract

Three type roles in the bar, never collapsed into one or two:

- **Wordmark face.** Expressive display type. Editorial serif (Domaine, GT Super, Tiempos Headline, Recoleta, Playfair Display for budget) or a characterful condensed sans with a real voice. Inter, Roboto, Arial, Space Grotesk, system stacks are banned per skill rule unless an articulated non-default justification exists.
- **Tagline face (optional but recommended).** Small, generously letter-spaced, uppercase. Humanist sans or geometric sans, usually the body face at small size with `letter-spacing: 0.15em` or higher. The tagline does three jobs at once: SEO keyword surface, category positioning, visual rhythm between wordmark and nav items.
- **Nav-item face.** Body sans, regular weight, small size. Underline on hover and on active route only. Never bold. Never uppercase in nav items (the tagline owns that texture).

The contrast between the wordmark and the nav items is part of the design. A serif wordmark sitting beside a calm sans nav reads as professional editorial. A bold sans wordmark beside a bold sans nav reads as a template.

## Spacing and rhythm

- Vertical padding inside the bar is generous. Minimum `1.25rem` top and bottom on desktop, `1rem` on mobile. Cramped nav bars read cheap.
- Horizontal page padding aligns with the page's content grid; do not full-bleed the bar contents unless the entire site uses an edge-to-edge grid.
- Gap between nav items: at least `2rem` on desktop; at least `1.5rem` between the last nav item and the CTA. Tight gaps read as a default CSS framework.
- The wordmark and CTA define the bar's vertical centre line. Nav items align to that centre line, never to the wordmark's baseline.

## CTA principles

The CTA is the single highest-leverage element in the bar.

- **Colour:** derived from the brand palette, never the generic delivery-app orange family (`#E85D2F` and neighbours) unless the brand genuinely owns that hue. Beauty and wellness sites lean dusty rose, terracotta, brass. Restaurants lean deep red, burnt sienna, forest green. Medical leans calm sage, deep teal, warm clay (never medical-blue gradient). Barbershops lean oxblood, brass, deep green.
- **Shape:** soft pill (Beauty Lounge example), refined rectangle with light radius, or a stamp shape (for vintage-leaning brands). Sharp corners read modern-app; full pills read pharmacy. Find the middle and commit.
- **Label:** verb plus one supporting word, maximum. `Termin`, `Reservieren`, `Bestellen`, `Tisch reservieren`, `Anrufen 0721 ...`. Never `Click here`. Never `Mehr erfahren` as the primary CTA.
- **State:** subtle hover (darken 6 to 10 percent or lift via shadow within the motion-craft envelope of <=300ms, custom cubic-bezier, transform and opacity only). No `scale(1.05)` bounces; this is a professional site, not a SaaS landing page.

## Colour and surface rules

- **Background:** never pure white (`#FFFFFF`) or pure black (`#000000`). Both read as a default stylesheet. Use a brand-derived cream, off-white, deep espresso, or warm charcoal. The background-depth rule from the skill applies here too; if the rest of the page has texture, the nav can carry a hair of that texture (subtle grain at 2 to 4 percent opacity) so the bar does not float as a flat slab.
- **Border or divider:** optional. If present, use a hairline at low opacity (`rgba(0,0,0,0.06)` family) or a soft inset shadow. No 1px solid black borders.
- **No drop shadow under the bar by default.** A heavy shadow under a fixed nav is the universal "I used a template" signal. If the bar is sticky and needs visual separation from page content, use a 1 to 2 percent darken on scroll, not a shadow.

## Sticky behaviour

- Default: not sticky. Sites under 5 viewport heights of content do not need a sticky bar; the user can scroll back up.
- Sticky is permitted when (a) the page exceeds 5 viewport heights, (b) the CTA is genuinely the page's purpose (booking, ordering), or (c) the prospect explicitly requests it.
- When sticky, the bar must change appearance on scroll: reduce vertical padding by 25 to 40 percent and add the subtle background darken or hairline border. The bar at the top of the page and the bar after 1000px of scroll should look measurably different; otherwise the sticky read as accidental.

## Mobile behaviour

- The mobile bar shows wordmark left, hamburger or single icon right, optional CTA right of hamburger if vertical commercial logic demands it (restaurants with delivery often keep the CTA visible).
- Hamburger icon is custom; never the default Bootstrap or Material three-bar. Two lines of unequal length, hand-drawn feel, brand-coloured. Or, for editorial sites, the word `Menü` in small caps replaces the icon.
- The opened menu is full-screen overlay, not a dropdown panel. Nav items at large type, centred or left-aligned per site direction, with the CTA at the bottom as a wide button.
- Tap targets >=44px in all states.

## Per-vertical adaptation

The structural pattern is fixed; the specific typography, palette, and CTA flex per vertical. Use the column on the right as a starting hypothesis; validate against the site's BRIEF.md and references.

| Vertical | Wordmark face direction | Tagline content | Single CTA | Palette direction |
|---|---|---|---|---|
| Barbershop, men's grooming | Slab serif, condensed sans, characterful | `KLASSISCHE HERRENPFLEGE` or city + craft | `Termin buchen` | Oxblood, brass, deep green, charcoal |
| Women's hair, beauty | Editorial serif, calligraphic display | `KOSMETIK · NAGELDESIGN · WELLNESS` style triplet | `Termin` | Dusty rose, terracotta, cream, sage |
| Doctor, general medical | Humanist serif or warm sans | `HAUSARZTPRAXIS DR. ...` plus city | `Termin vereinbaren` | Warm clay, sage, deep teal, cream |
| Dental | Editorial serif with one warm accent | Practice name + speciality | `Termin online` | Warm white, brass, soft coral, deep teal |
| Restaurant, fine dining | Editorial serif, often italic | Cuisine + neighbourhood | `Reservieren` | Deep red, forest, cream, brass |
| Restaurant, casual or pizzeria | Vintage condensed, hand-cut serif | Cuisine + city | `Bestellen` or phone number | Warm dark, brass, red, cream |
| Cafe | Hand-drawn or warm serif | Single word category or city | `Karte ansehen` or `Bestellen` | Warm cream, deep brown, brass, dusty olive |
| Nail salon, cosmetic | Calligraphic display, modern script | Service triplet | `Termin` | Soft neutrals + one bold accent (rose, mauve, deep teal) |

These are starting positions; the BRIEF anchors override the table when the references genuinely demand a different direction.

## The seven things to never do

These produce instant template signal. None of them are recoverable.

1. **Three CTAs in the bar.** Pick one, demote the others to body or footer.
2. **Bold sans wordmark with bold sans nav.** No type contrast equals no design.
3. **Default system fonts.** Even one. The bar is too prominent for fallbacks.
4. **Heavy box-shadow under a sticky bar.** Universal template signal.
5. **Delivery-app neon orange.** Unless the brand owns that hue, do not reach for it. Pull the CTA colour from the actual brand palette.
6. **Bootstrap-default hamburger icon.** Two unequal lines or a typeset word `Menü` instead.
7. **Logo PNG when the wordmark could be live type.** Live text scales, renders crisp, indexes for SEO, and respects type rules. PNG logos only when there is a real brand mark.

## Comparative-judgment gate (nav-specific)

Before declaring the nav done, take a 1440px screenshot of the bar in isolation. Place it next to:

- One named BRIEF anchor's nav bar
- One direct local competitor's nav bar (the prospect's actual competition in their city)

Write a paragraph answering: does this bar look like it belongs to the same world as the BRIEF anchor, and does it visibly outclass the competitor's bar? If the competitor's bar holds its own against this one, the bar is not done.

This nav-specific gate sits beside the hero-level comparative-judgment gate in `modules/CONCEIVE.md` §5 (match-then-exceed). Both fire; the nav gate isolates the bar, the hero gate judges the whole hero.

## Acceptance checklist

Before merging a site that uses this capability:

1. Exactly one CTA in the bar
2. Wordmark and nav items use type from outside the banned-defaults list
3. Tagline present unless explicitly omitted in BRIEF.md with reason
4. Vertical padding meets the minimum (`1.25rem` desktop, `1rem` mobile)
5. CTA colour traceable to the brand palette (cite the source in BRIEF.md)
6. Background is not pure white or pure black
7. No drop shadow under the bar in the default scroll state
8. Mobile menu is full-screen overlay with custom hamburger or `Menü` text
9. axe-core via CDP returns zero contrast violations in the bar (same CDP method as `references/a11y-verify.md`, not the Lighthouse CLI)
10. Comparative-judgment paragraph written against one BRIEF anchor and one local competitor
