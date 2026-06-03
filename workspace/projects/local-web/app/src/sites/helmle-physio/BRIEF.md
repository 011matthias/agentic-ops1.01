# BRIEF, helmle-physio (Physiotherapie / Krankengymnastik)

Source content: `workspace/projects/local-web/prospects/helmle-physio/data.md`.
Binding contract for this site's build. Reference-parity against the
anchors below is a definition-of-done gate (skil_web-build quality bar).

## The business

Krankengymnastik- und Massagepraxis Helmle & Helmle, Karlstr. 86,
Karlsruhe-Südweststadt. A real neighbourhood physiotherapy practice:
Krankengymnastik, Manuelle Therapie, Massagen, Lymphdrainagen, plus
Schlingentisch, Wärme/Kälte, Elektrotherapie, Naturfango and Hausbesuche.
The demo must read warm, calm and hands-on: a practice that takes its time,
not a cold clinic and not a luxury spa.

## Logo-DNA

Real logo committed at `app/src/assets/helmle-physio/logo.jpg`:
- A teal/blue twin-"H" figure mark: two stylised human figures, arms raised,
  each forming the letter H. Left figure in a darker petrol/teal-blue, right
  figure in a brighter teal-green. The mark reads as movement + people, which
  is exactly the body-wellness positioning.
- Wordmark "HELMLE & HELMLE" in a dark navy serif/blocky cap, with
  "Physiotherapie" set smaller beneath, underlined by a thin teal rule.
- Set on plain white.

Design consequence: the brand's own teal/blue is the figure mark; the site
palette is built on a warm sage + clay system (calm body-wellness, warm-
grounded) that sits next to, not against, the logo's teal. The logo is
rendered as-is (Astro `<Image>` from the asset, on a light header), never
recoloured. The sage accent is a cousin of the logo's teal-green, so the
header logo and the page accent read as one family rather than a clash.

## Reference anchors (design to this bar, intent only)

Knowledge-anchored taste targets; the extracted DNA is the binding part.

1. **Rela Spa Massage Salon** (awwwards.com/sites/rela-spa-massage-salon),
   warm-neutral wellness palette + an unhurried, generous-whitespace rhythm.
   Take: the calm pacing and warm-neutral surfaces. Leave: the spa-luxury
   gloss (this is a medical-adjacent Praxis, not a spa).
2. **Synergy Physical Therapy** (awwwards.com/sites/synergy-physical-therapy),
   real-photography-over-illustration hero, the body / the practitioner's
   hands as the subject, clinical confidence. Take: photography of real
   therapy (hands on a body in warm daylight), credible not stock-smiley.
3. **Anima Wellness** (awwwards.com/sites/anima-wellness-i-peachweb),
   scroll-storytelling for the care journey, muted-slate calm. Take: the
   journey-told-by-scroll idea, borrowed LIGHTLY, CSS scroll only, no heavy
   WebGL (protect Lighthouse).

## References intentionally NOT borrowed from (anti-direction, §3a)

- The German physio-practice CMS default: a medical-blue gradient hero, a
  stock "smiling therapist with crossed arms" headshot, and a symmetric
  three-card service grid with generic line icons. This is the exact
  template the build rejects.
- The luxury-spa direction (gold-on-charcoal, full-bleed WebGL, candle-lit
  mood). Borrowing Rela's calm but NOT its luxury gloss is what keeps the
  site credible as a medical-adjacent Praxis.

## Anti-patterns (do NOT produce)

- Medical-blue gradient hero, cross / caduceus iconography, headset-smiler
  or crossed-arms stock therapist.
- Symmetric three-card "Leistungen" grid with generic line icons.
- Sterile cool-grey on white. This practice's edge is warmth + hands-on time.
- Heavy WebGL / parallax canvas for the journey (Lighthouse risk). The
  signature is CSS-scroll only.

## Art direction (WHY per call, §3a)

- **Palette, warm sage + clay, no medical blue:**
  paper `#F6F3EC` (warm off-white), surface `#E4DED2` (soft stone),
  ink `#2C322E` (green-near-black, never pure black),
  sage `#6F8F7D` (display/large + fills only), sage-deep `#4F6A57`
  (small accent text, AA), clay accent `#A85734` (warm CTA),
  muted slate `#5C6B73` (calm secondary text), accent-soft `#EAF0EA`.
  WHY: medical blue is the anti-pattern; a warm sage carries calm body-
  wellness, a clay CTA carries the hands-on warmth, and the green-near-black
  ink keeps everything soft. The sage is a deliberate cousin of the logo's
  teal-green so header and accent read as one family.
  WHY these exact hexes: sage `#6F8F7D` on paper is only 3.21:1 (FAILS AA
  small-text), so it is restricted to large display + fills; sage-deep
  `#4F6A57` (5.37:1) carries any small sage-coloured text; the brief's clay
  `#C57B57` gives only 3.31:1 with white (FAILS), so the CTA clay is deepened
  to `#A85734` -> white text 5.15:1 (AA), and clay-on-paper 4.65:1 (AA), so
  the same token is link-safe; muted slate `#5C6B73` is 4.98:1 (AA). All
  ratios computed against paper `#F6F3EC`.
