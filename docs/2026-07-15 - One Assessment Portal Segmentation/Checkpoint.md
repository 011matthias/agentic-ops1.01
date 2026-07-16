# Checkpoint: One Assessment Portal Segmentation

**Date:** 2026-07-15
**Status:** DEPLOYED + live-verified (one-assessment-demo.fly.dev). Portal reworked; adversarial review + owner reports all fixed.

---

## Summary
Reworked the whole One Assessment client portal per the 2026-07-15 audit: one connecting header nav, a slim back-bar injected into the rendered pages, a state-aware hub, reviewer/customer separation, a unified "3 Schritte + Ergebnis" counting model, shared design tokens + portal dark mode + branded 404, and a 5-step intake wizard, plus two data bugs. A 13-agent adversarial review found 8 real findings (incl. a HIGH access-control bug) and the owner reported the start button was buried; all fixed and redeployed.

---

## What Was Done This Session
### Portal segmentation (the 5 audit requirements)
1. **Connecting header** on every portal surface (clickable logo -> /portal; tabs Ihr Bereich / Prozess / Beispiele with active marking; theme toggle) incl. Impressum/Datenschutz/Login. Slim **back-bar** injected at the `</head>` point of the rendered pages (`templates.head_inject`): Beispiel-Ansicht / Ihre Auswertung / Interne Demo-Ansicht + return link.
2. **State-aware hub**: after two owner corrections, "Ihr Assessment" (list of their questionnaires + finished evaluations + start button) is ALWAYS at the top; infographic + examples below. `?submitted=` banner; `id=beispiele`; "Zu Ihrem Assessment" on each process station.
3. **Reviewer/customer split**: `/demo` reviewer-only; anon unknown -> `/portal/login`; context-aware `/welcome`; feedback POST accepts the client cookie after the 12h reviewer cookie lapses.
4. **One counting model** "3 Schritte + Ergebnis" (Ergebnis = checkmark, incl. render.py); station cross-links -> `#pipe-1/2/3`; old `#s1-s5` kept; internal view keys pipeline/auswertung/wachstum unchanged.
5. **Shared foundation**: one token block (`templates.TOKENS` == `render._TOKENS`, drift-guard test; deleted the third app.py CSS copy), portal dark mode (localStorage key `theme`), branded 404 `templates.not_found`.

### Mid-turn owner additions
- **5-step intake wizard** (Rahmen & Kontakt -> Themen -> Fragen -> Unterlagen -> Prüfen & Einreichen), progressive enhancement (all fields stay in DOM; read-only / JS-off = plain scroll).
- **Two data bugs**: submit only after a CONFIRMED save (no silent answer loss); email promised only when an address was given (confirm dialog + EXPLAINER + `_P_ERG`).

### Fixes from the adversarial review (8 confirmed, 0 false positives)
- **HIGH access control (OWASP A01):** `/feedback-log` + `/feedback.jsonl` were readable by any logged-in customer (login mints an oa_reviewer cookie), exposing everyone's notes + IP/UA. Now `INTERNAL_PATHS` = reviewer cookie AND no oa_client; customer -> /portal. `/demo` back-bar made customer-aware.
- **HIGH (cosmetic):** read-only wizard leaked dead nav buttons (`display:flex` beat `[hidden]`) -> added `.wz-bar[hidden],.wz-nav[hidden]{display:none}`.
- bug2 completeness (EXPLAINER + `_P_ERG` still promised email); `/api/op` exact-path gate; reviewer-only 404 now offers "Zur Demo"; theme toggle added to /welcome + /feedback-log; render.py Ergebnis "4" -> checkmark.

### Verification
50/50 pytest (added: security gate, /api/op, drift guard, wizard/nav, counting, back-bar, feedback client-cookie); 7 JS blobs `node --check`; wizard + submit-guard run against the actual shipped JS in a DOM shim (14/14 + 8/8); **42/42 live checks** incl. the security lockdown. Deployed twice; `site/index.html` re-rendered; `musterkunde` showcase re-PUT (byte-identical to /demo).

---

## Key Decisions Made
### "Ihr Assessment" always on top (overrode audit req 2)
- **Choice:** Put the assessment list + start button at the top of the hub for everyone, not infographic-first for first-timers.
- **Rationale:** Owner reported twice that the start button was buried and finished assessments belong up top. The live directive supersedes the earlier "Erstbesucher sehen Infografik zuerst".

### Tokens duplicated + drift-guarded, not shared as a module
- **Choice:** `templates.TOKENS` and `render._TOKENS` are identical literals with a test asserting equality.
- **Rationale:** The running Fly app imports only the flat site-host modules, never the pipeline package, so a shared module isn't importable at runtime across the two deploy roots.

