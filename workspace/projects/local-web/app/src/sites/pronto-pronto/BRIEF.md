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
