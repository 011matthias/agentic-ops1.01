# Mini-Checkpoint: Web-Build Skill Restructure + Nav-Bar Standard

**Date:** 2026-06-03
**Status:** Skill restructure complete (staged, unshipped); nav-bar implementation on the 5 prototypes audited + specced, NOT yet applied
**Type:** mini

---

## Summary
Integrated a nav-bar component standard into `skil_web-build`, then restructured the
whole skill from a ~400-line monolith into a `trigger-pack`-style hub-and-spoke
(lean SKILL.md + modules/ + references/ + components/ + incidents.md). Then audited
the 5 local-web prototypes against the nav-bar standard and specced the fix; the
implementation itself was blocked by a stuck-cwd hook failure and handed off.

## What Was Done
- **`components/nav-bar.md`** created (the nav-bar capability the user authored),
  wired into the skill at 3 points: Critical Rules one-liner, Definition-of-Done
  item 15, and the component index.
- **Full `skil_web-build` restructure** (committed-pending, NOT shipped — `.claude/`
  scope, outside the local-web carve-out):
  - SKILL.md rewritten to a 147-line spine (was ~400): mental model, four failure
    modes, Critical Rules, Build Procedure table, single Definition-of-Done gate
    (15 items, each → a module), Module/Reference/Component index, Maintaining note.
  - New `modules/{CONCEIVE,DATA,BUILD,SHIP}.md`, `references/{motion-craft,
    a11y-verify,deploy-internals,depth-hero}.md`, `incidents.md`.
  - Migration verified: all cross-links resolve, every load-bearing rule survived,
    DoD intact at 15 items, no external refs to old section numbers broke.
- **Nav-bar audit of all 5 prototypes** (praxis-uslu, beauty-lounge, helmle-physio,
  meinzer-maler, pronto-pronto): items 1/2/5/6/7 PASS on all; gaps are uniform —
  item4 padding (0.9rem → ≥1.25rem), item8 mobile (links just `display:none`, no
  hamburger/overlay), item3 tagline (missing on helmle + meinzer), item10
  comparative-judgment paragraphs (none written). A full locked-pattern spec +
  continuation prompt were produced (see Working Notes / the chat).

## Current Status
- Skill restructure: DONE, staged, awaiting explicit ship order (`.claude/skills/`
  files — NOT auto-shippable; outside the prototype carve-out).
- Nav-bar on 5 prototypes: AUDITED + SPECCED, zero local-web files modified yet (the
  one attempted praxis-uslu markup edit was blocked by the hook and did NOT apply).
- BLOCKER this session: a `cd` inside the Bash tool stuck the harness cwd at
  `workspace/projects/local-web`, so every cwd-relative `.claude/hooks/*.py`
  PreToolUse hook crashed → Bash AND Edit bricked. A fresh session resets this.

## Next Steps
1. New session (resets cwd / hooks). Read `.claude/skills/skil_web-build/components/nav-bar.md`.
2. Implement the locked nav pattern on the 5 prototypes (the continuation prompt in
   the chat has the full spec: markup + CSS + JS + per-site specifics). Do praxis-uslu
   first as the reference, build-verify, then propagate to the other 4.
3. `npm --prefix workspace/projects/local-web/app run build` (validate-dist gate) +
   axe-core via CDP. Stage; deploy only on explicit owner order.
4. Decide ship of the staged `skil_web-build` restructure (explicit order needed).

## Files to Read First
- `.claude/skills/skil_web-build/components/nav-bar.md` (the standard)
- `.claude/skills/skil_web-build/SKILL.md` (new spine; DoD item 15 gates the nav bar)
- `workspace/projects/local-web/app/src/pages/praxis-uslu.astro` (reference impl)
- The continuation prompt in this conversation (full nav implementation spec)

## Working Notes
- Nav is per-page inline (no shared Nav component) — keep it that way (handoff
  independence; skill says no shared business data between sites).
- All 5 share `.site-head` (sticky, translucent paper bg, hairline border, no shadow)
  + `.site-head__row { padding-block: 0.9rem }` + `.site-nav` (3 links + 1
  `.site-nav__cta`). Mobile = `@media(max-width:640px){ .site-nav a:not(.cta){display:none} }`.
- Per-site brand classes differ: praxis `.brand__name`+`.brand__role`; beauty
  `.brand__mark`+`.brand__role`; helmle/meinzer logo `<Image class="brand__logo">`
  (no tagline); pronto logo `.masthead__logo` + `.masthead__descriptor`.
- Fonts all non-default serif wordmarks (Newsreader/Cormorant/Fraunces/Bitter/Fraunces).
  praxis body is Inter but paired with serif wordmark = sanctioned editorial contrast.
- CTA colours brand-derived + WCAG-documented in each theme.css (beauty rose-clay,
  helmle teal, meinzer copper, pronto burnt-sienna-not-neon, praxis sage).
- Existing `<script>` blocks (praxis/helmle/pronto) are open-state schedule logic —
  unrelated; use class `is-menu-open`, NOT the existing `is-open` (#open-state).
- ENV GOTCHA: never `cd` in the Bash tool; use absolute paths or `( cd X && … )`
  subshells, or the PowerShell tool. PowerShell bypasses the Bash/Edit PreToolUse
  gates, so do NOT run ship-class commands through it.
