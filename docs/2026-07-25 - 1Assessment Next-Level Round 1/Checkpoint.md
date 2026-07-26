# Checkpoint: 1Assessment Next-Level Round 1

**Date:** 2026-07-25
**Status:** 3 of 5 approved plan items shipped; showcase PUT owner-gated; #11 + #2 parked for fresh session

---

## Summary

Answered "anything new in One Assessment?" with a live sweep (Fly volume + both
mailboxes via Graph: nothing new since Jul 15, ball with Jochen), then ran a
36-idea multi-lens brainstorm ("bring the project to another level"), got the
plan approved, and executed its top solo items: the FIRST real end-to-end
NextDecade cycle (all three evidence channels), the contradiction publish
gate, and the adjudication click-through harness.

---

## What Was Done This Session

### Live-state sweep (question 1)
1. Fly volume read via `flyctl ssh`: 1 empty Jochen draft (Jul 15), feedback log unchanged since Jul 15 (all 7 entries resolved), newest data Jul 16.
2. Graph scan both mailboxes (app-only, hard allowlist): only surrounding-thread movement — Dirk sent "Meeting Minutes Karlsruhe 7/13-7/14 - Brisken 1Assessment (B1A)" to Jochen 07-17; Jochen's sole mail to Matthias was an empty sender-banner shell. Tool name in Dirk's subject: **1Assessment (B1A)**.

### Brainstorm (question 2, plan-mode)
1. 2 corpus explorers (DESIGN.md, PIPELINE-NOTES, portal, question bank, GTM docs) → 6-lens Workflow brainstorm (50 raw) → merge (30) → critic (+6) → 3-judge panel → **36 ranked ideas**; plan file + full detail preserved (paths below).
2. Top: #1 execute NextDecade run NOW (9.0) · #2 SAP release-to-capability atlas (9.0) · #3 domain-pack SDK (8.2) · #4 Jochen bus-factor kill (8.2). Kill list: freeze confidence-gate rework, chat/voice intake, Full tier until a real cycle completes.

