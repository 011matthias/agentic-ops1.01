# Brisken Design System

Brand and UI foundations for **Brisken** — TreasuryCentral, powered by the OnePilot platform.

## Company & product context

Brisken LLC (founded 2016, Houston / The Woodlands TX, plus Germany) builds and runs
governed financial-data applications for SAP treasury teams. It is an **SAP Co-Innovation
Partner** and PartnerEdge member, part of SAP Industry Cloud for Financial Services and
Commodities, listed on the SAP Store, ISO 27001 and SOC 1 Type II certified.

Three names matter, and the hierarchy between them is load-bearing in every design:

| Name | What it is |
| --- | --- |
| **Brisken** | The company. Endorsing brand: "BRISKEN" sits as a small label above a product name. |
| **OnePilot** | The platform: governed, no-code "Universal UI" that composes apps, data and permissioned AI agents onto one surface. Not limited to SAP or to finance. |
| **TreasuryCentral** | OnePilot's one shipped edition, live on SAP with customers — the treasury workspace. Always the hero. |
| **Digital Co-Worker** | The permissioned AI agent that runs the manual steps. Named as a colleague, never as a "bot". |

Applications on the platform: Market Data Hub, BST (Brisken Smart Trading), Remittance
Advice Gate, Bank Fee Portal, Credit Data Hub, ESG Data Hub, AI Digital Workforce,
IC funding request, Cash flow portal, Bank statement generator.

### Sources this system was built from

1. `uploads/Dirk - Brisken - TreasuryCentral Solutions Overview 2026-07-27.pptx`
   — 36 slides, 1920x1080. **Slides 10, 11 and 13 were excluded on the user's instruction**;
   they are older-template slides (Poppins / Lato / rainbow ring diagrams) and are NOT
   part of this system. Everything else uses the current Segoe UI + Century Gothic system.
   Extracted text lives in `scraps/slides_text.md`, full geometry in `scraps/slides_detail.md`.
2. <https://brisken.com/> and <https://onepilot.brisken.com/> — copy, IA and section order
   read from the live sites, **plus 10 full-page screenshots supplied 2026-07-27**, from which
   the website palette, type, button and card treatments were sampled directly.
3. **6 screenshots of the OnePilot product** (`brisken-demo.app.onepilot.ai`,
   `brisken-swt-qa.app.onepilot.ai`) supplied 2026-07-27 — the source for the dark app
   palette and the product UI kit.

**Remaining gap:** the sites' and product's stylesheets were still not readable, so exact
paddings, type sizes and the product's chart geometry are measured off screenshots rather
than lifted from source. Colours are sampled pixel-exact.

## Three surfaces, one brand

Brisken runs three visual surfaces. They share a teal and a type system, and differ in
foundation colour. Always pick the scope before you design.

| Surface | Scope | Field | Text | Accent |
| --- | --- | --- | --- | --- |
| **Deck** (PPTX, slides/) | default `:root` | white / `#0F1417` ink dividers | `#0F1417` ink | teal `#0E7C86` |
| **Websites** (brisken.com, onepilot.brisken.com) | `[data-theme="web"]`, `[data-theme="web-dark"]` | `#F4F7FB` page, `#032E59` panels, `#052A52` footer | navy `#01396F` / `#2D394A` | teal `#0E7C86` |
| **Product** (OnePilot app) | `[data-theme="app"]` | `#131314` canvas, `#1E1F20` surface | `#E3E3E3` | blue `#1876D2`, mark `#E8352E` |

## Content fundamentals

The voice is the most distinctive thing about this brand. It is plain, short, declarative
and deliberately unexcited. Copy the cadence, not just the words.

**Rules observed across deck and site**

- **Sentence case everywhere.** Headlines are sentences and take a full stop:
  "One source for every rate you rely on." · "Governed, in plain terms." ·
  "Autonomous trading, booked in SAP."
- **Eyebrows are ALL CAPS, widely tracked, teal**: `THE PLATFORM · GOVERNANCE`,
  `USE CASE · INTERCOMPANY FUNDING REQUEST`, `APPENDIX · BANK FEE PORTAL`.
  A middle dot separates the section from the topic. Never a colon.
- **Jargon is defined inline, in parentheses or a following sentence.**
  "your book of records (the official system where the numbers are final)",
  "Exposure: the money at risk from currency or price moves, which treasury hedges."
  Assume a smart reader who is not a treasurer.
- **"You" and "your", never "we" in feature copy.** "Your rates live in a dozen places."
  "We" appears only for the company's own commitments: "We show OnePilot running live on
  Brisken's own SAP environment, not slideware."
- **Anti-hype.** Claims are hedged or sourced, never inflated. "Not a roadmap: real
  customers, in production today." "Coverage figures are illustrative of category scope,
  not measured benchmarks." Illustrative material is literally labelled `Illustration`.
