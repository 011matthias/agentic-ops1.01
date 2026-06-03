# Reference: depth-map parallax hero (budgeted WebGL)

The home for the one sanctioned WebGL element. At most ONE per site, always
optional.

- **Linked from:** `modules/BUILD.md` §4
- **Gated by:** Definition-of-Done item 8

## Permission conditions (ALL required)

A depth hero ships only if every one of these holds:

1. **Lazy-init** on idle/scroll. Never blocks first paint or LCP.
2. **Static poster** image as the no-JS / pre-init fallback.
3. **Reduced motion:** `prefers-reduced-motion: reduce` renders the static
   poster, no loop.
4. **Mobile:** ≤768px serves the static image, not the WebGL canvas.
5. **Re-gate after adding:** re-run the `modules/SHIP.md` Lighthouse + axe
   gate. A 3D canvas is a classic silent perf/a11y regression. Perf 100 /
   0 WCAG2AA stays absolute; if the hero can't pass, it ships as the poster.

Out of scope: full multi-element interactive Three.js scenes. The hero is the
only WebGL budget, and the gate is non-negotiable.

## Implemented (2026-05-19, all 3 sites)

`DepthHero.astro`, a transparent enhancement of `<Figure>`:

- Zero-dep, hand-rolled WebGL1 shader.
- The poster `<Image>` stays the LCP and the entire fallback tree: no-JS,
  pre-init, reduced-motion, ≤768px, no-WebGL, Save-Data.
- `canvas` is `aria-hidden`.

Depth maps come from `app/scripts/depth-map.py` (Depth-Anything-V2-Small ONNX,
CPU, via uv). The PNGs are committed so the build stays hermetic.

## Live-verify method

Verify the live effect with `tools/depth-live.cjs`:

- Fresh zero-cache profile.
- A/B pointer parallax.
- Full-page `captureBeyondViewport` capture.

> **Hard lesson.** A bespoke CDP-`clip` screenshot probe reads the wrong region
> after `scrollIntoView`. Use the full-page capture path, and trust composited
> screenshots over a `readPixels` of a non-`preserveDrawingBuffer` context (that
> read is undefined post-composite and will false-fail).