- **Type, Fraunces (display) + Hanken Grotesk (body):**
  WHY: the physio-practice default is a clinical grotesk; a warm soft optical
  serif (Fraunces) IS the differentiator (warmth + care). Hanken Grotesk is a
  friendly humanist sans, legible for long German compound words and umlauts.
  Self-hosted via `@fontsource-variable`, no Google Fonts request. Banned
  defaults (Inter/Roboto/Arial/system/Space Grotesk) are not used as primary.
- **Layout, asymmetric editorial + a quiet data block:**
  WHY: a centered slab + 3-card grid IS the vertical default; asymmetric
  editorial signals "practice takes time with people". Hero = serif statement
  + a real warm therapy photo (Ken Burns drift), not a centered slab. Hours +
  address as a precise quiet data block (the thing patients actually need).
- **Background depth (no flat field, §3a):** the hero photo carries a soft
  paper scrim + a faint SVG fractal-noise grain (~8 percent, soft-light); the
  signature band sits on the sage `accent-soft` wash. No plain solid-colour
  primary section.
- **Motion (§3a quantified table):**
  - Reveal-on-scroll: reuse global.css `[data-reveal]` (custom
    `cubic-bezier(0.22, 1, 0.36, 1)`, ~0.7s but only opacity+transform,
    interruptible, withheld entirely under reduced-motion / no-JS so content
    is never hidden).
  - Hero photo: Ken Burns `kb-drift` (global.css), transform-only,
    reduced-motion -> none.
  - The Behandlungsreise progress rail: CSS scroll-driven only
    (`animation-timeline: scroll()` where supported), `transform`/`opacity`
    on the rail fill, never layout. No JS scroll listener, no WebGL.
    WHY scroll-driven CSS not JS: zero main-thread cost, gate-safe; degrades
    to a static full rail where unsupported (still serene, still correct).
  - Buttons: `:active` `scale(0.97)` press feedback (tips #1); hover lift on
    the global `.btn-primary` (transform+shadow, 0.18s ease). No bouncy
    motion in a medical context (restraint clause).
  - Duration ceiling <= 300ms on interaction transitions; `prefers-reduced-
    motion: reduce` always honoured (global.css base layer neutralises all).

## Bespoke / signature section, "Behandlungsreise" (treatment journey)

A calm vertical scroll spine down the left of the main journey content. A
thin sage progress rail marks the three stages: Beschwerde -> Behandlung ->
Erholung. CSS scroll-driven only (no WebGL, protect Lighthouse): the rail
fill grows with scroll via `animation-timeline: scroll()`, with a static-full
fallback where unsupported and under reduced-motion. Each stage is a calm
text block referencing only sourced service labels. This is the section that
inverts the prospect's likely current failure (a flat undated service list
with no sense of the care path) into a serene, legible journey. Lightweight,
serene, never a theme.

## Imagery plan (per slot, Pexels via fetch-imagery.mjs)

- **hero** (16/9, kenburns): real physiotherapy, a therapist's hands on a
  patient's back/shoulder, warm daylight, calm, NO headset-smiler stock, no
  people staring at camera. Query: "physiotherapist hands treating patient
  back warm daylight calm real therapy".
- **signature** (4/5): close, warm, hands-on, e.g. manual therapy on a knee
  or shoulder; one consistent warm grade. Query: "manual therapy hands on
  knee physiotherapy close warm natural light".
- One consistent warm treatment per brand. No fake team photos. Slots render
  as the honest `ImageSlot` until the pipeline lands the curated photos;
  `src/assets/helmle-physio/` is committed for a hermetic build.
  "Bilder: Pexels" footer credit present.

## Hard data rules (B4)

- Verified verbatim: name, full name, address (Karlstr. 86, 76137 Karlsruhe,
  Südweststadt), phone 0721 3842525, mobile 0152 53687646, email
  info@helmle-physio.de, the 12 services, the current/reduced opening hours,
  the "best reached by phone 08:30 to 12:30" note.
- Unverified -> render inline as `[BITTE PRÜFEN]`, never fabricated:
  Kassen / Privat, team / therapist names, prices.
- Impressum + Datenschutz: legally required, flagged as juristically prepared
  before publication, never faked.
- JSON-LD: `@type` Physiotherapy (a MedicalBusiness subtype), hand-written
  German meta title + description.