- **The recurring rhetorical move is before/after.** `BEFORE · TODAY, BY HAND` against
  `AFTER · THE DIGITAL CO-WORKER, IN ORDER`; `THE PROBLEM IT REMOVES` /
  `WHAT IT DOES, STEP BY STEP` / `WHAT YOU NO LONGER DO BY HAND`. Steps are numbered
  and each is one short sentence ending in a full stop.
- **Every automation claim closes with the human.** "A person approves the moves that
  matter." "A person signs off the disclosure; the numbers hold up." "You stay in
  control." This is a governance brand; never write copy where the agent acts alone.
- **Em dashes and middle dots do the connecting work.** Middle dot for metadata runs
  ("Founded 2016 · Houston, TX & Germany · On SAP Store"), arrows for flows
  ("Bloomberg · Refinitiv · 360T → SAP ECC & S/4HANA").
- **No emoji. Ever.** No exclamation marks. No questions as headlines in the deck (the
  site uses real search questions as FAQ headings — that is the one exception).
- Numbers stay concrete and attributed: "71% of the live SAP treasury job ads…",
  "Manual FX runs 10 to 15 minutes a trade (The Association of Corporate Treasurers)".

## Visual foundations

**The system in one line:** white page, near-black ink, one teal, flat grey cards with a
short teal tick above the title, generous 89px margins, and a hairline footer on every slide.

### Colour
Two-colour discipline. `#0F1417` ink and `#0E7C86` teal carry everything; `#17B0BE`
bright teal is used sparingly as the *highlight within* a set (one of four card ticks, the
"you stay in control" card, the ring around a hub). Greys step `#5B666B` body →
`#8A9599` muted → `#E2E7E9` hairline → `#F4F6F7` card fill. `#C26A1B` and
`#FF3A4C` appear once or twice as flags only. No third brand hue, no tints of teal used
as decoration beyond `#EAFBFC` / `#D6ECEE` for text on teal bands.

### Backgrounds
Flat fills only. Content slides are pure white; section dividers and the contact slide are
`#0F1417` full-bleed with a 13px teal bar pinned to the very top edge. **No gradients,
no photography, no texture, no illustration, no pattern.** The only "image" on a slide is a
logo, a certification badge, or a customer mark. Dark cards (`#0F1417`) are used to mark
the winning half of a comparison, with a 13px `#17B0BE` bar down the left edge.

### Type
**Poppins** sets every headline and **Lato** all running text — both are in the source PPTX and
are the closest available match to the websites, so nothing is substituted. Website headlines
are Poppins SemiBold at 1.14 line-height with -0.01em tracking; the product shell sets Poppins
Regular. Lato runs at 1.55 on the page, 1.45 in cards.

**Monospace carries every eyebrow.** ALL CAPS, 0.18em tracking, teal — and on the hero, inside
a `#E4F3F4` pill. Credential runs and metadata lines are monospace too, as are all figures in
the product. This is the single most recognisable typographic move in the brand.

For 1:1 deck recreation the PPTX's own pair is kept as `--font-deck-display`
(Century Gothic, regular weight, 1.02 line-height) and `--font-deck-sans` (Segoe UI /
Semibold 600). Nothing is italic; nothing is underlined except links on hover.

### Layout
**Website layout is centred**, not left-aligned: a ~1040px column, everything centre-aligned
including headlines, body and CTAs, with generous 84px section padding and full-bleed navy
panels breaking it up. The **product** is a fixed 300px sidebar + fluid canvas, 28px gutters.

**Deck layout** is a left-aligned rail: eyebrow at y=89, headline at y=147, optional lead paragraph, then a
card row, then a full-width band, then a hairline + footer at y=996/1008. 89px side
margins, 51px column gaps, 3/4/6-column card rows. Centre alignment is reserved for
diagram slides (sources → hub → destinations) and full-width bands. Footers carry
"TreasuryCentral, powered by OnePilot" left and the slide number right, both 18px
`#8A9599`.

### Cards
**Deck:** flat `#F4F6F7` fill, 24-28px radius, no border, no shadow, with a 49x7px teal tick
above the title. Bordered white cards (2px `#E2E7E9`, 4px `#17B0BE` for a hub) mark "the
thing itself" inside a diagram.

**Website:** white, 1px `#E2E9F2` hairline, 12px radius, a barely-there shadow — and a **3px
teal left edge** when the card carries proof or a live claim. Node cards on the platform map
have no edge.

**Product:** `#1E1F20` surface, 1px `#333537` border, 10px radius, no shadow.

### Buttons
Website buttons are **fully pill** (999px): solid teal with white text as primary, white on
navy panels, hairline-outline teal as secondary, and a mono uppercase outline pill for status
("LIVE ON SAP"). The product uses the same pill shape at 999px with a `#292A2C` fill or a
`#1876D2` outline.

