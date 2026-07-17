# Checkpoint: One Assessment Workshop Channel + Feedback Resolution

**Date:** 2026-07-15
**Status:** DEPLOYED + live-verified. All 6 reviewer feedback items resolved; the third data source (workshop) is structurally integrated end to end.

---

## Summary
Worked the 7 live feedback items on the One Assessment portal (5 shipped, 1 partial, 1 util-note), then built the third data source Jochen required, a workshop-protocol channel (oa-workshop/v1) that flows into scoring with honest evidence-origin labeling, and finally an in-app feedback resolution feature (status badges in `/feedback-log`) plus an internal register. Three Fly deploys, one showcase republish, Dirk's portal code minted.

---

## What Was Done This Session

### Feedback triage + items (owner delegated "entscheid du")
1. **Item 1 (Eingabe-Link, Dirk):** already fixed (hash router ignores in-page anchors); added a render-side router-guard test.
2. **Item 2 (where do I fill the gaps, Dirk):** action-callout at the top of "Gap und Empfehlung".
3. **Item 3 (as-is detailed + editable, Dirk):** showing part already live (full Fragebogen sheets); editing part left as an open product feature.
4. **Item 4b (regenerable, Dirk):** `cli reassess --id --generated` (pull → assess → render → publish, mail opt-in).
5. **Item 5 (Workshop step, Jochen):** Workshop as step 2 everywhere (render "Die 4 Schritte" + `#pipe-workshop`, portal station, infographic, explainer).
6. **Item 6 (Kapitel 4 Voraussetzungen, Jochen):** `voraussetzungen` from the solution library (Component Framework, 20/20) surfaced per Funktion in step 4 + benefit cards.
- Side fixes: `Cache-Control: no-store` on all session HTML; entry-safe access-code alphabet (`XXXXX-XXXXX-XXXXX-XXXXX`, no I/O/0/1); intake `<label for>`/`id` association; Produktweg pill AA contrast.

### Workshop data channel (oa-workshop/v1) — the third data source
1. Plan-mode design (2 Explore + 1 Plan agent), approved.
2. `AreaSelection.workshop` + `TcfCell.source_origin`; new `stage1_workshop.py` (md/json parser, single-point cap 4000, merge, `template_md` prep checklist).
3. `stage2_fill` scores against TWO separate haystacks (probe+company / workshop), never concatenated (splice-quote guard); `source_origin` labels evidence "aus dem Workshop" vs "aus Ihrem Fragebogen".
4. Server: `workshop.json` store helpers + `PUT/DELETE /api/op/submissions/{id}/workshop` (parser-free, 409/413/400/404 guards); `GET` detail carries the workshop.
5. Render: `#pipe-workshop` shows the real protocol when present, byte-identical static block when absent (NextDecade honesty, proven by diff).
6. CLI: `cli workshop --template/--push/--pull/--delete`, `assess --workshop`, `inbox --pull` fetches sibling workshop.json, reassess consumes it.

### In-app feedback resolution
1. `/feedback-log` gains a Status column (offen/erledigt/teilweise/Notiz badges), muted resolved rows, "davon N erledigt" header.
2. `GET /api/op/feedback` + `POST /api/op/feedback/resolve` (bearer-gated, content-hash keys, separate `feedback_resolutions.json` keeps the log append-only) + `cli feedback --list/--resolve`.
3. Marked all 7 live: 5 done, 1 partial (as-is editing open), 1 note (UTIL).
4. `FEEDBACK-REGISTER.md` internal copy.

### Access
- Minted Dirk Neumann's portal code `3WXH8-FXAJZ-TFRVR-6W7JP` (Brisken (intern)), owner-approved via AskUserQuestion; live-verified 303/401/401.
- Handed over Navid Hamidian's existing login for sending.

---

## Key Decisions Made

