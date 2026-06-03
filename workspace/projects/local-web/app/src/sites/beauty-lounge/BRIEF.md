# BRIEF, beauty-lounge (Kosmetik / Nageldesign / Wellness)

Source content: `workspace/projects/local-web/prospects/beauty-lounge/data.md`.
Binding contract for this site's build. Reference-parity against the
anchors below is a definition-of-done gate (skil_web-build quality bar).

## The business

Beauty Lounge Karlsruhe (Inh. Ilona Fait), Amalienstraße 39, 76133
Karlsruhe (Innenstadt-West). A multi-discipline salon: Kosmetik (Gesicht),
Nageldesign, and Wellness/Massage. It does NOT offer Friseur (hair); there
is no haircut, no hair styling anywhere in scope. The current live site is
down (expired SSL certificate), so it could not be read directly;
data_confidence is medium and verified via directories. The pitch: a warm,
credible, multi-discipline shopfront that the broken live site cannot give.

## Wordmark (no logo asset exists)

This business has NO logo asset. There is nothing to sample, no Logo-DNA to
extract. The brand mark is therefore a typeset wordmark: the words
"Beauty Lounge" set in Cormorant Garamond (the display face), used as the
header brand and repeated as the centered wordmark across the hero bands.
WHY a typeset wordmark, not a fabricated logo: inventing a logo would be a
B4 violation (fabricating a brand asset). A confident Cormorant wordmark is
honest, on-brand for luxury-beauty (anchor 3), and trivially replaceable if
the owner later supplies a real mark.

## Reference anchors (design to this bar, intent only)

Knowledge-anchored taste targets. The design DNA extracted below is the
binding part; URLs may be swapped without weakening the bar.

1. **Salon Sona** (awwwards.com/sites/salon-sona): warm-brown + coral on
   white, image-led, oversized editorial wordmark, full-bleed nav. Take:
   the oversized serif wordmark as the brand centrepiece and warm-brown +
   single-coral discipline.
2. **Ever Beauty in every details** (awwwards.com/sites/ever-beauty-in-every-details):
   earthy-brown over cream, hover-triggered service reveals, category-
   organized treatment menu. Take: the hover-reveal multi-discipline panels
   and the category-organized menu (ideal for a three-family salon).
3. **Monotype luxury-beauty serif survey**
   (monotype.com/resources/fonts-and-luxury-brands-beauty): high-contrast
   warm serif AS the luxury-beauty brand voice. Take: this validates
   Cormorant Garamond over a geometric/neutral sans for the brand voice.

**Design DNA to inherit:** warm tactile neutrals (crème + espresso +
mocha), one soft rose-clay accent, oversized high-contrast serif wordmark,
image-led but type-confident, category-organized treatment menu, hover-
reveal discipline panels, warm-real photography (treatment, nail detail,
hot-stone), never headset-smiler stock.

## Anti-patterns (the clichéd vertical template, do NOT produce)

- Cold-luxury black-and-gold "spa template": glossy black, gold foil,
  stock orchid, generic "PAMPER YOURSELF" hero. This salon's edge is warm +
  local + welcoming, the opposite of cold-luxury.
- Purple/lavender gradient "beauty SaaS" hero with rounded-everything cards.
- A hair/Friseur panel or any hair imagery. The salon does not do hair;
  including it would be a fabricated-service B4 violation.
- Symmetric three-card grid with generic line icons for the disciplines.

**References intentionally NOT borrowed from (§3a anti-direction):** the
cold-luxury black-and-gold spa template (named above) is the primary
rejection; naming it sharpens that the chosen anchors carry *warm tactile*
not *glossy luxury*. Second rejection: the lavender beauty-SaaS gradient
aesthetic, which would read tech-startup, not neighbourhood salon.

## Art direction (WHY per call, §3a)

