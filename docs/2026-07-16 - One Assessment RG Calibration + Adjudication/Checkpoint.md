# Checkpoint: One Assessment RG Calibration + Adjudication

**Date:** 2026-07-16
**Status:** Calibration thrust CLOSED with a pre-registered kill result; the fix now waits on Jochen's adjudication. 135/135 pytest, `cli verify` green, nothing deployed.

---

## Summary
Built the mined-RG-anchors thrust end to end (miner, injection, version stamps, rebuilt projection eval harness), measured it honestly, and followed the evidence to its real conclusion: prompt-side calibration is exhausted. Anchors v1 showed no lift and are now disabled by default; rubric v2 (process maturity) moved 2 of 84 scored rows in a fresh-scorer A/B (pre-registered kill fired); the residual gap to the CITTI golden is workshop knowledge the questionnaire never carried plus a rating convention that is inconsistent even inside the goldens. The calibration path forward is `REIFEGRAD-ADJUDIKATION.md` for Jochen.

---

## What Was Done This Session

### Thrust A: mined Reifegrad anchors (built, measured, parked)
1. `anchors.py` + `cli anchors`: deterministic miner over the 3 goldens' As-Is+RG columns (D+H), per (family, level, client) best-first candidates, name-stripped, personal-refs dropped, cross-level-deduped → `data/anchors-v1.json` (57 candidates, 8 families). Injection before `Regeln:`; `anchor_set_version` stamped; leave-one-client-out via `configure_anchors`.
2. Projection eval harness REBUILT (`projection.py` + `cli project`): the 2026-07-13 38%-baseline script was never committed; semantics reverse-verified against the surviving citti-eval.json (161 rows, 141/3/17 gold classes, wrong = NOT both_exact). Transports `--mock` / `--export-prompts`+`--responses` / `--real` (gated).
3. Real bug found + fixed on the way: `stage1_extract` exact-only section lookup silently dropped Corporate Finance + Governance evidence (headers differ cosmetically from taxonomy labels) → `_section_for` matches canonically, regression test added.
4. Offline A/B (leave-CITTI-out): NO lift (rg_exact 38 vs 36 of 141; 6 rows changed, 2 toward / 4 away).

### Diagnosis (read-only analysis workflow: 2 analysts + 3 design judges)
1. Rater consistency across the 3 goldens: pairwise exact 42-59%, Cohen's kappa -0.06 (CITTI-Ritter, below chance) / 0.10 / 0.22; 85-89% of disagreements on the gering/mittel boundary; P(mittel+|tool mentioned) CITTI 69% / Ritter 55% / STAEDTLER 48% (inverted convention). Cross-client absolute exemplars are unsound.
2. Error structure arm A: the one dominant cell = gold-mittel scored gering (23 of 36 wrong); 67 abstentions are 78% four whole-Funktion evidence deserts (IHB, Commodity, Treasury Investment, WCM) — a coverage problem, not calibration; forced conversion would mint ~0.49 unflagged-wrong per row (the gpt-4o pathology).
3. Naive rule fix falsified: "System genutzt → mindestens mittel" was ALREADY in the v1 rubric while the harsh cell happened.

### Calibration fix build (owner-decided: anchors off, Claude-first, adjudication sheet)
1. Anchors default-OFF (`configure_anchors` default disabled; set stays dormant on disk).
2. Rubric v2 (`_CALIBRATION_V2`, Prozessreife statt Werkzeug), `configure_calibration` (v1 selectable for paired arms), `calibration_version` + provenance stamped in result context, export manifests, projection `_meta`; `cli project --rubric v1|v2`.
3. Question-echo fail-closed guard (`stage2_fill._question_only_echo`): a source_quote living entirely in a probe QUESTION region → n/a + review; span-based and conservative ("…?: nein" quotes and the Mock echo pass). Wired into stage2_fill AND projection pre-diff.
4. Honest metric split in `projection.evaluate`: `rg_exact_scored_pct` / `coverage_pct` / `quote_question_echo` — "guess more" can no longer game rg_exact. This is the new DoD shape for calibration changes.
5. Pre-registered fresh-scorer A/B (arm A2 rubric v1 vs arm C rubric v2; each scored by an uncontaminated subagent seeing only PROMPTS.md, because the main loop had read gold labels during analysis): **identical toplines (43/141, 51% exact-on-scored, 60% coverage); rubric moved 2/84 scored rows; harsh cell 29 in BOTH arms → KILL fired.** Three independent Claude scorings all land at 51% exact-on-scored.
6. `REIFEGRAD-ADJUDIKATION.md` drafted for Jochen (German, plain): core question Prozess- vs Werkzeug-Lesart, 6 concrete cases from his own CITTI assessment (incl. the internally contradictory pair Zeile 126 vs 78), the knowledge-gap question (abstain + workshop follow-up vs conservative-low), the 25/50/75/100 scale item.

