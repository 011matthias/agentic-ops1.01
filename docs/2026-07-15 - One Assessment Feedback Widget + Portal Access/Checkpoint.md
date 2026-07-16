# Checkpoint: One Assessment Feedback Widget + Portal Access

**Date:** 2026-07-15
**Status:** Deployed + live-verified. Feedback widget now on every logged-in portal page. 7 feedback items pending triage (next session).

---

## Summary
Added Navid Hamidian's portal access, re-diagnosed Jannik's failing login (server fine, code being mistyped), and put the same feedback widget the assessment pages carry onto every logged-in portal/intake page, then deployed to Fly and verified live.

---

## What Was Done This Session

### Portal access
1. Created **Navid Hamidian** access code via `cli code` (login_name "Navid Hamidian", client "Jochen Projekt"). Code `BdmJj5enw9HtPSR5w7brNjIH`. Verified live: exact login 303, wrong code 401, first-name-only 401.
2. Re-diagnosed **Jannik** (owner reported failure twice). His exact code `x_M2gp7KkpIxVZqMiy4kvH1e` returns 303 live both times checked; registry record intact, not revoked. Root cause is input mistype (leading lowercase `x` auto-capitalized on mobile; capital `I` in `KkpIx`; digit `1` in `H1e`). Not a server/deploy issue. Fix offered but NOT executed (needs owner yes): mint a fresh code free of look-alike characters.

### Feedback widget everywhere (the main build)
3. Ported the FAB + double-click feedback popover into the portal shell so it renders on every logged-in page, not only the rendered assessment pages.
   - `render.py`: factored the static widget markup into `_FB_WIDGET_HTML` (behavior identical; `_fb_widgets()` now composes it + the JS).
   - `templates.py`: carries byte-identical `_FB_CSS` / `_FB_WIDGET_HTML` / `_FB_JS` + `feedback_block(identity)`; `page()` gained a `reviewer=` param that injects the widget when a login is present.
   - Wired the authenticated callers: hub, `/portal/prozess` overview + 4 stations, intake wizard, result-pending, the two intake validation pages, and `not_found` (when logged in).
   - Backend needed no change: `/feedback` already accepts the client cookie identity.
4. Left OFF the login gate (no session → would 401) and the static legal pages (no `request` in those handlers; low value). Stated as a scope decision, not silent.
5. Deployed `flyctl deploy --ha=false` from `site-host/`. Verified live: `/healthz` 200; live login 303; `feedbackFab` + placeholder + correct `__fbReviewer` on `/portal`, `/portal/prozess`, `/portal/prozess/eingabe`.

---

## Key Decisions Made

### Widget duplicated, not shared (parity-guarded)
- **Choice:** the widget literals live in both `render.py` and `templates.py`, kept byte-identical.
- **Rationale:** the Fly image (`Dockerfile`) copies only the site-host modules; the pipeline package is not deployed, so a shared import is impossible. Same split-deploy constraint as the design tokens. New drift guard `tests/test_feedback_widget_parity.py` fails if the two copies diverge.

