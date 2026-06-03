# Module: CONCEIVE

Load at **Build Procedure step 1**. This is where award-tier quality is decided:
the BRIEF and its art direction are the binding contract everything downstream
matches. Detail behind Definition-of-Done items 1, 5, 6, 12, 16-19, 21, 22 in
`SKILL.md`.

The quantified motion table lives in `references/motion-craft.md`; this module sets
the aesthetic direction, that reference sets the motion envelope.

## 0. The two standards (List A north-star, List B craft)

These sites are **cold walk-in pitch instruments** shown to a non-technical local
owner (and built for their non-designer customers), not portfolio pieces. The
north-star test is therefore NOT "would a designer admire this" but **"would THIS
owner pay for it, and would their customer act on it."** (Owner directive 2026-06-03;
see incidents.md → 2026-06-03.) Everything below this line operationalizes the two
lists; Definition-of-Done items 16-22 in `SKILL.md` make them checkable.

**List A — contextual / strategic (why a build is right *for this job*):**

1. **Recognition before impression.** The owner thinks "that's us," not "that's
   slick." Bespoke per business; across the set the sites must NOT read as one
   template (the per-SET diversity gate, below).
2. **Register fit.** Speak the trust vocabulary of the trade: calm-care for doctor /
   physio, solid "shows up on time, leaves it clean" for trades, tactile warmth for
   beauty. Wrong register destroys trust faster than weak craft.
3. **Don't out-dress the business.** The best honest version of THIS business;
   aspirational but recognisable, never a fancier different business.
4. **Findability is aesthetic.** Phone, hours, what-they-do reachable in ~2s on mobile
   for older eyes; click-to-call; WCAG AA is load-bearing, not theatre.
5. **Authenticity / absence of tells.** No stock headset-smilers, no gradient
   placeholders, no invented facts; honest gaps surfaced quietly (never a raw
   `[BITTE PRÜFEN]` sentinel on a pitchable page — see `modules/DATA.md`).
6. **Type + colour are the high-leverage differentiators** on content-light sites.
7. **"It just works"** — instant load, crisp images, no broken redirect/cert, no
   layout shift.
8. **Calibrated craft, not spectacle**; German-local-sober tone, no
   exclamation-marketing.

**List B — visual craft (what makes a content-light page "look expensive at a
glance"), in leverage order:**

1. **A confident, non-default typeface set BIG.** Large hero display, real type scale,
   tight tracking, weight contrast. Default/system fonts are the #1 cheap tell (§3
   bans). On a split/panel hero "big" is relative to the column: size to fill it,
   hyphenate German compounds, push weight/tracking rather than raw px.
2. **Whitespace.** Generous padding; crowding looks cheap.
3. **ONE disciplined accent on warm neutrals.** Warm off-white (not `#fff`),
   near-black (not `#000`), accent used sparingly. No rainbow, no multi-accent, no
   pure-black-on-pure-white.
4. **ONE strong, well-graded photograph.** ONE consistent warm grade across the page;
   one great photo beats a grid of stock tiles (the grade + real-work rule lives in
   `modules/BUILD.md` §3).
5. **Crisp, instant, stable render.** Then: scale contrast (one dominant H1, small
   tracked eyebrows, one focal point per section); alignment + rhythm (consistent
   margins, one spacing scale); **quiet depth** (hairline borders, ONE shadow tier,
   consistent radii, faint texture, never a flat slab).

**Two project-specific taste gates that fall out of List A:**

- **Per-SET hero diversity.** A new or reworked site must not clone an existing
  site's hero *structure*. Heroes in the current set are deliberately distinct:
  editorial split (praxis), stacked-cinematic (helmle), full-bleed overlay (pronto),
  panel + real-work photo (meinzer), tri-band hover (beauty). Adding a sixth means
  picking a sixth structure, not reusing one. This is List A1 made enforceable.
- **Logo / palette harmony.** If the business has a real brand mark, the site accent
  echoes the mark's hue (or deliberately reconciles it); the mark and the site read
  as one identity. A teal logo beside a clay CTA fights itself (helmle, fixed
  2026-06-03). No real mark → the typeset wordmark IS the mark; never invent a logo.

Cheap-tells to eliminate (each an instant template signal): default / trendy-geometric
fonts; `#000`-on-`#fff` or multi-accent; heavy drop-shadows / glassmorphism /
gradient-on-everything; the generic three-icon-card row; stock headset-smilers; clip
art; everything centred; exclamation marks; em-dashes; gradient placeholders.

## 1. Lock the BRIEF (anti-generic gate)

`app/src/sites/{slug}/BRIEF.md` with: 2-3 named award-tier references, extracted
design DNA, explicit anti-patterns (the clichéd vertical template to avoid), full
art direction (type pairing, hex palette, layout system, motion), one bespoke
signature section concept, imagery plan, B4 data rules.

Add `app/src/sites/{slug}/theme.css` — brand tokens scoped under
`[data-site="{slug}"]` (paper/surface/ink/muted/line/accent/accent-soft + display/
body fonts). Self-host fonts via `@fontsource-variable/*` (no Google Fonts request).

## 2. Articulated-WHY in the BRIEF

Every art-direction call (type pair, palette, spacing, motion easing/duration,
signature section) gets a one-line *"why this, not the default"*. Kowalski's frame:
every taste decision has a logical reason; document it or you're guessing
(`emilkowal.ski/ui/developing-taste`, `…/agents-with-taste`). The BRIEF must also
name 1-2 references it is intentionally NOT borrowing from (the anti-pattern
direction); naming the rejection sharpens what the chosen references actually carry.

## 3. Typography hard bans

Inter, Roboto, Arial, default system stacks, and Space Grotesk are banned as primary
type unless the BRIEF explicitly justifies one on a non-default basis. Reach for
distinctive display + body pairings via `@fontsource-variable`. Reason: these are the
AI-default fonts; using them is the signature of generic AI-generated UI (source:
`frontend-design` plugin skill).

## 4. Background depth rule

No flat solid-colour backgrounds in primary sections. Pick one of: gradient mesh,
noise/grain, layered photography, geometric pattern, or the depth-parallax hero
(`references/depth-hero.md`). Pages of plain white sections fail the impeccable bar
unless the BRIEF explicitly justifies the minimalism as the aesthetic direction
(luxury / editorial restraint). Source: `frontend-design` plugin skill, "atmosphere +
depth" rule.

## 5. Comparative-judgment gate (formal — match-then-exceed)

Before deploy, place a screenshot of the candidate hero next to ONE named BRIEF
anchor. The anchor is a FLOOR, not a ceiling. Articulate *in writing* (PR description
or BRIEF appendix), region by region:

1. **Parity** — for each load-bearing region of the hero (type treatment, palette,
   layout structure, imagery role, motion, trust/info surfacing, primary CTA), does
   the candidate sit credibly next to the anchor? If not yet, name the gap.
2. **Exceed** — for each region that already reaches parity, name where the candidate
   can go BEYOND the anchor. The anchors are often years old, sometimes drifted
   (rebrands, acquisitions), and may carry their own anti-pattern violations the BRIEF
   was written against. Best-in-class is the target, not "looks like the reference."

Both passes are mandatory. A page that matches the anchor in every region but exceeds
in none is shipped at the floor of the quality bar, not the ceiling. Sources:
`emilkowal.ski/ui/train-your-judgement`, plus owner directive 2026-06-01. The
articulated judgment IS the gate; "looks fine to me" is not, and neither is "matches
the reference."

Per-element bars (the nav bar in `components/nav-bar.md`) carry their own isolated
comparative-judgment gate that fires in addition to this hero-level one.
