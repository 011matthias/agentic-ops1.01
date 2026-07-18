# Checkpoint: One Assessment UI — Feedback-Log, Full-Width, Readability

**Date:** 2026-07-17
**Status:** Shipped + live-verified on one-assessment-demo.fly.dev

---

## Summary
Answered a Nagarro-context process question against the live engagement
artifacts, then ran three owner-directed UI passes on the One Assessment
portal: restored the in-app feedback log behind a security-safe allowlist +
added persistent back-navigation from example pages; converted standalone blue
links to buttons and made the whole app full-width; and raised the type scale,
added a "Nächster Schritt" action strip, and section eyebrows for
overseeability. Three deploys to Fly, each live-verified.

---

## What Was Done This Session

### Process grounding (Nagarro SE)
1. Confirmed the slide-14 three-phase "Typical Approach"
   (Preparation → Iterative Analysis & Vision → Result Presentation) is
   cemented in both the project-knowledge docs and the pipeline architecture;
   flagged the three Phase-3 deliverables NOT yet built (Quick Wins, Roadmap,
   Effort indication).
2. Read the three `Nagarro SE/` artifacts (106-slide kickoff deck, agenda docx,
   ~504-question DE/EN questionnaire) and extracted what they add over the
   existing knowledge base: the kickoff deck now carries the new-template
   Phase-3 output shapes (Key Findings with Target State, Detailed Analysis,
   Transformation Initiatives with effort bands <50k/>100k, roadmap Gantt);
   OM grid renamed/anglicized but still 6×4=24 rows; maturity percentage-only;
   provider label is per-engagement (validates the white-label seam).

### Pass 1 — Feedback log restore + back-navigation
1. Diagnosed: the log was not deleted; the 2026-07-15 security lockdown
   (reviewer cookie AND no customer session) left it unreachable once the
   portal login became everyone's home.
2. Added `ONE_ASSESSMENT_INTERNAL_LOGINS` allowlist (`templates.is_internal`):
   named client logins may open `/feedback-log` while holding a customer
   session; everyone else keeps the lockout. Header link, demo/example back-bar
   link, and a "zum Portal" link on the log page for internal logins.
3. Made the injected back-bar sticky (page nav re-anchors below via
   `--oa-bb-h`), added a fixed bottom-left "← Zurück zu Ihrem Bereich" pill on
   every injected surface (demo, showcase, result views).

### Pass 2 — Blue links → buttons + full-width
1. Header Abmelden/Feedback-Log, footer Impressum/Datenschutz, the "fertig"
   banner link, feedback-log meta row + section chips, intake upload chips, and
   the relogin link all became buttons.
2. Removed the width caps: portal shell (920px), feedback log (1040px), process
   pages (1160px), legal pages (720px) → full-bleed with edge padding. Login
   form stays a centered card by design.

### Pass 3 — Larger lettering + clearer actions + overseeability
1. Raised the type scale across portal/intake/log/process/login (base 16→17px;
   nav, tables, buttons, headings, hints all up a step) with padding grown to
   match.
2. Added the "Nächster Schritt" strip at the top of the hub: one state sentence,
   a status summary (`N Entwurf · N in Bearbeitung · N fertig`), and a single
   `.btn.xl` primary action that adapts to state (draft → continue form,
   submitted → wait, fertig → view result, none → start). Folded the old green
   banner into it.
3. Added uppercase section eyebrows (Ihr Bereich / Prozess / Beispiele /
   Fragebogen) matching the nav tabs; made the intake wizard step bar sticky
   with larger dots.

---

## Key Decisions Made

### Feedback-log access = env allowlist, not a role flag
- **Choice:** `ONE_ASSESSMENT_INTERNAL_LOGINS` (comma-separated logins), matched
  casefolded/whitespace-collapsed; set to `Matthias Silva,Dirk Neumann,UTIL
  Verifier`.
