# Checkpoint: Jochen Treasury Assessment Pipeline

**Date:** 2026-07-13
**Status:** Phase 1 projection delivered; build PAUSED pre-spec by owner. Pipeline scope re-set to Quick-tier end-to-end with website output.

---

## Summary
Ran the first end-to-end projection of Jochen Stiebe's SAP Treasury Assessment automation: CITTI questionnaire → 161-row TCF matrix via LLM → contract-conformant workbook + full Ergebnispräsentation deck (heat-maps recolored from generated maturity/priority), plus a Nagarro shell. Extracted Jochen's output structure into a machine-readable blueprint, then folded in his live review of our deck and six new process transcripts to define the next build.

---

## What Was Done This Session
### Grounding the output structure
1. Extracted `Reference/tcf-output-contract.json` mechanically from the 3 golden TCF workbooks + CITTI deck: headers/enums/OM roster, per-client taxonomies, heat-map grid, color encoding (tile fill = Reifegrad, status ball = Priorität), Ritter result-reference (Anhang table schema, 93/95% self-test), Nagarro kickoff process model.
2. Built a conformance validator (`validate_contract.py`) — passes all 3 goldens, rejects a mutated workbook (negative test).

### Projection run (CITTI as eval proxy)
3. Questionnaire ingest + per-Funktion LLM fill (gpt-4o, strict json_schema, confidence routing, cost ceiling): 161 rows, 20 calls, $0.63, zero fabricated cells.
4. Eval vs golden: Reifegrad 38% exact / 84% adjacent, Prio 51% / 76%, flag precision 92% / recall ~11% (confidence miscalibrated). Systematic one-notch-harsh (gen=gering vs gold=mittel).
5. Generated 24 OM-dimension rows ($0.05) for the OM overview slide.

### Rendering Jochen's actual final product (pptx)
6. Rendered a contract-conformant workbook (writable cells only, Agent-Review sheet, gate PASS).
7. Rendered the full Ergebnispräsentation deck: slide 9 OM overview (24/24 borders=Reifegrad, 24/24 balls=Prio), slides 10-11 heat maps (137/137 tiles + 137/137 balls), legend byte-identical to Jochen's, ENTWURF markers on regenerated slides only. Reverted the overflowing detail-text (kept Jochen's originals).
8. Nagarro deliverables: stage-1 gap report (504/504 items open, zero evidence) + TCF shell workbook (his structure, zero CITTI residue, gate PASS).

### New reference audios → pipeline direction
9. Re-transcribed truncated/missing audio; read 6 new transcripts (NR3-7 + Zusammenfassung). NR4 = Jochen reviewing OUR deck live.
10. Captured learnings in `automations/treasury-assessment/PIPELINE-NOTES.md` (evidence-backed): encoding confirmed by Jochen; Reifegrad calibration is #1 weakness; maturity wants a 25/50/75/100 percentage; detail = per-initiative Kurztext (Benefits); Ist = mechanical fill + solution library; two tiers Quick/Full; tool must be Brisken-independent.

### Handoff
11. Wrote a self-contained continuation prompt for the next chat: build the SIMPLIFIED Quick-tier pipeline end-to-end (light questionnaire → As-Is fill → gap/recommendation from solution library → assessment) with results rendered to a WEBSITE.

---

## Key Decisions Made
### Output structure is grounded in a file, not agent judgment
- **Choice:** All structure (headers, enums, OM roster, encoding, deck grid) lives in `tcf-output-contract.json`, extracted mechanically and self-tested against the goldens; renderer + gate load it.
- **Rationale:** Owner directive — generated output must be identical copies of Jochen's structure, not "close enough."

### Final product is the pptx Ergebnispräsentation (verified by content)
- **Choice:** Deliverable = the deck, not just the matrix xlsx. Verified by reading each golden deck's content (STAEDTLER "Einfüger" IS its result deck; Ritter's 134-slide deck renders the full matrix as Anhang).
- **Rationale:** Owner: "look through the true content of the files not just name."

### Maturity ball = Priorität, box border/fill = Reifegrad
- **Choice / Rationale:** Confirmed by Jochen verbatim (NR4): "Umrandung = Reifegrad, Punkte = Priorität."

### Next build = Quick-tier pipeline → website (not pptx)
- **Choice:** Simplified end-to-end: light questionnaire → mechanical As-Is fill → process eval/gap/recommendation → assessment, results on a website.
- **Rationale:** Owner's latest direction after the projection + transcripts.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/Jochen Projekt/Reference/tcf-output-contract.json | Created | Machine-readable output-structure blueprint (202 KB) |
| .../automations/treasury-assessment/tools/build_contract.py | Created | Regenerates the contract from goldens |
| .../automations/treasury-assessment/tools/validate_contract.py | Created | Conformance gate (passes goldens, rejects drift) |
| .../automations/treasury-assessment/PIPELINE-NOTES.md | Created | Transcript-derived pipeline spec + Jochen's review |
| .../out/2026-07-13-projection/CITTI_Ergebnispraesentation_generated_2026-07-13.pptx | Created | Generated deck (final product) |
| .../out/2026-07-13-projection/CITTI_TCF_generated_2026-07-13.xlsx | Created | Generated matrix workbook (gate PASS) |
| .../out/2026-07-13-projection/{citti-matrix-fill-full,citti-om-fill,citti-eval}.json | Created | Run data + eval metrics |
| .../out/2026-07-13-projection/ConVista..._Nagarro SE_Entwurf-Shell...xlsx + nagarro-stage1-gap-report.md | Created | Nagarro shell + gap report |
| Methodology briefings/{Jochen Präsentation,New Recording 2}.transcript.txt | Re-transcribed | Fixed truncation/missing |
| memory/project_jochen_treasury_assessment.md | Created+Updated | Project memory incl. NR4 review + process model |
| memory/MEMORY.md | Modified | Index line for the project |