### Workshop stays a separate field, not merged into probe
- **Choice:** `AreaSelection.workshop` distinct from `probe`; two separate traceability haystacks.
- **Rationale:** honest evidence origin ("aus dem Workshop"), and concatenating haystacks would let an 18-char run straddle the join boundary and pass as a fabricated splice quote.

### Server stays parser-free for workshop protocols
- **Choice:** operator writes markdown, CLI parses to JSON, server only caps + shape-checks.
- **Rationale:** DESIGN §8a doctrine (LLM/parsing operator-side, key never on server); mirrors the intake contract.

### Feedback resolutions in a side file, log stays append-only
- **Choice:** `feedback_resolutions.json` keyed by content hash, not edits to `feedback.jsonl`.
- **Rationale:** preserves the append-only audit log; resolutions survive restarts and duplicate timestamps.

### Dirk code minted (invasive) only after explicit yes
- **Choice:** AskUserQuestion before writing the live registry, despite the direct "hand me Dirk's login" request.
- **Rationale:** Dirk had no code (surprising fact worth surfacing) + label ambiguity; minting is a state-changing live action per the invasive-action rule.

---

## Files Modified
All under `workspace/clients/Jochen Projekt/` (gitignored — no commit/PR).

| File | Action | Purpose |
|------|--------|---------|
| src/treasury_assessment/models.py | Modified | AreaSelection.workshop, TcfCell.source_origin |
| src/treasury_assessment/stage1_workshop.py | Created | oa-workshop/v1 parser, merge, cap, template |
| src/treasury_assessment/llm.py | Modified | workshop prompt block + Mock echo |
| src/treasury_assessment/stage2_fill.py | Modified | two haystacks, source_origin routing |
| src/treasury_assessment/stage3_solution.py | Modified | voraussetzungen passthrough |
| src/treasury_assessment/render.py | Modified | action block, Voraussetzungen, workshop stage w/ data, origin label, pain workshop, 4-Schritte, _qa_sheet param |
| src/treasury_assessment/cli.py | Modified | --workshop, inbox workshop pull, cmd_workshop, cmd_feedback, reassess |
| site-host/app.py | Modified | no-store middleware, feedback resolution endpoints + log badges |
| site-host/auth.py | Modified | entry-safe code alphabet |
| site-host/store.py | Modified | workshop.json helpers |
| site-host/operator_api.py | Modified | workshop PUT/DELETE, workshop in op_get |
| site-host/portal.py | Modified | Workshop station + renumber, Voraussetzungen schema, pill contrast |
| site-host/templates.py | Modified | infographic 4 steps, explainer workshop |
| site-host/intake.py | Modified | label/id association |
| NextDecade/run_assessment.py | Modified | --render-only --as-of, source_origin |
| tests/test_workshop.py | Created | 11 pipeline/parser/render tests |
| tests/test_pipeline.py | Modified | voraussetzungen, 4-step + router guard |
| tests/test_site_host.py | Modified | counting model, no-store, code alphabet, labels, workshop endpoint, feedback resolution |
| PIPELINE-NOTES.md | Modified | sections O + P |
| DESIGN.md | Modified | build-state rows |
| FEEDBACK-REGISTER.md | Created | internal feedback-status copy |

**Live state changes:** 3× `flyctl deploy` (latest healthy, all verified); NextDecade showcase republished (volume write); `feedback_resolutions.json` written (7 marks); Dirk Neumann access code minted.

---

## Current Status
Live at https://one-assessment-demo.fly.dev, verified. 71/71 pytest. Feedback-log shows "davon 7 erledigt". Demo + `/portal/beispiel/nextdecade` show the 4-step flow with Voraussetzungen; workshop channel armed (first real use when a workshop happens). No `platform` section in infrastructure.yaml (Fly-hosted FastAPI, not Make/n8n — no ops-audit needed).

---

