# Reference: motion craft (quantified)

The single authoritative home for the motion envelope. `modules/BUILD.md` and the
`SKILL.md` Critical Rules link here; do not restate the table elsewhere.

Vague motion guidance is the source of janky-feeling animations. These rules are
structural. Cite the relevant row in PR descriptions or the BRIEF when a motion choice
is non-obvious. Two anchor sources: Emil Kowalski's UI lessons (`emilkowal.ski/ui/*`)
and the `frontend-design` plugin skill.

| Rule | Value | Source |
|------|-------|--------|
| Enter/exit easing | Custom `cubic-bezier`, not built-in `ease-out` (built-ins "usually not strong enough") | `…/7-practical-animation-tips` #4 |
| On-screen movement easing | `ease-in-out` | `…/great-animations` |
| Hover / colour easing | `ease` | Kowalski |
| Duration ceiling | ≤ 300ms; 180ms beats 400ms on perceived responsiveness | `…/great-animations` + tips #6 |
| Animated properties | ONLY `transform` + `opacity` (composite layer; no layout/paint cost) | `…/great-animations` |
| Initial scale | Never `scale(0)`; start from `0.95`+ | tips #2 |
| Button press feedback | `scale(0.97)` on `:active` | tips #1 |
| Transform origin | Per-element (popovers scale from trigger point, e.g. `var(--radix-…-transform-origin)`) | tips #5 |
| Interruptibility | Required (CSS transitions or Motion lib) | `…/great-animations` |
| Restraint | Never animate keyboard-initiated actions; skip animations on elements users see 100+×/day | `…/great-animations` + `…/you-dont-need-animations` |
| Escape hatch | `filter: blur()` to bridge state transitions when easing/duration alone cannot | tips #7 |
| Accessibility | `prefers-reduced-motion: reduce` always honoured | `…/great-animations` |