### Plan item #1 — first real end-to-end cycle (NextDecade)
1. Document channel first real use: `cli extract` on 5 client docs → 241 quotable Belege; operator curation routed 60 to 7 Bereiche (script-verified 60/60; Corporate Finance honestly empty; 181 low-value rows unassigned).
2. Offline-Claude scoring: `assess --export-prompts` → 8 parallel uncontaminated subagents (one per Bereich, prompt file only) → `responses.json` (counts matched manifest 8/8) → `assess --responses`. 20 cells: 16 scored / 4 n/a, 5 review, 42 %, $0.
3. Verified: anti-fab 0 unsourced scored cells; **source_origin 14 fragebogen + 2 dokument** (document channel's first contributed cells); `cli verify` green (15/15 vs baseline); `cli followup` flagged the 4 deserts (WCM, Kapitalstruktur, Zinsraten, TIM) + minted 31 questions → `followup.md` is the ready next ask to NextDecade.
4. Scrubbed render (`run_assessment.py` extended with `--run-dir`/`--result-name`): 0 PII names/IDs, honest 2026-07-25 stamp, "aus den Unterlagen" panels, validate-html 0 hits. Run log + punch list: PIPELINE-NOTES **§X**.

### Plan item #14a — contradiction publish gate
1. `stage3_solution.premise_conflict()`: hoch cell + low-maturity-premise library gap → asserted Gap/Nutzen withheld, initiative renders as "Empfehlung · in Klärung" conditional card (benefit card + pipeline stage-3 row branches). Premise vocabulary verified against all 20 library entries (incl. "ineffizient", "Lücken").
2. `TcfCell.solution_conflict` field; enrich idempotent on RG change. 11 new tests; **164/164 pytest**, verify gate green without `--update`. DESIGN §15 row → PARTIAL (gate built; maturity-banded library still PLANNED).

### Plan item #10 — adjudication harness
1. `tools/adjudication_harness.py --emit` → `out/adjudication/index.html`: REIFEGRAD-ADJUDIKATION.md as a 7-click one-screen page (Kernfrage PROZESS/WERKZEUG/anders, Fälle 1-6 verbatim, Teil B, Teil C skala), export downloads `adjudication-rulings.json` (oa-adjudication/v1), export gated until complete + named.
2. `--compile` → `data/adjudication-record.json` + rubric-v3 draft (verbatim Hausregel + 6 anchors + Wissenslücken-Regel + Skala) + `data/corrections-seed.jsonl` (6 rows, Fall→cell mapping). 6/6 pytest; page JS driven by an 11-check Node DOM shim (CDP :9222 down; shim is the documented fallback).

---

## Key Decisions Made

### Run NextDecade without the promised bank/entity tables
- **Choice:** Execute with what landed (honest abstention covers the gap).
- **Rationale:** Zero completed live runs was the measured bottleneck; the tables have been "next week" since Jul 14.

### Fragebogen xlsx stays OUT of the document channel
- **Choice:** Only the 5 non-questionnaire docs entered evidence extraction.
- **Rationale:** The questionnaire IS the Fragebogen channel; double-feeding duplicates evidence across channels.

### Contradiction gate abstains rather than invents
- **Choice:** hoch+conflict withholds Gap/Nutzen (conditional card), no hoch-band text generated.
- **Rationale:** Library-only solutions is a hard constraint; the real fix is the maturity-banded library (PLANNED).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `…/treasury-assessment/inbox/nextdecade-20260724/` | created | uploads + evidence (manifest, curated curation.md, questionnaire.json) |
| `…/treasury-assessment/out/2026-07-24-nextdecade/` | created | result.json, scrubbed index.html, followup.json/.md, prompts/ (+partial/, responses.json) |
| `…/treasury-assessment/src/treasury_assessment/models.py` | edit | `TcfCell.solution_conflict` |
| `…/treasury-assessment/src/treasury_assessment/stage3_solution.py` | rewrite | premise vocabulary + `premise_conflict()` + conditional enrich |
| `…/treasury-assessment/src/treasury_assessment/render.py` | edit | conflict branches (benefit card + stage-3 rows) |
| `…/treasury-assessment/tests/test_solution_conflict.py` | created | 11 gate tests (negative cases = contract) |
| `…/treasury-assessment/tools/adjudication_harness.py` | created | emit + compile |
| `…/treasury-assessment/tests/test_adjudication_harness.py` | created | 6 harness tests |
| `…/treasury-assessment/out/adjudication/index.html` | created | the 7-click page for Jochen |
| `…/treasury-assessment/PIPELINE-NOTES.md` | edit | §X first-live-run log + punch list |
| `…/treasury-assessment/DESIGN.md` | edit | §15 rows: RG-conditional Stage 3 → PARTIAL; Adjudikation row + harness |
| `…/NextDecade/run_assessment.py` | edit | `--run-dir` / `--result-name` (was run-hardcoded) |

(`…` = `workspace/clients/Jochen Projekt/automations`; entire corpus gitignored, no PR applies.)

---

## Current Status

Tool healthy on one-assessment-demo.fly.dev (machine started, checks passing).
Local state ahead of live: the verified scrubbed 07-24 run is NOT yet the live
showcase — **PUT owner-gated** (classifier stop, consistent with the deploy
pattern). Jochen still owes: adjudication (now 7 clicks), curation, scale,
minutes review. No infrastructure.yaml / comms-log for this client (custom
Fly host, comms live in Brisken threads).

---

## Next Steps

1. On owner "publish the showcase": `cli showcase --slug nextdecade … --site out/2026-07-24-nextdecade/index.html` + live verify (exact command in the continuation prompt, chat 2026-07-25).
2. #11 Ergebnispräsentation pptx via the Brisken deckgen/native engine, validated vs CITTI golden (contract-grounded, ENTWURf-marked).
3. #2 SAP release-to-capability atlas v1 (public sources, per-claim URL, B4-clean; no Stage-3 wiring before Dirk/Jochen review).
4. Pulled forward #9 document evidence miner (241-quote hand-curation proved it the operator bottleneck); test bed = CITTI docs.
5. Get `out/adjudication/index.html` in front of Jochen (via Dirk) — it replaces the md-sheet homework.

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\.claude\plans\brainstorm-ideas-that-could-enchanted-candy.md` (approved plan, ranked 36)
- `…/treasury-assessment/PIPELINE-NOTES.md` §X (run log + punch list)
- `…/treasury-assessment/out/2026-07-24-nextdecade/followup.md` (the next NextDecade ask)

### Open Questions
- Owner go for the showcase PUT?
- Deck format blessing (Jochen/Dirk) once #11 renders — ENTWURF until then.
- Does "Nagarro SE" corpus case = the NextDecade engagement (title "for Nagarro")? Still unconfirmed with Jochen.

### Working Notes
- Full 36-idea board with judge notes: session task file `w802n9lrz` output (scratchpad tasks dir); plan file carries the curated version. Fold into corpus only on request (W1).
- Punch list (§X): evidence miner is the bottleneck; checklist xlsx rows too thin as single quotes (bundle per topic at extract); per-client registry would have prevented the run-hardcoded runner; channel-assignment rule needed for questionnaire-shaped files.
- Offline scoring pattern that worked: 8 subagents, prompt-file-only input, results persisted per-notification to `prompts/partial/` before assembly (survives context compression).
- CDP :9222 was down → Playwright MCP unusable; Node DOM shim (scratchpad `shim_adjudication.js` pattern) is the working page-JS verifier.

### Reference Materials
- Continuation prompt: verbatim in chat 2026-07-25 (paste into fresh session).
- `…/treasury-assessment/REIFEGRAD-ADJUDIKATION.md` (source of the harness content).

---

## How to Continue

Paste the continuation prompt from the 2026-07-25 chat into a fresh session
(covers items 0-3 with paths, constraints, and verification requirements), or
`/resume` and read this checkpoint + PIPELINE-NOTES §X.

---

## Strategic Feedback

### What Worked Well This Session
- Brainstorm grounded in explored fact (2 explorers before ideation) produced a #1 idea ("just run it") that no backlog item contained — and executing it same-session surfaced 5 punch-list findings no amount of planning would have.
- Persisting each scorer's JSON to disk at notification time made the 8-agent fan-out immune to context compression.

### Suggestions
- The B1 stop-gate keeps catching the same session-closing deferral reflex (5th register row in 4 days, all "caught by stop-b1-gate"). The gate contains it, but the generation-time reflex persists; consider a closing-sentence lint in the B1 primer that fires BEFORE the first draft of a final response, not after.

### System Health
- Autonomy: 2 human interventions (plan approval + one interrupt/continue) — near-autonomous for a session spanning live-ops read, multi-agent brainstorm, and three build items.
- Gates: B1:1 B2:8 B3:1 skipped:1 (the caught deferral).