### Feedback log gated on "reviewer AND not customer"
- **Choice:** No separate internal-reviewer identity exists (the reviewer cookie is minted for customers too), so internal-only = reviewer cookie present AND no oa_client cookie.
- **Rationale:** Closes the A01 exposure without a schema change.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/templates.py | Modified | Shared TOKENS, theme boot/toggle, header nav, head_inject back-bar, not_found, dark overrides, EXPLAINER bug2 |
| .../site-host/app.py | Modified | Gate rework (INTERNAL_PATHS, /api/op exact, anon->login), context /welcome + toggle, feedback client-cookie, branded 404 handler, /demo customer-aware back-bar, deleted 3rd CSS copy |
| .../site-host/portal.py | Modified | Hub ordering (own on top), id=beispiele, 3-Schritte+Ergebnis counting, #pipe anchors, Zu Ihrem Assessment, back-bar in showcase/result, branded 404s, _P_ERG bug2 |
| .../site-host/intake.py | Modified | 5-step wizard, submit-after-confirmed-save, conditional mail, [hidden] guard, branded 404s |
| .../src/treasury_assessment/render.py | Modified | Shared _TOKENS, pipe-1 dedup, Ergebnis checkmark |
| .../site-host/site/index.html | Regenerated | build_site.py --generated 2026-07-15 (checkmark + tokens) |
| .../tests/test_site_host.py | Modified | New tests (security, /api/op, ordering, wizard, counting, back-bar, feedback client-cookie) |
| .../tests/test_design_tokens.py | Created | Token drift guard |
| ~/.claude/.../memory/project_jochen_treasury_assessment.md | Updated | 2026-07-15 segmentation + security entry |

(All of Jochen Projekt is gitignored -- no commit/PR. Deploy = `flyctl deploy` from site-host/.)

---

## Current Status
Live and verified on https://one-assessment-demo.fly.dev (Fly image deployment-01KXHFZ09XHZ..., single machine `e823d14c3e7448`, region fra, auto-stops when idle). All 8 review findings + both owner reports fixed. The live `/portal` correctly serves "Ihr Assessment" + start button at the top (confirmed via UTIL fixture). NextDecade untouched behind the code gate.

**Likely-stale-view note:** `/portal` responses set **no Cache-Control header**, so the owner's browser very probably showed a cached page after the redeploy ("immer noch nicht da"). A hard refresh (Ctrl+F5) resolves it; the durable fix is `Cache-Control: no-store` on the portal HTML responses (not yet built).

---

## Next Steps
1. **Add `Cache-Control: no-store`** (or `no-cache`) to the portal/intake HTML responses so a redeploy is visible without a hard refresh. This is the root cause of the "still not there" confusion.
2. (Owner-cancelled this session) Optionally surface the Beispiele under a button on `/portal/prozess` (the owner floated it, then said nevermind).
3. Get the two open Jochen items unblocked (question-bank curation, reifegrad_pct, Benefit-Voice) -- still pending Jochen.

---

## Context for Next Session
### Files to Read First
- workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/app.py (gate/tiers + 404 handler)
- .../site-host/portal.py (hub + process pages) and .../site-host/intake.py (wizard)
- .../PIPELINE-NOTES.md §O-§P and docs/2026-07-14 - One Assessment Intake Portal + Portal Home/Seiten-Audit.md
- context/test-fixtures.md (UTIL portal code; NextDecade warning)

### Open Questions
- Should the portal cache policy be `no-store` (always fresh, tiny page) or `no-cache` (revalidate)? Tiny HTML, `no-store` is simplest.
- Does the owner want the state-dependence back (infographic-first for true first-timers) or is always-own-first final? Current = always own-first.

### Working Notes
- The review's HIGH access-control bug largely PRE-EXISTED this session (the old gate also keyed /feedback-log on the reviewer name, which customers hold); this session's back-bar link made it more discoverable, and the review + fix closed it.
- The wizard is progressive enhancement: `_FORM_JS` is only injected when editable, so read-only degrades to a plain scroll. The `[hidden]` guard is load-bearing.
- Live verification scripts (curl UTIL fixture) + JS DOM shims are in the session scratchpad; re-derive from the test suite if needed.
- Deploy recipe: re-render site/index.html (build_site.py) if render.py changed, then `flyctl deploy --ha=false` from site-host/. Showcases are separate files on the volume (re-PUT via `cli showcase` or a direct API PUT to preserve the description).

### Reference Materials
- https://one-assessment-demo.fly.dev (UTIL: `UTIL Verifier` / `0bPHs6diepVIj-QMyZEoWfy3`)
- Adversarial review result: session task output wcg37ui7p (8 confirmed findings)

---

## How to Continue
The rework is live and green. If picking up: start with the `no-store` cache-header fix (Next Step 1), redeploy, and confirm with a fresh browser that the hub renders assessments + start on top. Everything else is verified.

---

## Strategic Feedback

### What Worked Well This Session
- The adversarial review workflow earned its keep: it caught a real HIGH access-control bug that 50 passing tests + 42 live checks missed. Running a structured review over the diff before calling a substantial change "done" is worth the tokens.

### Suggestions
- When redeploying a change you want to eyeball on the live site, hard-refresh (Ctrl+F5) the tab; the portal currently sends no cache headers, so a normal reload can show the old page.

### System Health
- **Verification gap:** the pre-deploy suite had no access-control / authz test, so "verified" did not mean "secure" -- the bug shipped in deploy #1. The durable fix landed (INTERNAL_PATHS + `test_feedback_log_is_internal_only`), but the general lesson is that a routing/gate change should always carry a "who must NOT reach this" test, not just "who may".
- **Caching:** dynamic HTML with no cache headers is a recurring source of "did the deploy work?" confusion; a small default `no-store` on the portal responses would remove it.
- Autonomy score: 3 human interventions this session (2 hub-ordering reports + 1 stale-view report).
