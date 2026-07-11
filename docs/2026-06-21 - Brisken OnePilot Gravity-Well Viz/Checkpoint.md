# Checkpoint: Brisken OnePilot Gravity-Well Viz

**Date:** 2026-06-21
**Status:** Spike validated + owner-approved; build EXPORTED to agentic-dev1 for production

---

## Summary
Conceptualized, spiked, and validated the synthesizing hero visualization for the
"paradigm shift onward" arc of the OnePilot platform page, landing (after two owner
redirects) on a dark cinematic WebGL gravity well. The approved spike plus a full
build brief were exported to agentic-dev1 (the production-build repo) per the
build-split rule.

---

## What Was Done This Session
### Concept (plan-gated)
1. Read `#different` -> `#editions` of `brisken-onepilot-platform.html` in full; extracted the through-line (the surface as a center of gravity).
2. Presented 3 conceptual directions (hourglass / day-ribbon / radial), critiqued, recommended; owner chose Direction C (radial), then escalated the ask to "exclusive instrument-grade feel" as a first-class deliverable.

### Spike + critique (Direction C, flat)
3. Built a standalone radial "engine-turned dial" spike in `.scratch/` (SVG/CSS), with the broken-ring coverage mechanic, the magnetize morph, light/dark, mobile stack.
4. Ran an 8-lens adversarial critique **workflow** (clutter, cliche, instrument-vs-infographic, inversion, ring-mechanic, felt-quality, credibility/honesty, mobile) over the rendered screenshots; synthesized a go/no-go. Verified and downgraded the one "fail" (ring mechanic) as a screenshot artifact (two 44% frames), not a real bug.

### Redirect -> gravity well (WebGL)
5. Owner redirected: "more like a horizon, black hole structure," then sent a plan to rebuild the visual body in real-time WebGL (gravity well + accretion).
6. Built a standalone **WebGL gravity-well** spike (raw GLSL fragment shader, zero deps): gravitational lensing, tilted Doppler-lit accretion disc, dark well, soft halo, bloom, the accretion morph (estate falls in / flings out), coverage arc, competitor focus; DOM-first content/logic; render loop paused offscreen, DPR capped.
7. Caught and fixed two craft failure modes myself: the "eye" (perfect ring + centered dot) and the "ringed planet" (crisp full photon ring); resolved to a soft gravitational halo + Doppler disc + bloom. Captured a morph clip (PIL-assembled GIF). Owner approved the look + motion.

### Export
8. Packaged the validated build into agentic-dev1 at `docs/handoffs/onepilot-gravity-well/`: a 301-line `HANDOFF.md` (content/data verbatim, integration target, tokens, critique residue, honesty, build backlog) + `reference/` (the spike, the target page copy, stills, the morph GIF).
9. Logged 4.0h to the Lead Generation tab; recorded the cross-repo move in memory.

---

## Key Decisions Made
### Medium: raw WebGL fragment shader, not Three.js/R3F
- **Choice:** the gravity well is one custom GLSL fragment shader on a fullscreen quad, zero dependencies.
- **Rationale:** the iconic black-hole look IS a fragment shader; R3F needs React + a build pipeline and does not fit a self-contained single HTML file; raw WebGL ports straight into the page.

### Rest state = consolidated (owner's reframe)
- **Choice:** the page rests on the closed-ring, user-centric, authoritative state; the "shift" demonstrates the contrast by flinging out and pulling back.
- **Rationale:** owner direction; a confident default rather than resting on the problem.

### Build diverts to agentic-dev1
- **Choice:** export rather than integrate in agentic-ops1.
- **Rationale:** the build-split rule (prototypes in ops1; landed-client production builds go to dev1 for highest quality). Owner directive this session.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `agentic-dev1/docs/handoffs/onepilot-gravity-well/HANDOFF.md` | Created | Master build brief (cross-repo) |
| `agentic-dev1/.../reference/` (spike, target page, 3 stills, GIF) | Created | Reference bundle for the dev1 build |
| `.scratch/onepilot-well-spike.html` | Created | The validated WebGL gravity-well spike (gitignored) |
| `.scratch/onepilot-dial-spike.html` + screenshots + `well-morph.gif` | Created | Radial spike + capture artifacts (gitignored) |
| `workspace/hours-tracker.xlsx` (+ CSV mirrors) | Modified | +2 Lead-Gen rows, +4.0h (local, gitignored) |
| `memory/project_brisken_onepilot_gravity_well.md` + `MEMORY.md` | Created/Modified | Record the gravity-well build + the dev1 export |

Note: no agentic-ops1 tracked-tree changes this session. The spike is scratch, the export is in dev1, the memory is the separate store. Nothing to commit here.

---