## Next Steps
1. **First real workshop:** `cli workshop --id <fall> --template` → fill → `--push` → `cli reassess`. The channel is untested against a live client submission (only mock E2E + TestClient so far).
2. **Item 3 editing (open):** editable As-Is workbench (reopen input post-submit, change answers/docs, ad-hoc topics). Biggest open feature; DESIGN §PLANNED.
3. **Workshop-memo verification playback** (Jochen's methodology): play the protocol back to the client to confirm/change. PLANNED.
4. **Pending Jochen sign-off (no code):** question-bank curation, reifegrad_pct scale, benefit voice.
5. **Optional:** mint Jannik an entry-safe code (his current one works via copy-paste); owner has not said yes.

---

## Context for Next Session

### Files to Read First
- workspace/clients/Jochen Projekt/automations/treasury-assessment/FEEDBACK-REGISTER.md
- workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md (§P workshop, §O feedback round)
- workspace/clients/Jochen Projekt/automations/treasury-assessment/src/treasury_assessment/stage1_workshop.py
- workspace/clients/Jochen Projekt/automations/treasury-assessment/DESIGN.md (build-state table)

### Open Questions
- Client label for Dirk's portal entry ("Brisken (intern)" chosen; owner may want another).
- Whether the workshop channel should eventually accept the raw audio transcript operator-side via `cli extract` (currently a separate PLANNED §8a item for documents).

### Working Notes
- **Deploy path:** `flyctl deploy --ha=false` from `site-host/`, waits for explicit owner "deploy". Showcase/registry are volume writes surviving deploys; render.py changes reach the demo only via re-render + showcase republish.
- **NextDecade render-only:** `run_assessment.py --render-only --as-of <date>` re-renders from saved result.json with no LLM run; deterministic Stage-3 enrich fills new fields (e.g. voraussetzungen). Byte-identical when no workshop doc.
- **Feedback keys** (content-hash, for future resolves): pulled live via `cli feedback --list` / `GET /api/op/feedback`.
- **Codes documented:** Jochen `J6q1WfqP5rsyCsNyfXbgU6iu`, Jannik `x_M2gp7KkpIxVZqMiy4kvH1e`, Navid `BdmJj5enw9HtPSR5w7brNjIH`, Dirk `3WXH8-FXAJZ-TFRVR-6W7JP` (new format). Old codes' plaintext is unrecoverable (hashed) — mint fresh if lost.
- **Failed approach:** Playwright/CDP browser click-test of Item 1 hung ~30 min against the user's busy Edge (known pattern); verified statically via live HTML + a new render test instead. Don't reach for CDP browser automation against the live Edge for these checks.

### Reference Materials
- Plan file: C:\Users\neuma_p1qrsic\.claude\plans\jochen-sagt-wir-m-ssen-peppy-mist.md
- Live app: https://one-assessment-demo.fly.dev (portal), /demo (NextDecade), /feedback-log (internal, reviewer cookie)

---

## How to Continue
Run a real workshop through the loop (template → push → reassess) to validate the channel against a live submission, or pick up the editable As-Is workbench (item 3's open half). For access issues, all four Jochen-side + Dirk logins are live; mint via `cli code` (now entry-safe).

---

## Strategic Feedback

### What Worked Well This Session
- "entscheid du" on the feedback triage let me batch all six items without round-tripping each wording decision; plan-mode for the workshop channel caught a real design flaw (haystack splice) before any code.

### Suggestions
- The workshop channel needs one real protocol to shake out the markdown parser against how a memo is actually written; a 10-minute dry run with a fake submission would de-risk the first live use.

### System Health
- The treasury-assessment app now has three distinct deploy-gated surfaces (site-host code, showcase volume, registry) plus render.py that only reaches the demo via republish. This split is powerful but easy to mis-sequence; PIPELINE-NOTES §N/§O/§P captures it, but a one-page "what a change touches → what to redeploy" map would prevent a future stale-surface slip.
- Autonomy score: 0 human interventions this session — the 1 friction event (CDP browser hang) was self-detected and self-corrected.
