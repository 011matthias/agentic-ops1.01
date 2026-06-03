# BRIEF: Michael Meinzer Malerfachbetrieb (meinzer-maler)

Bespoke demo site for a real Karlsruhe-Knielingen Malerfachbetrieb. The
direction is "Werkstatt-warm, not industrial-cold": a solid, trustworthy,
hands-on trades site that feels like warm workshop daylight, with copper
used sparingly like a signature stamp.

## Logo-DNA

Real logo file: `app/src/assets/meinzer-maler/logo.jpg` (sampled visually).

- **Shape / mark:** three painter-stroke "M" shapes on the left, each a
  rough, hand-painted brush-stroke letterform (not a clean geometric M).
  They read as three quick strokes of a loaded brush. To their right sits
  the wordmark.
- **Colours in the mark:** the three Ms are primary blue, yellow and red,
  flat (no gradients). These are bright sign-paint primaries.
- **Type in the wordmark:** "Michael Meinzer" set on two lines in a heavy
  dark-grey bold sans (near-black warm grey, very bold). Beneath it
  "MALERFACHBETRIEB" in tracked caps, with "FACH" bolded inside the word.
- **Ground:** white / no background.

**What the DNA tells the site.** The logo's own typography is a heavy bold
sans in dark warm grey, so the site's INK (`#232a2e`) and the body sans
echo the wordmark directly. The brush-stroke Ms say "real brush, real
hand", which licenses the craft/heritage slab display (Bitter) and the
hand-worked copper-stamp motifs. The bright primary trio (blue/yellow/red)
is left to the LOGO ALONE: reproducing three loud primaries across the
page would fight the warm, calm mood, so the page reads in warm
neutrals + a single copper signature, letting the multicolour logo be the
one bright punctuation mark. This is deliberate: the logo is the colour
accent, the page is its quiet frame.

## Reference anchors (design intent only; patterns, not content)

1. **Plumbly** (awwwards.com/sites/plumbly) - typography-forward trades
   site, warm not industrial. BORROW: oversized slab headline + a
   full-bleed hero scene; type as the primary design feature so the page
   stands on its words before any photo lands.
2. **SPS Plumbers** (awwwards.com/sites/sps-plumbers) - trust signals.
   BORROW: a trust block high on the page (years-in-trade stat, marked
   [BITTE PRÜFEN] since unverified; a workmanship/Festpreis guarantee
   callout; Meister credential surfaced early).
3. **Plumber 128** (awwwards.com/sites/plumber-128) - practical local-
   service IA. BORROW: a structured service hierarchy and a mobile-first
   section order (hero, then services, then the trust/process band, then
   hours/contact).

## References intentionally NOT borrowed from (the rejection)

- **Generic "trade-blue + checkmark-bullets + headset stock-photo"
  template.** Naming the rejection sharpens the chosen direction: the
  anchors above are warm and type-led; the cold-blue plumber template is
  exactly the cliché this BRIEF exists to avoid. No sterile blue primary,
  no stock smiling team in branded polos, no green tick bullet lists.
- **Thin-grotesk SaaS minimalism** (the Inter/Space-Grotesk tech look).
  A heritage handwork trade should feel solid and worked, not like a
  startup landing page; hence the slab display, not a thin sans.

## Anti-patterns (do not produce)

- Sterile plumber-blue as the primary brand colour.
- Stock photos of smiling teams, headsets, handshakes, or fake "our crew".
- Green-tick bullet lists of services.
- Flat solid-colour sections (background-depth rule); every primary band
  carries a tint, a paper-grain, or a photo.
- Inter / Roboto / Arial / Space Grotesk / system stacks as display type.
- Any em-dash (U+2014), `&mdash;`, or ` -- ` typographic substitute.
- Invented prices, email, team size, or years in trade.

## Art direction (palette / type / layout, with articulated WHY)

**Palette** (full tokens + WHY live in `theme.css`; summary here):
- Paper off-white `#F4F1EA`. WHY: warm workshop daylight ground, not the
  sterile white of the cold-blue template.
- Ink deep slate `#232A2E`. WHY: echoes the logo wordmark's heavy dark-grey
  sans; ~13.2:1 on paper, calm near-black that stays warm.
- Accent copper `#A8551F` (deep) / `#C2683A` (bright display). WHY: tool-
  handle warmth is the single differentiator versus plumber-blue; the deep
  copper passes AA for small text and for white-on-copper buttons, the
  bright copper is reserved for large numerals (AA-large 3:1).
- Steel-blue `#3E5C6E`. WHY: technical/utility cue (the process brackets)
  without becoming the loud primary blue the rejection bans.
