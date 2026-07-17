# Checkpoint: One Assessment Intake Portal + Portal Home

**Date:** 2026-07-14
**Status:** LIVE on https://one-assessment-demo.fly.dev — portal is the home page, all features verified live

---

## Summary

Built the One Assessment online intake portal end-to-end (self-assembling Fragebogen, uploads, access-code logins, Graph notification mails, showcases) and evolved the site through four owner-directed iterations into its current shape: the portal hub IS the home page, every process station has its own detail page carrying the real templates/structures, and the Musterkunde demo has visible entry points.

---

## What Was Done This Session

### Intake portal (built + deployed)

1. Question bank from the blank STAEDTLER template (`build_question_bank.py`, 338 questions, 88 curated quick; curation PENDING JOCHEN in `question_bank_curation.json`)
2. 3-tier auth: demo name gate (unchanged) / client tier (name + hashed access code, `oa_client` 30d sliding) / operator Bearer token
3. Submissions store on the Fly volume (`/data/intake/`, status entwurf→eingereicht→in_bearbeitung→fertig, events.jsonl, atomic writes)
4. File uploads: raw-body per file, allowlist xlsx/csv/docx/pdf/pptx, magic bytes, 25MB/20 files/100MB caps, sha256 manifest
5. Operator CLI: `assess` (incl. `--mock`), `inbox --pull` (sha256 verify), `publish` (mints fresh access code + Graph mail), `code --mail`, `showcase`

### Notifications + showcases

1. Graph mail as matthias.silva@brisken.com, operator-side only (server calls NO APIs in dev phase); HARD allowlist assert per rule_brisken_graph_first
2. Access codes ride in every notification/invite mail; login page hints where to find them
3. Showcase injection: `PUT /api/op/showcase/{slug}` → `/portal/beispiel/{slug}`

### Render standard + NextDecade case

1. Tabs "Die 3 Schritte" / "Ergebnis" / "Produktweg" (internal view keys unchanged); infographic pipe-nodes; Ergebnis opens with "Schmerzpunkte und Bedarf" (verbatim client quotes only)
2. NextDecade: real gpt-4o run from `intake-md/` (20 cells, overall 44%, 16/20 sourced, $0.0506); PII scrub (13 names + 100xxx IDs) at render; scope_note never renders as client quote
3. Produktweg honesty fix (B4): step 1 "Formular geplant" was stale after the portal shipped → now "live"; both showcases re-rendered

### Portal home + page-per-station (final shape)

1. `/` = home: redirect matrix (client cookie → /portal, reviewer → /demo, anonymous → /portal/login); demo moved to `/demo`, fragments survive the 303 so old deep links hold
2. `/portal/prozess` = overview (4 stage cards + s5 Produktweg); each infographic button now opens its OWN page: `/portal/prozess/{eingabe,ist-situation,empfehlung,ergebnis}` with prev/Übersicht/next nav
3. Station pages carry the real material: live questionnaire template from `question_bank.json` (Eingabe), entry schemas for Ist-Situation and Gap/Empfehlung (slot cards, no invented data), fixed Ergebnis section order mirroring `#auswertung`
4. Demo entry points: ghost button "Demo ansehen: Musterkunde" on `/portal/login` + link line in the hub's Beispiel-Assessments card

---

## Key Decisions Made

### Server never runs the pipeline (dev phase)

- **Choice:** Hosted server only collects; all pipeline runs happen locally via `cli assess` (owner directive)
- **Rationale:** No API keys on the host, operator reviews every run

### Notification mails from matthias.silva@brisken.com

- **Choice:** Operator-side Graph send, hard mailbox allowlist, codes hashed at rest with fresh mint per mail
- **Rationale:** Owner directive; neutral One Assessment sender domain stays an open owner decision

### Page-per-station over anchor navigation

- **Choice:** Four own pages + overview instead of one long page with anchors
- **Rationale:** Owner: "ausführliche Trennung und Übersicht"; old s1-s4 anchors kept on the overview

### Slot schemas instead of example data on the prozess pages