### Shadows, transparency, blur
Effectively unused. The deck has no drop shadows at all. For screen UI, keep to a 1px
`rgba(15,20,23,.05)` lift on sticky headers and a soft overlay shadow for dialogs.
No glassmorphism, no backdrop blur.

### Borders & rules
Three widths only: 1.5px (`0.75pt`) light dividers, 2px (`1pt`) card borders, 4px
(`2pt`) emphasis rings. Horizontal rules are `#E2E7E9` 2px. Accent rules are teal and
short (49x7 above card titles, 317x6 under the title-slide product name, 288x6 on contact).

### Motion & states
The deck is static; the sites are quiet. Use 120-200ms `cubic-bezier(.2,0,.2,1)` fades
and 1-2px translations. Hover: teal deepens `#0E7C86` → `#0A5A61`, grey cards go
`#F4F6F7` → `#ECEFF0`, hairlines pick up teal. Press: no scale change, one step darker.
Focus: 2px `#17B0BE` outline at 2px offset. No bounces, no springs, no parallax,
no animated gradients.

### Imagery
There is none to copy — and that is the rule. Where a design needs an image, use a flat
grey `#F4F6F7` well with a monospace label naming what belongs there, or use the real
logo/badge assets in `assets/`. Do not introduce stock photography, AI imagery or
hand-drawn illustration into Brisken material.

## Iconography

**Brisken's current material uses almost no icons, and this should be respected.**
Across the 33 in-scope slides there is not a single UI icon: hierarchy is carried by
numbered teal circles (43px, `#0E7C86`, white Segoe UI Semibold numeral), short teal
rules, right-arrow shapes between diagram columns, and typographic marks. The excluded
slides 10/11/13 are the exception — they carried a rainbow ring of thin coloured line
icons from the previous template, which is why they were dropped.

- **Typographic marks stand in for icons:** `·` middle dot as separator, `→` as the
  flow/benefit arrow (teal on dark, `#17B0BE`), `+` for "your own apps",
  `☼/☾` on the websites for the light/dark toggle.
- **Numbered steps** are the primary "icon": a filled teal rounded square (10px radius)
  with a white numeral, 43x43 on slide scale.
- **Arrows between diagram blocks** are solid `#17B0BE` right-arrow shapes, not glyphs.
- **The websites use small thin line icons** — a hairline circle-check beside each credential,
  a house / grid / layers / question glyph on each platform-map node, a chevron on each FAQ row.
  **The product uses a full thin line icon set**: one per space in the sidebar, plus search,
  filter, refresh, export, paperclip, image and send.
- **No icon font or sprite sheet was available to copy**, so `Icon` in the product kit renders
  **Lucide** at 1.6px stroke, `currentColor`. **This is a flagged substitution** — send the
  real set and it swaps out in one file. Keep icons to navigation, controls and status; never
  decorate content with them.
- The deck itself uses **no icons at all** — numbered teal badges, short teal rules and
  typographic marks do that work.
- **Real image assets** are logos and third-party credentials only — see `assets/`.
- **Emoji are never used.**

## Logo

`assets/logos/brisken-logo.png` — lowercase "brisken" wordmark in `#0F1417` with a
two-tone cube mark (`#17B0BE` / `#00B5D0` on `#0F1417`) to its right.
`assets/logos/brisken-logo-reversed.png` is the same lock-up with a white wordmark, for
`#0F1417` backgrounds. On slides it sits bottom-right, ~210-224px wide on the 1920
canvas, with 89px clearance. Never recoloured, never rotated, never on a busy field.

## Intentional additions

The sources define no UI component library — they are a deck plus two marketing sites. The
components in `components/` are therefore derived from repeated **deck and site patterns**
(eyebrow, tick card, chip, step list, band, logo well, credential row, FAQ row, stat) rather
than invented from a generic checklist. Each component's `.prompt.md` names the slide or
page section it came from.

## Index

- `styles.css` — the single entry point consumers link. `@import`s only.
- `tokens/` — `colors.css`, `typography.css`, `spacing.css`, `shape.css`,
  `slide.css` (1920x1080 deck geometry), `fonts.css`, `base.css`.
- `guidelines/` — foundation specimen cards (colour, type, spacing, brand, voice).
- `components/core/` — Eyebrow, Headline, TickCard, Chip, StepList, Band, NumberBadge,
  Button, LogoWell, CredentialRow, Stat, FaqRow, SlideFooter.
- `ui_kits/website/` — brisken.com and onepilot.brisken.com recreation, with light/dark toggle,
  the clickable platform map and its dialog, the FAQ accordion and the demo dialog.
- `ui_kits/onepilot/` — the OnePilot product app: spaces sidebar, audit log, investment
  dashboard, assistant panel.
- `slides/` — the deck's layout system, one HTML per slide type.
- `SKILL.md` — Agent Skills wrapper for use in Claude Code.
- `scraps/` — raw extraction from the PPTX (text, geometry, all media). Reference material,
  not part of the shipped system.
