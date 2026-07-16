# Mini-Checkpoint: Brisken OnePilot Orbit Review (rounds 1-4)

**Date:** 2026-06-21
**Status:** Live + verified; iterating on reviewer feedback
**Type:** mini

---

## Summary
The OnePilot platform page (Fly host `brisken-onepilot.fly.dev`, the name-gated
internal review host) now serves the agentic-dev1 "orbit" build, and four rounds
of reviewer feedback have been implemented and deployed on it. Reviewer notes
arrive via the double-click annotator into the live `/feedback.jsonl` (filed under
the name "Deploy Check", the cookie I set during deploy-verify).

## What Was Done (this session)
- Replaced the served platform page with the dev1 orbit build (orbit centerpiece
  -> applications -> governed -> problem -> answers -> demo + footer); ported the
  review feedback annotator into the ops1 served copy only.
- **Round 1** (commit 2318828): hover-peek title (fade to reveal + zoom), removed
  hero sub-text/hint, problem "using not moving" emphasis, applications breadth
  chips, centered layout, accordion answers, removed divider lines + demo blue
  line (a `.demo .row` border-left collision).
- **Round 2** (07186d4): OnePilot core is now an openable node ("OnePilot, the
  universal UI" panel); symbol changed from the brand cube to a luminous ORB.
- **Round 3** (98e3ceb): depth-of-field hero, orbit blurred at rest, sharp on
  hover; title reappearance slowed to ~3.4s (fade-out stays quick).
- **Round 4** (e5d9a83): centered the four section H2s (h2 box needed auto
  margins, not just text-align); renamed orbit nodes to plain labels + added an
  Integrations node ("What it connects to"); strengthened non-SAP / non-finance
  emphasis in the applications section and the new node.

## Current Status
Live + verified each round (local E2E + live curl markers, 0 console errors, 0
em-dashes, validate-html clean). ops1 commits on `client/brisken/lead-gen-onepilot`,
pushed, no PR (internal WIP). The canonical dev1 `onepilot-orbit.html` carries all
changes on disk (untracked in dev1). NOTE: a concurrent session put a separate
Vercel platform page at `onepilot.brisken.com`; the Fly orbit host is a different
surface (owner to reconcile which is canonical).

## Next Steps
1. Watch `/feedback.jsonl` for the next reviewer round; implement + deploy.
2. dev1 production build for `onepilot.brisken.com` (no-WebGL fallback, light
   theme) is owner-gated, belongs in an agentic-dev1 session.
3. Infra watch: the dev1->deliverable sync re-injected the ~200-line review module
   3x (rounds 1-2 via cp+reinject; rounds 3-4 switched to parallel 2-file edits,
   which is safer for small edits). If a big structural round comes, build a tiny
   `build-deliverable.py` (or move the module to app.py serve-time injection).

## Files to Read First
- `workspace/clients/brisken/deliverables/brisken-onepilot-platform.html` (served orbit page + review module)
- `agentic-dev1/docs/handoffs/onepilot-gravity-well/onepilot-orbit.html` (canonical source)
- `memory/project_brisken_onepilot_site_hosting.md` (live-state record, rounds 1-4)

## Note
Session log / context YAML / INDEX bookkeeping intentionally NOT churned this
checkpoint: a concurrent session (brisken.com launch) is actively editing those
shared files, and at critical context pressure the durable record (git commits +
this file + memory) is what matters. Pick up via `/resume brisken`.
