# BRIEF — pronto-pronto (Pizza Heimservice & Restaurant)

Source content: `workspace/projects/local-web/prospects/pronto-pronto/data.md`.
Binding contract. Reference-parity is a definition-of-done gate.

## The business

Pronto-Pronto Heimservice und Restaurant, Moltkestr. 79a, Karlsruhe.
Pizza/Pasta/Burger/Calzone and more, delivery to 19 zones, 10% online-order
discount, MBW €0,00. Current site: dense text, dated layout, no dish prices
on the homepage, weak photography, no CTA hierarchy. Competing
Lieferando-style pages all look identical.

## Logo-DNA (named anchor for the comparative-judgment gate)

Source file: `app/src/assets/pronto-pronto/logo.png` (560x370, transparent).
All hex values below are SAMPLED from that file (dominant-colour pass over
7,482 opaque pixels), not guessed. Where they correct the original romantic
brief read, that is noted.

- **Palette (sampled, with centroids):**
  - Ivory / cream (the script wordmark + the chef figure): `#FDFCFA`.
    NOTE: the brief called the script "red"; the script is ivory. The red
    belongs to the car.
  - Terracotta / burnt-orange banner family (the ribbon under the mark):
    `#EB880F` (bright), `#D26F08` (mid), `#C45303` and `#BA4B01` (burnt
    sienna shadow). THIS warm earthy orange is the accent to mine, and it
    is distinct from the neon delivery-app orange the hero currently uses.
  - Brass / amber (frame + car-body warmth): `#CE8504`, `#B16F04`.
  - Acid yellow-green disc / halo behind the chef: `#D6E505`, `#CCD505`.
    NOTE: the brief read this as "brass and gold"; sampled, it is a
    chartreuse yellow-green. It is the ONE element that fights a warm-
    vintage palette. Decision: it stays on the logo, it is NOT propagated
    into the site palette (see theme.css). Pulling acid-green into a warm-
    terracotta scheme would re-introduce exactly the clash this rework
    exists to remove.
  - Pillar-box red (the illustrated car): `#D20000`.
  - Dark espresso brown (every keyline + illustration shadow + wear):
    `#5A2A02`. This is the natural warm-dark base hue, not a neutral
    charcoal.
- **Type personality:** the wordmark is a bold brush-script, heavy weight,
  right-leaning, ivory with a dark keyline; 1970s-80s hand-painted
  pizzeria / gelateria sign-lettering. "HEIMSERVICE" is a condensed bold
  all-caps grotesque, arched. Implied companion: a warm humanist serif or a
  sturdy condensed display for headings, a calm humanist sans for body.
- **Era / mood:** Era is late-1970s to 1980s European neighbourhood
  Heimservice/pizzeria. Mood is nostalgic, casual, unpretentious family
  warmth, not luxury and not editorial-minimal.
- **Shape vocabulary:** elliptical badge, arched ribbon banner with notched
  ends, rounded cartoon illustration, thick dark keylines around every
  shape.
- **Implied textures:** flat screen-print / decal finish with hard
  outlines; the era it evokes is the printed paper menu and the
  hand-painted shop sign. Paper grain + a faint ink/wear texture are the
  honest texture cues to bring into the site.

**Register caveat (surfaced, not blocking):** the real mark is warm-vintage
but KITSCH-CARTOON (mascot chef + car), not elegant-heritage-editorial. The
rework anchors warm-vintage-Italian *casual* (signage / trattoria), not
luxury editorial, so the hero does not "out-dress" the logo and re-open the
mismatch from the other side.

## Reference anchors (design to this bar)

