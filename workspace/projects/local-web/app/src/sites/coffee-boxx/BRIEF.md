# BRIEF — coffee-boxx (Café)

Source content: `workspace/projects/local-web/prospects/coffee-boxx/data.md`.
Binding contract. Reference-parity is a definition-of-done gate.

## The business

Coffee Boxx, Moltkestr. 44, Karlsruhe (a second Kaiserstr. 93 location is
`[BITTE PRÜFEN]`). Marco + team. Kaffeespezialitäten, Panini, Kuchen.
Current site: "Meinewebsite" builder, seasonal Easter text frozen as the
homepage, menu buried in a PDF, no socials, no menu visibility. Imagery is
the single biggest quality lever for a café — this build leans on it hard.

## Reference anchors (design to this bar)

Knowledge-anchored taste targets; design DNA below is the binding part.

1. **Onyx Coffee Lab** (onyxcoffeelab.com) — award-tier roaster site:
   characterful display type, confident editorial layout, product/space
   photography front and centre. The bar for "independent coffee, done well".
2. **Sey Coffee** (seycoffee.com) — restrained, warm minimalism; lets
   photography and type carry it.
3. **Verve Coffee** (vervecoffee.com) — menu/retail as first-class
   content, warm palette, strong grid with editorial breaks.

**Design DNA to inherit:** warm independent-roaster editorial — big
characterful serif display, paper-grain warmth, real coffee + space
photography offset in an editorial gallery (not a symmetric grid), the menu
treated as real indexable HTML with leader rows, location + live open-state
above the fold.

## Anti-patterns (do NOT produce)

- "Meinewebsite"/Wix-builder look: centered everything, default sans, stock
  latte-art-on-wood banner with a quote overlay.
- Menu as a PDF link or an image. It must be real HTML, scannable.
- Generic café-brown corporate gradient.

## Art direction

- **Type:** Fraunces Variable (display, high-contrast characterful serif,
  optical sizing) + Inter Variable (body/UI). Oversized warm H1.
- **Palette (theme.css tokens):**
  - paper `#f4ece0` (warm cream) · surface `#fffaf2` · ink `#2a201a`
  - muted `#7a6a59` · line `#e3d6c4`
  - accent `#b5562b` (burnt terracotta) · accent-ink `#fff7ee`
  - subtle grain texture overlay on hero/bands.
- **Layout:** editorial magazine. Offset asymmetric gallery (varied
  aspect ratios), big type, generous negative space. Menu = typeset
  list with dotted leader rows to prices, grouped by category.
- **Motion:** gentle parallax-free reveal; reduced-motion honored.

## Articulated-WHY (§3a)

Each art-direction call needs a one-line "why this, not the default".

- **Type · Fraunces + Inter:** Fraunces' high-contrast characterful
  serif with optical sizing IS the *independent-roaster* signature
  (Onyx, Sey, Verve all lean characterful serif). The default café
  type is a soft script or default sans; Fraunces' edge is what makes
  the site read as award-tier instead of Meinewebsite.
- **Palette · warm cream + burnt terracotta:** the café-brown
  corporate gradient is the cliché. Warm cream paper + a single
  burnt-terracotta accent reads as *third-wave roaster*, not delivery
  franchise.
- **Layout · offset asymmetric gallery + leader-row menu:** menu as
  PDF/image is the failure being inverted. Leader rows turn the menu
  into the signature feature, not buried content. Asymmetric gallery
  beats symmetric grid for a magazine feel.
- **Motion · gentle reveal, no parallax:** §3a rules apply: custom
  `cubic-bezier` ease-out, ≤300ms, `transform`+`opacity` only,
  `prefers-reduced-motion` honoured. Restraint clause: one
  well-orchestrated reveal beats scattered micro-interactions for
  café context (Kowalski's `…/you-dont-need-animations`).
- **Anti-references:** the "Anti-patterns" block above (Meinewebsite /
  Wix builder default, latte-art-on-wood stock banner, brown
  corporate gradient) IS the §3a anti-direction list. One named
  anti-reference site: `[BITTE PRÜFEN — owner to name 1-2 specific
  Karlsruhe café sites whose direction we are intentionally rejecting,
  e.g. a competitor with a Wix template]`.

## Bespoke / signature section

"Die Karte" — the menu as the hero feature, the exact thing the current
site hides. Typeset, categorized, leader rows, real HTML. Plus an open-now
state computed from opening hours (Mo–Fr 07:30–19:00, Sa–So 10:00–18:00)
shown above the fold next to the address. This directly inverts the
current site's biggest failure.

## Imagery plan (per section)

- Hero: AI-generated warm coffee atmosphere / steam / texture — no people.
- Gallery band: curated Unsplash/Pexels — espresso, café interior,
  panini/Kuchen; one consistent warm grade. No fake staff portraits.
- Marco + team is real (site copy) but no faces invented.

## Hard data rules (B4)

Exact menu items + prices, email, socials, primary-location decision are
unverified → `[BITTE PRÜFEN]` placeholders in the menu structure, never
invented prices. CafeOrCoffeeShop JSON-LD, hand-written meta.