---

## Key Decisions Made

### Anchors v1 disabled by default (owner)
- **Choice:** `configure_anchors` defaults disabled; evals/future validated sets enable explicitly.
- **Rationale:** A/B showed 3 of 4 anchor-moved rows dragged correct gold-mittel to gering; kappa data shows cross-client absolute exemplars cannot converge.

### Claude is the reference scorer for the testing phase (owner)
- **Choice:** "adapt it to Claude — once we finish testing we can set it up with OpenAI gpt-4o." Offline fresh-scorer arms are THE instrument; no gpt-4o runs now.
- **Rationale:** extends the 2026-07-16 offline testing directive; gpt-4o setup becomes a later phase with its own validation.

### Fresh-subagent scorers for all eval arms (methodology)
- **Choice:** each arm's PROMPTS.md is scored by a fresh subagent with no other context.
- **Rationale:** the main loop was contaminated (analysis quoted gold labels); also removes sequential-arm bias. Scorer stability proven (51% exact-on-scored across three independent scorings).

### Stop prompt work; adjudication is the calibration path (pre-registered kill)
- **Choice:** no anchors-v2 mining, no contrastive pairs, no abstention-loosening until Jochen rules.
- **Rationale:** kill bar (harsh cell ≥18) fired at 29; the residual is evidence gaps + a convention that only the owner-consultant can standardize.

---

## Files Modified
All under `workspace/clients/Jochen Projekt/automations/treasury-assessment/` (gitignored — no commit/PR) unless noted.

| File | Action | Purpose |
|------|--------|---------|
| src/treasury_assessment/anchors.py | Created (then default-OFF) | miner/writer/loader + process-scoped anchor policy |
| src/treasury_assessment/projection.py | Created | rebuilt projection eval harness (chunks, transports, eval math, echo guard, metric split) |
| src/treasury_assessment/llm.py | Modified | anchors slot; `_CALIBRATION_V1/V2` + `configure_calibration` + provenance |
| src/treasury_assessment/stage2_fill.py | Modified | `_question_only_echo` fail-closed guard wired into `_cell_from_score` |
| src/treasury_assessment/stage1_extract.py | Modified | `_section_for` canonical header match (CF+Gov evidence recovered) |
| src/treasury_assessment/pipeline.py | Modified | `anchor_set_version` + `calibration_version` stamped into result context |
| src/treasury_assessment/cli.py | Modified | `anchors` + `project` subcommands (--rubric, --no-anchors, honest triple print); manifest stamps |
| data/anchors-v1.json | Created | dormant treatment (57 candidates) |
| tests/test_anchors.py, test_projection.py, test_calibration.py | Created/Modified | 34 new tests total; suite 135/135 |
| REIFEGRAD-ADJUDIKATION.md | Created | Jochen decision sheet (6 cases + knowledge-gap + scale) |
| out/2026-07-16-proj-{A,B,A2,C}/ | Created | frozen eval arms (prompts, responses, projection-eval.json) |
| DESIGN.md | Modified | Stage-2 calibration story; §15 rows (anchors default-OFF, rubric-v2 kill, adjudication OPEN) |
| PIPELINE-NOTES.md | Modified | §T (anchors + harness rebuild) + §U (diagnosis, kill, adjudication) |
| memory project_jochen_treasury_assessment.md | Modified (repo-external) | session facts + owner decisions |

---

