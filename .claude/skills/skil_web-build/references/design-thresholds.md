# Reference: design thresholds (quantified)

The single authoritative home for the numeric type/colour/layout floors and
ceilings. `modules/CONCEIVE.md` §3 and the `SKILL.md` Critical Rules link here;
do not restate the numbers elsewhere. The motion envelope is NOT here — it lives
in `references/motion-craft.md` (one home per rule).

Each rule carries a stable ID; `tools/audit-local-web-aesthetics.py` cites these
IDs in its findings, and `tools/check-skill-map.py` flags duplicate IDs across the
skill. Thresholds adopted from impeccable (Apache-2.0) 2026-06-11; values are
theirs unless noted.

| ID | Rule | Value |
|----|------|-------|
| `web-type-tracking-floor` | Display letter-spacing floor | Never tighter than `-0.04em`; `-0.02` to `-0.03em` is plenty for a tight grotesque display face |
| `web-type-hero-clamp-ceiling` | Hero `clamp()` max | ≤ `6rem` (~96px); above that the page is shouting, not confident |
| `web-type-clamp-ratio` | Fluid type bounds | `clamp()` max ≤ ~2.5× min, or browser zoom / reflow breaks |
| `web-type-line-length` | Body line length | 65–75ch target; flag `max-width` in `ch` outside 45–78 |
| `web-type-caps-tracking` | ALL-CAPS labels (eyebrows, buttons) | +0.05 to +0.12em tracking, always |
| `web-type-dark-compensation` | Light-on-dark text | Compensate on three axes: +0.05–0.1 line-height, +0.01–0.02em tracking, body weight up one notch |
| `web-type-text-wrap` | Heading/prose wrapping | `text-wrap: balance` on h1–h3, `text-wrap: pretty` on prose |
| `web-color-muted-contrast` | Muted/placeholder text contrast | Same 4.5:1 floor as body text — muted gray that fails contrast is the most common shipped a11y bug, not a design choice |
| `web-layout-z-index-scale` | z-index | Semantic scale (dropdown < sticky < modal < toast < tooltip), never `999`/`9999` |
| `web-motion-reveal-safety` | Scroll-reveal visibility | Never gate content visibility on a class-triggered *transition* alone: transitions pause in hidden tabs / headless renderers and the section ships blank. Reveal CSS needs a no-JS/`prefers-reduced-motion` exposure path (the `.no-js [data-reveal]` reset in `global.css`) |

Two clarifications the table can't carry:

- **Ambient loops are exempt from the 300ms ceiling.** The motion-craft duration
  ceiling governs enter/exit and interaction animations. A 14s Ken Burns drift or
  a slow marquee is ambient by design; the audit script exempts animations ≥5s
  and `kenburns`-named keyframes. <!-- rule:web-motion-ambient-exemption -->
- **The cream band** (`web-color-cream-band`) and the saturated font tier live in
  `modules/CONCEIVE.md` §6 — they are saturation-list entries (dated, rotating),
  not permanent thresholds, so they live with the list mechanics.
