# Checkpoint: One Assessment Document Channel + Gate + Manual-LLM

**Date:** 2026-07-16
**Status:** Three roadmap thrusts shipped + verified (101/101 pytest, `cli verify` green). Nothing deployed; all operator-side, gitignored.

---

## Summary
Drove the One Assessment treasury-assessment tool down its roadmap across three thrusts: the document channel (the last of Jochen's three required data sources now flows into scoring), the metrics release gate (a deterministic regression guard), and an offline/manual-LLM mode (for testing, scoring runs through this environment instead of gpt-4o). The whole `Jochen Projekt/` tree is gitignored, so no commit/PR/deploy applies; `site-host/` was untouched by all three.

---

## What Was Done This Session

### Document channel — source 2 (oa-evidence/v1)
1. `cli extract --inbox inbox/<id>` runs typed extractors (xlsx/csv rows + docx paragraphs) over the mirrored uploads, emitting verbatim anchored quotes with `area:null` into an immutable `manifest.json`, plus an operator `curation.md` and `00-facts.md`. Tables >200 rows yield a schema-summary only (never row-dumped).
2. The operator routes each quote to a Bereich in `curation.md` (the machine never auto-routes — that would fabricate area assignments; NextDecade's hand-verified AREA_MAP does not generalize).
3. `stage1_document` reconciles manifest + curation, re-verifies each source sha256 (staleness/tamper guard), and caps per area at one point (`DOCUMENT_AREA_CAP=4000`).
4. `stage2_fill` tests a third `hay_doc` PER discrete quote (kills cross-file splice, stronger than the workshop join); `source_origin="dokument"` (precedence fragebogen > dokument > workshop) renders as "Unterlagen" sheets under the Eingabe node, labelled "aus den Unterlagen".
5. `assess`/`reassess` auto-discover the sibling `evidence/`. 18 tests.

### Metrics release gate — `cli verify`
1. `verify_assert` runs the CITTI eval with `MockLLMClient` (deterministic, keyless, free) and asserts the 13 non-cost stats + `overall_pct` against the committed `data/expected-metrics.json`.
2. Hard-asserts `cells_without_source==0` (anti-fab invariant) in both modes; exits non-zero with a field diff on drift. `--update` regenerates after a legit golden/contract change (`_real_floors` preserved); `--real` = true LLM with structural-exact + owner floors.
3. DoD proven: DRIFT → exit 1, CLEAN → exit 0; a seeded `_STATE_RG` flip / review-floor change reddens the gate. The green-on-clean test makes the gate CI-enforced. 6 tests.

### Offline / manual-LLM mode — `cli assess` (owner directive)
1. `assess --export-prompts <dir>` builds the LightQuestionnaire with all merges, writes the exact per-area prompts (`stage2_fill.export_prompts` → `llm.build_area_prompt`, three-source evidence included) + a combined `PROMPTS.md` + `manifest.json`, and STOPS (no API call).
2. The operator runs `PROMPTS.md` through this environment (Claude) and saves the JSON as `responses.json`; `assess --responses <dir>` scores via `llm.FileLLMClient` and renders.
3. The OpenAI parse was factored into a shared `_scores_from_payload` (both transports parse identically). The anti-fab guard still runs on imported scores — a fabricated quote is forced to n/a regardless of which model produced it. 6 tests + a Mock CLI E2E.

---

## Key Decisions Made

### Document routing stays operator-curated
- **Choice:** `cli extract` is a two-pass extract → operator-routes → read loop; the machine emits `area:null`.
- **Rationale:** a general tool cannot honestly map an arbitrary client's rows/paragraphs to the 8 Funktionsgruppen; auto-routing would fabricate area assignments.

### Per-quote document trace (stronger than the workshop join)
- **Choice:** `hay_doc` is tested per discrete manifest quote, not against the joined area text.
- **Rationale:** an 18-char run must live inside one verbatim quote, so it can't straddle the " | " join of two documents (cross-file splice).

### Release gate uses deterministic Mock, not the real LLM
- **Choice:** the gate scores CITTI with `MockLLMClient`; `--real` is floor/invariant only.
- **Rationale:** gpt-4o drifts (temp-0 boundary noise); the Mock run is byte-deterministic, so it is the CI-safe teeth.

### Manual mode is a transport swap, not a guard change
- **Choice:** the LLM node is fulfilled from a file; every guard, schema, and render step is unchanged.
- **Rationale:** the anti-fabrication contract must hold regardless of which model scored; gpt-4o / `--mock` / server / `reassess` stay untouched.

---

## Files Modified
All under `workspace/clients/Jochen Projekt/` (gitignored — no commit/PR) unless noted.

| File | Action | Purpose |
|------|--------|---------|
| src/treasury_assessment/stage0_extract.py | Created | document extractors (xlsx/csv/docx) → manifest + curation.md + 00-facts.md |
| src/treasury_assessment/stage1_document.py | Created | read / route / verify-sha256 / cap / apply document evidence |
| src/treasury_assessment/verify.py | Modified | verify_assert + write_expected + EXPECTED_METRICS_PATH (release gate) |
| src/treasury_assessment/llm.py | Modified | dokument prompt block; _scores_from_payload (shared); build_area_prompt; RESPONSE_SCHEMA; FileLLMClient |
| src/treasury_assessment/stage2_fill.py | Modified | third haystack + per-quote trace + origin precedence; export_prompts |
| src/treasury_assessment/models.py | Modified | AreaSelection.dokument + .dokument_quotes; TcfCell.source_origin doc |
| src/treasury_assessment/render.py | Modified | "aus den Unterlagen" label + Unterlagen sheets + evidence= kwarg |
| src/treasury_assessment/cli.py | Modified | extract + verify subcommands; assess evidence auto-discovery + --export-prompts/--responses |
| data/expected-metrics.json | Created | release-gate baseline (deterministic Mock CITTI metrics) |
| pyproject.toml | Modified | +python-docx |
| tests/test_document.py | Created | 18 (document channel: origin, splice, sha256, extractors, render) |
| tests/test_verify_gate.py | Created | 6 (green-on-clean + seeded regressions + invariant break) |
| tests/test_manual_llm.py | Created | 6 (export blocks, FileLLMClient round-trip, fab-guard, missing-area) |
| tests/test_workshop.py | Modified | FabricatingLLM gains the dokument kwarg |
| DESIGN.md | Modified | §8a (document + offline-LLM modes) + §15 build-state rows |
| PIPELINE-NOTES.md | Modified | §Q (document channel) + §R (release gate) + §S (manual-LLM) |
| CONTINUE-PROMPT.md | Created | next-session bootstrap prompt |

---

## Current Status
101/101 pytest; `cli verify` (mock) green against `data/expected-metrics.json`. Live demo unchanged (`https://one-assessment-demo.fly.dev`); NextDecade render byte-identical (proven). No deploys this session; `site-host/` untouched, so nothing is pending a deploy. All three of Jochen's data sources (Fragebogen, Unterlagen, Workshop) now flow into scoring with honest per-source origin labels. No `platform` section in `infrastructure.yaml` for this client (Fly-hosted FastAPI, not Make/n8n) — no ops-audit applies.

---

## Next Steps
1. **Mined Reifegrad anchors** (thrust A, #1 accuracy lever; DoD: projection rg_exact above the 38% baseline). Now safely gated by `cli verify`. CITTI is the only complete input→golden pair.
2. **Fold-back learning loop** — append-only corrections store → versioned `anchors-vN.json` consumed by `llm.py`; the "the tool learns which questions it needs" half.
3. **First real document-bearing submission** through the full offline loop, to shake out the extract/curation ergonomics (only mock-tested so far).
4. **Editable As-Is workbench** (Dirk's open item 3, DESIGN §PLANNED).

---

## Context for Next Session

### Files to Read First
- workspace/clients/Jochen Projekt/automations/treasury-assessment/DESIGN.md (§8a + §15)
- workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md (§Q/§R/§S)
- workspace/clients/Jochen Projekt/automations/treasury-assessment/src/treasury_assessment/{stage1_document.py, stage2_fill.py, llm.py, verify.py}
- docs/2026-07-16 - One Assessment Document Channel + Gate + Manual-LLM/CONTINUE-PROMPT.md

### Open Questions
- Owner sign-offs (no code): question-bank curation (Quick-Satz), reifegrad_pct band mapping (25/50/75/100) + the "100" level, benefit voice, product ownership, Nagarro as first use case.
- Precedence label order fragebogen > dokument > workshop is a defensible default; only matters when a quote coincidentally traces to >1 source.

### Working Notes
- Whole tree gitignored → ripgrep `--no-ignore`; tests `uv run --directory <ta> --extra dev pytest -q`.
- The offline test loop: `inbox --pull <id>` → (`extract` + edit `curation.md`, if documents) → `assess --export-prompts <dir>` → paste `PROMPTS.md` into the Claude session → save the JSON as `responses.json` → `assess --responses <dir>` → (`publish` when ready).
- Release gate: run `cli verify` before shipping any scoring change; `cli verify --update` ONLY after a legit golden/contract change (regenerates the baseline).
- NextDecade byte-regression tool: `NextDecade/run_assessment.py --render-only --as-of <date>` re-renders from the saved result.json with no LLM run; diff vs the saved index.html to prove a render change is inert when a source is absent.
- Manual-LLM honest blind spots (covered by unit tests, not the gate): the anti-fab loosening bypass, origin-precedence, Stage-3 enrich.

### Reference Materials
- Live app: https://one-assessment-demo.fly.dev (portal), /demo (NextDecade showcase), /feedback-log (internal)
- Prior checkpoint: docs/2026-07-15 - One Assessment Workshop Channel + Feedback Resolution/Checkpoint.md

---

## How to Continue
Paste `CONTINUE-PROMPT.md` into a fresh chat, or run `/resume` (memory + this checkpoint reconstruct the context). Recommended next thrust: mined Reifegrad anchors — the accuracy lever Jochen flagged, now backed by the release gate. Confirm the thrust, plan it in plan mode, build + verify (pytest + `cli verify` + mock CLI E2E + NextDecade byte-regression where render changes), stop at the deploy gate.

---

## Strategic Feedback

### What Worked Well This Session
- Building the release gate immediately AFTER a new scoring source (documents) and BEFORE the accuracy work — correct sequencing, so mined anchors will land against a locked baseline. The document channel reused the workshop pattern almost 1:1, so the third source cost far less than the first.

### Suggestions
- The offline manual-LLM mode is proven only on synthetic submissions. The highest-value next move is one REAL document-bearing submission through the full loop (extract → curate → export → score-here → responses → render), to shake out the curation ergonomics before more features stack on top.

### System Health
- Autonomy score: 1 human intervention (I hand-rolled a checkpoint instead of invoking `/comd_checkpoint` on the first "checkpoint here"; user corrected). 2 B1 closing-deferral fires were caught by the stop-hook and self-corrected.
- The workflow tool's StructuredOutput schema was too strict for `claude-fable-5` (design agent hit the retry cap); the two free-text Understand agents succeeded and I salvaged their output from `journal.jsonl`. Keep workflow output schemas loose on smaller models.
- Three deploy-gated surfaces (site-host code, showcase volume, registry) plus render-via-republish remain easy to mis-sequence; none touched this session, but a one-page "what a change touches → what to redeploy" map would de-risk the next live change.
