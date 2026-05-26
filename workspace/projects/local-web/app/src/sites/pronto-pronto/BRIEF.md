# BRIEF — pronto-pronto (Pizza Heimservice & Restaurant)

Source content: `workspace/projects/local-web/prospects/pronto-pronto/data.md`.
Binding contract. Reference-parity is a definition-of-done gate.

## The business

Pronto-Pronto Heimservice und Restaurant, Moltkestr. 79a, Karlsruhe.
Pizza/Pasta/Burger/Calzone and more, delivery to 19 zones, 10% online-order
discount, MBW €0,00. Current site: dense text, dated layout, no dish prices
on the homepage, weak photography, no CTA hierarchy. Competing
Lieferando-style pages all look identical.

## Reference anchors (design to this bar)

Knowledge-anchored taste targets; design DNA below is the binding part.

1. **&pizza** (andpizza.com) — bold, appetite-first, confident type and
   motion without the generic pizza-red template.
2. **Pizza Pilgrims** (pizzapilgrims.co.uk) — warm, characterful, real
   food photography hero, energetic but crafted.
3. **Roberta's** (robertaspizza.com) — editorial food brand; proves a
   pizzeria can look designed, not like a delivery aggregator.

**Design DNA to inherit:** appetite-driven, real food photography hero,
fast clear order CTA above the fold on mobile, a **searchable** menu (real
client-side filter, not a PDF), delivery zones as scannable chips, energetic
but crafted typography. The 10% online offer is a headline asset.

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