- **Choice:** Structure cards show labeled slots, never invented client values (B4)
- **Rationale:** Deep links onto the living Musterkunde case provide the real example

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/app.py` | Modified | `/` = portal home redirect matrix, demo at `/demo` |
| `.../site-host/portal.py` | Modified | Login, hub, stage pages `_STAGES`, overview, showcases, legal pages, demo entry points |
| `.../site-host/intake.py` | Modified | Form fragment embedding, uploads, autosave, goto=portal |
| `.../site-host/{auth,store,templates,operator_api,build_question_bank}.py` | Created | 3-tier auth, volume store, shells + infographic, operator API, question bank |
| `.../src/treasury_assessment/{cli,stage1_intake,md_intake,render,stage2_fill}.py` | Modified | assess/inbox/publish/code/showcase, oa-intake reader, md reader + source_qa, render standard + growth honesty, `_traceable()` guard |
| `workspace/clients/Jochen Projekt/NextDecade/run_assessment.py` | Modified | PII scrub + expectations fix + source_qa |
| `.../tests/test_site_host.py` | Modified | 37 tests incl. root matrix, prozess structures, uploads, gates |
| `.../PIPELINE-NOTES.md` (§J-§P) / `DESIGN.md` (§8a et al) | Modified | Runbooks + design state |
| `workspace/clients/Jochen Projekt/context/{.env,test-fixtures.md}` | Created/Modified | Operator creds (gitignored); UTIL fixture + NextDecade gating WARNUNG |
| Memory: `project_jochen_treasury_assessment.md`, `feedback_reviews_in_plain_language.md` | Modified/Created | Project state; plain-language review directive |

---

## Current Status

Everything the owner ordered this session is LIVE and verified on https://one-assessment-demo.fly.dev: 37/37 pytest, live-check rounds 14/14 → 17/17 → 16/16 against the deployed origin. Both showcases injected (Musterkunde 90.2 KB, NextDecade 132.4 KB). Production data on the Fly volume: users.json (UTIL Verifier + Matthias Silva), showcases, no client submissions yet.

---

## Next Steps

1. **Owner asked (this checkpoint's turn): audit the pages for visual + functional improvements and write a prompt for better page-to-page segmentation** — in progress in the current session
2. Waiting on Jochen: Quick-Satz curation review, reifegrad_pct band mapping, benefit voice
3. Open owner decisions: neutral One Assessment mail sender domain; NextDecade case anonymization/removal BEFORE any external access code (HARD RULE)
4. Future build (decided shape, not ordered): `cli extract` document-to-dimension extraction (`evidence/` with typed extractors)
5. Exchange Application Access Policy for the Graph credential still missing (compensating hard allowlist in code)

---

## Context for Next Session

### Files to Read First

- `workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md` (§J-§P = this session's runbooks)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/DESIGN.md` (§8a intake portal)
- `workspace/clients/Jochen Projekt/context/test-fixtures.md` (UTIL login + NextDecade WARNUNG)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/portal.py` (hub + stage pages)

### Open Questions

- Neutral sender domain for One Assessment mails (currently matthias.silva@brisken.com per directive)?
- Is corpus "Nagarro SE" case actually the NextDecade engagement (title "for Nagarro")? Ask Jochen.

### Working Notes

- Graph gotcha: `contains()` `$filter` + `$orderby` = InefficientFilter, silently swallowed by `.get('value')` — filter without orderby
- Exchange Safe Links rewrites URLs in mail bodies — never match bare paths in body checks
- Live-verify pattern: scratchpad `live_verify{3,4,5}.py` (httpx + UTIL fixture + cleanup); `live_verify4.py --push` re-PUTs both showcase HTMLs
- Showcase rebuild: `uv run python site-host/build_site.py --generated {date}` (Musterkunde) + scratchpad `rerender_nextdecade.py` (no LLM re-run)
- Deploy: `flyctl deploy --remote-only` from `site-host/` (classifier requires the deploy to be named in the current turn)

### Reference Materials

- https://one-assessment-demo.fly.dev (login: UTIL fixture in context/test-fixtures.md)
- Fly app `one-assessment-demo`, volume `one_assessment_data` (1GB, fra)

---

## How to Continue

`/comd_resume jochen-projekt` → read PIPELINE-NOTES §J-§P. For UI work: edit `site-host/{portal,templates,intake}.py`, run `uv run pytest tests/ -q`, deploy on owner order, verify with a `live_verify*.py` round. The audit + segmentation prompt from this checkpoint's turn continues in the current session.

---

## Strategic Feedback

### What Worked Well This Session

- Owner's screenshot-driven directives ("mach die Seite hier im screenshot zur haupt home page") were unambiguous and fast to execute against
- The per-turn "deploy" order pattern kept the gated floor clean without slowing iteration

### Suggestions

- The four-iteration UI evolution (hub → home → split pages) happened in single-feature turns; a short sketch of the target sitemap up front would have collapsed two rounds into one. The segmentation prompt being written this turn is exactly that artifact.

### System Health

- Autonomy score: 1 human intervention this session (plain-language review correction → `feedback_reviews_in_plain_language.md`). Fragile fix — memory-based; consider a rule-layer addition to `rule_human_communication.md` if it recurs.
- The em-dash-strip-gate + validate-output hooks fired correctly on all client-path writes; no drift.
