# Mini-Checkpoint: Brisken OnePilot Orbit Review Round 1

**Date:** 2026-06-21
**Status:** Live + verified
**Type:** mini

---

## Summary
Replaced the served OnePilot platform page at `brisken-onepilot.fly.dev` with the
agentic-dev1 "orbit" build, then implemented round 1 of reviewer feedback (9
notes) on it. Both deployed and verified on the live origin.

## What Was Done
- Swapped the live platform page for `onepilot-orbit.html` (orbit centerpiece →
  applications → governed → problem → answers → demo + footer). Ported the
  review feedback annotator into the ops1 served copy and restyled it to the
  orbit dark theme (the dev1 artifact stays pristine, no annotator).
- Applied all 9 reviewer notes: hero title enlarged + overlapping the orbit with
  hover fade-to-reveal + ease-zoom (sub-paragraph + hint removed); problem
  reframed on "using not moving" data; applications shows non-finance breadth
  (illustrative) + one-place utility; centered from applications down; answers =
  click-to-reveal accordion (text stays in DOM for AEO); section divider lines +
  the demo "blue line" removed.
- Fixed the "blue line": the demo `.row` collided with the panel
  `.row{border-left:2px var(--hue)}` rule; overrode with `border-left:none`.
- Verified locally end to end (gate, render, double-click context, POST 200,
  accordion, hover-peek) and live (markers present, 0 console errors, 0
  em-dashes, validate-html clean). ops1 commits `cda1117` + `2318828`, pushed.

## Current Status
Live at `https://brisken-onepilot.fly.dev/` (name-gated, scale-to-zero). The
canonical dev1 source `docs/handoffs/onepilot-gravity-well/onepilot-orbit.html`
carries all 9 changes on disk (untracked in dev1, as it has been). Reviewer
feedback log (incl. the round-1 notes, filed under "Deploy Check") lives on the
app's Fly volume, readable via the gated `/feedback.jsonl`.

## Next Steps
1. Await the next reviewer round on the live orbit page (notes land in
   `/feedback.jsonl`); the round-1 notes are now implemented.
2. dev1 production build for `onepilot.brisken.com`: no-WebGL/reduced-motion
   fallback, light-theme pass, then promote (owner-gated). Build-split: that
   work belongs in an agentic-dev1 session.
3. Brisken (unchanged): Rome E2 send Mon 2026-06-22; await Dirk on broader
   positioning.

## Files to Read First
- `workspace/clients/brisken/deliverables/brisken-onepilot-platform.html` (served orbit page + review module)
- `agentic-dev1/docs/handoffs/onepilot-gravity-well/onepilot-orbit.html` (canonical source)
- `memory/project_brisken_onepilot_site_hosting.md` (live-state record, updated)