## Current Status
The gravity-well look and motion are owner-approved off the spike. The production
build now lives in agentic-dev1 with everything needed to continue. The Brisken
OnePilot platform page (`brisken-onepilot.fly.dev`) is unchanged; the new
centerpiece is not yet integrated (that is dev1's job).

Brisken has no workflow-engine ops to track (OnePilot host is FastAPI/static on
Fly; the expense-recon `platform` section is a custom standalone build, tier by
design "unknown"), so no ops-usage line applies.

---

## Next Steps
1. Continue the build in **agentic-dev1** from `docs/handoffs/onepilot-gravity-well/HANDOFF.md`: production WebGL piece + static fallback (no-WebGL/mobile/reduced-motion) + dark-well-in-light-theme + wire reach-down + ship/verify.
2. Integrate into `brisken-onepilot-platform.html` superseding `#different`, without breaking the double-click annotator.
3. Brisken (unchanged from prior): Rome E2 send Mon 2026-06-22; await Dirk on the broader OnePilot positioning; brisken.com subdomain deploy when decided.

---

## Context for Next Session
### Files to Read First
- `agentic-dev1/docs/handoffs/onepilot-gravity-well/HANDOFF.md` (the whole build brief)
- `agentic-dev1/docs/handoffs/onepilot-gravity-well/reference/onepilot-well-spike.html` (the validated visual)
- `workspace/clients/brisken/deliverables/brisken-onepilot-platform.html` (integration target, `#different` section)
- `memory/project_brisken_onepilot_gravity_well.md`

### Open Questions
- Packaging at integration: keep raw WebGL (recommended, self-contained) or vendor Three.js for true multi-pass bloom / particles?
- Light-theme handling: dark-stage-always (recommended) or retint?
- Where does the production piece live in agentic-dev1: scaffold a `products/` entry, or build it as an embedded component for the existing page?

### Working Notes
- Shader pitfalls (do not regress): a bright perfect ring + centered dot reads as an "eye"; a crisp full photon ring reads as a "ringed planet." The fix is a tilted Doppler-lit accretion disc that crosses in front of the lower well + a SOFT gravitational halo (low amplitude, wide falloff) + a soft top lens-glow, never a hard drawn circle.
- The coverage arc must be data-driven (arc length = coverage %), and the broken state must read as a real gap, not a faint full ring. Both are done in the spike.
- The 8-lens critique residue still to honor in the build: co-locate the "illustrative / framework-vs-shipped-edition" qualifier with the big "100%"; soften "absorbs all of them" where it sits near "does not become the system of record."
- Capture hook in the spike for deterministic frames: `window.__cap(scatter, coverage, tsec)`.
- The local spike + screenshots + GIF are in `agentic-ops1/.scratch/` (gitignored, throwaway); a background `python -m http.server 8123` over `.scratch/` may still be running.

### Reference Materials
- Spike served locally at `http://127.0.0.1:8123/onepilot-well-spike.html`
- Build-split rule: [[project_local_web_proto_vs_client_build_split]]

---

## How to Continue
The look is the spec; the spike is the reference; the content is fixed. Open a
session in agentic-dev1, read the HANDOFF, and build the production version to that
repo's bar (rule_dev_loop). Do not promote to onepilot.brisken.com without an
explicit owner go.

---

## Strategic Feedback

### What Worked Well This Session
- The spike-then-show loop did its job: each cheap standalone spike (radial, then WebGL) surfaced a real verdict on pixels, and the owner could redirect on what they saw rather than on a description. The two redirects were the process working, not failing.
- The owner escalating ambition through successive prompt docs (Direction C -> exclusive feel -> 3D gravity well) kept each step concrete and signed off before build.

### Suggestions
- When the brief's core ask is a premium / exclusive / "epic" FEEL, name the medium ceiling up front. A flat SVG/CSS centerpiece was spiked before flagging that the medium could not reach "instrument-grade exclusive," which is what the WebGL redirect corrected. One sentence at plan time ("SVG/CSS caps out here; if the bar is exclusive, that means WebGL") would have skipped a cycle.

### System Health
- **Friction (1): `strategic-gap`, and a regression.** This is the same shape as the 2026-05-18 local-web strategic-gap (built single-file HTML prototypes before questioning whether the format could meet the aesthetic bar). That fix was scoped to skil_web-build sites; it did not cover a one-off deliverable centerpiece, so the medium-ceiling check did not fire here. The durable fix is to generalize "assess whether the medium can reach the stated feel before spiking" beyond web-build into any deliverable whose brief leads with an aesthetic/feel bar.
- Autonomy score: 1 human intervention this session (the medium redirect).
- The cross-repo export worked cleanly, but agentic-ops1 has no convention for "build handed to dev1" beyond a memory note; if this becomes common, a thin `/comd_export-to-dev1` (stage bundle + HANDOFF scaffold + memory) would make it one step.
