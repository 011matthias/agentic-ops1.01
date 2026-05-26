# BRIEF — praxis-uslu (Hausarztpraxis)

Source content: `workspace/projects/local-web/prospects/praxis-uslu/data.md`.
Binding contract for this site's build. Reference-parity against the
anchors below is a definition-of-done gate (REBUILD-SPEC quality bar).

## The business

Praxis Dr. med. Sema Uslu, Fachärztin für Allgemeinmedizin, Karlsruhe-
Mühlburg. Allgemeinmedizin, Notfallmedizin, Naturheilverfahren, Akupunktur.
Current site (praxis-uslu.de) host did not respond — effectively no web
presence. The pitch writes itself; the demo must look like a practice that
takes its time with people.

## Reference anchors (design to this bar)

Knowledge-anchored taste targets — the design DNA extracted below is the
binding part; the human may swap specific URLs without weakening the bar.

1. **One Medical** (onemedical.com) — calm clinical, generous whitespace,
   humanist sans, warm not sterile. Take: trust without medical-blue cliché.
2. **Parsley Health** (parsleyhealth.com) — editorial wellness, soft warm
   palette, large serif headlines, real human warmth in imagery.
3. **Maven Clinic** (mavenclinic.com) — structured care information that
   stays soft; clear hierarchy for services without feeling like a CMS.

**Design DNA to inherit:** editorial-calm, paper-warm surfaces, one organic
accent (sage/eucalyptus), humanist serif display + clean sans body, photography
that is warm and real (light through a window, hands, the space — never a
headset-smiler or blue-gradient template), credentials and languages surfaced
as trust signals, emergency numbers explicit.

## Anti-patterns (the clichéd vertical template — do NOT produce)

- Medical-blue gradient hero, caduceus/cross iconography, stock doctor in
  white coat with crossed arms.
- Symmetric three-card "Leistungen" grid with generic line icons.
- Sterile cool-grey on white. This practice's edge is *warmth + time*.

## Art direction

- **Type:** Newsreader Variable (display, warm humanist serif) + Inter
  Variable (body/UI). Large editorial H1, comfortable measure (~62ch).
- **Palette (theme.css tokens):**
  - paper `#f6f3ec` · surface `#fffdf9` · ink `#23211d`
  - muted `#6b6459` · line `#e4ddcd`
  - accent `#5c7a63` (eucalyptus) · accent-ink `#ffffff`
- **Layout:** asymmetric editorial. Hero = serif statement + practice
  photo treatment, not a centered slab. Services as an editorial list
  with hairline rules, not a card grid. Hours + address as a quiet
  precise data block (the thing patients actually need).
- **Motion:** minimal, reduced-motion honored. Subtle reveal on scroll
  only; nothing bouncy in a medical context.

## Articulated-WHY (§3a)

Each art-direction call needs a one-line "why this, not the default".

- **Type · Newsreader + Inter:** humanist serif carries *editorial
  calm and warmth* (the practice's edge over the medical-blue cliché).
  The default for German Hausarzt sites is a clinical sans, so a serif
  display IS the differentiator. Inter for body sits in supporting role
  only; the display face carries the brand.
- **Palette · paper + eucalyptus, no blue:** medical-blue is the
  anti-pattern. Warm paper + one organic sage accent communicates
  *time and warmth*; that is the explicit positioning vs the cliché.
- **Layout · asymmetric editorial:** centered slab + 3-card services
  grid IS the vertical default. Asymmetric editorial signals *practice
  takes time with people*, not *CMS template*.
- **Motion · scroll-only reveals:** §3a rules apply: custom
  `cubic-bezier` ease-out, ≤300ms, `transform`+`opacity` only,
  `prefers-reduced-motion` honoured. Restraint clause: no hover-lift
  interactions in a medical context (services list uses hairline rules,
  not interactive cards) — Kowalski's
  `…/you-dont-need-animations`.
- **Anti-references:** the "Anti-patterns" block above (medical-blue
  hero, caduceus iconography, headset-smiler stock) IS the §3a
  anti-direction list. One named anti-reference site: `[BITTE PRÜFEN —
  owner to name 1-2 specific Hausarzt sites whose direction we are
  intentionally rejecting, e.g. a jameda/doctolib profile page or a
  local competitor]`.

## Bespoke / signature section (so it never reads as a theme)

"In der Praxis" — a calm editorial band: warm imagery + a short first-person
note on the practice's approach (time, Naturheilverfahren alongside
schulmedizinische Versorgung), plus surfaced credentials and spoken
languages. This is the section that signals *practice with time*.

## Imagery plan (per section, both-sourcing per locked decision)

- Hero: AI-generated warm atmosphere (light, calm interior texture) — no
  people. Curated stock fallback: warm clinic/daylight interior.
- "In der Praxis": curated Unsplash/Pexels — warm consultation space /
  hands / daylight; one consistent warm grade. No fake team photos.
- Never invent staff. Team/MFA names are `[BITTE PRÜFEN]` (data.md).

## Hard data rules (B4)

Email, team members, Kassen list are unverified → render as `[BITTE PRÜFEN]`
inline, never fabricated. Emergency: 116117 (Bereitschaft) / 112 (Notruf)
explicit. Impressum + Datenschutz flagged as legally required, not faked.
MedicalClinic / Physician JSON-LD, hand-written meta.