### Jannik fix not executed
- **Choice:** did not mint a replacement code.
- **Rationale:** minting is a live-registry write; `feedback_no_invasive_action_without_ask` needs an explicit per-action yes. Owner said "deploy" (authorizing the widget deploy), not "make a new code."

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../src/treasury_assessment/render.py` | Modified | Expose `_FB_WIDGET_HTML` constant (behavior unchanged) |
| `.../site-host/templates.py` | Modified | `_FB_CSS`/`_FB_WIDGET_HTML`/`_FB_JS` + `feedback_block()`; `page(reviewer=)` injects widget; `not_found` carries it |
| `.../site-host/portal.py` | Modified | hub / prozess overview+stage / result-pending pass `reviewer=login` |
| `.../site-host/intake.py` | Modified | wizard form + 2 validation pages pass `reviewer=login` |
| `.../tests/test_site_host.py` | Modified | `test_feedback_widget_on_every_portal_page` (end-to-end submit + read-back) |
| `.../tests/test_feedback_widget_parity.py` | Created | Drift guard vs render.py + escaping + page() gating |

(All under the gitignored `workspace/clients/Jochen Projekt/` tree — not in git; deployed only via `flyctl deploy`.)

---

## Current Status
Live on `one-assessment-demo.fly.dev`. 55/55 pytest green. Feedback reachable on every logged-in portal page for Jochen, Jochen Stiebe, Navid, Jannik (once he's in).

**7 feedback items sitting in the log, untriaged** (pulled this session) — see next-session prompt below.

---

## Next Steps
1. **Triage + act on the 7 feedback items** (the continuation prompt in `CONTINUE-PROMPT.md` starts here).
2. Resolve Jannik's login (relay copy-paste-safe code, or mint an entry-safe code on owner yes).
3. Add `Cache-Control: no-store` to portal/intake HTML responses (the "immer noch nicht da" stale-view root cause).
4. Pending Jochen items: question-bank curation, `reifegrad_pct`, Benefit-Voice.
5. Deferred a11y: intake form `<label for>` association; darken Produktweg green pill for AA.

---

## Context for Next Session

### Files to Read First
- `CONTINUE-PROMPT.md` (this folder) — the starting prompt
- `.../site-host/app.py` (feedback endpoints + gate), `render.py` / `templates.py` (widget)
- `docs/sessions/2026-07-15-context.yaml`

### The 7 feedback items (pulled live 2026-07-15)
From **Dirk (DN)**, 2026-07-14, on the assessment pages:
1. Pipeline "Eingabe" link jumps back to the Auswertung page instead of Eingabe (may already be fixed in a prior render.py pass — VERIFY on the live NextDecade demo before acting).
2. "action? where do fill the gaps?" (Lücke und Empfehlung) — make the gap section actionable.
3. Make the as-is data collection more detailed: show all data collected, the entire as-is input structure (Light-Fragebogen).
4. Need to regenerate the Ist-Aufnahme section when the input changes (changes the Reifegrad).

From **Jochen Stiebe**, 2026-07-15, on the new process pages:
5. "Einbau weiter Schritt nach Schritt 1 Eingabe: Workshop" — add a Workshop step after Step 1 Eingabe.
6. "Wir benötigen hier noch das Kapitel 4. Voraussetzungen" (Gap und Empfehlung) — add a "Voraussetzungen" chapter, sourced from the Component Framework.

(1 further row is a `UTIL Verifier` self-test note, ignore.)

### How to read the feedback live
Reviewer path (reviewer cookie, no client cookie): `POST /welcome {name, next:/feedback-log}` then `GET /feedback.jsonl`. Or `flyctl ssh console` into `one-assessment-demo` and `cat /data/feedback.jsonl`. Operator token does NOT gate `/feedback-log` (that path needs a reviewer cookie).

### Working Notes
- Deploy path: `flyctl deploy --ha=false` from `site-host/` (app `one-assessment-demo`, region fra, scale-to-zero, persistent `one_assessment_data` volume at `/data`). Registry + feedback + showcases live on the volume, survive deploys. A "not listening on 0.0.0.0:8080" warning during rolling deploy is the scale-to-zero machine caught mid-start; the health check still passed.
- Widget parity is enforced by `tests/test_feedback_widget_parity.py`. If you change the widget in `render.py`, re-sync `templates.py` or the test fails.

---

## How to Continue
Start a fresh session, `/resume jochen-projekt`, open `CONTINUE-PROMPT.md`, and work the feedback items top-down. Verify item 1 against the live demo first (it may be stale feedback).

---

## Strategic Feedback

### What Worked Well This Session
- "dann deploy" as a one-word authorization kept the deploy gate clean without a back-and-forth.
- Re-verifying Jannik's login live (read-only) instead of asking the owner to try again closed the diagnosis definitively.

### Suggestions
- The Jannik loop is a UX problem in the codes themselves. Worth generating access codes from an unambiguous alphabet (no `I l 1 O 0`, no leading lowercase) at mint time in `auth.new_access_code`, so hand-entry stops failing. One-line change, prevents the whole class.

### System Health
- The feedback widget is now a two-surface duplicated asset guarded by a parity test (like TOKENS). That's the third such split-deploy duplication; if a fourth appears, consider a build-time codegen step that stamps the shared literals into site-host from the pipeline package.
- Autonomy score: 1 human intervention (B1 stop-hook on a closing "want me to..." offer; reframed as a decision). Same recurring closing-offer class.