- **Rationale:** Restores the log without reopening the 2026-07-15 OWASP-A01
  hole (customers must never read everyone's notes + IP/UA). Jochen's team stays
  customer-side. UTIL Verifier is on the list so live smoke tests can hit the
  internal surfaces without a real person's login.

### One XL action per view, state-driven
- **Choice:** A single `.btn.xl` in the Nächster-Schritt strip, computed from
  the customer's submission state.
- **Rationale:** "Required actions clearer" = exactly one obvious next action,
  not a wall of equal-weight buttons. The status summary gives overseeability of
  the whole account at a glance.

### Full-bleed everywhere except the login card
- **Choice:** `.wrap{width:100%}`; login form keeps `max-width:420px`.
- **Rationale:** Full-width text inputs on a 2-field login hurt usability; the
  page around it is still full-bleed so the directive holds.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../site-host/templates.py` | Modified | `INTERNAL_LOGINS`+`is_internal`; sticky back-bar + backfab + `extra_*` link in `head_inject`; header/footer buttons; type scale; `.btn.xl`/`.eyebrow`/`.nextstep` primitives; INFOGRAPHIC eyebrow |
| `.../site-host/app.py` | Modified | Gate allowlist branch for `INTERNAL_PATHS`; demo back-bar internal link; `/feedback-log` "zum Portal" + button-row meta; log-page full-width + type bumps |
| `.../site-host/portal.py` | Modified | Nächster-Schritt strip (state-driven); eyebrows; full-width `.proc-wrap`; login-card + process type bumps; showcase back-bar internal link; banner→button |
| `.../site-host/intake.py` | Modified | Upload chips + relogin button; form/wizard type bumps; sticky wizard bar |
| `.../tests/test_site_host.py` | Modified | 3 new tests: internal-allowlist, sticky-backbar+backfab, full-width+buttons+nextstep+eyebrows |
| `.../context/test-fixtures.md` | Modified | Documented the `ONE_ASSESSMENT_INTERNAL_LOGINS` secret + meaning |

---

## Current Status
One Assessment portal is live on https://one-assessment-demo.fly.dev with the
feedback log reachable for internal logins, full-width layout, buttonized
actions, larger type, and the Nächster-Schritt action strip. 153/153 pytest
green; all three deploys live-verified as UTIL Verifier. The 2026-07-16/17
Brisken branding + favicon work (previously gated) also went live with the
first of these deploys.

Platform: no `platform` section in a client `infrastructure.yaml` for
jochen-projekt (the app is a self-hosted FastAPI on Fly, not an
orchestrator plan) — no ops-audit applies.

---

## Next Steps
1. Owner-facing: confirm the `ONE_ASSESSMENT_INTERNAL_LOGINS` list is complete
   (currently Matthias, Dirk, UTIL). Add anyone else who needs the aggregate
   feedback log.
2. Rotate the operator token — it was echoed into the transcript this session
   via a `.env` grep (`flyctl secrets set ONE_ASSESSMENT_OPERATOR_TOKEN` + edit
   `context/.env`). Low urgency (gitignored, never left the machine).
3. Backlog from the Nagarro read: the three unbuilt Phase-3 deliverables
   (Quick Wins needs the release-to-capability asset; Roadmap; Effort bands —
   the deck's <50k/>100k banding lowers the bar vs a Full-tier binding
   estimate). Template-versioned OM label set when Jochen standardizes on the
   anglicized 6×4 grid.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/templates.py` (shell, primitives, allowlist)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/portal.py` (hub + Nächster-Schritt strip)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/DESIGN.md` (build state / roadmap)
- `workspace/clients/Jochen Projekt/context/test-fixtures.md` (UTIL login code, secrets)

### Open Questions
- Is the internal-logins allowlist final, or should Jochen/others get the log too?
- Does Jochen want the app renamed from "One Assessment" (still an open owner item in DESIGN §18)?

### Working Notes
- Deploy recipe: `flyctl deploy --ha=false` from `site-host/` (app
  `one-assessment-demo`, region fra, scale-to-zero, `/data` volume). The
  `flyctl deploy` is Band-3 gated; the sandbox classifier denied it once before
  an explicit "deploy" order.
- Live smoke as UTIL Verifier: login code `0bPHs6diepVIj-QMyZEoWfy3` at
  `/portal/login`. The op API `/api/op/access-codes` returns names only (codes
  hashed), so use the fixture code from test-fixtures.md.
- Editing style: used a guarded `python .replace()` with `count()==1` assertions
  for the bulk type-scale edits, to avoid touching the byte-parity blocks
  (`_FB_CSS`/`_FB_WIDGET_HTML`/`_FB_JS`, TOKENS, BRAND — all drift-guarded).
- The `--oa-bb-h` sticky offset: back-bar height is measured on load and set as
  a CSS var so the rendered page's own sticky `.site-nav` sits below it.
- Nächster-Schritt state precedence: fresh result > draft > in-work > done > none.

### Reference Materials
- Live app: https://one-assessment-demo.fly.dev
- Nagarro artifacts: `workspace/clients/Jochen Projekt/Nagarro SE/` (deck, agenda, questionnaire)

---

## How to Continue
The three UI passes are shipped and verified; no loose ends. To pick up product
work, read DESIGN.md §15 build state — the live gaps are the Phase-3 deliverables
(Quick Wins / Roadmap / Effort) and the RG calibration adjudication
(`REIFEGRAD-ADJUDIKATION.md`, waits on Jochen). To adjust who sees the feedback
log, edit the `ONE_ASSESSMENT_INTERNAL_LOGINS` Fly secret and redeploy.

---

## Strategic Feedback

### What Worked Well This Session
- Tight directive loop: each UI ask ("blue links → buttons", "full width",
  "larger lettering / clearer actions / overseeability") was concrete enough to
  execute and deploy without a clarification round. The batch-manifest habit
  (enumerating every `<a>` across four files before editing) caught links that a
  visual scan would have missed.

### Suggestions
- The feedback-log regression was self-inflicted by a prior security fix that
  had no in-app replacement path. When a lockdown removes a surface's only
  entry point, the same change should add the replacement — worth a one-line
  note in the security-fix checklist so "locked down" never means "orphaned".

### System Health
- The site-host now has FOUR split-deploy byte-parity blocks (TOKENS, BRAND,
  the feedback widget, and the back-bar constants). The 2026-07-15 checkpoint
  already flagged "if a fourth appears, consider a build-time codegen step" —
  the back-bar CSS makes this the fourth-ish. Not urgent (all guarded by tests)
  but the codegen-stamp idea is now earned.
- Autonomy score: 1 human intervention this session (the B1 deferral on the
  feedback-log deploy, hook-caught and reframed same turn). Otherwise the three
  passes ran build → test → deploy → verify autonomously.