- Trust green-grey `#4C5B48`. WHY: calm reassurance colour for the
  guarantee callouts (Festpreis, sauber, pünktlich), AA-safe.
- Hairline warm grey `#D9D2C5`. WHY: soft 1px joins, decorative only.

**Type:**
- Display: **Bitter Variable** (slab serif). WHY this, not the default: a
  slab carries heritage/craft warmth and reads solid and hand-worked, which
  matches the brush-stroke logo; a thin grotesk would read tech-startup,
  the exact anti-pattern. Self-hosted via `@fontsource-variable/bitter`.
- Body: **Source Sans 3 Variable** (humanist sans). WHY: precise but
  approachable, and it echoes the logo wordmark's bold sans; it offers
  tabular figures for the process strip and hours table (alignment matters
  in a "we measure carefully" trade). Self-hosted via
  `@fontsource-variable/source-sans-3`.
- Banned defaults (Inter/Roboto/Arial/Space Grotesk/system) are NOT used.

**Layout:**
- Type-led full-bleed hero (Plumbly pattern): a heavy slab headline carries
  the page even before the Ken-Burns Fassade photo lands. WHY: the site
  must look intentional with the honest image slot in place, never depend
  on a photo to not look broken.
- Mobile-first section order (Plumber 128 pattern): hero, services
  (editorial hairline list, numbered, not a tick-bullet grid), the bespoke
  "Meisterbrief Werkbank" signature band, then hours + contact.
- Generous whitespace, heavy slab headings, copper used sparingly as a
  signature stamp (the offer/accent), warm neutrals everywhere else.

**Motion (per skil_web-build §3a, quantified table):**
- Scroll reveals via the shared global.css `[data-reveal]` layer: custom
  `cubic-bezier(0.22, 1, 0.36, 1)`, ~700ms opacity + translateY only
  (composite-only, no layout/paint), starts from `translateY(22px)` (never
  `scale(0)`), interruptible, fully neutralised under
  `prefers-reduced-motion: reduce` and no-JS (content never left hidden).
- Hero photo: Ken-Burns slow drift (shared `.is-kenburns`, 26s, transform
  only, reduced-motion safe). NOT DepthHero (no WebGL budget spent here).
- Buttons: `transform`/`box-shadow` transitions from the shared `.btn`
  (<=180ms ease) plus `scale(0.97)` on `:active` for press feedback.
- WHY the custom easing, not built-in `ease-out`: Kowalski tip #4, built-in
  ease-outs are "usually not strong enough"; the custom curve gives the
  premium settle the trade-trust mood wants.

**Background depth (no flat fields):** the hero carries the photo + a
warm scrim + a faint paper-grain SVG layer; the signature band sits on the
`--color-accent-soft` tinted workbench ground with a CSS engineering-grid
overlay. No primary section is a flat solid colour.

## Bespoke signature section: "Meisterbrief Werkbank"

A tactile paper / engineering-grid band that makes the German trades
promise (Festpreis, sauber, pünktlich) visual. Pure CSS, no image:

- A faint blueprint/engineering grid background on the tinted ground.
- A numbered 1-2-3-4 process strip: **Anfrage, Vor-Ort-Termin,
  Festpreis-Angebot, Saubere Ausführung**. Big slab-serif numerals
  (display copper) over one-line humanist-sans descriptions.
- Copper bracket lines (CSS `::before`/`::after` corner brackets, steel-blue
  on desktop) connecting the steps, like a draughtsman's dimension marks.
- A small "Meisterbetrieb" seal at the end of the strip (CSS-drawn copper
  stamp ring), tying the promise to the Meister credential.

WHY: it inverts the current trades-site failure (a flat PDF-tier service
list with no proof of HOW the work is run). It turns the intangible "we
work cleanly and to a fixed price" into a scannable, tactile process the
prospect can see, which is the SPS-Plumbers trust-block lesson made
bespoke for a German Handwerksbetrieb.

## Hard data rules (B4)

Source of truth: `prospects/meinzer-maler/data.md`. Verified facts (name,
owner Michael Meinzer, Malermeister, address Saarlandstr. 84 / 76187
Karlsruhe-Knielingen, phone 0721 9702290, fax 0721 9702292, the Mo-Fr
07-17 / Sa 07-12 hours, and the six verbatim services) render directly.
Everything unverified renders as the `CHECK = "[BITTE PRÜFEN]"` chip and is
NEVER invented: e-mail, prices/Festpreis figures, years in trade, team
size, certifications. The signature band describes the Festpreis PROCESS
qualitatively (no number). JSON-LD `@type`: `HousePainter`.