REPLACED 2026-06-01. The prior anchors (&pizza, Pizza Pilgrims, Roberta's)
pulled toward bold-modern-appetite, which is what made the hero fight the
logo. These three were found and live-verified (workflow
`pronto-reference-anchors`, 9/12 candidates verified reachable + genuinely
warm-vintage) to match the Logo-DNA above. Each carries the ONE element we
borrow.

1. **Re Pomodoro** (fontsinuse.com/uses/72587/re-pomodoro) [signage] WHY:
   the closest single match, warm red/yellow into terracotta, a brand built
   to recreate "ancient hand-made labels" on circular wood-fired-oven
   compositions, casual-pizzeria not luxury. BORROW: the hand-made-label
   lockup, a sturdy display logotype with a brush-script flourish for the
   name, sitting on a warm circular badge.
2. **HT Pizzeria** (creativemarket.com/dharmatype/2068816-HT-Pizzeria)
   [signage] WHY: a script face literally drawn from hand-painted 1950s
   Italian shopfront and wall-advert lettering, the exact source register
   of the logo's own brush-script wordmark, zero luxury/neon affect.
   BORROW: the hand-painted brush-script as the single heritage accent for
   the name/hero, held apart from the calm body face.
3. **Landini Brothers** (landinibrothers.com) [awards/getBento] WHY:
   "Since 1979" italic warm serif headlines + brass/amber (~#C8A04F) on an
   espresso-dark ground, maps almost exactly onto this site's brass
   (`#B16F04`) token, the Fraunces serif, and the espresso base. BORROW:
   the brass accent + italic heritage serif + a "Since {year}" nostalgia
   line as the family-heritage signature. (Its mood skews upscale-Tuscan;
   take the accent and serif, not the restraint.)

**Intentionally NOT borrowed (anti-references, per skill 3a):**
- **Pizza Pizza** (awwwards.com/sites/pizza-pizza), cold-modern editorial-
  minimal, one coral accent on neutral white. This is the studio-portfolio
  register the rework exists to leave; the single red hue is the only
  overlap.
- The site's OWN previous direction (neon delivery-app orange `#e0612b` +
  Space Grotesk grotesk). Documented here so it is not re-introduced.

**Design DNA to inherit:** warm-vintage Italian neighbourhood pizzeria;
espresso-warm dark ground with paper grain (not flat charcoal), terracotta
+ brass + ivory drawn from the logo, a warm humanist serif voice (Fraunces),
the 10% offer as a vintage stamp. KEEP the build's modern strengths: real
food-photo hero, fast order CTA above the fold on mobile, the **searchable**
client-side menu (not a PDF), delivery zones as scannable chips.

## Anti-patterns (do NOT produce)

- The generic Lieferando/aggregator template: pure red `#d6312a`, tomato
  clipart, stocky pizza-on-wooden-board banner, undifferentiated.
- Wall-of-text menu with no prices and no search.
- CTA buried below dense paragraphs.

## Art direction

- **Type:** Space Grotesk Variable (display, bold geometric, energetic) +
  Inter Variable (body/UI). Tight punchy H1.
- **Palette (theme.css tokens):**
  - paper `#1c1a17` (warm charcoal, appetite works on dark) ·
    surface `#262220` · ink `#f4efe7`
  - muted `#a99e8d` · line `#3a3430`
  - accent `#e0612b` (warm ember, NOT generic delivery-red) ·
    accent-ink `#1c1a17`
- **Layout:** food-photo-led dark editorial. Hero = full-bleed appetite
  image + tight headline + order CTA + the 10% offer chip. Menu =
  searchable, categorized, price column (prices `[BITTE PRÜFEN]`).
  Delivery zones as a wrap of chips.
- **Motion:** snappy reveal, hover lift on dishes; reduced-motion honored.

## Articulated-WHY (§3a)

Each art-direction call needs a one-line "why this, not the default".

- **Type · Space Grotesk + Inter [§3a-FLAGGED]:** Space Grotesk
  appears on §3a's typography ban list as a frequent AI-default.
  Justification for retaining it here: the brand direction (&pizza,
  Pizza Pilgrims, Roberta's) is geometric and energetic, and Space
  Grotesk's tight geometric weight fits the appetite-first dark
  editorial. **Owner action:** review §3a (2026-05-26 update) and
  decide whether a more distinctive alternative (Plus Jakarta Sans,
  Geist Sans, Cabinet Grotesk, Editorial New) better serves the
  appetite-first direction. Resolve before the next live revision.
- **Palette · warm charcoal + warm ember (NOT delivery-red):** the
  generic delivery-red `#d6312a` is the Lieferando/aggregator
  signature. Warm charcoal background + warm-ember accent inverts the
  aggregator template and lets food photography do the work.
- **Layout · full-bleed appetite hero + searchable menu:** the
  searchable client-side menu IS the inversion of the current site's
  PDF-tier failure. The 10% offer + MBW €0 chips above the fold are
  the headline assets the current site buries.
- **Motion · snappy reveal + hover lift on dishes:** §3a rules apply:
  custom `cubic-bezier` ease-out, ≤300ms (180ms preferred over 300ms
  for perceived responsiveness in a food-order context),
  `transform`+`opacity` only. Press feedback uses `scale(0.97)` on
  `:active` per §3a button-press rule. Initial scale on reveal starts
  from `0.95`+, never `scale(0)`. `prefers-reduced-motion` honoured.
- **Anti-references:** Lieferando.de + the generic
  delivery-aggregator template (named explicitly in the
  "Anti-patterns" block above) ARE the §3a anti-reference direction.
  Second named anti-reference: `[BITTE PRÜFEN — owner to optionally
  add one local Karlsruhe pizzeria whose site direction we are also
  rejecting]`.

## Bespoke / signature section

"Speisekarte" — a real client-side searchable menu (instant filter over
categorized dishes). This is the precise inversion of the current site's
biggest failure (no prices, no search, PDF-tier). Plus a "Liefergebiet"
band: 19 zones as scannable chips with the MBW €0,00 / 10% online facts.

## Imagery plan (per section)

- Hero: AI-generated appetite-grade pizza/food atmosphere on dark — no
  people, no clipart.
- Menu/feature shots: curated Unsplash/Pexels — real pizza, pasta, calzone;
  one consistent warm-on-dark grade.

## Hard data rules (B4)

Individual dish prices and email unverified → `[BITTE PRÜFEN]` in the
price column, never invented. Facts that ARE sourced (19 zones, hours,
payment methods, 10%/€0,00, socials) used verbatim. Restaurant JSON-LD
with delivery method, hand-written meta.

## Comparative-judgment (2026-06-01 cohesion rework)

Compared: the new hero (local build screenshot), the logo
(`app/src/assets/pronto-pronto/logo.png`), and reference anchor Landini
Brothers (live screenshot).

Does the hero feel like it could come from the same brand as the logo?
Yes, now. Before, the espresso/terracotta/brass/ivory palette is sampled
directly from the logo, so the hero ground is the logo's own keyline-brown,
the accent is the logo's own banner-terracotta, and the stamp frame is the
logo's brass. The Fraunces display (soft + wonk axes) speaks the same warm
hand-painted-sign era as the logo's script, where the old Space Grotesk
spoke "modern tech". The 10% offer is now a rotated gummed stamp echoing the
logo's ribbon banner, not an app pill. The two no longer make contradictory
brand promises in the first 600ms; they both say handcrafted-warm-family.

Against the Landini quality bar: the hero shares Landini's espresso ground,
brass accent, and warm heritage-serif headline. Mine is deliberately warmer
and more saturated (terracotta + a warm pizza photo) where Landini is
restrained upscale-Tuscan (B&W, cream, negative space). That divergence is
correct, not a miss: the logo's register is casual neighbourhood pizzeria,
not fine dining, so borrowing Landini's accent + serif while staying warmer
is the intended read.

What still reads not-fully-vintage, honestly: (1) the logo's acid-chartreuse
disc is the one element outside the warm scheme; it is a logo property, kept
on the logo per the Logo-DNA decision and softened by the header
desaturation filter, but it remains the least-integrated pixel on the page.
(2) The layout grid + the searchable menu stay crisp-modern by design (the
brief's "keep the modern strengths" constraint), so the page is warm-vintage
in skin, modern in structure, intended. (3) Fraunces is warm-editorial
rather than a literal painted brush-script; a true HT-Pizzeria-style script
on the wordmark would push further but is not a free/installed face, logged
as a future option, not done.

Verdict: PASS. Same-brand cohesion achieved, warm-vintage register
established, palette + type discipline at the reference bar. The one residual
clash (chartreuse) belongs to the logo asset, not the hero, and is out of
scope to change (the logo is the immovable B4 asset).