## Current Status
Pipeline unchanged for clients except: anchors OFF by default, rubric v2 text active (verbatim-stamped, provenance "Adjudikation ausstehend"), question-echo guard live. 135/135 pytest; `cli verify` green with NO `--update` (Mock gate untouched); mock CLI E2E stamps both versions; render.py untouched so no NextDecade byte-regression applies; nothing deployed (site-host untouched). No `platform` section in `infrastructure.yaml` for this client (Fly-hosted FastAPI) — no ops-audit applies. No comms-log exists for Jochen Projekt (GTM comms run through Brisken's log).

---

## Next Steps
1. **Deliver `REIFEGRAD-ADJUDIKATION.md` to Jochen** (owner decides channel; likely via Dirk alongside the pending Quick-Satz/reifegrad_pct items). His rulings → rubric v3 verbatim + fold-back corrections seed.
2. **Coverage thrust** (the larger accuracy lever, independent of adjudication): the 4 abstention-desert Funktionen are an evidence problem — document channel + workshop channel exist; the follow-up-loop controller (DESIGN PLANNED) is the designed fix.
3. **First real document-bearing submission** through the full offline loop (extract → curate → export → fresh-scorer → responses → render) — still only mock-tested.
4. Parked until adjudication: anchors-v2 mining, contrastive pairs, `_real_floors`, gpt-4o setup (post-testing phase per owner).

---

## Context for Next Session

### Files to Read First
- workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md (§T + §U — the full calibration story)
- workspace/clients/Jochen Projekt/automations/treasury-assessment/DESIGN.md (Stage-2 calibration + §15 rows)
- workspace/clients/Jochen Projekt/automations/treasury-assessment/REIFEGRAD-ADJUDIKATION.md (the open deliverable)
- docs/2026-07-16 - One Assessment RG Calibration + Adjudication/CONTINUE-PROMPT.md

### Open Questions
- Jochen's adjudication answers (Prozess- vs Werkzeug-Lesart, 6 cases, knowledge-gap policy, 25/50/75/100 scale) — gates rubric v3 + any anchor revival.
- Prior owner sign-offs still pending: Quick-Satz curation, benefit voice, product ownership ("1Assessment" naming per Dirk's Protokoll round), Nagarro as first use case.

### Working Notes
- Frozen eval arms: out/2026-07-16-proj-A (my scoring, rubric v1, 38/141), -B (anchors v1, 36/141), -A2 (fresh scorer, rubric v1, 43/141), -C (fresh scorer, rubric v2, 43/141). Scored-row accuracy is 51% in all three independent scorings — treat that as the stable Claude baseline.
- Fresh-scorer protocol: export arm → spawn a subagent whose ONLY context is that arm's PROMPTS.md → it writes responses.json → `cli project --responses <dir> --out <dir> --rubric <v>`. The main loop must NOT score arms anymore (gold-label contamination).
- Do NOT run `cli verify --update` — the Mock baseline is untouched by all of this (prompt-blind by design).
- The 2026-07-13 "38%" gpt-4o baseline bought its exact count with 95 unflagged-wrong; comparisons must always use the honest triple (exact-on-scored / coverage / unflagged-wrong), now first-class in projection stats.
- Golden As-Is texts contain workshop knowledge absent from the questionnaire (e.g. Fragebogen "Systeme: keine" vs golden "Litreca Treasury, Excel") — any questionnaire-only eval is information-capped; this validates the three-source methodology and defines the coverage thrust.
- Whole tree gitignored → ripgrep `--no-ignore`; tests `uv run --directory <ta> --extra dev pytest -q`.

### Reference Materials
- Live app: https://one-assessment-demo.fly.dev (unchanged this session)
- Prior checkpoint (same day, first half): docs/2026-07-16 - One Assessment Document Channel + Gate + Manual-LLM/Checkpoint.md

---

## How to Continue
Paste `CONTINUE-PROMPT.md` (same folder) into a fresh chat. Recommended next thrust: the coverage/evidence work or the first real document-bearing submission; calibration itself is blocked on Jochen's adjudication sheet.

---

## Strategic Feedback

### What Worked Well This Session
- Pre-registered pass/kill bars turned a would-be judgment call into a clean stop signal: the rubric-v2 kill (harsh cell 29 vs bar 18) prevented an open-ended prompt-tuning loop on noise. The sequencing discipline (instrument → treatment → measurement) paid for itself twice in one day.

### Suggestions
- The adjudication sheet is the highest-leverage open item and costs Jochen ~10 minutes; bundling it with the already-pending reifegrad_pct decision in one Dirk-mediated ask would clear four owner-gated items at once.

### System Health
- Autonomy score: 0 human interventions this session (owner inputs were decisions I explicitly surfaced, not corrections). One self-detected friction logged: `strategic-gap` — anchors v1 went production-default-ON before its DoD was measured; fixed structurally same day (default-OFF + "treatments stay dormant until instrument-validated" now in DESIGN). Transferable principle: activating a treatment and measuring it are separate gates.
- The scorer-contamination problem (analyst output quoting gold labels poisons the main loop as scorer) is now solved procedurally (fresh subagents) but worth remembering as a standing rule for ANY eval this system runs on itself.
