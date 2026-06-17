---
name: prototype
description: Content-adaptive front end for any web prototype build — derive the information architecture from the real subject and content (never a fixed template), catch thin-content and structural slop before it becomes invented sections, then route execution and quality gates to the right per-substrate stack. Use at the START of a prototype build — local-business site, client product/proposal/doc site, single-file HTML deliverable, or platform page — and for Elevate passes on an existing one.
---

# Prototype (content-adaptive front end)

The shared front door for prototype builds. It owns ONE thing the execution
regimes don't: deriving structure from the real content, and refusing to pad.
It does NOT re-implement quality — it routes to the stack that already owns
that. Born 2026-06-17 from the content-adaptive blueprint, after the Brisken
OnePilot prototype was hand-rolled with no skill backing it because neither the
local-web Astro pipeline nor the client-page roster fit a content-rich product
site.

Two commitments, both from the blueprint:

- **Structure follows content, not a fixed template.** The section set and IA
  are an *output* of the real subject, never imposed. A data-rich subject earns
  a data section; a real sequence earns a flow; live proof earns an evidence
  block. Nothing exists because "landing pages usually have one."
- **Floor, not look.** This skill standardizes how the structure is derived and
  how thin content is caught. It never dictates the visual identity — that is
  per-substrate and per-project (the routed stack owns it).

## When this skill runs (and when it doesn't)

Runs at the start of a prototype build, and for Elevate passes on an existing
one. It is the front end; it always HANDS OFF to an execution stack:

| If the prototype is... | Route execution + quality gates to |
|---|---|
| a local-business marketing site (Astro/Fly, content-light) | `skil_web-build` — its CONCEIVE + quantified gates own the look; do not duplicate them here |
| a client product / proposal / doc site (multi-page static HTML) | `rule_client_page_structure` + `tools/audit-client-pages.py` |
| a self-contained single-file HTML deliverable (Brisken-class) | `rule_deliverables` + `tools/validate-deliverable.py` + `tools/validate-html.py` |
| a platform (unpauseai.com) marketing / proposal page | `rule_platform_standards` + `tools/validate-platform-content.py` |

If the work is pure execution on a site whose IA is already locked ("rebuild the
hero with a new anchor", "fix the nav contrast"), skip this skill and go straight
to the execution stack. This skill is for deriving and deciding structure, not
pixel work on a settled structure.

## Front-end procedure (both modes)

1. **Intake.** Absorb the real inputs as-is: brief, spec, transcript, a live
   product, source data, a reference or competitor site, scattered notes. Handle
   "a pile of material" as gracefully as a clean brief. Name the canonical
   source(s) so downstream B4 checks have a target.
2. **Derive.** From the content, extract the subject, the audience, the page's
   single job, the *real* value props, the proof actually available and how
   strong it is, and the domain vocabulary.
3. **Calibrate.** Set this build's boldness ceiling and STATE it: enterprise /
   finance reads distinctive-but-credible; consumer / creative gets more
   latitude; German-local SMB stays calibrated-sober (`skil_web-build` List A).
   Distinctiveness never costs the trust the audience requires.

Then branch by mode.

### Create mode

- **Derive the IA from content.** Let the section set emerge from what the
  content supports. Map content shape to structure: a sequence becomes a
  flow/timeline; a comparison becomes a table; a standout metric becomes a stat
  moment; a rich subject world earns a signature visualization; live customer
  proof earns an evidence block.
- **Flag thin spots; never pad.** If the content does not support a section, the
  section does not exist. Surface the gap and ask. Do not invent a claim, metric,
  testimonial, or logo to fill a layout. This is the IA clause of
  `rule_anti_slop` — structural slop, the sibling of prose slop.
- **Draft copy as design material**, in the subject's own vernacular, as
  intentional as spacing. No lorem, no generic filler, no cleverness over
  clarity.

### Elevate mode

- **Preserve-inventory first.** List what is already good and must not regress:
  content substance, working interactions, accessibility floor, dark mode, SEO,
  performance, substantiated claims, token architecture. Catalog before changing
  anything.
- **Audit, leverage-ordered.** Run the routed stack's quality rubric
  (`skil_web-build` CONCEIVE List B for Astro sites; `rule_deliverables` for
  single-file HTML). Diagnose the highest-leverage gaps first; do not regress the
  preserve-inventory.

## Plan-gate (mandatory, both modes)

Produce a short plan: the derived IA / section set (Create) or the
preserve-inventory plus leverage-ordered gaps (Elevate); the single signature
element; and the chosen substrate + quality stack. Run two self-tests before
presenting:

- **Generic-default test.** Would I produce this look for any brief? If yes,
  rework.
- **Template-IA test.** Is this section set coming from the content, or from
  habit? If a competitor's site would carry the same sections in the same order,
  the IA is templated — rederive. (For Astro SMB sites, also run the second-order
  slop test in `skil_web-build` CONCEIVE §2.)

Present the plan and WAIT for approval before building. Approval on the plan
saves rebuilds; never skip it.

## Content-fidelity at IA time

Never fabricate claims, metrics, credentials, testimonials, or logos; thin
content is a signal to surface, not a gap to fill. This is enforced downstream by
B4 (`rule_behaviors`), `tools/validate-output.py` `unsourced-claim`, and the
routed stack's own data gate (`skil_web-build` DATA module / `CHECK` sentinel).
This skill's job is to catch it earlier — at IA-derivation time, before it reaches
those gates. When the proof is thinner than the layout wants, downgrade the
treatment rather than overstate: "17 of 21 ads" beats a hero "81%" off n=21.

## Definition of done

The front-end is done when the IA is derived-and-justified (Create) or the
preserve-inventory is logged (Elevate), the two plan-gate self-tests pass, thin
content is flagged not padded, the substrate + quality stack is named, and the
plan is approved. Execution and the hard quality / ship gates belong to the
routed stack, not here. This skill never declares a site shipped — the routed
stack's definition of done does that.

## Maintaining this skill

After each prototype, append any reusable content-to-structure heuristic and any
new IA tell (a section that kept appearing from habit, not content). Keep it thin.
If a rule belongs to an execution stack it lives there and this skill links to it;
two copies is drift (the `skil_web-build` "one home per rule" invariant applies
here too). The day this file grows a second quality rubric, it has failed.
