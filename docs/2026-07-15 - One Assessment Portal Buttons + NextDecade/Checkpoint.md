# Checkpoint: One Assessment Portal Buttons + NextDecade

**Date:** 2026-07-15
**Status:** DEPLOYED + live-verified (one-assessment-demo.fly.dev). Buttons/layout rework, NextDecade as the sole example + demo case, review fixes shipped.

---

## Summary
Second same-day pass on the One Assessment portal: turned every standalone blue link into a button, made the forward "Weiter" the clear primary control (and killed a dead one on the last wizard step), enlarged + widened + grid-ified the four process one-pagers with equal-height cards on steps 2/3, and switched the example customer to NextDecade only (showcase links + `/demo` + labels; Musterkunde showcase deleted). A 13-agent adversarial review found 8 real issues (incl. a regression I introduced); 6 fixed, 2 deferred. Deployed to Fly and verified on the live origin. Also minted + smoke-tested a portal access code for Jochen.

---

## What Was Done This Session
### Links to buttons (whole app)
- One button system in `templates.PORTAL_CSS`: `.btn` (primary filled), `.btn.ghost` (outline), `.btn.sm`, `.btn.danger`, `.btnrow`. Converted the standalone action/nav links across hub, process pages, showcase card, table-row actions (Weiter ausfullen / Auswertung ansehen / Loschen), back-bar, `/welcome`. In-sentence links (login "(Datenschutz)") + footer legal stay plain text.

### "Weiter" adjustment
- Process-page `_stage_nav`: forward step = primary `.btn` on the right; back/Ubersicht = `.btn.ghost.sm`.
- Intake wizard `#wzNext`: enlarged + a sticky bottom bar.

### Four process one-pagers enlarged
- `.proc-wrap` 1160px (was 820), a `.proc-hero` (big number chip + big h1 + lead + a `.proc-rail` 1-2-3-check step rail), grid bodies (`.qb-grid` questionnaire, `.proc-cols` two-column for stations 2/3, `.erg-grid` 6 cards for Ergebnis), `.proc-cta` strip.
- **Equal-height cards on 2/3** (owner ask): heading full width, then the schema card and the example card as direct `.proc-cols` grid children with `align-items:stretch` (+ zeroed schema margin) so both share one height.

### NextDecade = the only example customer (owner directive)
- `_EXAMPLE` + `_PRODUKTWEG` links -> `/portal/beispiel/nextdecade#{pipe-1/2/3,auswertung,wachstum}` (anchors verified live: pipe-* are ids, auswertung/wachstum are `data-view` fragment-switches). Labels "NextDecade".
- **`/demo` now serves the nextdecade showcase** (`app.DEMO_SHOWCASE_SLUG`, via `store.load_showcase`, fallback = baked `site/index.html`). Login button + hub line + `_welcome_copy` de-Musterkunde'd.
- **Musterkunde showcase DELETED** on prod (`DELETE /api/op/showcase/musterkunde`, `{"ok":true}`). Only `nextdecade` remains.
- Owner authorized public exposure: "das muss fur jeden Nutzer der den Link bekommt sichtbar und einfach zuganglich sein" (`/demo` is name-gated only = effectively public).

### Adversarial-review fixes (8 confirmed, 6 fixed / 2 deferred)
- FIXED: dead `#wzNext` on the last wizard step (`.btn{display:inline-flex}` beat the UA `[hidden]`; added `.btn[hidden]{display:none}`); primary `.btn` white-on-accent AA fail in dark (dark override to brand-blue `#2563eb` fill + hover + number chips + logo); error-red `#b3261e` dark override; `.hint` base in PORTAL_CSS (unstyled on hub with no draft); login `p.err` dark override; hub `<h1>`.
- DEFERRED (pre-existing): form-field `label for/id` association; green Produktweg pill contrast.

