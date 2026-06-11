# Reference: motion craft (quantified)

The single authoritative home for the motion envelope. `modules/BUILD.md` and the
`SKILL.md` Critical Rules link here; do not restate the table elsewhere.

Vague motion guidance is the source of janky-feeling animations. These rules are
structural. Cite the relevant row in PR descriptions or the BRIEF when a motion choice
is non-obvious. Two anchor sources: Emil Kowalski's UI lessons (`emilkowal.ski/ui/*`)
and the `frontend-design` plugin skill.

Rule IDs (first column) are the stable citation handles —
`tools/audit-local-web-aesthetics.py` names them in motion-scan findings. The
duration ceiling governs enter/exit + interaction animations; ambient loops (Ken
Burns, marquee, ≥5s) are exempt per `references/design-thresholds.md`
`web-motion-ambient-exemption`.

| ID | Rule | Value | Source |
|----|------|-------|--------|
| `web-motion-easing-custom` | Enter/exit easing | Custom `cubic-bezier`, not built-in `ease-out` (built-ins "usually not strong enough") | `…/7-practical-animation-tips` #4 |
| `web-motion-easing-movement` | On-screen movement easing | `ease-in-out` | `…/great-animations` |
| `web-motion-easing-hover` | Hover / colour easing | `ease` | Kowalski |
| `web-motion-duration-ceiling` | Duration ceiling | ≤ 300ms; 180ms beats 400ms on perceived responsiveness | `…/great-animations` + tips #6 |
| `web-motion-composite-only` | Animated properties | ONLY `transform` + `opacity` (composite layer; no layout/paint cost) | `…/great-animations` |
| `web-motion-no-scale-zero` | Initial scale | Never `scale(0)`; start from `0.95`+ | tips #2 |
| `web-motion-press-feedback` | Button press feedback | `scale(0.97)` on `:active` | tips #1 |
| `web-motion-transform-origin` | Transform origin | Per-element (popovers scale from trigger point, e.g. `var(--radix-…-transform-origin)`) | tips #5 |
| `web-motion-interruptible` | Interruptibility | Required (CSS transitions or Motion lib) | `…/great-animations` |
| `web-motion-restraint` | Restraint | Never animate keyboard-initiated actions; skip animations on elements users see 100+×/day | `…/great-animations` + `…/you-dont-need-animations` |
| `web-motion-blur-bridge` | Escape hatch | `filter: blur()` to bridge state transitions when easing/duration alone cannot | tips #7 |
| `web-motion-reduced-motion` | Accessibility | `prefers-reduced-motion: reduce` always honoured | `…/great-animations` |