- **Type, Cormorant Garamond (display) + Mulish (body):** high-contrast
  warm serif IS the luxury-beauty brand voice (anchor 3); it is also the
  honest stand-in for the missing logo. WHY not a geometric sans: that is
  the beauty-SaaS anti-direction. Cormorant is thin/high-contrast, so it is
  display-only (wordmark, H1/H2, family headings) at LARGE sizes where the
  thin strokes stay AA-legible; Mulish carries all prose, prices, and labels
  because small Cormorant would fail legibility + AA.
- **Palette, warm neutrals + single rose-clay:** crème canvas #F7F1EA +
  espresso ink #2E2722 + mocha structure #7A6047, with one soft Rose-Clay
  #C98B7A accent and rare Terracotta #B5553F emphasis. WHY warm tactile, not
  black-gold: the positioning is welcoming-local, the explicit inverse of
  the cold-luxury cliché. WHY accent-ink is Espresso (dark) on the rose-clay
  CTA, not white: Rose-Clay is light, so white-on-clay fails AA (~2.2:1);
  Espresso-on-clay clears it (~5.9:1). See theme.css per-token AA notes.
- **Layout, multi-discipline reveal bands + category menu:** centered slab
  + 3-icon grid IS the vertical default. Hover-reveal discipline bands
  (Ever Beauty) + a category-organized treatment menu signal a real
  multi-discipline salon, not a CMS template, and solve the overseeability
  cue (the visitor sees all three disciplines at once).
- **Motion (§3a quantified):** reveal-on-scroll via the shared `data-reveal`
  (custom cubic-bezier, ~0.7s opacity/transform only, reduced-motion
  honoured by global.css). The signature hover-reveal uses `transform` +
  flex-basis on a custom cubic-bezier, <=300ms, `scale(0.97)` button press,
  per-element origin, interruptible. WHY restrained: an unhurried salon
  mood (Kowalski restraint clause) wants calm reveals, nothing bouncy.
- **Background depth:** the soft rose-clay reveal-panel tints + the crème
  surface gradient + warm imagery satisfy the no-flat-field rule; no plain
  white primary section.

## Bespoke / signature section (so it never reads as a theme)

A multi-discipline tri-band hero for the salon's three REAL service
families (Gesicht & Kosmetik / Nageldesign / Wellness & Massage). Soft-
cornered full-height image panels under a crème-tinted overlay; on desktop,
hovering one panel widens it and reveals its treatment list + a
"Termin buchen" CTA while the others recede; the Cormorant "Beauty Lounge"
wordmark sits centered across all three. On touch/mobile the panels stack
and show their lists statically (no stuck hover). Below it: a quiet
Preisliste table (every price `[BITTE PRÜFEN]`) and a sticky warm-clay
booking bar with the phone number. This inverts the broken live site's
single biggest failure (visitors cannot even reach it, let alone see what
the salon offers) into instant multi-discipline overseeability. NO hair
panel: the three bands are exactly the three real families.

## Imagery plan (per slot, Figure falls back to honest slot until fetched)

One consistent warm, tactile grade. No people's faces, no fake team, no
headset-smiler stock.

- `hero-gesicht` (landscape): elegant facial / skincare treatment, warm
  soft light, close up, no faces.
- `hero-nageldesign` (portrait): manicure / nail detail, elegant hands,
  warm tactile close up.
- `hero-wellness` (portrait): hot-stone / wellness, warm stones on linen,
  calm still life.
- `signature` (landscape): warm tactile studio atmosphere, lamplight on a
  clay wall, no people.

Queries recorded in `imagery.json`. Add matching `SLOTS` entries to
`app/scripts/fetch-imagery.mjs` and run `npm run imagery` before deploy.

## Hard data rules (B4)

data_confidence is medium: verified via directories, the live site is down
(expired SSL cert) and could not be read directly. Verified verbatim:
name + owner (Ilona Fait), address, phone, hours, the service list.
Unverified -> render `[BITTE PRÜFEN]` inline, NEVER fabricated: E-Mail,
ALL prices, any staff beyond the owner. NO hair / Friseur anywhere (the
salon does not offer it). JSON-LD `@type` BeautySalon, hand-written German
meta. Impressum + Datenschutz flagged as legally required, not faked.