### Verification + deploy
- 51/51 pytest (added: button/layout test, `/demo`-serves-nextdecade behavioral test, `.btn[hidden]` regression guard, NextDecade anchor asserts). 0 em-dashes; validate-html clean; 7 static preview renders.
- `flyctl deploy --ha=false` (image deployment-01KXHM2S...). Live-verified: `/portal` (nextdecade card, 0 Musterkunde), process pages (proc-hero/rail, nextdecade#pipe, `.btn[hidden]` + dark `.btn` shipped), login "Demo ansehen: NextDecade", `/demo` (132KB, banks JPM/UOB, Schmerzpunkt/Pain Points, Interne Demo-Ansicht bar).
- Jochen access code created + smoke-tested (login name `Jochen`, portal loads, wrong-name -> 401).

---

## Key Decisions Made
### `/demo` serves the live nextdecade showcase (not a re-render)
- **Choice:** point `/demo` at the already-published `nextdecade` showcase file (runtime), fallback to the baked `site/index.html`.
- **Rationale:** one canonical NextDecade rendering (no drift, no re-derivation), no real customer data into git (`site/index.html` + the `out/2026-07-14-nextdecade/*.json` source are both gitignored). Cleaner than rebuilding `site/index.html` via a NextDecade `build_site` variant.

### NextDecade made intentionally public
- **Choice:** NextDecade (real case, person-names removed, company + banks shown) is the sole example AND the name-gated `/demo` case.
- **Rationale:** explicit, informed owner directive after the confidentiality flag was raised. Recorded in `context/test-fixtures.md` so a later session does not "helpfully" remove it.

### Equal-height via grid children, not wrapper
- **Choice:** put `.schema` and `.proc-example` as direct `.proc-cols` children with `align-items:stretch` (+ `.proc-cols>.schema{margin:0}`), heading above / note below.
- **Rationale:** stretching a wrapper would not stretch the inner card; margins on one child would desync the heights.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| .../site-host/templates.py | Modified | Button system (.btn/.ghost/.sm/.danger/.btnrow), `.btn[hidden]` guard, dark `.btn`+chip overrides, `.hint` base, back-bar pill, INFOGRAPHIC button |
| .../site-host/portal.py | Modified | Process-page redesign (hero/rail/grids/cta/stage-nav, equal-height cols), `_EXAMPLE`/`_PRODUKTWEG` -> nextdecade, `_row` button actions, login+hub NextDecade labels, login p.err dark, hub h1, `_P_ERG` reword |
| .../site-host/intake.py | Modified | Sticky prominent `#wzNext`, error-red dark override, link->button conversions |
| .../site-host/app.py | Modified | `import store`, `DEMO_SHOWCASE_SLUG`, `_demo_html()` (serve nextdecade showcase), `_welcome_copy` reword |
| .../tests/test_site_host.py | Modified | New button/layout + `/demo`-nextdecade + `.btn[hidden]` tests; nextdecade anchor + label asserts |
| .../context/test-fixtures.md | Modified | NextDecade = deliberate public example (do-not-remove note) |
| .scratch/oa-preview/oa_preview.py | Created | Local static-render preview harness (ephemeral) |

(All of Jochen Projekt is gitignored -- no commit/PR. Deploy = `flyctl deploy` from site-host/.)

---

## Current Status
Live and verified on https://one-assessment-demo.fly.dev (image deployment-01KXHM2S..., machine e823d14c3e7448, fra, auto-stops when idle). Only NextDecade shows as the example + demo. Jochen has a working portal code.

**Jochen access (handed to owner):** `/portal/login`, name `Jochen`, code held by owner (not stored here). `/demo` needs no code (name only).

---

## Next Steps
1. **Deferred a11y (small):** associate intake form `<label>`s with inputs (`for/id` or wrap); darken the Produktweg green pill text for AA.
2. **Cache-Control:** the portal HTML still sends no cache header (the earlier "immer noch nicht da" root cause) -- add `no-store` if stale-view confusion recurs.
3. Still pending Jochen: question-bank curation, reifegrad_pct, Benefit-Voice.

---

## Context for Next Session
### Files to Read First
- .../site-host/app.py (`_demo_html` + `DEMO_SHOWCASE_SLUG`, gate/404)
- .../site-host/portal.py (process pages: hero/rail/grids, `_EXAMPLE`, `_stage_nav`) and templates.py (button system)
- context/test-fixtures.md (UTIL code; NextDecade public-example note; operator `.env` at the CLIENT `context/` level, NOT under automations/)

### Open Questions
- Keep `/demo` coupled to the nextdecade showcase (current), or bake an independent NextDecade `site/index.html`?

### Working Notes
- **Operator `.env` lives at `workspace/clients/Jochen Projekt/context/.env`** (client level), NOT under `automations/treasury-assessment/context/`. Using the wrong path returns empty vars silently.
- The adversarial review caught a regression I introduced: adding `display:inline-flex` to `.btn` defeated the `hidden` attribute on `#wzNext` (author-origin display beats UA `[hidden]`). Transferable lesson: any `.btn` that is toggled via the `hidden` attribute needs a `.btn[hidden]{display:none}` guard -- the code already had this pattern for `.wz-bar`/`.wz-nav` but not the button.
- Live-verify scripts (curl + UTIL/operator token) are in the session scratch; the preview harness re-renders the portal pages to `.scratch/oa-preview/`.

### Reference Materials
- https://one-assessment-demo.fly.dev (UTIL: `UTIL Verifier` / `0bPHs6diepVIj-QMyZEoWfy3`)
- Adversarial review result: task `w2f2wgryq` (8 confirmed findings)

---

## How to Continue
Everything is live and green. If picking up: the two deferred a11y items are the only open portal work; otherwise the pending Jochen content items (question bank, reifegrad, benefit voice) are the substance.

---

## Strategic Feedback

### What Worked Well This Session
- Build-solo-then-adversarially-review is paying off repeatedly: the 13-agent review caught a regression I introduced AND real dark-mode AA failures that 51 passing tests missed, all before deploy.

### Suggestions
- When you want a link "for anyone with the link", say whether it's the code-less `/demo` view or the logged-in portal -- they are different surfaces (one round-trip lost this session guessing).

### System Health
- **Verification env footgun:** the operator `.env` path is easy to get wrong (client `context/` vs the automations subtree). Recorded in the checkpoint + test-fixtures; a `tools/` helper that resolves it would remove the recurrence.
- Autonomy score: 1 human intervention (the Jochen-link interpretation) + 2 self-detected slow-paths (wrong `.env` path, bare-`cd` cwd drift). The design refinements (equal-height, NextDecade, public `/demo`) were new requirements, not corrections.