_All Jochen-folder paths are gitignored (line 147) — work product, not tracked._

---

## Current Status
Projection complete and validated end-to-end: matrix fill works, fabrication control holds, structure conformance is enforced, and the deck renders in Jochen's exact format with his confirmed encoding. Jochen reviewed it live and confirmed the approach; his corrections are captured. The build of the actual tool is PAUSED pre-spec by the owner. Scope for the next session is re-set: Quick-tier simplified pipeline with website output. Nagarro is the intended first real client but currently has zero corpus evidence (blank questionnaire).

---

## Next Steps
1. Start a fresh session with the handoff prompt (below): build the Quick-tier pipeline — light questionnaire → As-Is fill → gap/recommendation → assessment → website.
2. First action there: propose + confirm the precise typed structure for all 4 stages before coding.
3. Reifegrad calibration (Jochen's #1 fix): few-shot maturity anchors mined from the 3 goldens.
4. Build the per-Bereich solution library from the goldens (grounds Gap/Empfehlung).
5. Add `reifegrad_pct` (25/50/75/100) — confirm exact enum→pct mapping with Jochen.

---

## Context for Next Session
### Files to Read First
- workspace/clients/Jochen Projekt/Reference/tcf-output-contract.json
- workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md
- ~/.claude/plans/task-notification-task-id-b9nkyzmeu-tas-virtual-bird.md
- workspace/clients/Jochen Projekt/Reference/*.transcript.txt (esp. New Recording 4, 5, 6)

### Open Questions
- Exact `reifegrad_pct` mapping (does hoch=75 or 100? is there a distinct top band?) — confirm with Jochen.
- Website surface: gated `platform/public/docs/{client}/` doc-site vs self-contained HTML deliverable — decide with owner (tool must stay Brisken-neutral).
- Which client provides the first real Quick-tier input (Nagarro has none yet).

### Working Notes
- LLM key: vault "OpenAI Brisken" (`uv run ~/vault.py get "OpenAI Brisken"`). Reuse pattern: brisken expense-reconciliation `llm/client.py`.
- CITTI is the ONLY complete input→golden pair (usable for eval). Nagarro/STAEDTLER questionnaires: Nagarro blank, STAEDTLER partial.
- Heat-map ball geometry: text tiles carry the ball top-right (+1.14,-0.10); textless band tiles centered (+0.51,+0.10). Slide 9 OM overview: border=Reifegrad, ball=Prio, 6×4 grid, balls in group "Gruppieren 24".
- Detail-narrative auto-fill overflowed the fixed boxes → reverted. Correct approach = summarized per-initiative Kurztext, not concatenated As-Is.
- pptx/xlsx writes need Excel/PowerPoint closed first (COM lock → PermissionError). Visual verification = export slides to PNG via PowerPoint COM (`Presentations.Open(path,ReadOnly)` then `Slide.Export`) and view.

### Reference Materials
- Continuation prompt: in the conversation immediately before this checkpoint (paste-ready block).
- oneproposal-handoff-2026-07-10.txt (repair-then-validate discipline, cost ceilings).

---

## How to Continue
Open a fresh chat, paste the handoff prompt (last assistant turn before this checkpoint). It front-loads the contract + PIPELINE-NOTES and specifies the 4-stage Quick-tier pipeline with website output. The new session should propose and confirm the precise typed structure first, then scaffold from `workspace/templates/client-automation` and build. Do NOT re-run the CITTI projection (done); reuse its outputs for eval.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding every structural claim in a self-tested contract file (extract → assert vs goldens → negative test) made "identical to Jochen's" checkable, not asserted.
- Reading the golden decks by content (not filename) resolved which artifact is the real deliverable and caught the STAEDTLER "Einfüger" naming trap.

### Suggestions
- For rendered/visual deliverables (pptx, HTML, images), send a rendered preview proactively when declaring done — the user caught 4 visual defects across rounds that a self-exported PNG check would have surfaced first.

### System Health
- **Gap: no visual-verification gate for rendered deliverables.** The done-verifier agent exists for web deploys; there is no analogue for pptx/rendered output. This session's friction was entirely "programmatic checks passed, visual result wrong." Candidate structural fix: a render-and-view step (export → read the image) folded into the B2 done-gate for any generated pptx/image/HTML deliverable. Autonomy score elevated (4) — worth a /system-dev pass.
- Autonomy score: 4 human interventions this session (elevated — run /system-dev to close the visual-verification gap).
